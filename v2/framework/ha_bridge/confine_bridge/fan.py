"""Fans published by confined integrations (bridge batch B1, 2026-10-31).

The speed, its step, the preset modes, oscillation and direction come from the integration's own
instance. (A) works out `toggle`, `increase_speed` and `decrease_speed` from them, and checks a
preset mode against the published list, before anything is sent; what reaches the integration
through the mediator is a turn on or off, a percentage, a preset, oscillation or a direction
(`notes/bridge_kinds_b1_prediction_20261031.md`).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature

from .entity import BridgedEntity, setup_platform


class BridgedFan(BridgedEntity, FanEntity):

    _described = frozenset({"percentage", "percentage_step", "preset_mode", "preset_modes",
                            "oscillating", "direction", "supported_features"})
    _published_on: bool | None = None

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._published_on = None if state not in ("on", "off") else state == "on"
        self._attr_percentage = attributes.get("percentage")
        step = attributes.get("percentage_step")
        # Home Assistant publishes the step as 100 / speed count.
        self._attr_speed_count = (max(1, round(100 / step))
                                  if isinstance(step, (int, float)) and step > 0 else 100)
        self._attr_preset_mode = attributes.get("preset_mode")
        self._attr_preset_modes = attributes.get("preset_modes")
        self._attr_oscillating = attributes.get("oscillating")
        self._attr_current_direction = attributes.get("direction")
        self._attr_supported_features = FanEntityFeature(
            int(attributes.get("supported_features") or 0))

    @property
    def is_on(self) -> bool | None:
        # As published: Home Assistant's own rule (a percentage above 0, or a preset) would show
        # a fan with neither as off.
        return self._published_on

    def _restorable_empty(self) -> bool:
        return self._published_on is None

    def _restore(self, state: str) -> None:
        self._published_on = None if state not in ("on", "off") else state == "on"

    async def _send(self, service: str, data: dict[str, Any] | None = None) -> None:
        await self._data.command(self._integration, self._published_id, service, data or {})

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None,
                            **kwargs: Any) -> None:
        data: dict[str, Any] = {}
        if percentage is not None:
            data["percentage"] = percentage
        if preset_mode is not None:
            data["preset_mode"] = preset_mode
        await self._send("turn_on", data)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send("turn_off")

    async def async_set_percentage(self, percentage: int) -> None:
        await self._send("set_percentage", {"percentage": percentage})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self._send("set_preset_mode", {"preset_mode": preset_mode})

    async def async_oscillate(self, oscillating: bool) -> None:
        await self._send("oscillate", {"oscillating": oscillating})

    async def async_set_direction(self, direction: str) -> None:
        await self._send("set_direction", {"direction": direction})


async_setup_entry = setup_platform("fan", BridgedFan)
