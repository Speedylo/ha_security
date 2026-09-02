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

from sandbox_runtime import build_hass, drive_flow


async def run(spec: dict) -> dict:
    from homeassistant.config_entries import ConfigEntryState
    from homeassistant.setup import async_setup_component

    domain = spec["domain"]
    config_dir = spec["config_dir"]
    result: dict = {"domain": domain, "arm": "unconfined"}

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

    result["flow"] = await drive_flow(hass, domain, spec.get("flow_input") or {},
                                      spec.get("menu_choice") or {}, setup_log_into=result)
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(domain)
    result["entries"] = [{"title": e.title, "state": str(e.state),
                          "loaded": e.state is ConfigEntryState.LOADED} for e in entries]
    result["loaded"] = any(e.state is ConfigEntryState.LOADED for e in entries)
    world = set(spec.get("world") or {})
    result["own_entities"] = sorted(
        s.entity_id for s in hass.states.async_all()
        if s.entity_id not in world and s.entity_id.split(".")[0] != "persistent_notification")

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
