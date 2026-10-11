"""A test integration for F59: what it stores must survive a restart, and nothing else may.

Written for this project, not taken from the corpus (`notes/f59_kept_storage_prediction.md` §3).
Each setup does what an OAuth integration does when it refreshes its token: it reads its entry and
stores a new token in it, here `refresh-<n>`, one more than it read. Its sensor shows the token, so
a restart that kept the entry reads `refresh-2`, and one that lost it reads `refresh-1` again.

It also does two things a hostile integration might, so that the test of what is kept is not
vacuous. It **plants code**: it replaces its own `custom_components/demo_keep` link, in its
configuration folder, with a copy of its code plus a file `PLANTED`; a copy that finds `PLANTED`
beside itself shows `planted` instead of a token. And it makes a directory nobody may read (mode
`000`), which a careless deletion of the folder would leave behind.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

DOMAIN = "demo_keep"
PLATFORMS = [Platform.SENSOR]
HERE = Path(__file__).resolve().parent


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    refreshes = int(entry.data.get("refreshes", 0)) + 1
    token = f"refresh-{refreshes}"
    hass.config_entries.async_update_entry(entry, data={"token": token, "refreshes": refreshes})
    planted = (Path(__file__).parent / "PLANTED").exists()
    hass.data[DOMAIN] = {"state": "planted" if planted else token, "plant": "pending",
                         "locked": "pending", "sensor": None}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # After the platform is imported, so that this run's code is the code it was given.
    config = Path(hass.config.config_dir)
    hass.data[DOMAIN]["plant"] = await hass.async_add_executor_job(_plant, config, planted)
    hass.data[DOMAIN]["locked"] = await hass.async_add_executor_job(_lock, config)
    sensor = hass.data[DOMAIN]["sensor"]
    if sensor is not None:
        sensor.async_write_ha_state()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _plant(config: Path, planted: bool) -> str:
    """Replace the link to the approved code with a directory of our own."""
    if planted:
        return "skipped"
    link = config / "custom_components" / DOMAIN
    staging = config / "custom_components" / f".{DOMAIN}_new"
    try:
        shutil.copytree(HERE, staging, ignore=shutil.ignore_patterns("__pycache__"))
        (staging / "PLANTED").write_text("not the approved code\n")
        link.unlink()
        staging.rename(link)
    except OSError as err:
        return f"{type(err).__name__}: {err}"
    return "done"


def _lock(config: Path) -> str:
    """A directory holding one file, that nobody may read or enter."""
    locked = config / "locked"
    try:
        locked.mkdir(exist_ok=True)
        (locked / "inside").write_text("x\n")
        locked.chmod(0)
    except OSError as err:
        return f"{type(err).__name__}: {err}"
    return "done"
