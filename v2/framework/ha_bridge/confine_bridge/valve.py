"""Valves published by confined integrations (bridge batch B2, 2026-10-31).

The state (open, closed, opening, closing), the position and the supported features come from the
integration's own instance. (A) turns opening or closing a valve that reports its position into a
position of 100 or 0, and works out `toggle`; what reaches the integration through the mediator is
an open, close or stop, or a position (`notes/bridge_kinds_b2_prediction_20261031.md`).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.valve import ValveEntity, ValveEntityFeature

from .entity import BridgedEntity, setup_platform


class BridgedValve(BridgedEntity, ValveEntity):

    _described = frozenset({"current_position", "supported_features"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_is_opening = state == "opening"
        self._attr_is_closing = state == "closing"
        self._attr_is_closed = (None if state not in ("open", "closed", "opening", "closing")
                                else state == "closed")
        position = attributes.get("current_position")
        self._attr_reports_position = position is not None
        self._attr_current_valve_position = position
        self._attr_supported_features = ValveEntityFeature(
            int(attributes.get("supported_features") or 0))

    def _restorable_empty(self) -> bool:
        return self._attr_is_closed is None

    def _restore(self, state: str) -> None:
        self._take_state(state, {})

    async def _send(self, service: str, data: dict[str, Any] | None = None) -> None:
        await self._data.command(self._integration, self._published_id, service, data or {})

    async def async_open_valve(self) -> None:
        await self._send("open_valve")

    async def async_close_valve(self) -> None:
        await self._send("close_valve")

    async def async_stop_valve(self) -> None:
        await self._send("stop_valve")

    async def async_set_valve_position(self, position: int) -> None:
        await self._send("set_valve_position", {"position": position})


async_setup_entry = setup_platform("valve", BridgedValve)
