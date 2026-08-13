"""Sensor entities created on behalf of sandboxed integrations.

Each one is an ordinary Home Assistant entity: it has a unique_id, so it gets an
entity-registry row; it belongs to this bridge's config entry; and it is attached
to a device named after the sandboxed integration that produced it. That is the
whole difference between this and posting to /api/states.

``RestoreEntity`` is what closes the restart gap. On startup the bridge recreates
every entity in its roster, and each one restores the last state Home Assistant
saw — so a restart no longer erases everything the supervisor published, even
before the supervisor next runs.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ATTR_ATTRIBUTES,
    ATTR_ENTITY_ID,
    ATTR_INTEGRATION,
    ATTR_KEY,
    ATTR_STATE,
    DOMAIN,
    SIGNAL_NEW_ENTITY,
)

# Attributes Home Assistant derives itself; passing them through as extra state
# attributes would duplicate them and, for friendly_name, fight the device naming.
_RESERVED = {"friendly_name", "unit_of_measurement", "device_class", "state_class", "icon"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Recreate stored entities, then listen for newly published ones."""
    data = hass.data[DOMAIN][entry.entry_id]

    def build(definition: dict[str, Any]) -> SandboxedSensor:
        entity = SandboxedSensor(definition)
        data.live[entity.unique_id] = entity
        return entity

    restored = [build(definition) for definition in data.roster.values()]
    if restored:
        async_add_entities(restored)

    @callback
    def handle_new(definition: dict[str, Any]) -> None:
        unique_id = f"{definition[ATTR_INTEGRATION]}:{definition[ATTR_KEY]}"
        if (existing := data.live.get(unique_id)) is not None:
            existing.apply(definition)
            return
        async_add_entities([build(definition)])

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_ENTITY, handle_new))


class SandboxedSensor(RestoreEntity, SensorEntity):
    """A sensor whose value is produced by an integration running outside HA."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, definition: dict[str, Any]) -> None:
        self._integration: str = definition[ATTR_INTEGRATION]
        self._key: str = definition[ATTR_KEY]
        self._attr_unique_id = f"{self._integration}:{self._key}"

        # Preserve the entity_id the integration would have produced inside HA, so
        # dashboards and automations do not have to change when an integration is
        # moved into the sandbox.
        self.entity_id = definition[ATTR_ENTITY_ID]

        # One device per sandboxed integration: it groups the entities in the UI
        # and makes the sandboxing visible to the user rather than invisible.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._integration)},
            name=self._integration,
            manufacturer="Sandboxed integration",
            model="Runs outside Home Assistant, under manifest enforcement",
        )

        self._apply_locally(definition)

    # -- state ----------------------------------------------------------
    def _apply_locally(self, definition: dict[str, Any]) -> None:
        attributes: dict[str, Any] = definition.get(ATTR_ATTRIBUTES) or {}
        self._attr_native_value = definition.get(ATTR_STATE)
        self._attr_native_unit_of_measurement = attributes.get("unit_of_measurement")
        self._attr_device_class = attributes.get("device_class")
        self._attr_state_class = attributes.get("state_class")
        self._attr_icon = attributes.get("icon")
        # HA composes the displayed name as "<device> <entity name>".
        self._attr_name = attributes.get("friendly_name") or self._key
        self._attr_extra_state_attributes = {
            key: value for key, value in attributes.items() if key not in _RESERVED
        }

    @callback
    def apply(self, definition: dict[str, Any]) -> None:
        """Take a new value from the supervisor and write it to the state machine."""
        self._apply_locally(definition)
        if self.hass is not None:
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore the last known value, so a restart does not blank the entity."""
        await super().async_added_to_hass()
        if self._attr_native_value is not None:
            return
        if (last := await self.async_get_last_state()) is not None:
            self._attr_native_value = last.state
