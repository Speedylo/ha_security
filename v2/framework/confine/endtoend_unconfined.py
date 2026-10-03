"""§7.17's missing arm: the same five integrations set up in an unconfined Home Assistant.

§7.17.5 recorded the gap the moment the confined arm landed: `scheduler` and `powercalc` were
attributed to the design **by their tracebacks rather than by comparison**, which is weaker
evidence than §7.12's and is exactly the substitution the baseline arm exists to prevent. If
zeroconf cannot join a multicast group in an ordinary process on this host either, then
`scheduler` is not confinement's cost and the conclusion drawn from it collapses.

Everything is held fixed but confinement: same corpus, same release, same interpreter, same
world of entities, and the **same flow driver** — `drive_flow` is imported from
`sandbox_runtime`, not reimplemented, for the reason §7.12.1 gives.

The instance is deliberately generous, as §7.12's baseline is: the base `homeassistant`
component, `default_config`, the integration's declared components, and the platform's core
packages. A stingy baseline understates what confinement costs.

Run through `endtoend`, not directly.
"""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from pathlib import Path

from sandbox_runtime import CURRENT_PHASE, build_hass, drive_flow, record_egress_attempts


async def run(spec: dict) -> dict:
    from homeassistant.config_entries import ConfigEntryState
    from homeassistant.setup import async_setup_component

    domain = spec["domain"]
    config_dir = spec["config_dir"]
    result: dict = {"domain": domain, "arm": "unconfined"}

    # `endtoend_egress` has always sent `record_egress: True` and nothing read it, so §7.27's
    # arm A never recorded where it went. Honoured from §7.31, where a subject with several
    # possible hosts makes *where the unconfined arm went* the check on the declared set.
    # It is §7.18's in-process recorder and inherits its blind spot: names resolved through
    # `aiodns` are not seen, only the address they connect to. `requests` and `httpx` resolve
    # through `getaddrinfo` and are seen by name.
    attempts: list = []
    if spec.get("record_egress"):
        record_egress_attempts(attempts)
        result["egress_attempts"] = attempts

    hass = await build_hass(config_dir, with_auth=True)

    result["components_setup"] = {}
    for name in (["homeassistant", "default_config"] + list(spec.get("setup_components") or [])):
        if name in result["components_setup"]:
            continue
        try:
            result["components_setup"][name] = bool(
                await async_setup_component(hass, name, {}))
        except Exception as err:  # noqa: BLE001
            result["components_setup"][name] = f"{type(err).__name__}: {err}"[:160]

    # The same world the confined arm's mediator holds, here as ordinary states — which is
    # what an integration configured from other entities needs in order to be configurable.
    for entity_id, (state, attributes) in (spec.get("world") or {}).items():
        hass.states.async_set(entity_id, state, attributes)
    await hass.async_block_till_done()

    # Attribution, per §7.18.2: everything recorded before this line is the platform's own
    # (`network` probing 8.8.8.8, zeroconf joining mDNS), not the integration's.
    CURRENT_PHASE[0] = "integration"
    result["flow"] = await drive_flow(hass, domain, spec.get("flow_input") or {},
                                      spec.get("menu_choice") or {}, setup_log_into=result,
                                      select_first=spec.get("select_first") or ())
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()

    # The confined arm settles after `async_start` so a coordinator's first fetch — scheduled
    # rather than immediate — actually happens (`sandbox_runtime`, §7.25's window). An arm
    # compared against it must settle for the same period or the comparison varies in two
    # things. Defaults to 0, so every existing caller is unaffected.
    settle = float(spec.get("settle_seconds", 0))
    if settle:
        deadline = asyncio.get_running_loop().time() + settle
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(1.0)
            try:
                await asyncio.wait_for(hass.async_block_till_done(), timeout=5)
            except (TimeoutError, asyncio.TimeoutError):
                pass

    entries = hass.config_entries.async_entries(domain)
    result["entries"] = [{"title": e.title, "state": str(e.state),
                          "loaded": e.state is ConfigEntryState.LOADED} for e in entries]
    result["loaded"] = any(e.state is ConfigEntryState.LOADED for e in entries)
    world = set(spec.get("world") or {})
    own = [s for s in hass.states.async_all()
           if s.entity_id not in world
           and s.entity_id.split(".")[0] != "persistent_notification"]
    result["own_entities"] = sorted(s.entity_id for s in own)
    # The confined arm reports what crossed the boundary *with its value* (`bridge.published`),
    # because F1 is about the value being right and not only about the entity existing. The
    # unconfined arm has no boundary, so its counterpart is the state machine itself — named
    # `published` so the two arms are comparable field for field.
    result["published"] = sorted(
        ({"entity": s.entity_id, "state": s.state} for s in own),
        key=lambda item: item["entity"])

    try:
        await hass.async_stop()
    except Exception:  # noqa: BLE001
        pass
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
