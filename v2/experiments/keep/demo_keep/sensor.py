"""The token sensor: its state is the token the entry held after this setup."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    sensor = Token()
    hass.data[DOMAIN]["sensor"] = sensor
    async_add_entities([sensor])


class Token(SensorEntity):
    _attr_name = "Demo Keep Token"
    _attr_unique_id = "demo_keep_token"
    _attr_should_poll = False

    @property
    def native_value(self) -> str:
        return self.hass.data[DOMAIN]["state"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"plant": self.hass.data[DOMAIN]["plant"],
                "locked": self.hass.data[DOMAIN]["locked"]}
