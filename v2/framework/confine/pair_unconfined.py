"""T06's pair, the unconfined arm: an ordinary integration's listener inside a real Home Assistant.

The same three undeclared entities as `selftest_push`, changed by the platform's own state write,
and counted at a listener on `EVENT_STATE_CHANGED`, which any integration may register with no
permission of any kind. Predictions: `notes/t06_true_pair_prediction.md`.

Run through `pair_subscriptions`, not directly.
"""

from __future__ import annotations

import asyncio
import json
import platform
import sys
import traceback
from pathlib import Path

from sandbox_runtime import build_hass

DECLARED = "sensor.pair_declared"
UNDECLARED = ["sensor.bedroom_occupancy", "lock.front_door", "person.younes"]


async def run(spec: dict) -> dict:
    from homeassistant.const import EVENT_STATE_CHANGED, __version__

    hass = await build_hass(spec["config_dir"])
    await hass.async_start()
    for entity_id in [DECLARED, *UNDECLARED]:
        hass.states.async_set(entity_id, "0")
    await hass.async_block_till_done()

    received: list[tuple[str, str]] = []
    hass.bus.async_listen(EVENT_STATE_CHANGED, lambda event: received.append(
        (event.data["entity_id"], event.data["new_state"].state)))

    for entity_id in [DECLARED, *UNDECLARED]:
        hass.states.async_set(entity_id, "on")
    await hass.async_block_till_done()
    await hass.async_stop()

    return {"arm": "unconfined", "ha_version": __version__, "host": platform.node(),
            "declared_delivered": (DECLARED, "on") in received,
            "undeclared_delivered": sorted(e for e, s in received if e in UNDECLARED and s == "on"),
            "undeclared": UNDECLARED}


def main() -> int:
    spec = json.loads(Path(sys.argv[1]).read_text())
    try:
        print(json.dumps(asyncio.run(run(spec))))
    except Exception:  # noqa: BLE001 — the traceback is the result
        print(json.dumps({"arm": "unconfined", "fatal": traceback.format_exc()[-1500:]}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
