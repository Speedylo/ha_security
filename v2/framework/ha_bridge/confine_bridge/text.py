"""Text inputs published by confined integrations (bridge step 1, 2026-10-25).

The limits and the mode come from the attributes the integration's own instance gave the entity,
so (A) draws the same input. Setting a value sends it to the integration, as a switch's command
does; the new value arrives back as a publish.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.text import TextEntity, TextMode

from .entity import BridgedEntity, setup_platform


class BridgedText(BridgedEntity, TextEntity):

    _described = frozenset({"min", "max", "pattern", "mode"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_native_value = None if state in (None, "unknown", "unavailable") else str(state)
        self._attr_native_min = int(attributes.get("min", 0))
        self._attr_native_max = int(attributes.get("max", 255))
        self._attr_pattern = attributes.get("pattern")
        self._attr_mode = TextMode(attributes.get("mode") or TextMode.TEXT)

    def _restorable_empty(self) -> bool:
        return self._attr_native_value is None

    def _restore(self, state: str) -> None:
        self._attr_native_value = state

    async def async_set_value(self, value: str) -> None:
        await self._data.command(self._integration, self._published_id, "set_value",
                                 {"value": value})


async_setup_entry = setup_platform("text", BridgedText)
