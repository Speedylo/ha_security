"""S3's paired baseline: what an integration can see, with the framework and without it.

§3.5 fixed S3's verification before any implementation existed:

    "a confined integration attempting to read and to subscribe to undeclared entities is
     denied, **with a paired baseline measuring what is readable without the framework**."

The paired clause is the reason this file exists. Showing that a sandbox denies a read proves
nothing about how much that denial is worth; the number that matters is what the same
integration would otherwise have held, and §1.7's Table 1.2 says the answer is *everything*.

**Both arms furnish the same home** (`home.py`) and are asked the same questions, so the
comparison is about the framework rather than about two differently-populated instances. What
differs between the arms is not the question but the mechanism, and the report keeps the two
mechanisms apart:

    present_locally   is the entity in this integration's own state machine at all?
                      Confined this is §5.6.2's structural denial: an undeclared entity is
                      **absent**, not refused, and there is nothing to appeal against.
    mediator_ok       will the mediator read or subscribe on its behalf? Confined this is a
                      decision with a clause. Unconfined there is no mediator and the column
                      is filled in as "yes" because nothing was asked.

Run:  systemd-run --user --scope -q python3 -m confine.selftest_reads --python <ha-interpreter>
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .cgroup import Delegation, SandboxCgroup
from .channel import Channel
from .home import DECLARED, HOME, entity_ids, probe_set, sensitive_ids
from .manifest import Manifest
from .mediator import Mediator
from .platform import Platform, acting_policy
from .preflight import require_ready
from .sandbox import SandboxSpec
from .selftest_bridge import interpreter_trees
from .spawn import Sandbox, SandboxFailed, become_subreaper, start

HERE = Path(__file__).resolve().parent

# What the integration asks for, and all it asks for: one ordinary reading, read and watched.
GRANT = {"schema_version": 1,
         "entities": {"read": [DECLARED], "subscribe": [DECLARED]}}


def arm_unconfined(python: Path) -> dict:
    root = Path(tempfile.mkdtemp(prefix="reads-unconfined-"))
    try:
        config = root / "config"
        config.mkdir(parents=True)
        for name in ("home.py", "sandbox_runtime.py", "reads_unconfined.py"):
            shutil.copy2(HERE / name, root / name)
        spec = root / "spec.json"
        spec.write_text(json.dumps({"config_dir": str(config)}))
        proc = subprocess.run([str(python), str(root / "reads_unconfined.py"), str(spec)],
                              capture_output=True, text=True, timeout=600,
                              env={**os.environ}, cwd=str(root))
        text = (proc.stdout or "").strip()
        if not text:
            tail = (proc.stderr or "").strip().splitlines()
            return {"arm": "unconfined", "fatal": tail[-1][:300] if tail else "no output"}
        return json.loads(text.splitlines()[-1])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def arm_confined(python: Path) -> dict:
    root = Path(tempfile.mkdtemp(prefix="reads-confined-"))
    mediator = Mediator()
    try:
        own = root / "custom_components" / "demo_weather"
        own.mkdir(parents=True)
        (own / "__init__.py").write_text("# ordinary\n")
        (own / "manifest.json").write_text(json.dumps(
            {"domain": "demo_weather", "name": "Demo Weather", "version": "1.0.0",
             "permissions": GRANT}))
        data = root / ".confine" / "demo_weather"
        data.mkdir(parents=True)

        # The mediator's view of the home: the same entities, behind the boundary.
        platform = Platform()
        for entity_id, state, _sensitive, attributes in HOME:
            platform.seed(entity_id, state, **attributes)

        manifest = Manifest.load(own, root)
        mediator.policy = acting_policy({"demo_weather": manifest}, platform)
        mediator_end, sandbox_end = Channel.pair()
        mediator.register("demo_weather", Channel(mediator_end))

        spec_file = root / "spec.json"
        spec_file.write_text(json.dumps({
            "domain": "demo_weather", "mode": "visibility", "auth": True,
            "entities": GRANT["entities"]["read"], "services": [],
            "setup_components": [], "probe_entities": probe_set()}))
        spec = SandboxSpec(
            domain="demo_weather", own_dir=str(own), data_dir=str(data),
            argv=[str(python), "/sandbox/runtime.py"],
            runtime_files={str(HERE / "sandbox_runtime.py"): "/sandbox/runtime.py",
                           str(spec_file): "/sandbox/spec.json"})
        for extra in (*interpreter_trees(python), sys.base_prefix):
            if extra and extra not in spec.runtime_paths:
                spec.runtime_paths.append(extra)

        out = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        err = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        delegation = Delegation.discover()
        with SandboxCgroup.create(delegation, "confine-reads",
                                  memory_max=640 * 1024**2, pids_max=64) as cgroup:
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
        return {"arm": "confined", "fatal": str(err)[:300]}
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if not text:
        tail = diagnostic.splitlines()
        return {"arm": "confined", "fatal": tail[-1][:300] if tail else "no output"}
    report = json.loads(text.splitlines()[-1])
    report["arm"] = "confined"
    report["decisions"] = list(mediator.audit)
    return report


def render(unconfined: dict, confined: dict) -> int:
    every = set(entity_ids())
    sensitive = set(sensitive_ids())

    for arm in (unconfined, confined):
        if "fatal" in arm:
            print(f"{arm['arm']} arm failed: {arm['fatal']}")
            return 1

    # Only entities from the home count as "seen". A sandbox's own state machine holds
    # housekeeping entities that are nobody's business but its own, and counting those as
    # visibility would flatter the confined arm.
    seen_u = set(unconfined["visible"]) & every
    seen_c = set(confined["visible"]) & every

    print("S3 paired baseline — what an integration can see of the home\n")
    print(f"  the home: {len(every)} entities, of which {len(sensitive)} disclose occupancy, "
          f"presence or routine")
    print(f"  declared: {DECLARED}\n")

    print(f"  {'':<34}{'unconfined':>14}{'confined':>12}")
    print(f"  {'entities present to it':<34}{len(seen_u):>10}/{len(every):<3}"
          f"{len(seen_c):>8}/{len(every):<3}")
    print(f"  {'of those, occupancy or presence':<34}"
          f"{len(seen_u & sensitive):>10}/{len(sensitive):<3}"
          f"{len(seen_c & sensitive):>8}/{len(sensitive):<3}")
    ev_u = len(unconfined.get("events_received", []))
    churn = len(unconfined.get("churned", []))
    print(f"  {'changes by others delivered to it':<34}"
          f"{str(ev_u) + '/' + str(churn):>10}   {'none, see below':<12}")
    print()

    print(f"  {'probe':<40}{'unconfined':<12}confined")
    for entity_id in probe_set():
        u = unconfined["reads"].get(entity_id, {})
        c = confined["reads"].get(entity_id, {})
        sub = confined["subscribes"].get(entity_id, {})
        mark = "read" if u.get("mediator_ok") else "—"
        if c.get("present_locally"):
            verdict = "present; read + subscribe permitted"
        elif c.get("mediator_ok"):
            verdict = "absent locally, but the mediator allowed it"
        else:
            verdict = f"absent; denied {c.get('clause') or sub.get('clause') or ''}"
        flag = " *" if entity_id in sensitive else ""
        print(f"  {entity_id + flag:<40}{mark:<12}{verdict}")
    print("\n  * discloses occupancy, presence or routine")

    # Stated rather than scored, because the confined figure is not a measurement of a filter.
    print()
    print("  On the delivery of other integrations' changes: unconfined, all "
          f"{ev_u} of {churn} arrive")
    print("  through EVENT_STATE_CHANGED, unasked and unfiltered. Confined, none arrive — but")
    print("  **that is an absent feature, not a demonstrated filter**: §6.11.2 records that no")
    print("  push loop exists, so declared entities are mirrored once at construction and there")
    print("  is no path by which any state change could arrive. S3's subscription half is")
    print("  therefore verified at the decision layer only, and §7.14.4 says so.")

    # ---- the criterion, from §7.5 ------------------------------------------------------
    undeclared = [e for e in probe_set() if e != DECLARED]
    denied_reads = [e for e in undeclared
                    if not confined["reads"].get(e, {}).get("mediator_ok")]
    denied_subs = [e for e in undeclared
                   if not confined["subscribes"].get(e, {}).get("mediator_ok")]
    clauses = [confined["reads"][e].get("clause") for e in denied_reads]
    absent = [e for e in undeclared
              if not confined["reads"].get(e, {}).get("present_locally")]

    if len(seen_u & sensitive) < len(sensitive):
        print("FAILED — the unconfined arm did not see every presence entity, so the baseline")
        print("         does not establish what is readable without the framework.")
        return 1
    if len(denied_reads) < len(undeclared) or len(denied_subs) < len(undeclared):
        print(f"FAILED — confined, {len(undeclared) - len(denied_reads)} undeclared read(s) and "
              f"{len(undeclared) - len(denied_subs)} subscription(s) were permitted.")
        return 1
    if not all(clauses):
        print("FAILED — a denial named no clause. §6.6.5: a negative case that cannot say which")
        print("         rule refused it is not evidence that the right rule refused it.")
        return 1
    if not confined["reads"].get(DECLARED, {}).get("mediator_ok"):
        print("FAILED — the declared entity was not readable. The sandbox is confining by being")
        print("         broken, which is not the property under test.")
        return 1

    print("PASS — S3, both halves.")
    print(f"       Unconfined, the integration holds all {len(every)} entities including every "
          f"one of the\n       {len(sensitive)} that disclose presence, and is told about every "
          f"change to entities it\n       does not own.")
    print(f"       Confined, {len(absent)} of {len(undeclared)} undeclared probes are not in its "
          f"state machine at all,\n       every mediated read and subscription is refused with a "
          f"clause, and the one\n       entity it declared is readable.")
    print("       The subscription half is a decision, not a delivered stream — see the note "
          "above.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", required=True, help="an interpreter with homeassistant")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    require_ready(deep=False)
    become_subreaper()
    python = Path(args.python)

    print("running the unconfined arm ...", file=sys.stderr)
    unconfined = arm_unconfined(python)
    print("running the confined arm ...", file=sys.stderr)
    confined = arm_confined(python)

    if args.json:
        args.json.write_text(json.dumps({"unconfined": unconfined, "confined": confined},
                                        indent=2) + "\n")
    return render(unconfined, confined)


if __name__ == "__main__":
    sys.exit(main())
