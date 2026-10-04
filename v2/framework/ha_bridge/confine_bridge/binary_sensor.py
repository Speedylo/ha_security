"""Binary sensors published by confined integrations."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import BridgedEntity, setup_platform


class BridgedBinarySensor(BridgedEntity, BinarySensorEntity):

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_is_on = None if state in (None, "unknown", "unavailable") else state == "on"

    def _restorable_empty(self) -> bool:
        return self._attr_is_on is None

    def _restore(self, state: str) -> None:
        self._attr_is_on = state == "on"


async_setup_entry = setup_platform("binary_sensor", BridgedBinarySensor)
