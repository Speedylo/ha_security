"""Climate devices published by confined integrations (bridge step 3, 2026-10-25).

The state is the HVAC mode; the attributes give everything Home Assistant needs to draw the
thermostat card. **Temperatures are in °C**, because the sandbox's instance is always metric
(`sandbox_runtime.py`): a house set to °F shows °F, and Home Assistant converts a temperature the
user sets back to this entity's °C before `async_set_temperature` is called, so the integration
receives what its own instance would have. Every command goes to the integration through the
mediator, which forwards only the services and data listed for a climate.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (ClimateEntity, ClimateEntityFeature, HVACAction,
                                              HVACMode)
from homeassistant.const import UnitOfTemperature

from .entity import BridgedEntity, setup_platform

# The state attribute each `_attr_` is published under, as Home Assistant's own climate writes it.
_PLAIN = {"current_temperature": "_attr_current_temperature",
          "temperature": "_attr_target_temperature",
          "target_temp_high": "_attr_target_temperature_high",
          "target_temp_low": "_attr_target_temperature_low",
          "target_temp_step": "_attr_target_temperature_step",
          "min_temp": "_attr_min_temp", "max_temp": "_attr_max_temp",
          "current_humidity": "_attr_current_humidity", "humidity": "_attr_target_humidity",
          "min_humidity": "_attr_min_humidity", "max_humidity": "_attr_max_humidity",
          "fan_mode": "_attr_fan_mode", "fan_modes": "_attr_fan_modes",
          "preset_mode": "_attr_preset_mode", "preset_modes": "_attr_preset_modes",
          "swing_mode": "_attr_swing_mode", "swing_modes": "_attr_swing_modes",
          "swing_horizontal_mode": "_attr_swing_horizontal_mode",
          "swing_horizontal_modes": "_attr_swing_horizontal_modes"}


def _mode(value: Any) -> HVACMode | None:
    try:
        return HVACMode(value)
    except ValueError:
        return None


class BridgedClimate(BridgedEntity, ClimateEntity):

    _described = frozenset({*_PLAIN, "hvac_modes", "hvac_action", "supported_features"})
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_hvac_mode = _mode(state)
        self._attr_hvac_modes = [m for m in map(_mode, attributes.get("hvac_modes") or [])
                                 if m is not None]
        try:
            self._attr_hvac_action = (HVACAction(attributes["hvac_action"])
                                      if attributes.get("hvac_action") else None)
        except ValueError:
            self._attr_hvac_action = None
        for key, name in _PLAIN.items():
            if key in attributes:
                setattr(self, name, attributes[key])
        self._attr_supported_features = ClimateEntityFeature(
            int(attributes.get("supported_features") or 0))

    def _restorable_empty(self) -> bool:
        return self._attr_hvac_mode is None

    def _restore(self, state: str) -> None:
        self._attr_hvac_mode = _mode(state)

    async def _send(self, service: str, data: dict[str, Any] | None = None) -> None:
        await self._data.command(self._integration, self._published_id, service, data or {})

    async def async_turn_on(self) -> None:
        await self._send("turn_on")

    async def async_turn_off(self) -> None:
        await self._send("turn_off")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self._send("set_hvac_mode", {"hvac_mode": str(hvac_mode)})

    async def async_set_temperature(self, **kwargs: Any) -> None:
        # Already converted to this entity's °C by Home Assistant; `hvac_mode` may come with it.
        data = {k: v for k, v in kwargs.items()
                if k in ("temperature", "target_temp_low", "target_temp_high")}
        if kwargs.get("hvac_mode") is not None:
            data["hvac_mode"] = str(kwargs["hvac_mode"])
        await self._send("set_temperature", data)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self._send("set_fan_mode", {"fan_mode": fan_mode})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self._send("set_preset_mode", {"preset_mode": preset_mode})

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        await self._send("set_swing_mode", {"swing_mode": swing_mode})

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode: str) -> None:
        await self._send("set_swing_horizontal_mode",
                         {"swing_horizontal_mode": swing_horizontal_mode})

    async def async_set_humidity(self, humidity: int) -> None:
        await self._send("set_humidity", {"humidity": humidity})


async_setup_entry = setup_platform("climate", BridgedClimate)
