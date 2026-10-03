#!/usr/bin/env python3
"""R2 feasibility — can a minimal Home Assistant host an unmodified integration, and what does it cost?

Chapter 5 §5.6 has to choose between two ways of running an unmodified integration outside
the platform's process:

    R1  give it a stand-in `hass` and forward every attribute access to a mediator
    R2  run a real, stripped Home Assistant inside the sandbox, and forward only the
        permitted effects

R2's advantage is that Home Assistant's helper layer — which 91% of integrations import and
which R1 would have to emulate — is the genuine article. R2's risk is footprint: one core
per sandbox on a 4 GB Raspberry Pi. This script measures the risk and tests the premise.

It answers three questions, in order:

    Q1  Can a HomeAssistant object be constructed and started WITHOUT bootstrap, i.e.
        without the HTTP server, the recorder, the frontend or auth?
    Q2  Does an ordinary integration — one written against DataUpdateCoordinator,
        SensorEntity and async_add_entities, the 38%/63% pattern — actually run against it?
    Q3  What does that cost in resident memory and startup time?

Q3 is meaningless if Q1 or Q2 fails, so the script stops at the first failure and says so.

Run:  python measure.py [--json out.json]
Needs: Python >= 3.14.2 and `homeassistant` installed (see README.md in this directory).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).parent

# Stages are recorded as (label, resident KB, seconds since start). Resident memory is read
# from /proc rather than sampled, so each figure is the process as it stood at that moment.
STAGES: list[tuple[str, int, float]] = []
T0 = time.perf_counter()


def rss_kb() -> int:
    """Resident set size of this process, in KB, from /proc/self/status."""
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except OSError:
        pass
    return -1


def mark(label: str) -> None:
    STAGES.append((label, rss_kb(), time.perf_counter() - T0))
    print(f"  {label:<44} {STAGES[-1][1] / 1024:8.1f} MB   {STAGES[-1][2]:6.2f}s")


async def build_minimal_hass(config_dir: str, builder: str = "original"):
    """Construct and start a Home Assistant object without going through bootstrap.

    bootstrap.py imports the frontend unconditionally at module level — its own comment in
    pyproject.toml says so — which is exactly the weight a sandbox does not want. The
    recipe below is Home Assistant's own, taken from tests/common.py's
    async_test_home_assistant, minus the parts that exist only to accommodate mocks.
    """
    from homeassistant import config_entries, loader
    from homeassistant.core import CoreState, HomeAssistant
    from homeassistant.helpers import (
        area_registry,
        category_registry,
        condition,
        device_registry,
        entity,
        entity_registry,
        floor_registry,
        issue_registry,
        label_registry,
        restore_state,
        translation,
        trigger,
    )
    from homeassistant.util.hass_dict import HassKey
    from homeassistant.util.unit_system import METRIC_SYSTEM

    hass = HomeAssistant(config_dir)

    # No pip at runtime: a sandboxed integration must not be able to install packages,
    # and this also keeps the measurement free of network time.
    hass.config.skip_pip = True
    hass.config.skip_pip_packages = []
    hass.config.latitude = 51.5
    hass.config.longitude = -0.12
    hass.config.elevation = 0
    hass.config.units = METRIC_SYSTEM
    await hass.config.async_set_time_zone("UTC")

    # No custom-component scan of the real config dir; the sandbox supplies its own.
    hass.data[loader.DATA_CUSTOM_COMPONENTS] = None

    hass.config_entries = config_entries.ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()

    # Subsystems the helper layer reaches for. Home Assistant normally wires these up in
    # bootstrap, which cannot be used here: bootstrap imports `.components` at module level
    # — the frontend and the recorder's sensor support among them — which is precisely the
    # weight a sandbox exists to avoid. Doing it by hand is what keeps the instance small.
    entity.async_setup(hass)
    if builder == "corrected":
        # §7.31's two helpers, which bootstrap sets up beside `entity` and this recipe did not.
        from homeassistant.helpers import frame, template
        frame.async_setup(hass)
        template.async_setup(hass)
    loader.async_setup(hass)
    await condition.async_setup(hass)
    await trigger.async_setup(hass)
    hass.data[translation.TRANSLATION_FLATTEN_CACHE] = translation._TranslationCache(hass)  # noqa: SLF001
    device_registry.async_setup(hass)

    # The registries entity_platform and the entity base classes write into. An integration
    # cannot publish an entity without them.
    for reg in (
        area_registry, category_registry, device_registry, entity_registry,
        floor_registry, issue_registry, label_registry, restore_state,
    ):
        await reg.async_load(hass)

    # Tell the platform the registries are up. The key is constructed rather than imported
    # from bootstrap, for the reason above.
    hass.data[HassKey("bootstrap_registries_loaded")] = None

    if builder == "corrected":
        # §7.31: the `network` singleton is stage 0 in a real instance. And §6.3.3: the
        # instance is *not* marked running here. The caller starts it with `async_start()`
        # once the integration is set up, which fires EVENT_HOMEASSISTANT_START and the
        # deferred callbacks that `set_state` skips — the defect §7.20.4 left unmeasured.
        from homeassistant.components.network.network import async_get_network
        await async_get_network(hass)
        return hass

    hass.set_state(CoreState.running)
    return hass


async def start_if_corrected(hass, builder: str) -> None:
    """The corrected recipe's last step: start the instance the way the platform does."""
    if builder == "corrected":
        await hass.async_start()
        await hass.async_block_till_done()


async def run(builder: str = "original") -> dict:
    result: dict = {
        "builder": builder,
        "host": {
            "machine": platform.machine(),
            "python": platform.python_version(),
            "node": platform.node(),
        },
        "questions": {},
    }

    mark("bare interpreter")

    # --- Q1: can a minimal instance be built at all? --------------------------------
    import homeassistant.const as ha_const
    result["host"]["ha_version"] = ha_const.__version__
    mark("+ import homeassistant.const")

    from homeassistant.core import HomeAssistant  # noqa: F401
    mark("+ import homeassistant.core")

    # The helper layer: what 91% of integrations import, and what R1 would have to emulate.
    from homeassistant.helpers import entity_platform  # noqa: F401
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator  # noqa: F401
    from homeassistant.components.sensor import SensorEntity  # noqa: F401
    mark("+ import helper layer + sensor platform")

    config_dir = tempfile.mkdtemp(prefix="r2-sandbox-")
    shutil.copytree(HERE / "custom_components",
                    Path(config_dir) / "custom_components", dirs_exist_ok=True)

    try:
        hass = await build_minimal_hass(config_dir, builder)
    except Exception as err:  # noqa: BLE001 — the point of Q1 is to report the failure
        result["questions"]["Q1_minimal_instance"] = {"ok": False, "error": repr(err)}
        return result
    # The defect §7.20.4 names is that `set_state` never fires the start event, so the
    # deferred callbacks waiting on it never run. Listen for it, and the report says
    # whether it fired rather than inferring it from the recipe.
    from homeassistant.const import EVENT_HOMEASSISTANT_START
    fired: list = []
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, fired.append)
    mark("+ minimal hass constructed and running")
    result["questions"]["Q1_minimal_instance"] = {"ok": True}

    # --- Q2: does an ordinary integration run against it? ---------------------------
    from homeassistant.setup import async_setup_component

    # `homeassistant` is the platform's own base component; nothing loads without it.
    ok_base = await async_setup_component(hass, "homeassistant", {})
    mark("+ base 'homeassistant' component")

    # probe_sensor is written the way integrations are actually written: a config-entry
    # setup, a DataUpdateCoordinator, a SensorEntity, async_add_entities. It is loaded
    # from custom_components/, i.e. by exactly the path a HACS integration takes.
    from homeassistant.config_entries import ConfigEntry, ConfigEntryState, SOURCE_USER

    entry = ConfigEntry(
        version=1, minor_version=1, domain="probe_sensor", title="probe",
        data={"host": "example.invalid"}, source=SOURCE_USER, options={},
        unique_id=None, discovery_keys={}, subentries_data=(),
    )
    entry.add_to_hass(hass) if hasattr(entry, "add_to_hass") else None
    await hass.config_entries.async_add(entry)
    await hass.async_block_till_done()
    await start_if_corrected(hass, builder)
    mark("+ probe integration set up")

    result["core_state"] = str(hass.state)
    result["start_event_fired"] = bool(fired)
    result["start_event_pending_listeners"] = hass.bus.async_listeners().get(
        EVENT_HOMEASSISTANT_START, 0)

    states = hass.states.async_all()
    entity_ids = sorted(s.entity_id for s in states)
    published = [e for e in entity_ids if e.startswith("sensor.")]

    result["questions"]["Q2_integration_runs"] = {
        "ok": bool(published) and entry.state is ConfigEntryState.LOADED,
        "base_component": ok_base,
        "entry_state": str(entry.state),
        "entities_published": published,
        "all_entity_ids": entity_ids,
        "sensor_value": next(
            (s.state for s in states if s.entity_id in published), None),
    }

    # --- Q3: what did it cost? -------------------------------------------------------
    await hass.async_stop()
    mark("after hass.async_stop()")

    result["stages"] = [
        {"stage": s, "rss_mb": round(kb / 1024, 1), "elapsed_s": round(t, 2)}
        for s, kb, t in STAGES
    ]
    peak = max(kb for _, kb, _ in STAGES)
    result["questions"]["Q3_footprint"] = {
        "peak_rss_mb": round(peak / 1024, 1),
        "rss_at_running_mb": round(
            next(kb for s, kb, _ in STAGES if s.startswith("+ probe")) / 1024, 1),
        "time_to_running_s": round(
            next(t for s, _, t in STAGES if s.startswith("+ probe")), 2),
    }

    shutil.rmtree(config_dir, ignore_errors=True)
    return result


async def serve(builder: str = "original") -> None:
    """Build one sandbox, load the probe, announce readiness, then idle until killed.

    Used by measure_scale.py, which needs several live sandboxes at once to find the
    *marginal* cost of one. A single sandbox's RSS overstates that badly: the interpreter
    and the Home Assistant library are read-only pages the kernel shares between processes,
    so the second sandbox costs far less than the first.
    """
    config_dir = tempfile.mkdtemp(prefix="r2-sandbox-")
    shutil.copytree(HERE / "custom_components",
                    Path(config_dir) / "custom_components", dirs_exist_ok=True)
    hass = await build_minimal_hass(config_dir, builder)

    from homeassistant.config_entries import SOURCE_USER, ConfigEntry
    from homeassistant.setup import async_setup_component

    await async_setup_component(hass, "homeassistant", {})
    entry = ConfigEntry(
        version=1, minor_version=1, domain="probe_sensor", title="probe",
        data={"host": "example.invalid"}, source=SOURCE_USER, options={},
        unique_id=None, discovery_keys={}, subentries_data=(),
    )
    await hass.config_entries.async_add(entry)
    await hass.async_block_till_done()
    await start_if_corrected(hass, builder)

    print(f"READY {os.getpid()} {rss_kb()}", flush=True)
    while True:
        await asyncio.sleep(3600)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, help="write the full result here")
    ap.add_argument("--serve", action="store_true",
                    help="build one sandbox and idle (used by measure_scale.py)")
    ap.add_argument("--builder", choices=["original", "corrected"], default="original",
                    help="original: §5.6.3's recipe, kept so its figures stay reproducible; "
                         "corrected: §6.3.3's start order and §7.31's helpers, base component "
                         "kept, so the two differ only in what §7.20.4 asked about")
    args = ap.parse_args()

    if args.serve:
        import logging
        logging.disable(logging.CRITICAL)
        try:
            asyncio.run(serve(args.builder))
        except KeyboardInterrupt:
            pass
        return 0

    if sys.version_info < (3, 14, 2):
        print(f"Home Assistant 2026.8 needs Python >= 3.14.2; this is "
              f"{platform.python_version()}", file=sys.stderr)
        return 2

    print(f"R2 feasibility — {platform.machine()}, Python {platform.python_version()}, "
          f"{args.builder} builder")
    print(f"{'stage':<46} {'RSS':>11}   {'elapsed':>7}")
    result = asyncio.run(run(args.builder))

    q = result["questions"]
    print()
    print(f"Q1  minimal instance builds : {'YES' if q['Q1_minimal_instance']['ok'] else 'NO'}")
    if not q["Q1_minimal_instance"]["ok"]:
        print(f"    {q['Q1_minimal_instance']['error']}")
        return 1
    q2 = q["Q2_integration_runs"]
    print(f"Q2  integration runs        : {'YES' if q2['ok'] else 'NO'}"
          f"  (entry {q2['entry_state']}, entities {q2['entities_published']})")
    q3 = q["Q3_footprint"]
    print(f"    core state {result['core_state']}; start event fired: "
          f"{result['start_event_fired']}; listeners still waiting for it: "
          f"{result['start_event_pending_listeners']}")
    print(f"Q3  RSS with integration up : {q3['rss_at_running_mb']} MB"
          f"   (peak {q3['peak_rss_mb']} MB, ready in {q3['time_to_running_s']}s)")

    total_mb = None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                total_mb = int(line.split()[1]) / 1024
                break
    except OSError:
        pass
    if total_mb:
        share = q3["rss_at_running_mb"] / total_mb * 100
        print(f"    host has {total_mb:.0f} MB — one sandbox is {share:.1f}% of it, "
              f"about {int(total_mb * 0.6 // q3['rss_at_running_mb'])} sandboxes in 60% of RAM")
        result["questions"]["Q3_footprint"]["host_mem_mb"] = round(total_mb)

    if args.json:
        args.json.write_text(json.dumps(result, indent=2) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
