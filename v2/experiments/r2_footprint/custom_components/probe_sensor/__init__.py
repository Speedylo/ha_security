"""R2 probe integration.

Deliberately ordinary. It is written the way real Home Assistant integrations are written —
a config-entry setup, a DataUpdateCoordinator, entities forwarded to the sensor platform —
because the question this experiment asks is whether *that* shape works against a minimal,
locally-constructed Home Assistant, not whether some hand-tuned special case does.

The only departure from a real integration is that its data source is a counter rather than
a network call, so the measurement is offline and deterministic. Nothing else about the
control flow differs, and in particular it goes through the helper layer that §5.6's
measurement found 91% of integrations importing.
"""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import ProbeConfigEntry, ProbeCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ProbeConfigEntry) -> bool:
    """Set up the probe from a config entry."""
    coordinator = ProbeCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ProbeConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
