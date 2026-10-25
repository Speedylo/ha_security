"""Selects published by confined integrations (bridge step 1, 2026-10-25).

The options come from the integration's own instance. Choosing one sends it to the integration;
the choice it made arrives back as a publish.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity

from .entity import BridgedEntity, setup_platform


class BridgedSelect(BridgedEntity, SelectEntity):

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_options = list(attributes.get("options") or [])
        self._attr_current_option = (None if state in (None, "unknown", "unavailable")
                                     else str(state))

    def _restorable_empty(self) -> bool:
        return self._attr_current_option is None

    def _restore(self, state: str) -> None:
        self._attr_current_option = state

    async def async_select_option(self, option: str) -> None:
        await self._data.command(self._integration, self._published_id, "select_option",
                                 {"option": option})


async_setup_entry = setup_platform("select", BridgedSelect)
