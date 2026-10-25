"""Sensors published by confined integrations."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity

from .entity import BridgedEntity, setup_platform


class BridgedSensor(BridgedEntity, SensorEntity):

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        # No value while the integration has none. Passed through as the string "unknown", a
        # sensor with a device class, state class and unit is refused by Home Assistant, and the
        # publish failed in (A) (F66, found by bridge step 5's first real-house run).
        self._attr_native_value = None if state in (None, "unknown", "unavailable") else state
        self._attr_native_unit_of_measurement = attributes.get("unit_of_measurement")
        self._attr_state_class = attributes.get("state_class")
        # An enum sensor must say what its states can be, or Home Assistant refuses the state.
        self._attr_options = attributes.get("options")

    def _restorable_empty(self) -> bool:
        return self._attr_native_value is None

    def _restore(self, state: str) -> None:
        if state not in ("unknown", "unavailable"):
            self._attr_native_value = state


async_setup_entry = setup_platform("sensor", BridgedSensor)
