#!/usr/bin/env python3
"""Sandbox entrypoint: load one unmodified HACS integration under the shim.

Runs as a child of supervisor.py. Everything HA would normally do — import the
integration, hand it a ``hass`` object, forward its platforms, keep its
coordinator ticking — happens here, except that the ``hass`` object is the shim
and every effect leaves through the bridge socket.

The integration source under target/ is never edited. That is the point being
tested: does a real integration run unmodified against a shim of this size.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
SHIM_DIR = SPIKE_DIR / "shim"

# The shim must win over any real `homeassistant` that happens to be installed.
sys.path.insert(0, str(SHIM_DIR))

INTEGRATION_DIR = Path(os.environ["HACS_INTEGRATION_DIR"]).resolve()
DOMAIN = os.environ["HACS_DOMAIN"]
# Parent of custom_components/, so `import custom_components.<domain>` resolves.
sys.path.insert(1, str(INTEGRATION_DIR.parent.parent))

from homeassistant._bridge import Bridge, PermissionDenied  # noqa: E402
from homeassistant.config_entries import ConfigEntry, current_entry  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.helpers import aiohttp_client, entity as entity_helper  # noqa: E402

LOG_FORMAT = "  %(levelname)-7s %(name)s: %(message)s"


def load_translations(hass_domain: str) -> None:
    """Give the shim the integration's own translations, as HA would."""
    for language in ("en",):
        path = INTEGRATION_DIR / "translations" / f"{language}.json"
        if path.is_file():
            entity_helper.set_translations(hass_domain, json.loads(path.read_text(encoding="utf-8")))
            return


async def main() -> int:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stdout)

    bridge = Bridge.from_env()
    sandbox_dir = os.environ.get("HACS_SANDBOX_DIR", os.getcwd())
    hass = HomeAssistant(bridge, config_dir=sandbox_dir)
    load_translations(DOMAIN)

    manifest_path = INTEGRATION_DIR / "manifest.json"
    ha_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}

    entry = ConfigEntry(
        domain=DOMAIN,
        title=ha_manifest.get("name", DOMAIN),
        data=json.loads(os.environ.get("HACS_ENTRY_DATA", "{}")),
        version=2,
        entry_id="sandbox0000000000000000000000000",
    )
    hass.config_entries._register(entry)
    # Set for the whole setup, as HA does: helpers built during setup pick their
    # own config entry off this context variable.
    current_entry.set(entry)

    print(f"sandbox: importing custom_components.{DOMAIN} against the shim", flush=True)
    module = importlib.import_module(f"custom_components.{DOMAIN}")

    exit_code = 0
    try:
        if (setup := getattr(module, "async_setup", None)) is not None:
            await setup(hass, {})

        setup_entry = getattr(module, "async_setup_entry")
        await setup_entry(hass, entry)
        await hass.async_block_till_done()
        print("sandbox: async_setup_entry completed", flush=True)

        # A second poll, to show the update path rather than just first setup.
        coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator is not None and hasattr(coordinator, "async_refresh"):
            print("sandbox: forcing a second coordinator refresh", flush=True)
            await coordinator.async_refresh()
            await hass.async_block_till_done()

        if os.environ.get("HACS_PROBE") == "1":
            from probe import run_probe

            await run_probe(hass)

        if (unload := getattr(module, "async_unload_entry", None)) is not None:
            await unload(hass, entry)
        if coordinator is not None and hasattr(coordinator, "async_shutdown"):
            await coordinator.async_shutdown()

    except PermissionDenied as err:
        print(f"sandbox: integration stopped by the supervisor: {err}", flush=True)
        exit_code = 2
    except Exception as err:  # noqa: BLE001 - a spike wants the failure, not a traceback-free exit
        logging.exception("sandbox: integration failed: %s", err)
        exit_code = 1
    finally:
        await aiohttp_client.async_close_sessions()
        await hass.async_stop()
        bridge.close()

    return exit_code


if __name__ == "__main__":
    sys.path.insert(0, str(SPIKE_DIR))
    sys.exit(asyncio.run(main()))
