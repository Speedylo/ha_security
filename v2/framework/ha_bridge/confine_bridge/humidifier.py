"""Humidifiers published by confined integrations (bridge batch B2, 2026-10-31).

The humidity range, the modes and the target come from the integration's own instance. (A) checks a
humidity against the published range and works out `toggle`; what reaches the integration through
the mediator is a turn on or off, a humidity or a mode (`notes/bridge_kinds_b2_prediction_20261031.md`).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.humidifier import (HumidifierAction, HumidifierEntity,
                                                 HumidifierEntityFeature)

from .entity import BridgedEntity, setup_platform

_PLAIN = {"min_humidity": "_attr_min_humidity", "max_humidity": "_attr_max_humidity",
          "humidity": "_attr_target_humidity", "current_humidity": "_attr_current_humidity",
          "target_humidity_step": "_attr_target_humidity_step",
          "available_modes": "_attr_available_modes", "mode": "_attr_mode"}


class BridgedHumidifier(BridgedEntity, HumidifierEntity):

    _described = frozenset({*_PLAIN, "action", "supported_features"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_is_on = None if state not in ("on", "off") else state == "on"
        for key, name in _PLAIN.items():
            if attributes.get(key) is not None:
                setattr(self, name, attributes[key])
        try:
            self._attr_action = (HumidifierAction(attributes["action"])
                                 if attributes.get("action") else None)
        except ValueError:
            self._attr_action = None
        self._attr_supported_features = HumidifierEntityFeature(
            int(attributes.get("supported_features") or 0))

    def _restorable_empty(self) -> bool:
        return self._attr_is_on is None

    def _restore(self, state: str) -> None:
        self._attr_is_on = None if state not in ("on", "off") else state == "on"

    async def _send(self, service: str, data: dict[str, Any] | None = None) -> None:
        await self._data.command(self._integration, self._published_id, service, data or {})

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send("turn_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send("turn_off")

    async def async_set_humidity(self, humidity: int) -> None:
        await self._send("set_humidity", {"humidity": humidity})

    async def async_set_mode(self, mode: str) -> None:
        await self._send("set_mode", {"mode": mode})


async_setup_entry = setup_platform("humidifier", BridgedHumidifier)
