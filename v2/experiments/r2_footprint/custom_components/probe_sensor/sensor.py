"""Sensor platform for the R2 probe.

This is the path that matters: async_add_entities (63% of integrations) publishing a
CoordinatorEntity-backed SensorEntity. If this works against a minimal Home Assistant, the
helper layer works, and R2's premise holds.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ProbeConfigEntry, ProbeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ProbeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the probe sensor."""
    async_add_entities([ProbeSensor(config_entry.runtime_data)])


class ProbeSensor(CoordinatorEntity[ProbeCoordinator], SensorEntity):
    """A sensor reporting the coordinator's tick count."""

    _attr_has_entity_name = True
    _attr_name = "Ticks"
    _attr_unique_id = "probe_sensor_ticks"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the current tick count."""
        return self.coordinator.data["ticks"]
