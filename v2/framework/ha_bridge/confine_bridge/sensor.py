"""Sensors published by confined integrations."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity

from .entity import BridgedEntity, setup_platform


class BridgedSensor(BridgedEntity, SensorEntity):

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_native_value = state
        self._attr_native_unit_of_measurement = attributes.get("unit_of_measurement")
        self._attr_state_class = attributes.get("state_class")
        # An enum sensor must say what its states can be, or Home Assistant refuses the state.
        self._attr_options = attributes.get("options")

    def _restorable_empty(self) -> bool:
        return self._attr_native_value is None

    def _restore(self, state: str) -> None:
        self._attr_native_value = state


async_setup_entry = setup_platform("sensor", BridgedSensor)
