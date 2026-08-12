"""Shim of homeassistant.components.sensor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from ...helpers.entity import Entity, EntityDescription

DOMAIN = "sensor"
ENTITY_ID_FORMAT = DOMAIN + ".{}"


class SensorDeviceClass(StrEnum):
    """What a sensor measures. Pure data — generated in the real deliverable."""

    APPARENT_POWER = "apparent_power"
    AQI = "aqi"
    ATMOSPHERIC_PRESSURE = "atmospheric_pressure"
    BATTERY = "battery"
    CO = "carbon_monoxide"
    CO2 = "carbon_dioxide"
    CURRENT = "current"
    DATA_RATE = "data_rate"
    DATA_SIZE = "data_size"
    DATE = "date"
    DISTANCE = "distance"
    DURATION = "duration"
    ENERGY = "energy"
    ENERGY_STORAGE = "energy_storage"
    ENUM = "enum"
    FREQUENCY = "frequency"
    GAS = "gas"
    HUMIDITY = "humidity"
    ILLUMINANCE = "illuminance"
    IRRADIANCE = "irradiance"
    MOISTURE = "moisture"
    MONETARY = "monetary"
    NITROGEN_DIOXIDE = "nitrogen_dioxide"
    OZONE = "ozone"
    PM1 = "pm1"
    PM10 = "pm10"
    PM25 = "pm25"
    POWER = "power"
    POWER_FACTOR = "power_factor"
    PRECIPITATION = "precipitation"
    PRECIPITATION_INTENSITY = "precipitation_intensity"
    PRESSURE = "pressure"
    REACTIVE_POWER = "reactive_power"
    SIGNAL_STRENGTH = "signal_strength"
    SOUND_PRESSURE = "sound_pressure"
    SPEED = "speed"
    SULPHUR_DIOXIDE = "sulphur_dioxide"
    TEMPERATURE = "temperature"
    TIMESTAMP = "timestamp"
    VOLATILE_ORGANIC_COMPOUNDS = "volatile_organic_compounds"
    VOLTAGE = "voltage"
    VOLUME = "volume"
    WATER = "water"
    WEIGHT = "weight"
    WIND_SPEED = "wind_speed"


class SensorStateClass(StrEnum):
    """How a sensor's value evolves over time."""

    MEASUREMENT = "measurement"
    TOTAL = "total"
    TOTAL_INCREASING = "total_increasing"


@dataclass(kw_only=True)
class SensorEntityDescription(EntityDescription):
    """Description of a sensor entity."""

    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | str | None = None
    last_reset: datetime | None = None
    native_unit_of_measurement: str | None = None
    suggested_display_precision: int | None = None
    suggested_unit_of_measurement: str | None = None
    options: list[str] | None = None


class SensorEntity(Entity):
    """Base class for sensors.

    ``state`` deriving from ``native_value`` is the contract integrations rely
    on: they implement ``native_value`` and never touch ``state``.
    """

    entity_description: SensorEntityDescription | None = None

    _attr_native_value: Any = None
    _attr_native_unit_of_measurement: str | None = None
    _attr_state_class: SensorStateClass | str | None = None
    _attr_suggested_display_precision: int | None = None
    _attr_options: list[str] | None = None
    _attr_last_reset: datetime | None = None

    @property
    def native_value(self) -> Any:
        return self._attr_native_value

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self._attr_native_unit_of_measurement is not None:
            return self._attr_native_unit_of_measurement
        if self.entity_description is not None:
            return self.entity_description.native_unit_of_measurement
        return None

    @property
    def unit_of_measurement(self) -> str | None:
        return self.native_unit_of_measurement

    @property
    def state_class(self) -> SensorStateClass | str | None:
        if self._attr_state_class is not None:
            return self._attr_state_class
        if self.entity_description is not None:
            return self.entity_description.state_class
        return None

    @property
    def suggested_display_precision(self) -> int | None:
        if self._attr_suggested_display_precision is not None:
            return self._attr_suggested_display_precision
        if self.entity_description is not None:
            return self.entity_description.suggested_display_precision
        return None

    @property
    def last_reset(self) -> datetime | None:
        if self._attr_last_reset is not None:
            return self._attr_last_reset
        if self.entity_description is not None:
            return self.entity_description.last_reset
        return None

    @property
    def options(self) -> list[str] | None:
        if self._attr_options is not None:
            return self._attr_options
        if self.entity_description is not None:
            return self.entity_description.options
        return None

    @property
    def state(self) -> Any:
        """HA does unit conversion and rounding here; the shim passes through."""
        value = self.native_value
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    def _build_attributes(self) -> dict[str, Any]:
        attributes = super()._build_attributes()
        if (state_class := self.state_class) is not None:
            attributes["state_class"] = str(state_class)
        if (precision := self.suggested_display_precision) is not None:
            attributes["suggested_display_precision"] = precision
        if (options := self.options) is not None:
            attributes["options"] = options
        return attributes


class RestoreSensor(SensorEntity):
    """Sensor that restores its previous value; the sandbox has no store yet."""

    async def async_get_last_sensor_data(self) -> None:
        return None


__all__ = [
    "DOMAIN",
    "ENTITY_ID_FORMAT",
    "RestoreSensor",
    "SensorDeviceClass",
    "SensorEntity",
    "SensorEntityDescription",
    "SensorStateClass",
]
