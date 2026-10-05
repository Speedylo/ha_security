"""A test integration for the refusal flood: one switch that makes it misbehave on demand.

Written for this project, not taken from the corpus. Turning *Misbehave* on makes it retry a
host its manifest does not declare, in a loop, as a buggy integration retrying a host it missed
would. Each attempt is a request the mediator refuses, so the switch is a flood a person can start
from the house's own interface (`notes/flood_cutoff_prediction.md` §6).
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

PLATFORMS = [Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
