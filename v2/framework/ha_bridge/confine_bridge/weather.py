"""Weather published by confined integrations (bridge step 4, 2026-10-25).

The condition is the state, and the current values and their units come from the published
attributes: the sandbox's own display units, so they are this entity's native units, and Home
Assistant converts them to the house's. A forecast is a **question** to the integration,
`get_forecasts`, whose answer the mediator checks; when the integration publishes again, open
forecast cards are told to ask again.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.weather import Forecast, WeatherEntity, WeatherEntityFeature

from .entity import BridgedEntity, setup_platform

# Published attribute -> this entity's attribute.
_CURRENT = {"temperature": "_attr_native_temperature",
            "apparent_temperature": "_attr_native_apparent_temperature",
            "dew_point": "_attr_native_dew_point", "humidity": "_attr_humidity",
            "pressure": "_attr_native_pressure", "wind_speed": "_attr_native_wind_speed",
            "wind_gust_speed": "_attr_native_wind_gust_speed", "wind_bearing": "_attr_wind_bearing",
            "visibility": "_attr_native_visibility", "cloud_coverage": "_attr_cloud_coverage",
            "uv_index": "_attr_uv_index", "ozone": "_attr_ozone",
            "temperature_unit": "_attr_native_temperature_unit",
            "pressure_unit": "_attr_native_pressure_unit",
            "wind_speed_unit": "_attr_native_wind_speed_unit",
            "visibility_unit": "_attr_native_visibility_unit",
            "precipitation_unit": "_attr_native_precipitation_unit"}
# A forecast entry's display field -> the native field a weather entity returns. The sandbox's
# display units are this entity's native ones, so the values carry over unchanged.
_NATIVE = {"temperature": "native_temperature", "templow": "native_templow",
           "apparent_temperature": "native_apparent_temperature", "dew_point": "native_dew_point",
           "pressure": "native_pressure", "wind_speed": "native_wind_speed",
           "wind_gust_speed": "native_wind_gust_speed", "precipitation": "native_precipitation"}


class BridgedWeather(BridgedEntity, WeatherEntity):

    _described = frozenset({*_CURRENT, "supported_features"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_condition = None if state in (None, "unknown", "unavailable") else str(state)
        for key, name in _CURRENT.items():
            if key in attributes:
                setattr(self, name, attributes[key])
        self._attr_supported_features = WeatherEntityFeature(
            int(attributes.get("supported_features") or 0))
        if self.hass is not None:
            # The integration published again: forecast cards that are open ask again.
            self.hass.async_create_task(self.async_update_listeners(None))

    def _restorable_empty(self) -> bool:
        return self._attr_condition is None

    def _restore(self, state: str) -> None:
        self._attr_condition = state

    async def _forecast(self, kind: str) -> list[Forecast] | None:
        answer = await self._data.command(self._integration, self._published_id,
                                          "get_forecasts", {"type": kind})
        return [Forecast(**{_NATIVE.get(k, k): v for k, v in item.items()})
                for item in answer or []]

    async def async_forecast_daily(self) -> list[Forecast] | None:
        return await self._forecast("daily")

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        return await self._forecast("hourly")

    async def async_forecast_twice_daily(self) -> list[Forecast] | None:
        return await self._forecast("twice_daily")


async_setup_entry = setup_platform("weather", BridgedWeather)
