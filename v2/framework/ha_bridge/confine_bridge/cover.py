"""Covers published by confined integrations (bridge batch B1, 2026-10-31).

The state (open, closed, opening, closing), the position and tilt and the supported features come
from the integration's own instance. (A) works out `toggle` and `toggle_tilt` from them; what
reaches the integration through the mediator is an open, close or stop, of the cover or its tilt,
or a position (`notes/bridge_kinds_b1_prediction_20261031.md`).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import CoverEntity, CoverEntityFeature

from .entity import BridgedEntity, setup_platform


class BridgedCover(BridgedEntity, CoverEntity):

    _described = frozenset({"current_position", "current_tilt_position", "is_closed",
                            "supported_features"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_is_opening = state == "opening"
        self._attr_is_closing = state == "closing"
        self._attr_is_closed = (None if state not in ("open", "closed", "opening", "closing")
                                else state == "closed")
        self._attr_current_cover_position = attributes.get("current_position")
        self._attr_current_cover_tilt_position = attributes.get("current_tilt_position")
        self._attr_supported_features = CoverEntityFeature(
            int(attributes.get("supported_features") or 0))

    def _restorable_empty(self) -> bool:
        return self._attr_is_closed is None

    def _restore(self, state: str) -> None:
        self._take_state(state, {})

    async def _send(self, service: str, data: dict[str, Any] | None = None) -> None:
        await self._data.command(self._integration, self._published_id, service, data or {})

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._send("open_cover")

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._send("close_cover")

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self._send("stop_cover")

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        await self._send("set_cover_position", {"position": kwargs["position"]})

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        await self._send("open_cover_tilt")

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        await self._send("close_cover_tilt")

    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:
        await self._send("stop_cover_tilt")

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        await self._send("set_cover_tilt_position", {"tilt_position": kwargs["tilt_position"]})


async_setup_entry = setup_platform("cover", BridgedCover)
