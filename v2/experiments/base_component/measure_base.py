#!/usr/bin/env python3
"""Does a sandbox need Home Assistant's own `homeassistant` base component?

§5.6.5 hands Chapter 6 one measurement to run before any other: **60 MB of the 176 MB a
sandbox costs is the platform's base component**, and §5.8.1's third qualification says
that if it can be dropped the sandbox budget roughly doubles. Neither section knows whether
it can be. This settles it.

Answering only "does the integration still load?" would be the cheap and dishonest version,
so the script asks four questions and reports all four even when one of them is inconvenient:

    Q1  Does an ordinary integration still load with the base component absent?
    Q2  What does dropping it actually save *at scale*?
    Q3  What is lost — what does the base component put in a sandbox that then is not there?
    Q4  Does state restoration survive, or was the base component carrying it?

Q2 is the question most easily got wrong. §5.6.3 established that a single sandbox's RSS
overstates the cost of N sandboxes, because interpreter and library pages are shared; the
same arithmetic applies to a *saving*. Sixty megabytes off one sandbox's RSS is sixty
megabytes off the budget only if those pages were private. So the saving is measured the
same way the cost was — marginally, across several live sandboxes — and not by subtracting
two single-process numbers.

Q4 is a falsification attempt. `custom_components/probe_restore/` publishes a generation
counter that only increments if state restoration actually ran, and the round trip is two
processes sharing a configuration directory, because restoration that "works" within one
process would prove nothing.

`build_minimal_hass` is imported from `experiments/r2_footprint/measure.py` rather than
copied. That is deliberate: this experiment's whole content is a difference between two
sandboxes, so both arms must be the same instance §5.6.3 measured, and a copy is a thing
that can drift.

Run:  python measure_base.py [--count 6] [--json results/out.json]
Needs: Python >= 3.14.2 and `homeassistant` installed (see r2_footprint/README.md).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "r2_footprint"))

from measure import build_minimal_hass, rss_kb  # noqa: E402  (path set above)

# The two probes. probe_sensor is the §5.6.3 integration, unchanged, so Q1 is asked against
# the same subject as the measurement it revises. probe_restore is new, and exists for Q4.
PROBES = ("probe_sensor", "probe_restore")


def meminfo_kb(field: str) -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(f"{field}:"):
            return int(line.split()[1])
    return -1


def proc_mem_kb(pid: int) -> dict[str, int]:
    """RSS and PSS for one process, from smaps_rollup."""
    out = {"rss_kb": -1, "pss_kb": -1}
    try:
        for line in Path(f"/proc/{pid}/smaps_rollup").read_text().splitlines():
            if line.startswith("Rss:"):
                out["rss_kb"] = int(line.split()[1])
            elif line.startswith("Pss:"):
                out["pss_kb"] = int(line.split()[1])
    except OSError:
        pass
    return out


# --------------------------------------------------------------------------- child side


def make_config_dir(base: str | None = None) -> str:
    config_dir = base or tempfile.mkdtemp(prefix="base-arm-")
    shutil.copytree(HERE / "custom_components",
                    Path(config_dir) / "custom_components", dirs_exist_ok=True)
    return config_dir


async def ensure_entry(hass, domain: str):
    """Add the probe's config entry, or set up the one already stored.

    Both cases occur: the footprint arms use a fresh configuration directory every time, and
    the restore round trip's second phase finds the entry its first phase persisted.
    """
    from homeassistant.config_entries import SOURCE_USER, ConfigEntry

    existing = hass.config_entries.async_entries(domain)
    if existing:
        await hass.config_entries.async_setup(existing[0].entry_id)
        return existing[0]
    entry = ConfigEntry(
        version=1, minor_version=1, domain=domain, title=domain,
        data={"host": "example.invalid"}, source=SOURCE_USER, options={},
        unique_id=None, discovery_keys={}, subentries_data=(),
    )
    await hass.config_entries.async_add(entry)
    return entry


async def build_arm(with_base: bool, config_dir: str, stages: list | None = None,
                    legacy_start: bool = False):
    """Build one sandbox, with or without the base component, and load both probes.

    `legacy_start` reproduces the recipe §5.6.3 published, which reaches the running state
    by calling `hass.set_state(CoreState.running)` directly. That is not the same thing as
    starting: it changes the flag without firing `EVENT_HOMEASSISTANT_START`, so every
    callback registered through `helpers.start.async_at_start` never runs. State restoration
    is one of them. This experiment found that by accident and the finding is kept rather
    than quietly patched, because a sandbox that silently loses state restoration is exactly
    the kind of defect a compatibility evaluation would later blame on confinement.
    """
    def mark(label: str) -> None:
        if stages is not None:
            stages.append({"stage": label, "rss_mb": round(rss_kb() / 1024, 1)})

    mark("bare interpreter")
    from homeassistant.components.sensor import SensorEntity  # noqa: F401
    from homeassistant.helpers import entity_platform  # noqa: F401
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator  # noqa: F401
    mark("+ import helper layer + sensor platform")

    hass = await build_minimal_hass(config_dir)
    mark("+ minimal hass constructed")

    if not legacy_start:
        # The correction. `build_minimal_hass` is imported unmodified from
        # experiments/r2_footprint so §5.6.3's numbers stay reproducible exactly as
        # published; the fix is applied here, where this experiment is answerable for it.
        await hass.async_start()
        mark("+ hass.async_start() — fires EVENT_HOMEASSISTANT_START")

    base_ok = None
    if with_base:
        from homeassistant.setup import async_setup_component
        base_ok = await async_setup_component(hass, "homeassistant", {})
    mark("+ base 'homeassistant' component" if with_base else "  (base component skipped)")

    entries = {}
    for domain in PROBES:
        entries[domain] = await ensure_entry(hass, domain)
    await hass.async_block_till_done()
    mark("+ probe integrations set up")
    return hass, entries, base_ok


def snapshot(hass, entries, base_ok) -> dict:
    """What this sandbox can do, recorded so the two arms can be diffed."""
    from homeassistant.config_entries import ConfigEntryState

    states = {s.entity_id: s for s in hass.states.async_all()}
    generation = states.get("sensor.probe_restore_generation")
    if generation is None:  # the entity id depends on the friendly name; find it
        generation = next((s for eid, s in states.items()
                           if "generation" in eid), None)
    return {
        "base_component_setup": base_ok,
        "entry_states": {d: str(e.state) for d, e in entries.items()},
        "all_loaded": all(e.state is ConfigEntryState.LOADED for e in entries.values()),
        "entities": sorted(states),
        "services": {domain: sorted(svcs)
                     for domain, svcs in sorted(hass.services.async_services().items())},
        "components": sorted(hass.config.components),
        "restore": {
            "entity_id": generation.entity_id if generation else None,
            "generation": generation.state if generation else None,
            "restored_from": (generation.attributes.get("restored_from")
                              if generation else None),
        },
    }


async def child_report(with_base: bool, legacy_start: bool = False) -> None:
    stages: list = []
    config_dir = make_config_dir()
    hass, entries, base_ok = await build_arm(with_base, config_dir, stages, legacy_start)
    out = snapshot(hass, entries, base_ok)
    out["stages"] = stages
    out["rss_mb"] = round(rss_kb() / 1024, 1)
    await hass.async_stop()
    shutil.rmtree(config_dir, ignore_errors=True)
    print("RESULT " + json.dumps(out), flush=True)


async def child_serve(with_base: bool, legacy_start: bool = False) -> None:
    config_dir = make_config_dir()
    hass, _, _ = await build_arm(with_base, config_dir, None, legacy_start)
    print(f"READY {os.getpid()} {rss_kb()}", flush=True)
    while True:
        await asyncio.sleep(3600)


async def child_restore(with_base: bool, config_dir: str,
                        legacy_start: bool = False) -> None:
    """One phase of the restore round trip against a persistent configuration directory."""
    make_config_dir(config_dir)
    hass, entries, base_ok = await build_arm(with_base, config_dir, None, legacy_start)
    out = snapshot(hass, entries, base_ok)["restore"]
    # The dump is hooked to EVENT_HOMEASSISTANT_STOP, so stopping is what persists state.
    await hass.async_stop()
    print("RESULT " + json.dumps(out), flush=True)


# -------------------------------------------------------------------------- parent side


def run_child(args_list: list[str]) -> dict:
    """Run one child and return the object on its RESULT line."""
    proc = subprocess.run([sys.executable, str(HERE / "measure_base.py"), *args_list],
                          capture_output=True, text=True, timeout=600)
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[len("RESULT "):])
    sys.stderr.write(proc.stdout[-2000:] + "\n" + proc.stderr[-2000:] + "\n")
    raise SystemExit(f"child {args_list} produced no RESULT line")


def scale_arm(with_base: bool, count: int) -> dict:
    """Marginal cost of a sandbox in this arm, by both of §5.6.3's methods.

    Both are reported because they disagree here and the disagreement is informative.
    `MemAvailable` is the whole machine before and after, which §5.6.3 called ground truth;
    it is also sensitive to what was already in the page cache, so the arm that runs second
    reads warm files and appears cheaper than it is. PSS is per process and carries no such
    history, so it is what this experiment quotes — and `--order` exists to demonstrate that
    the choice is not arbitrary.
    """
    flag = "yes" if with_base else "no"
    avail_before = meminfo_kb("MemAvailable")
    procs: list[subprocess.Popen] = []
    per_sandbox: list[dict] = []
    try:
        for i in range(count):
            p = subprocess.Popen(
                [sys.executable, str(HERE / "measure_base.py"), "--serve", "--base", flag],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            procs.append(p)
            line = p.stdout.readline()
            if not line.startswith("READY"):
                raise SystemExit(f"sandbox {i} (base={flag}) failed to start: {line!r}")
            time.sleep(0.3)
            avail_now = meminfo_kb("MemAvailable")
            per_sandbox.append({"n": i + 1, "pid": p.pid,
                                "machine_used_mb": round((avail_before - avail_now) / 1024, 1)})
        settled = [proc_mem_kb(p.pid) for p in procs]
        machine_delta = (avail_before - meminfo_kb("MemAvailable")) / 1024
        first = per_sandbox[0]["machine_used_mb"]
        marginal = (machine_delta - first) / (count - 1) if count > 1 else None
        sum_pss = sum(m["pss_kb"] for m in settled) / 1024
        return {
            "count": count,
            "sum_rss_mb": round(sum(m["rss_kb"] for m in settled) / 1024, 1),
            "sum_pss_mb": round(sum_pss, 1),
            "pss_per_sandbox_mb": round(sum_pss / count, 1),
            "machine_delta_mb": round(machine_delta, 1),
            "first_sandbox_mb": round(first, 1),
            "marginal_mb": round(marginal, 1) if marginal else None,
        }
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


def restore_round_trip(with_base: bool, legacy_start: bool) -> dict:
    """Two processes, one configuration directory. Phase b restores what phase a wrote."""
    flag = "yes" if with_base else "no"
    extra = ["--legacy-start"] if legacy_start else []
    config_dir = tempfile.mkdtemp(prefix="base-restore-")
    try:
        a = run_child(["--restore-phase", "a", "--config-dir", config_dir,
                       "--base", flag, *extra])
        b = run_child(["--restore-phase", "b", "--config-dir", config_dir,
                       "--base", flag, *extra])
        return {"phase_a": a, "phase_b": b,
                "restored": b.get("restored_from") is not None,
                "generation_advanced": (a.get("generation"), b.get("generation"))}
    finally:
        shutil.rmtree(config_dir, ignore_errors=True)


def capacity(per_sandbox_mb: float, total_mb: float) -> int:
    """Sandboxes in 60% of the machine — §5.6.3's budget, so the two are comparable."""
    if per_sandbox_mb <= 0:
        return 0
    return int(total_mb * 0.6 / per_sandbox_mb)


def parent(count: int, out_path: Path | None, order: list[str]) -> int:
    total_mb = meminfo_kb("MemTotal") / 1024
    print(f"Base component — {platform.machine()}, Python {platform.python_version()}, "
          f"{total_mb:.0f} MB, {count} sandboxes per arm, order {'/'.join(order)}\n")

    result: dict = {
        "host": {"machine": platform.machine(), "python": platform.python_version(),
                 "node": platform.node(), "mem_total_mb": round(total_mb)},
        "count": count, "order": order, "arms": {},
    }

    for label in order:
        with_base = label == "with_base"
        print(f"--- {label} " + "-" * (60 - len(label)))
        rep = run_child(["--report", "--base", "yes" if with_base else "no"])
        for st in rep["stages"]:
            print(f"  {st['stage']:<46} {st['rss_mb']:8.1f} MB")
        print(f"  entries: {rep['entry_states']}")
        print(f"  entities: {rep['entities']}")

        sc = scale_arm(with_base, count)
        cap = capacity(sc["pss_per_sandbox_mb"], total_mb)
        print(f"  at {count} sandboxes: PSS/sandbox {sc['pss_per_sandbox_mb']:.1f} MB "
              f"-> {cap} sandboxes in 60% of RAM")
        print(f"    (MemAvailable marginal {sc['marginal_mb']:.1f} MB — reported, "
              f"not quoted; see scale_arm)")

        restores = {}
        for recipe, legacy in (("corrected", False), ("legacy_5_6_3", True)):
            rt = restore_round_trip(with_base, legacy)
            restores[recipe] = rt
            print(f"  restore, {recipe:<12} generations {rt['generation_advanced']}  "
                  f"{'RESTORED' if rt['restored'] else 'NOT RESTORED'}")

        result["arms"][label] = {"report": rep, "scale": sc,
                                 "restore": restores, "capacity": cap}
        print()

    a, b = result["arms"]["with_base"], result["arms"]["without_base"]
    lost_services = {d: sorted(set(sv) - set(b["report"]["services"].get(d, [])))
                     for d, sv in a["report"]["services"].items()}
    lost_services = {d: sv for d, sv in lost_services.items() if sv}
    result["delta"] = {
        "single_rss_saved_mb": round(a["report"]["rss_mb"] - b["report"]["rss_mb"], 1),
        "pss_saved_per_sandbox_mb": round(a["scale"]["pss_per_sandbox_mb"]
                                          - b["scale"]["pss_per_sandbox_mb"], 1),
        "memavailable_marginal_saved_mb": round(a["scale"]["marginal_mb"]
                                                - b["scale"]["marginal_mb"], 1),
        "capacity": [a["capacity"], b["capacity"]],
        "capacity_ratio": round(b["capacity"] / a["capacity"], 2) if a["capacity"] else None,
        "services_lost": lost_services,
        "components_lost": sorted(set(a["report"]["components"])
                                  - set(b["report"]["components"])),
        "entities_lost": sorted(set(a["report"]["entities"]) - set(b["report"]["entities"])),
        "still_loads": b["report"]["all_loaded"],
        "restore_corrected": {k: v["restore"]["corrected"]["restored"]
                              for k, v in result["arms"].items()},
        "restore_legacy": {k: v["restore"]["legacy_5_6_3"]["restored"]
                           for k, v in result["arms"].items()},
    }
    d = result["delta"]
    print("=" * 74)
    print(f"Q1  integration still loads without it : {'YES' if d['still_loads'] else 'NO'}")
    print(f"Q2  saved on one sandbox (RSS)         : {d['single_rss_saved_mb']:.1f} MB")
    print(f"    saved per sandbox at scale (PSS)   : "
          f"{d['pss_saved_per_sandbox_mb']:.1f} MB   <- the figure that moves the budget")
    print(f"    capacity  {d['capacity'][0]} -> {d['capacity'][1]} sandboxes "
          f"({d['capacity_ratio']}x)")
    print(f"Q3  services lost                      : "
          f"{sum(len(v) for v in d['services_lost'].values())} "
          f"across {sorted(d['services_lost'])}")
    print(f"    components lost                    : {d['components_lost']}")
    print(f"    entities lost                      : {d['entities_lost'] or 'none'}")
    print(f"Q4  restoration, corrected recipe      : {d['restore_corrected']}")
    print(f"    restoration, §5.6.3 recipe as published : {d['restore_legacy']}")

    if out_path:
        out_path.write_text(json.dumps(result, indent=2) + "\n")
        print(f"\nwrote {out_path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", choices=["yes", "no"], help="child mode: set up the base component")
    ap.add_argument("--serve", action="store_true", help="child mode: build one sandbox and idle")
    ap.add_argument("--report", action="store_true", help="child mode: build one sandbox and report")
    ap.add_argument("--restore-phase", choices=["a", "b"], help="child mode: restore round trip")
    ap.add_argument("--config-dir", help="child mode: persistent configuration directory")
    ap.add_argument("--legacy-start", action="store_true",
                    help="child mode: reproduce §5.6.3's recipe, which never fires "
                         "EVENT_HOMEASSISTANT_START")
    ap.add_argument("--count", type=int, default=6, help="sandboxes per arm for the scale run")
    ap.add_argument("--order", default="with_base,without_base",
                    help="arm order; reverse it to expose the page-cache artifact")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    if args.serve or args.report or args.restore_phase:
        logging.disable(logging.CRITICAL)
        with_base = args.base == "yes"
        try:
            if args.serve:
                asyncio.run(child_serve(with_base, args.legacy_start))
            elif args.report:
                asyncio.run(child_report(with_base, args.legacy_start))
            else:
                asyncio.run(child_restore(with_base, args.config_dir, args.legacy_start))
        except KeyboardInterrupt:
            pass
        return 0

    if sys.version_info < (3, 14, 2):
        print(f"Home Assistant 2026.8 needs Python >= 3.14.2; this is "
              f"{platform.python_version()}", file=sys.stderr)
        return 2
    order = [a.strip() for a in args.order.split(",")]
    if sorted(order) != ["with_base", "without_base"]:
        print(f"--order must name both arms once: {args.order!r}", file=sys.stderr)
        return 2
    return parent(args.count, args.json, order)


if __name__ == "__main__":
    sys.exit(main())
