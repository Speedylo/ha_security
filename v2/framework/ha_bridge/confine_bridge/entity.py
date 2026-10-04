"""The entity every published state becomes, whatever its domain.

Each one is an ordinary Home Assistant entity: it has a `unique_id`, so it gets an entity-registry
row; it belongs to the bridge's config entry; and it hangs off a device named after the confined
integration that produced it, which makes the confinement visible in the UI rather than hidden.
`RestoreEntity` closes the restart gap: on start the bridge rebuilds every entity in its roster,
and each restores the last state Home Assistant saw, before its sandbox has run again.
"""

from __future__ import annotations

from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, SIGNAL_NEW_ENTITY

#: Attributes Home Assistant derives from the entity's own properties. Passing them through as
#: extra attributes as well would duplicate them, and `friendly_name` would fight the device name.
RESERVED = {"friendly_name", "unit_of_measurement", "device_class", "state_class", "icon",
            "options"}


class BridgedEntity(RestoreEntity):
    """Common to every domain: identity, device, and taking a new definition."""

    _attr_should_poll = False

    def __init__(self, definition: dict[str, Any], data) -> None:
        self._data = data
        self._integration: str = definition["integration"]
        self._published_id: str = definition["entity_id"]
        self._attr_unique_id = f"{self._integration}:{self._published_id}"
        # Ask for the id the integration would have had inside Home Assistant, so dashboards and
        # automations need not change when an integration moves into a sandbox. The registry may
        # still assign another if that one is taken; the publish command reports which.
        self.entity_id = self._published_id
        # The name as the integration's own registry has it. Home Assistant 2026.8 builds a
        # friendly name from the registry as "<device name> <entity name>", whatever the state
        # attribute says, so the device must carry the integration's device name and the entity
        # its own. With only the composed name, (A) showed "thermal_comfort living room Dew
        # point" where the integration unconfined shows "living room Dew point" (§7.37). Without
        # naming from the sandbox, one device per integration, named after it, is the fallback.
        naming = definition.get("naming") or {}
        device = naming.get("device")
        self._own_name = naming.get("name") if device else None
        self._attr_has_entity_name = bool(device) and bool(naming.get("has_entity_name", True))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._integration}:{device}" if device
                          else self._integration)},
            name=device or self._integration,
            manufacturer=f"Confined integration: {self._integration}",
            model="Runs in a sandbox, under its manifest")
        self._take(definition)

    def _take(self, definition: dict[str, Any]) -> None:
        attributes: dict[str, Any] = definition.get("attributes") or {}
        self._attr_device_class = attributes.get("device_class")
        self._attr_icon = attributes.get("icon")
        self._attr_name = (self._own_name if self._own_name is not None
                           else attributes.get("friendly_name")
                           or self._published_id.partition(".")[2])
        self._attr_extra_state_attributes = {k: v for k, v in attributes.items()
                                             if k not in RESERVED}
        self._take_state(definition.get("state"), attributes)

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        raise NotImplementedError

    @callback
    def apply(self, definition: dict[str, Any]) -> None:
        self._take(definition)
        if self.hass is not None:
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._data.live[self.unique_id] = self
        if (waiting := self._data.waiting.get(self.unique_id)) and not waiting.done():
            waiting.set_result(self.entity_id)
        if self._restorable_empty() and (last := await self.async_get_last_state()):
            self._restore(last.state)

    async def async_will_remove_from_hass(self) -> None:
        self._data.live.pop(self.unique_id, None)

    def _restorable_empty(self) -> bool:
        raise NotImplementedError

    def _restore(self, state: str) -> None:
        raise NotImplementedError


def setup_platform(domain: str, cls: Callable[[dict, Any], BridgedEntity]):
    """The platform-level `async_setup_entry` for one domain."""

    async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                                async_add_entities: AddEntitiesCallback) -> None:
        data = hass.data[DOMAIN]
        restored = [cls(definition, data) for definition in data.roster.values()
                    if definition["entity_id"].partition(".")[0] == domain]
        if restored:
            async_add_entities(restored)

        @callback
        def new(definition: dict[str, Any]) -> None:
            unique_id = f"{definition['integration']}:{definition['entity_id']}"
            if (existing := data.live.get(unique_id)) is not None:
                existing.apply(definition)
                return
            async_add_entities([cls(definition, data)])

        entry.async_on_unload(
            async_dispatcher_connect(hass, SIGNAL_NEW_ENTITY.format(domain), new))

    return async_setup_entry
