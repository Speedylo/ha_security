"""`demo_flood` that will not stop by itself: the case the supervisor's kill exists for.

Written for this project (verification 4.12, 2026-10-07). Identical to `demo_flood` except that
turning *Misbehave* on also blocks the event loop, as integration code that calls something
blocking from a coroutine does. The sandbox's runtime notices the mediator closing the channel
from that loop, so this integration never stops on its own after a cut-off, and only the
supervisor's kill through its cgroup ends it. With `demo_flood` the runtime stops itself, which
is why mutant M31 (the kill removed) survived every suite until this integration was added.
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
