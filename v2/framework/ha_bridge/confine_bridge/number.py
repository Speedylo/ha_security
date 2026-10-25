"""Numbers published by confined integrations (bridge step 1, 2026-10-25).

The range, the step, the mode and the unit come from the integration's own instance, so (A) draws
the same slider or box. Setting a value sends it to the integration; the value it settled on
arrives back as a publish.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode

from .entity import BridgedEntity, setup_platform


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class BridgedNumber(BridgedEntity, NumberEntity):

    _described = frozenset({"min", "max", "step", "mode"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_native_value = _number(state)
        self._attr_native_min_value = _number(attributes.get("min")) or 0.0
        self._attr_native_max_value = _number(attributes.get("max"))
        if self._attr_native_max_value is None:
            self._attr_native_max_value = 100.0
        self._attr_native_step = _number(attributes.get("step")) or 1.0
        self._attr_mode = NumberMode(attributes.get("mode") or NumberMode.AUTO)
        self._attr_native_unit_of_measurement = attributes.get("unit_of_measurement")

    def _restorable_empty(self) -> bool:
        return self._attr_native_value is None

    def _restore(self, state: str) -> None:
        self._attr_native_value = _number(state)

    async def async_set_native_value(self, value: float) -> None:
        await self._data.command(self._integration, self._published_id, "set_value",
                                 {"value": value})


async_setup_entry = setup_platform("number", BridgedNumber)
