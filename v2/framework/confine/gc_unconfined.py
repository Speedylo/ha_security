"""§7.15's unconfined arm: two integrations in one process, and the heap walk that reaches across.

This is Corno and Mannella's setup (§2.4.1) reproduced in a real Home Assistant: a victim
integration holds an API token in a live client object, and a second integration — the adversary
— walks `gc.get_objects()` and reads it. Both are set up through the platform's own config-entry
path, so the object the adversary reaches is genuinely the victim's, in the shared heap that
every in-process design leaves open.

There is no framework here. That is the point: this is what the platform does today, and §7.15's
confined arm is what changes it.

Run through `selftest_gc`, not directly.
"""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from pathlib import Path

from gc_probe import CANARY_CREDENTIAL, GC_SWEEP, write_victim
from sandbox_runtime import build_hass

exec(GC_SWEEP)  # defines gc_find; shared verbatim with the confined arm


async def run(spec: dict) -> dict:
    from homeassistant.config_entries import ConfigEntry, SOURCE_USER

    root = Path(spec["config_dir"])
    write_victim(root)

    hass = await build_hass(str(root), with_auth=True)
    hass.data[__import__("homeassistant.loader", fromlist=["DATA_CUSTOM_COMPONENTS"])
              .DATA_CUSTOM_COMPONENTS] = None

    # Set the victim up as a real integration, so its credential enters the heap the way a real
    # one's does — through its own async_setup_entry, not by the test placing it.
    entry = ConfigEntry(version=1, minor_version=1, domain="victim_cloud", title="victim",
                        data={"token": CANARY_CREDENTIAL}, source=SOURCE_USER, options={},
                        unique_id=None, discovery_keys={}, subentries_data=())
    result: dict = {"arm": "unconfined"}
    try:
        await hass.config_entries.async_add(entry)
        await hass.async_block_till_done()
        result["victim_loaded"] = entry.state.recoverable if hasattr(entry.state, "recoverable") \
            else str(entry.state)
    except Exception as err:  # noqa: BLE001
        result["victim_error"] = f"{type(err).__name__}: {err}"[:200]

    # The adversary now runs its heap walk in the very same process, as a co-resident
    # integration would. No traversal, no exploit — a supported API returning live objects.
    hits = gc_find(CANARY_CREDENTIAL)
    result["gc_hits"] = hits[:20]
    result["gc_hit_count"] = len(hits)
    result["found_credential"] = len(hits) > 0

    await hass.async_stop()
    return result


def main() -> int:
    spec = json.loads(Path(sys.argv[1]).read_text())
    try:
        print(json.dumps(asyncio.run(run(spec))))
    except Exception:  # noqa: BLE001
        print(json.dumps({"fatal": traceback.format_exc()[-1500:]}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
