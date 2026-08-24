"""DataUpdateCoordinator for the R2 probe — the polling pattern 38% of integrations use."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

type ProbeConfigEntry = ConfigEntry[ProbeCoordinator]


class ProbeCoordinator(DataUpdateCoordinator[dict[str, int]]):
    """Poll a local counter instead of a remote API, so the run stays offline."""

    config_entry: ProbeConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ProbeConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="probe_sensor",
            update_interval=timedelta(seconds=30),
        )
        self._tick = 0

    async def _async_update_data(self) -> dict[str, int]:
        self._tick += 1
        return {"ticks": self._tick}
