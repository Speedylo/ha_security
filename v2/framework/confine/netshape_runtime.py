"""One integration, unconfined, with its network behaviour recorded rather than blocked.

This is the arm in which egress **works**. §7.18 could only watch attempts fail against a
namespace with no route, which tells you a host was wanted and nothing about what serving it
would involve. Here the integration reaches the real internet, and the recorder answers the
question the proxy has to be designed against: not *whether* egress is needed but *of what kind*.

**Why a failing credential is still a complete observation.** §7.17.1 found that 26 of 37 need a
credential before any flow completes, and §7.18 concluded from the same wall that egress demand
is unobservable. The wall is real and it is in the wrong place for this question: a config flow
validates a credential *by making the call*, so a wrong key still produces the resolution, the
connection, the handshake and the request, and only the last of those is refused. Every mechanism
a mediator would have to implement has run by then. What cannot be measured this way is how
*often* an integration would poll, and this run does not claim it.

The credentials supplied are deliberately invalid and deliberately non-secret — see
`egress_shape.CREDENTIALS`. Nothing here authenticates to anything.

Run through `egress_shape`, not directly.
"""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from pathlib import Path

import netshape
from netshape import Recorder
from sandbox_runtime import build_hass, drive_flow


class FlowInput(dict):
    """The credential answers, with address-shaped field names matched by suffix.

    `fill_schema` decides whether it has an answer with `name in overrides` and then reads
    `overrides[name]`. Supplying a mapping that answers those two questions more generously
    adds suffix matching — `inverter_host`, `bridge_address`, `device_ip` — **without editing
    `fill_schema`**, which §7.17's confined and unconfined arms both call. A shared function
    changed for this experiment would silently move an already-published comparison.
    """

    suffixes = ("_host", "_ip", "_address", "_ip_address", "_hostname")

    def __contains__(self, name: object) -> bool:
        if super().__contains__(name):
            return True
        return isinstance(name, str) and name.endswith(self.suffixes)

    def __missing__(self, name: str) -> object:
        if isinstance(name, str) and name.endswith(self.suffixes):
            return "127.0.0.1"
        raise KeyError(name)


async def run(spec: dict) -> dict:
    from homeassistant.config_entries import ConfigEntryState
    from homeassistant.setup import async_setup_component

    domain = spec["domain"]
    component_dir = str(Path(spec["config_dir"]) / "custom_components" / domain)
    result: dict = {"domain": domain, "arm": "unconfined-recorded"}

    # Installed before anything else runs, so that the platform's own egress is recorded in the
    # platform phase and cannot be charged to the integration. §7.18.2's whole correction.
    recorder = Recorder(component_dir=component_dir,
                        deps_dir=spec.get("deps_dir", ""))
    recorder.install()

    try:
        netshape.CURRENT_PHASE[0] = "instance"
        hass = await build_hass(spec["config_dir"], with_auth=True)

        netshape.CURRENT_PHASE[0] = "components"
        result["components_setup"] = {}
        for name in (["homeassistant", "default_config"]
                     + list(spec.get("setup_components") or [])):
            if name in result["components_setup"]:
                continue
            try:
                result["components_setup"][name] = bool(
                    await async_setup_component(hass, name, {}))
            except Exception as err:  # noqa: BLE001
                result["components_setup"][name] = f"{type(err).__name__}: {err}"[:160]

        for entity_id, (state, attributes) in (spec.get("world") or {}).items():
            hass.states.async_set(entity_id, state, attributes)
        await hass.async_block_till_done()

        # From here on, anything recorded is the integration's — its flow handler, its vendor
        # library, or a coordinator it started.
        netshape.CURRENT_PHASE[0] = "integration"
        result["flow"] = await drive_flow(hass, domain, FlowInput(spec.get("flow_input") or {}),
                                          spec.get("menu_choice") or {}, setup_log_into=result)
        await hass.async_block_till_done()
        try:
            await hass.async_start()
        except Exception:  # noqa: BLE001
            pass

        # A coordinator's first refresh is scheduled, not immediate. Without a settle period the
        # run would report the flow's egress and miss the polling that F2 is actually about.
        settle = float(spec.get("settle_seconds", 20))
        try:
            await asyncio.wait_for(_settle(hass, settle), timeout=settle + 10)
        except (TimeoutError, asyncio.TimeoutError):
            pass

        entries = hass.config_entries.async_entries(domain)
        result["entries"] = [{"title": e.title, "state": str(e.state),
                              "loaded": e.state is ConfigEntryState.LOADED} for e in entries]
        result["loaded"] = any(e.state is ConfigEntryState.LOADED for e in entries)

        try:
            await hass.async_stop()
        except Exception:  # noqa: BLE001
            pass
    finally:
        recorder.uninstall()

    result["netshape"] = recorder.summary()
    if spec.get("full_events"):
        result["events"] = recorder.events[:4000]
    return result


async def _settle(hass, seconds: float) -> None:
    """Let scheduled work run. Polled rather than slept in one block so that a run whose work
    finishes early does not pay the whole budget on every integration."""
    deadline = asyncio.get_running_loop().time() + seconds
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(1.0)
        try:
            await asyncio.wait_for(hass.async_block_till_done(), timeout=5)
        except (TimeoutError, asyncio.TimeoutError):
            pass


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
