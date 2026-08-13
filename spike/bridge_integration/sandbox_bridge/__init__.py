"""Bridge that gives sandboxed integrations first-class entities in Home Assistant.

The framework runs untrusted HACS integrations outside Home Assistant's process
and publishes their results in. Publishing over the REST states API works, but it
produces *states without identity*: no entity-registry row, no config entry, no
device, and nothing that survives a restart.

This integration closes that gap. It is deliberately tiny and does exactly one
thing: it owns a config entry and a device per sandboxed integration, and creates
real registry-backed entities on their behalf. All the untrusted code still runs
outside Home Assistant, behind the supervisor's manifest checks — nothing here
loads, imports, or executes any part of a sandboxed integration.

Trust boundary: this component is **trusted** and belongs to the framework, not to
any integration it publishes for. It accepts state updates through a service call
that only the supervisor's token can make, and it never evaluates anything it is
given — a state is stored as a string and attributes as plain data.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .const import (
    ATTR_ATTRIBUTES,
    ATTR_ENTITY_ID,
    ATTR_INTEGRATION,
    ATTR_KEY,
    ATTR_STATE,
    DOMAIN,
    SERVICE_PUBLISH,
    SERVICE_REMOVE,
    SIGNAL_NEW_ENTITY,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

PUBLISH_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_INTEGRATION): cv.string,
        vol.Required(ATTR_KEY): cv.string,
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_STATE): vol.Any(cv.string, int, float, None),
        vol.Optional(ATTR_ATTRIBUTES, default=dict): dict,
    }
)

REMOVE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_INTEGRATION): cv.string,
        vol.Required(ATTR_KEY): cv.string,
    }
)


class BridgeData:
    """Roster of every entity the supervisor has published, and how to reach them."""

    def __init__(self, store: Store) -> None:
        self._store = store
        # unique_id -> definition needed to rebuild the entity after a restart
        self.roster: dict[str, dict[str, Any]] = {}
        # unique_id -> live entity object, for updates that need no new entity
        self.live: dict[str, Any] = {}

    async def load(self) -> None:
        self.roster = await self._store.async_load() or {}

    async def save(self) -> None:
        await self._store.async_save(self.roster)

    @staticmethod
    def unique_id(integration: str, key: str) -> str:
        return f"{integration}:{key}"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the bridge and restore every entity it published before."""
    data = BridgeData(Store(hass, STORAGE_VERSION, STORAGE_KEY))
    await data.load()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = data
    entry.runtime_data = data

    _LOGGER.info("sandbox bridge: restoring %d entities from storage", len(data.roster))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_publish(call: ServiceCall) -> None:
        """Create or update one entity on behalf of a sandboxed integration."""
        integration = call.data[ATTR_INTEGRATION]
        key = call.data[ATTR_KEY]
        unique_id = BridgeData.unique_id(integration, key)

        definition = {
            ATTR_INTEGRATION: integration,
            ATTR_KEY: key,
            ATTR_ENTITY_ID: call.data[ATTR_ENTITY_ID],
            ATTR_STATE: call.data[ATTR_STATE],
            ATTR_ATTRIBUTES: call.data[ATTR_ATTRIBUTES],
        }

        known = unique_id in data.roster
        data.roster[unique_id] = definition
        await data.save()

        if (entity := data.live.get(unique_id)) is not None:
            entity.apply(definition)
        elif not known or unique_id not in data.live:
            # Either brand new, or restored from storage but not yet instantiated.
            async_dispatcher_send(hass, SIGNAL_NEW_ENTITY, definition)

    async def handle_remove(call: ServiceCall) -> None:
        """Forget an entity the sandboxed integration no longer publishes."""
        unique_id = BridgeData.unique_id(call.data[ATTR_INTEGRATION], call.data[ATTR_KEY])
        data.roster.pop(unique_id, None)
        await data.save()
        if (entity := data.live.pop(unique_id, None)) is not None:
            await entity.async_remove(force_remove=True)

    hass.services.async_register(DOMAIN, SERVICE_PUBLISH, handle_publish, schema=PUBLISH_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_REMOVE, handle_remove, schema=REMOVE_SCHEMA)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the bridge."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.services.async_remove(DOMAIN, SERVICE_PUBLISH)
        hass.services.async_remove(DOMAIN, SERVICE_REMOVE)
    return unloaded


@callback
def async_get_data(hass: HomeAssistant, entry: ConfigEntry) -> BridgeData:
    return hass.data[DOMAIN][entry.entry_id]
