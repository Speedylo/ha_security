"""The five platform-only end-to-end integrations, retested for function (2026-10-09).

§7.17 and the 2026-10-03 rerun showed these five *load* confined and unconfined. Only
`thermal_comfort` was checked against a value; for the other four the runs counted entities, and
three of them never did their job (`notes/e2e_functional_retest_prediction.md` §0). This gives
each a stimulus and records what it produced, in both arms and in the withheld-clause arms.
The predictions were committed before this file existed; `verdicts()` reads them off the reports.

It is a separate module so that the harness every earlier result came from (`endtoend.py`) is
unchanged. The runtime gained only opt-in fields (`steps`, `report_attributes`,
`record_services`, `report_history`), which no earlier caller sends.

Run (on the Pi, from `framework/`):
    systemd-run --user --scope -q python3 -m confine.endtoend_function \\
        --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python --json OUT.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .audit import attach
from .audit import summarise as durable_summary
from .cgroup import Delegation, SandboxCgroup
from .channel import Channel
from .compat import (DEPS, PLATFORM_DEPS, component_requirements, declared_components_of,
                     declared_requirements, find_ha_components, install_requirements)
from .endtoend import WORLD
from .manifest import Manifest
from .mediator import Mediator
from .platform import Platform, acting_policy
from .preflight import require_ready
from .provenance import record_run
from .sandbox import SandboxSpec
from .selftest_bridge import interpreter_trees
from .spawn import SandboxFailed, become_subreaper, start

HERE = Path(__file__).resolve().parent

LIGHT = "light.living_room"
TEMPERATURE = "sensor.living_room_temperature"
HUMIDITY = "sensor.living_room_humidity"
MODES = {"supported_color_modes": ["brightness"]}

# P2's file. One declared entity, one that exists but is undeclared confined, one that exists
# nowhere, and one action that exists nowhere (prediction §3, P2).
WATCHMAN_YAML = f"""- id: retest
  alias: retest
  triggers:
    - trigger: state
      entity_id: {TEMPERATURE}
  conditions:
    - condition: state
      entity_id: {LIGHT}
      state: "on"
    - condition: state
      entity_id: sensor.does_not_exist
      state: "on"
  actions:
    - action: notify.nobody_here
"""

READ_LIGHT = {"read": [LIGHT], "subscribe": [LIGHT]}

POWERCALC = {
    "domain": "powercalc",
    "flow_input": {"entity_id": LIGHT, "name": "lamp power", "mode": "linear",
                   "min_power": 1, "max_power": 11},
    "menu_choice": {"user": "virtual_power"},
    "settle": 45,
    "steps": [{"kind": "world", "at": 15, "entity": LIGHT, "state": "on",
               "attributes": {**MODES, "brightness": 51}},
              {"kind": "world", "at": 30, "entity": LIGHT, "state": "off",
               "attributes": MODES}],
}
WATCHMAN = {"domain": "watchman", "flow_input": {}, "settle": 45,
            "config_files": {"automations.yaml": WATCHMAN_YAML}}
ADAPTIVE = {
    "domain": "adaptive_lighting", "flow_input": {"name": "confined test"}, "settle": 30,
    "steps": [{"kind": "options_flow", "at": 2, "input": {"lights": [LIGHT]}}],
    "record_services": ["light.turn_on"],
}
SCHEDULER = {
    "domain": "scheduler", "flow_input": {}, "settle": 160,
    "steps": [{"kind": "service", "at": 2, "domain": "scheduler", "service": "add",
               "data": {"timeslots": [{"start": "$START", "actions": [
                   {"service": "light.turn_on", "entity_id": LIGHT,
                    "service_data": {"brightness": 200}}]}],
                        "repeat_type": "single", "name": "retest"}}],
    "record_services": ["light.turn_on"],
}
THERMAL = {
    "domain": "thermal_comfort", "settle": 10,
    "flow_input": {"name": "living room", "temperature_sensor": TEMPERATURE,
                   "humidity_sensor": HUMIDITY},
}

#: Each variant: a base subject and the manifest the confined arm gets. `arms` says which arms
#: run it; a withheld-clause variant has no unconfined counterpart, since nothing is withheld there.
VARIANTS: dict[str, dict] = {
    "powercalc": {**POWERCALC, "permissions": {"entities": READ_LIGHT}},
    "powercalc-no-subscribe": {**POWERCALC, "arms": ["confined"],
                               "permissions": {"entities": {"read": [LIGHT]}}},
    "powercalc-no-read": {**POWERCALC, "arms": ["confined"], "permissions": {}},
    "watchman": {**WATCHMAN, "permissions": {"entities": {"read": [TEMPERATURE]}}},
    "watchman-both-declared": {**WATCHMAN, "arms": ["confined"],
                               "permissions": {"entities": {"read": [TEMPERATURE, LIGHT]}}},
    "adaptive_lighting": {**ADAPTIVE, "permissions": {
        "entities": READ_LIGHT, "services": {"call": ["light.turn_on"]}}},
    "adaptive_lighting-no-service": {**ADAPTIVE, "arms": ["confined"],
                                     "permissions": {"entities": READ_LIGHT}},
    # An integration that acts on a device must see it: `scheduler` checks that its target exists
    # before acting (amendment 2, 2026-10-09). Without the read it fires and declines.
    "scheduler": {**SCHEDULER, "permissions": {"entities": {"read": [LIGHT]},
                                               "services": {"call": ["light.turn_on"]}}},
    "scheduler-no-read": {**SCHEDULER, "arms": ["confined"],
                          "permissions": {"services": {"call": ["light.turn_on"]}}},
    "scheduler-no-service": {**SCHEDULER, "arms": ["confined"],
                             "permissions": {"entities": {"read": [LIGHT]}}},
    "thermal_comfort": {**THERMAL, "permissions": {
        "entities": {"read": [TEMPERATURE, HUMIDITY]}}},
}


def _install(component: Path, deps: Path, python: Path, uv: str | None) -> dict:
    wanted = declared_components_of(component)
    extra = component_requirements(wanted, find_ha_components(python))
    install = {"ok": True, "installed": [], "note": "not attempted"}
    if uv:
        try:
            install = install_requirements(declared_requirements(component) + extra,
                                           deps, python, uv)
        except (subprocess.TimeoutExpired, OSError) as err:
            install = {"ok": False, "installed": [], "error": str(err)[:200]}
    deps.mkdir(parents=True, exist_ok=True)
    return install


def run_confined(name: str, variant: dict, component: Path, python: Path,
                 delegation: Delegation, uv: str | None, platform_deps: Path | None) -> dict:
    domain = variant["domain"]
    root = Path(tempfile.mkdtemp(prefix=f"fn-{domain}-"))
    mediator = Mediator()
    audit_dir = attach(mediator, f"fn-audit-{domain}-")
    durable: dict = {}
    platform = Platform()
    # Every state the platform holds, in order, the world's changes included, so a value can be
    # read before and after each step. And every call the mediator let through, with its time.
    history: list[list] = []
    calls: list[dict] = []
    began: list[float] = []
    try:
        own = root / "custom_components" / domain
        own.parent.mkdir(parents=True)
        shutil.copytree(component, own, ignore=shutil.ignore_patterns("__pycache__"))
        permissions = {"schema_version": 1, **variant["permissions"]}
        (root / "custom_components" / f"{domain}.permissions.json").write_text(
            json.dumps(permissions))
        data = root / ".confine" / domain
        data.mkdir(parents=True)
        for filename, text in (variant.get("config_files") or {}).items():
            (data / filename).write_text(text)
        deps = root / "deps"
        install = _install(component, deps, python, uv)

        for entity_id, (state, attributes) in WORLD.items():
            platform.seed(entity_id, state, **attributes)

        def observe(entity_id: str, state: str, _attributes: dict) -> None:
            history.append([entity_id, state])
            # The clock for the world's steps starts at the integration's first publish of its
            # own, the nearest this side has to the unconfined arm's "after async_start".
            if entity_id not in WORLD and not began:
                began.append(time.monotonic())
        platform.listeners.append(observe)

        def call_service(service_domain: str, service: str, data: dict) -> None:
            from datetime import datetime, timezone
            calls.append({"service": f"{service_domain}.{service}", "data": data,
                          "utc": datetime.now(timezone.utc).isoformat()})
            Platform.call_service(platform, service_domain, service, data)
        platform.call_service = call_service  # type: ignore[method-assign]

        manifest = Manifest.load(own, root)
        mediator.policy = acting_policy({domain: manifest}, platform)
        platform.listeners.append(mediator.push)
        mediator_end, sandbox_end = Channel.pair()
        mediator.register(domain, Channel(mediator_end), component=own, installed=deps)

        entities = permissions.get("entities") or {}
        wanted = declared_components_of(component)
        spec_file = root / "spec.json"
        spec_file.write_text(json.dumps({
            "domain": domain, "mode": "flow", "auth": True,
            "entities": list(entities.get("read") or []),
            "services": list((permissions.get("services") or {}).get("call") or []),
            "setup_components": wanted,
            "push": True, "settle_seconds": variant.get("settle", 0),
            "steps": [s for s in variant.get("steps") or [] if s["kind"] != "world"]
                     or [{"kind": "none", "at": 0}],
            "report_attributes": True,
            "menu_choice": variant.get("menu_choice") or {},
            "flow_input": variant["flow_input"]}))

        spec = SandboxSpec(
            domain=domain, own_dir=str(own), data_dir=str(data),
            argv=[str(python), "/sandbox/runtime.py"],
            runtime_files={str(HERE / "sandbox_runtime.py"): "/sandbox/runtime.py",
                           str(spec_file): "/sandbox/spec.json",
                           str(deps): DEPS},
            env={"PYTHONPATH": DEPS})
        if platform_deps:
            spec.runtime_files[str(platform_deps)] = PLATFORM_DEPS
            spec.env["PYTHONPATH"] = f"{DEPS}:{PLATFORM_DEPS}"
        for tree in (*interpreter_trees(python), sys.base_prefix):
            if tree and tree not in spec.runtime_paths:
                spec.runtime_paths.append(tree)

        world_steps = sorted((s for s in variant.get("steps") or [] if s["kind"] == "world"),
                             key=lambda s: s["at"])
        out = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        err = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        limits = manifest.resources
        spec.tmp_size_mb = limits.disk_mb
        with SandboxCgroup.create(delegation, f"fn-{domain}"[:60], limits) as cgroup:
            with open(out.name, "wb") as stdout, open(err.name, "wb") as stderr:
                sandbox = start(spec, cgroup, stdout=stdout.fileno(), stderr=stderr.fileno(),
                                channel_end=sandbox_end.fileno())
                sandbox_end.detach()
                # Served in one-second slices so the world's steps are applied between requests,
                # on this thread, never inside one: the rule `Mediator.serve` keeps for (A).
                deadline = time.monotonic() + 300
                while mediator.open_channels and time.monotonic() < deadline:
                    mediator.serve(timeout=1.0, until=time.monotonic() + 1.0)
                    while world_steps and began and \
                            time.monotonic() - began[0] >= world_steps[0]["at"]:
                        step = world_steps.pop(0)
                        history.append(["<world>", f"{step['entity']} {step['state']}"])
                        platform.set_state(step["entity"], step["state"], step["attributes"])
                sandbox.wait(timeout=60)
        text = Path(out.name).read_text().strip()
        diagnostic = Path(err.name).read_text().strip()
        Path(out.name).unlink(missing_ok=True)
        Path(err.name).unlink(missing_ok=True)
    except (SandboxFailed, OSError, TimeoutError) as error:
        return {"variant": name, "arm": "confined", "level": "sandbox_failed",
                "error": str(error)[:200]}
    finally:
        shutil.rmtree(root, ignore_errors=True)
        durable = durable_summary(mediator, audit_dir)

    if not text:
        tail = diagnostic.splitlines()
        return {"variant": name, "arm": "confined", "level": "no_report", "durable": durable,
                "error": tail[-1][:200] if tail else ""}
    report = json.loads(text.splitlines()[-1])
    report.update({"variant": name, "arm": "confined", "install": install, "durable": durable,
                   "decisions": list(mediator.audit), "history": history, "calls": calls,
                   "platform_states": {k: v[0] for k, v in platform.states.items()},
                   "log_tail": diagnostic.splitlines()[-15:]})
    return report


def run_unconfined(name: str, variant: dict, component: Path, python: Path, uv: str | None,
                   platform_deps: Path | None) -> dict:
    domain = variant["domain"]
    root = Path(tempfile.mkdtemp(prefix=f"fn-base-{domain}-"))
    try:
        config = root / "config"
        (config / "custom_components").mkdir(parents=True)
        # Linked, not copied in: the sandbox links its read-only copy into the same place
        # (`place_component`), and a recursive scan of the config directory (`watchman`) does not
        # follow a link. A real directory here would be scanned in this arm only.
        code = root / "component"
        shutil.copytree(component, code, ignore=shutil.ignore_patterns("__pycache__"))
        (config / "custom_components" / domain).symlink_to(code)
        for filename, text in (variant.get("config_files") or {}).items():
            (config / filename).write_text(text)
        for module in ("sandbox_runtime.py", "endtoend_unconfined.py"):
            shutil.copy2(HERE / module, root / module)
        deps = root / "deps"
        _install(component, deps, python, uv)

        spec_file = root / "spec.json"
        spec_file.write_text(json.dumps({
            "domain": domain, "config_dir": str(config),
            "setup_components": declared_components_of(component),
            "world": {k: list(v) for k, v in WORLD.items()},
            "settle_seconds": variant.get("settle", 0),
            "steps": variant.get("steps") or [{"kind": "none", "at": 0}],
            "report_attributes": True, "report_history": True,
            "record_services": variant.get("record_services") or [],
            "menu_choice": variant.get("menu_choice") or {},
            "flow_input": variant["flow_input"]}))
        path = [str(deps)] + ([str(platform_deps)] if platform_deps else [])
        env = {**os.environ, "PYTHONPATH": ":".join(path)}
        try:
            proc = subprocess.run(
                [str(python), str(root / "endtoend_unconfined.py"), str(spec_file)],
                capture_output=True, text=True, timeout=600, env=env, cwd=str(root))
        except subprocess.TimeoutExpired:
            return {"variant": name, "arm": "unconfined", "level": "timeout"}
    finally:
        shutil.rmtree(root, ignore_errors=True)
    text = (proc.stdout or "").strip()
    if not text:
        tail = (proc.stderr or "").strip().splitlines()
        return {"variant": name, "arm": "unconfined", "level": "no_report",
                "error": tail[-1][:200] if tail else ""}
    report = json.loads(text.splitlines()[-1])
    report.update({"variant": name, "arm": "unconfined",
                   "log_tail": (proc.stderr or "").strip().splitlines()[-15:]})
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--uv", default=str(Path.home() / ".local/bin/uv"))
    ap.add_argument("--only", help="comma-separated variant names")
    ap.add_argument("--arm", choices=["confined", "unconfined", "both"], default="both")
    ap.add_argument("--json", type=Path, required=True)
    args = ap.parse_args()

    python = Path(args.python)
    uv = args.uv if Path(args.uv).exists() else None
    platform_deps = Path.home() / "r2exp/platform-deps"
    platform_deps = platform_deps if platform_deps.is_dir() else None
    delegation = None
    if args.arm != "unconfined":
        require_ready(deep=False)
        become_subreaper()
        delegation = Delegation.discover()

    only = set(args.only.split(",")) if args.only else None
    results = []
    for name, variant in VARIANTS.items():
        if only and name not in only:
            continue
        component = args.corpus / variant["domain"]
        arms = variant.get("arms") or ["confined", "unconfined"]
        # Back to back, unconfined first, so the two arms of one integration are minutes apart
        # (`adaptive_lighting`'s output moves with the sun).
        for arm in ("unconfined", "confined"):
            if arm not in arms or args.arm not in (arm, "both"):
                continue
            print(f"  {name:<30} {arm:<10}", end=" ", flush=True)
            if arm == "confined":
                report = run_confined(name, variant, component, python, delegation, uv,
                                      platform_deps)
            else:
                report = run_unconfined(name, variant, component, python, uv, platform_deps)
            results.append(report)
            print("loaded" if report.get("loaded") else report.get("level", "not loaded"))
            args.json.write_text(json.dumps(results, indent=2) + "\n")
    record_run(args.json)  # F14
    print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
