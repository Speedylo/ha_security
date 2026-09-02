"""N2's second number: real integrations set up through their own config flows, confined.

§3.6's N2 requires that "executed end-to-end" be reported **separately** from "imports-clean",
and never conflated, because import success is an upper bound on compatibility. §7.12 supplied
the first number across 37 integrations. This supplies the second, and it does not scale to 37
for a reason worth stating rather than apologising for.

**Why the set is small, and why the reason is itself a result.** A config entry needs data only
each integration's own flow can produce, and for most of this corpus that data is a credential
or a device on the network. Surveying the 37 by what their `config_flow.py` asks for:

    26 of 37   ask for an API key, token, password, username, host or email
    11 of 37   ask for none of those — they are configured from other entities or from
               nothing at all

**So the ceiling on any end-to-end measurement of this corpus is 11, not 37**, and it is a
property of the ecosystem rather than of this framework. Anyone repeating this measurement —
including for an unconfined baseline — meets the same wall. Reporting a rate over 37 would
therefore be doubly wrong: it would conflate N2's two numbers *and* imply a denominator that
no measurement of any confinement scheme could reach.

**The selection is stated so it can be argued with.** From the 11, this takes those that
exercise something the design must get right, and it excludes `battery_notes` because §7.12
established it fails at import on this release in **both** arms.

Run:  systemd-run --user --scope -q python3 -m confine.endtoend --corpus ~/r2exp/corpus \\
          --python ~/r2exp/ha314/bin/python
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import os

from .cgroup import Delegation, SandboxCgroup
from .channel import Channel
from .compat import (DEPS, PLATFORM_DEPS, component_requirements, declared_components_of,
                     declared_requirements, find_ha_components, install_requirements)
from .manifest import Manifest
from .mediator import Mediator
from .platform import Platform, acting_policy
from .preflight import require_ready
from .sandbox import SandboxSpec
from .selftest_bridge import interpreter_trees
from .spawn import Sandbox, SandboxFailed, become_subreaper, start

HERE = Path(__file__).resolve().parent

# The entities the sandbox's world contains, so that an integration configured *from* entities
# has something real to be configured from. Seeded in the mediator's platform and declared by
# whichever subject needs them, so they arrive by the mediated read path and no other.
WORLD = {
    "sensor.living_room_temperature": ("21.4", {"unit_of_measurement": "°C",
                                                "device_class": "temperature"}),
    "sensor.living_room_humidity": ("48", {"unit_of_measurement": "%",
                                           "device_class": "humidity"}),
    "light.living_room": ("on", {"supported_color_modes": ["brightness"], "brightness": 180}),
}

# Each subject: what it declares, and the input its own flow needs. The flow input is the
# integration's, not the harness's — it is fed to `async_configure`, and the integration
# validates it exactly as it would from the UI.
SUBJECTS: dict[str, dict] = {
    "scheduler": {
        "why": "its flow creates an entry from no input at all — the simplest possible "
               "end-to-end case, and it isolates setup from configuration",
        "permissions": {"schema_version": 1},
        "flow_input": {},
    },
    "adaptive_lighting": {
        "why": "configured from a name and a light entity; exercises an integration that "
               "acts on another integration's entity",
        "permissions": {"schema_version": 1,
                        "entities": {"read": ["light.living_room"]}},
        "flow_input": {"name": "confined test"},
    },
    "thermal_comfort": {
        "why": "**the case that matters.** It is configured from two entities it does not "
               "own, reads them through the mediator, and publishes derived sensors back "
               "out — the whole mediated round trip in one integration",
        "permissions": {"schema_version": 1,
                        "entities": {"read": ["sensor.living_room_temperature",
                                              "sensor.living_room_humidity"]}},
        "flow_input": {"name": "living room",
                       "temperature_sensor": "sensor.living_room_temperature",
                       "humidity_sensor": "sensor.living_room_humidity"},
    },
    "powercalc": {
        "why": "configured from another integration's entity and publishes derived power "
               "sensors; a second instance of the round trip, by a different author",
        "permissions": {"schema_version": 1,
                        "entities": {"read": ["light.living_room"]}},
        "flow_input": {"entity_id": "light.living_room", "name": "lamp power",
                       "fixed_value": 5},
        "menu_choice": {"user": "virtual_power"},
    },
    "watchman": {
        "why": "configured from nothing external and inspects the instance it runs in, so it "
               "sees the confined world rather than the user's",
        "permissions": {"schema_version": 1},
        "flow_input": {},
    },
}


def run_one(domain: str, component: Path, subject: dict, python: Path,
            delegation: Delegation, uv: str | None, platform_deps: Path | None) -> dict:
    root = Path(tempfile.mkdtemp(prefix=f"e2e-{domain}-"))
    mediator = Mediator()
    try:
        own = root / "custom_components" / domain
        own.parent.mkdir(parents=True)
        shutil.copytree(component, own)
        # The authority manifest goes beside the integration, never inside its own manifest.json
        # — §5.9.4's precedence: the file's location is the provenance signal, and rewriting the
        # integration's own file would breach C1.
        (root / "custom_components" / f"{domain}.permissions.json").write_text(
            json.dumps(subject["permissions"]))
        data = root / ".confine" / domain
        data.mkdir(parents=True)

        deps = root / "deps"
        install = {"ok": True, "installed": [], "note": "not attempted"}
        wanted = declared_components_of(component)
        extra = component_requirements(wanted, find_ha_components(python))
        if uv:
            try:
                install = install_requirements(declared_requirements(component) + extra,
                                               deps, python, uv)
            except (subprocess.TimeoutExpired, OSError) as err:
                install = {"ok": False, "installed": [], "error": str(err)[:200]}
        deps.mkdir(parents=True, exist_ok=True)

        platform = Platform()
        for entity_id, (state, attributes) in WORLD.items():
            platform.seed(entity_id, state, **attributes)

        manifest = Manifest.load(own, root)
        mediator.policy = acting_policy({domain: manifest}, platform)
        mediator_end, sandbox_end = Channel.pair()
        mediator.register(domain, Channel(mediator_end))

        declared_entities = list(
            (subject["permissions"].get("entities") or {}).get("read") or [])
        spec_file = root / "spec.json"
        spec_file.write_text(json.dumps({
            "domain": domain, "mode": "flow", "auth": True,
            "entities": declared_entities, "services": [],
            "setup_components": wanted,
            "record_egress": True,
            "menu_choice": subject.get("menu_choice") or {},
            "flow_input": subject["flow_input"]}))

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

        out = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        err = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        limits = replace(manifest.resources, memory_mb=max(manifest.resources.memory_mb, 640))
        spec.tmp_size_mb = limits.disk_mb
        with SandboxCgroup.create(delegation, f"e2e-{domain}"[:60], limits) as cgroup:
            with open(out.name, "wb") as stdout, open(err.name, "wb") as stderr:
                sandbox: Sandbox = start(spec, cgroup, stdout=stdout.fileno(),
                                         stderr=stderr.fileno(),
                                         channel_end=sandbox_end.fileno())
                sandbox_end.detach()
                mediator.serve(timeout=300)
                sandbox.wait(timeout=300)
        text = Path(out.name).read_text().strip()
        diagnostic = Path(err.name).read_text().strip()
        Path(out.name).unlink(missing_ok=True)
        Path(err.name).unlink(missing_ok=True)
    except (SandboxFailed, OSError, TimeoutError) as err:
        return {"domain": domain, "level": "sandbox_failed", "error": str(err)[:200]}
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if not text:
        tail = diagnostic.splitlines()
        return {"domain": domain, "level": "no_report", "install": install,
                "error": tail[-1][:200] if tail else ""}
    report = json.loads(text.splitlines()[-1])
    if "fatal" in report:
        return {"domain": domain, "level": "fatal", "install": install,
                "error": report["fatal"].strip().splitlines()[-1][:200]}
    report["install"] = install
    report["decisions"] = [d for d in mediator.audit]
    report["platform_states"] = {k: v[0] for k, v in platform.states.items()
                                 if k not in WORLD}
    return report


def run_one_unconfined(domain: str, component: Path, subject: dict, python: Path,
                       uv: str | None, platform_deps: Path | None) -> dict:
    """The same integration, the same flow, no sandbox. §7.17.5's owed comparison."""
    root = Path(tempfile.mkdtemp(prefix=f"e2e-base-{domain}-"))
    try:
        config = root / "config"
        (config / "custom_components").mkdir(parents=True)
        shutil.copytree(component, config / "custom_components" / domain)
        for name in ("sandbox_runtime.py", "endtoend_unconfined.py"):
            shutil.copy2(HERE / name, root / name)

        deps = root / "deps"
        wanted = declared_components_of(component)
        extra = component_requirements(wanted, find_ha_components(python))
        if uv:
            try:
                install_requirements(declared_requirements(component) + extra, deps, python, uv)
            except (subprocess.TimeoutExpired, OSError):
                pass
        deps.mkdir(parents=True, exist_ok=True)

        spec_file = root / "spec.json"
        spec_file.write_text(json.dumps({
            "domain": domain, "config_dir": str(config),
            "setup_components": wanted,
            "world": {k: list(v) for k, v in WORLD.items()},
            "record_egress": True,
            "menu_choice": subject.get("menu_choice") or {},
            "flow_input": subject["flow_input"]}))

        path = [str(deps)] + ([str(platform_deps)] if platform_deps else [])
        env = {**os.environ, "PYTHONPATH": ":".join(path)}
        try:
            proc = subprocess.run(
                [str(python), str(root / "endtoend_unconfined.py"), str(spec_file)],
                capture_output=True, text=True, timeout=600, env=env, cwd=str(root))
        except subprocess.TimeoutExpired:
            return {"domain": domain, "arm": "unconfined", "level": "timeout"}
        text = (proc.stdout or "").strip()
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if not text:
        tail = (proc.stderr or "").strip().splitlines()
        return {"domain": domain, "arm": "unconfined", "level": "no_report",
                "error": tail[-1][:200] if tail else ""}
    report = json.loads(text.splitlines()[-1])
    if "fatal" in report:
        return {"domain": domain, "arm": "unconfined", "level": "fatal",
                "error": report["fatal"].strip().splitlines()[-1][:200]}
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--uv", default=str(Path.home() / ".local/bin/uv"))
    ap.add_argument("--only", help="one domain, for iterating")
    ap.add_argument("--baseline", action="store_true",
                    help="§7.17.5's arm: the same five unconfined, so the two failures are "
                         "attributed by comparison rather than by their tracebacks")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    delegation = None
    if not args.baseline:
        require_ready(deep=False)
        become_subreaper()
        delegation = Delegation.discover()
    python = Path(args.python)
    uv = args.uv if Path(args.uv).exists() else None
    platform_deps = Path.home() / "r2exp/platform-deps"
    platform_deps = platform_deps if platform_deps.is_dir() else None

    subjects = {k: v for k, v in SUBJECTS.items() if not args.only or k == args.only}
    arm = "UNCONFINED (§7.17.5's baseline)" if args.baseline else "confined"
    print(f"N2's second number — {len(subjects)} integrations through their own config flows, "
          f"{arm}\n")

    results = []
    for index, (domain, subject) in enumerate(subjects.items(), 1):
        component = args.corpus / domain
        if not component.is_dir():
            print(f"  [{index}] {domain:<20} not in the corpus")
            continue
        if args.baseline:
            report = run_one_unconfined(domain, component, subject, python, uv, platform_deps)
        else:
            report = run_one(domain, component, subject, python, delegation, uv, platform_deps)
        results.append(report)
        entities = [e for e in report.get("own_entities", report.get("local_entities", []))
                    if e.split(".")[0] not in ("persistent_notification",)
                    and e not in WORLD]
        published = len(report.get("published") or [])
        mark = "ok  " if report.get("loaded") else "    "
        detail = (f"entry {report['entries'][0]['state'].split('.')[-1]}"
                  if report.get("entries") else
                  f"{report.get('level', 'no entry')}: {(report.get('error') or '')[:40]}")
        print(f"  [{index}] {mark}{domain:<20} {detail:<34} "
              f"own entities {len(entities):>2}  published {published:>2}")

    loaded = [r for r in results if r.get("loaded")]
    publishing = [r for r in results if (r.get("published") or [])]
    print(f"\n  config entry LOADED           {len(loaded)}/{len(results)}")
    print(f"  published through the mediator {len(publishing)}/{len(results)}")
    print("\n  Reported as a named set, never as a rate (§3.6 N2). The denominator for any")
    print("  end-to-end measurement of this corpus is 11, not 37: 26 of the 37 need a")
    print("  credential or a device before any config flow can complete.")

    if args.json:
        args.json.write_text(json.dumps(results, indent=2) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
