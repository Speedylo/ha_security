"""Probe integration for the *second* question this experiment asks.

`probe_sensor` (copied from `experiments/r2_footprint/`) answers "does an ordinary
integration still load?". It cannot answer "what is lost?", because it uses nothing the
`homeassistant` base component might have been providing.

This one does. It uses `RestoreSensor`, so its published value survives a restart only if
the state-restoration machinery is actually running. That machinery is the most plausible
casualty of dropping the base component: the base component registers
`homeassistant.save_persistent_states`, and if that service were the only thing writing the
restore file, dropping it would silently break every integration whose entities restore.

The probe is therefore a falsification attempt, not a demonstration. It is written to fail
loudly in the arm where the base component is absent, if there is anything to fail.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the restore probe from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
