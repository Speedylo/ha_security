"""Sensors published by confined integrations."""

from __future__ import annotations

import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.util import dt as dt_util

from .entity import BridgedEntity, setup_platform


def _value(state: Any, device_class: str | None) -> Any:
    """The native value for a published state.

    None while the integration has none: passed through as the string "unknown", a sensor with a
    device class, state class and unit is refused by Home Assistant (F66). A timestamp sensor needs
    a `datetime` and a date sensor a `date`, not the string the sandbox published (F67); a state
    that does not parse as one gives no value. Both found by bridge step 5's real-house runs.
    """
    if state in (None, "unknown", "unavailable"):
        return None
    if device_class == "timestamp":
        try:
            moment = datetime.datetime.fromisoformat(str(state))
        except ValueError:
            return None
        return moment if moment.tzinfo else moment.replace(tzinfo=dt_util.get_default_time_zone())
    if device_class == "date":
        try:
            return datetime.date.fromisoformat(str(state))
        except ValueError:
            return None
    return state


class BridgedSensor(BridgedEntity, SensorEntity):

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        # No value while the integration has none. Passed through as the string "unknown", a
        # sensor with a device class, state class and unit is refused by Home Assistant, and the
        # publish failed in (A) (F66, found by bridge step 5's first real-house run).
        self._attr_native_value = _value(state, attributes.get("device_class"))
        self._attr_native_unit_of_measurement = attributes.get("unit_of_measurement")
        self._attr_state_class = attributes.get("state_class")
        # An enum sensor must say what its states can be, or Home Assistant refuses the state.
        self._attr_options = attributes.get("options")

    def _restorable_empty(self) -> bool:
        return self._attr_native_value is None

    def _restore(self, state: str) -> None:
        self._attr_native_value = _value(state, self._attr_device_class)


async_setup_entry = setup_platform("sensor", BridgedSensor)
