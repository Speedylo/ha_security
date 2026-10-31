"""Water heaters published by confined integrations (bridge batch B2, 2026-10-31).

The state is the current operation; the attributes give the operation list, the temperatures and
the away mode. **Temperatures are in °C**, as for the bridged climate: the sandbox's instance is
always metric, and (A) converts what a user sets to this entity's °C before the bridge sends it.
(A) checks an operation mode against the published list and turns `set_away_mode` into away mode on
or off, which goes to the integration as `set_away_mode`, the service its own instance runs
(`notes/bridge_kinds_b2_prediction_20261031.md`).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import WaterHeaterEntity, WaterHeaterEntityFeature
from homeassistant.const import UnitOfTemperature

from .entity import BridgedEntity, setup_platform

_PLAIN = {"min_temp": "_attr_min_temp", "max_temp": "_attr_max_temp",
          "temperature": "_attr_target_temperature",
          "current_temperature": "_attr_current_temperature",
          "target_temp_high": "_attr_target_temperature_high",
          "target_temp_low": "_attr_target_temperature_low",
          "target_temp_step": "_attr_target_temperature_step",
          "operation_list": "_attr_operation_list"}


class BridgedWaterHeater(BridgedEntity, WaterHeaterEntity):

    _described = frozenset({*_PLAIN, "operation_mode", "away_mode", "supported_features"})
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_current_operation = (None if state in (None, "unknown", "unavailable")
                                        else str(state))
        for key, name in _PLAIN.items():
            if attributes.get(key) is not None:
                setattr(self, name, attributes[key])
        away = attributes.get("away_mode")
        self._attr_is_away_mode_on = None if away not in ("on", "off") else away == "on"
        self._attr_supported_features = WaterHeaterEntityFeature(
            int(attributes.get("supported_features") or 0))

    def _restorable_empty(self) -> bool:
        return self._attr_current_operation is None

    def _restore(self, state: str) -> None:
        self._attr_current_operation = state if state not in ("unknown", "unavailable") else None

    async def _send(self, service: str, data: dict[str, Any] | None = None) -> None:
        await self._data.command(self._integration, self._published_id, service, data or {})

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send("turn_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send("turn_off")

    async def async_set_temperature(self, **kwargs: Any) -> None:
        # Home Assistant passes the whole service data (`async_service_temperature_set`), the
        # target included; only these two go on.
        await self._send("set_temperature", {k: v for k, v in kwargs.items()
                                             if k in ("temperature", "operation_mode")})

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        await self._send("set_operation_mode", {"operation_mode": operation_mode})

    async def async_turn_away_mode_on(self) -> None:
        await self._send("set_away_mode", {"away_mode": True})

    async def async_turn_away_mode_off(self) -> None:
        await self._send("set_away_mode", {"away_mode": False})


async_setup_entry = setup_platform("water_heater", BridgedWaterHeater)
