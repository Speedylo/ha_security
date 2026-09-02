"""§7.14's unconfined arm: what an ordinary integration can see inside a real Home Assistant.

S3's verification (§3.5) requires "a paired baseline measuring what is readable without the
framework". This is that measurement, and it is deliberately the dullest code in the project:
build an instance, put a home in it, and ask — as any integration may, at any time, with no
permission of any kind — for every state it holds.

    hass.states.async_all()

That single call is the whole of the baseline. §1.7's Table 1.2 lists *entity states* first
among the authorities an integration holds today, and this is the API by which it holds them.
The integration also subscribes to `EVENT_STATE_CHANGED`, which is the other half of S3: a
design mediating reads but not subscriptions would leave a stream that returns the same
information a moment later.

Run through `selftest_reads`, not directly.
"""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from pathlib import Path

from home import HOME, probe_set
from sandbox_runtime import build_hass


async def run(spec: dict) -> dict:
    from homeassistant.const import EVENT_STATE_CHANGED

    hass = await build_hass(spec["config_dir"], with_auth=True)
    await hass.async_start()

    # The home, as any other integration would have published it.
    for entity_id, state, _sensitive, attributes in HOME:
        hass.states.async_set(entity_id, state, attributes)
    await hass.async_block_till_done()

    # The subscription half. No filter is available to ask for and none is imposed: an
    # integration subscribing to state changes receives every integration's changes.
    received: list[str] = []
    hass.bus.async_listen(EVENT_STATE_CHANGED,
                          lambda event: received.append(event.data.get("entity_id")))

    result: dict = {"arm": "unconfined"}
    result["visible"] = sorted(s.entity_id for s in hass.states.async_all())

    # Reads of everything the confined arm is asked about, by the ordinary API.
    reads = {}
    for entity_id in probe_set():
        state = hass.states.get(entity_id)
        reads[entity_id] = {"present_locally": state is not None,
                            "mediator_ok": state is not None,   # there is no mediator
                            "clause": None,
                            "value": state.state if state else None}
    result["reads"] = reads

    # Now change some entities the integration has nothing to do with, and count how many of
    # those changes it is told about.
    churn = ["device_tracker.younes_phone", "binary_sensor.bedroom_occupancy",
             "lock.front_door", "alarm_control_panel.home_alarm"]
    for entity_id in churn:
        hass.states.async_set(entity_id, "changed-by-someone-else", {})
    await hass.async_block_till_done()
    result["churned"] = churn
    result["events_received"] = sorted(set(e for e in received if e in churn))

    await hass.async_stop()
    return result


def main() -> int:
    spec = json.loads(Path(sys.argv[1]).read_text())
    try:
        print(json.dumps(asyncio.run(run(spec))))
    except Exception:  # noqa: BLE001 — the traceback is the result
        print(json.dumps({"fatal": traceback.format_exc()[-1500:]}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
