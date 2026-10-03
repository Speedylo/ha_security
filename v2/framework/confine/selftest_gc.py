"""§7.15 — the garbage-collector attack, with and without the framework, and the credential real.

§2.4.1's attack is what forces this project's architecture (S1: enforcement outside the
integration's process; S2: the credential held away from it). §6.9's suite already runs the
sweep confined and finds nothing — but with only its own integration in the process, "found
nothing" is close to a tautology, and the confined arm of §6.9 has no victim whose secret it
*could* have found. This closes both gaps:

    unconfined   the victim integration holds a live token; the adversary, co-resident, reaches
                 it through `gc.get_objects()`. The attack SUCCEEDS. (`gc_unconfined.py`)
    confined     the credential is the mediator's (S2), in the mediator's process. The adversary
                 is in a sandbox (S1), a different process. The sweep finds nothing — and the
                 mediator's own heap is checked to confirm the credential is genuinely there,
                 so "nothing" means "unreachable" and not "absent".

The pass criterion has two halves and needs both: the attack must work unconfined, or the
confined block proves nothing; and the confined credential must be real, or its absence from the
sandbox is uninformative.

Run:  systemd-run --user --scope -q python3 -m confine.selftest_gc --python <ha-interpreter>
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

from .audit import attach, report_durable
from .audit import summarise as durable_summary
from .cgroup import Delegation, ResourceLimits, SandboxCgroup
from .channel import Channel
from .gc_probe import CANARY_CREDENTIAL, GC_SWEEP
from .mediator import Mediator
from .preflight import require_ready
from .sandbox import SandboxSpec
from .selftest_bridge import interpreter_trees
from .spawn import Sandbox, SandboxFailed, become_subreaper, start

HERE = Path(__file__).resolve().parent

exec(GC_SWEEP)  # defines gc_find in this process too — used to confirm the mediator holds it


def arm_unconfined(python: Path) -> dict:
    root = Path(tempfile.mkdtemp(prefix="gc-unconfined-"))
    try:
        config = root / "config"
        config.mkdir(parents=True)
        for name in ("gc_probe.py", "sandbox_runtime.py", "gc_unconfined.py"):
            shutil.copy2(HERE / name, root / name)
        spec = root / "spec.json"
        spec.write_text(json.dumps({"config_dir": str(config)}))
        proc = subprocess.run([str(python), str(root / "gc_unconfined.py"), str(spec)],
                              capture_output=True, text=True, timeout=600,
                              env={**os.environ}, cwd=str(root))
        text = (proc.stdout or "").strip()
        if not text:
            tail = (proc.stderr or "").strip().splitlines()
            return {"arm": "unconfined", "fatal": tail[-1][:300] if tail else "no output"}
        return json.loads(text.splitlines()[-1])
    finally:
        shutil.rmtree(root, ignore_errors=True)


# The adversary, in a sandbox, running only the published sweep and reporting what it reached.
ADVERSARY = GC_SWEEP + f'''
import json, sys
hits = gc_find({CANARY_CREDENTIAL!r})
sys.stdout.write(json.dumps({{"gc_hits": hits[:20], "gc_hit_count": len(hits),
                             "found_credential": len(hits) > 0,
                             "heap_size": len(__import__("gc").get_objects())}}) + "\\n")
'''


def arm_confined(python: Path) -> dict:
    # S2: the credential the mediator holds. It is a live object in *this* process — the
    # mediator's — for the whole time the adversary runs. This is not decoration: the confined
    # result is only meaningful if the thing the sweep is looking for genuinely exists and is
    # genuinely reachable by a gc walk in the process that holds it.
    class MediatorCredential:
        def __init__(self, token: str) -> None:
            self._platform_token = token

    held = MediatorCredential(CANARY_CREDENTIAL)  # noqa: F841 — kept live on purpose

    root = Path(tempfile.mkdtemp(prefix="gc-confined-"))
    mediator = Mediator()
    audit_dir = attach(mediator, "confine-gc-audit-")
    try:
        own = root / "custom_components" / "adversary"
        own.mkdir(parents=True)
        (own / "__init__.py").write_text("# adversary\n")
        (own / "manifest.json").write_text(json.dumps(
            {"domain": "adversary", "name": "Adversary", "version": "1.0.0"}))
        data = root / ".confine" / "adversary"
        data.mkdir(parents=True)
        mediator_end, sandbox_end = Channel.pair()
        mediator.register("adversary", Channel(mediator_end), component=own)

        spec = SandboxSpec(domain="adversary", own_dir=str(own), data_dir=str(data),
                           argv=[str(python), "-c", ADVERSARY])
        for extra in (*interpreter_trees(python), sys.base_prefix):
            if extra and extra not in spec.runtime_paths:
                spec.runtime_paths.append(extra)

        out = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        err = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        delegation = Delegation.discover()
        with SandboxCgroup.create(delegation, "confine-gc",
                                  ResourceLimits(memory_mb=512)) as cgroup:
            with open(out.name, "wb") as stdout, open(err.name, "wb") as stderr:
                sandbox: Sandbox = start(spec, cgroup, stdout=stdout.fileno(),
                                         stderr=stderr.fileno(),
                                         channel_end=sandbox_end.fileno())
                sandbox_end.detach()
                mediator.serve(timeout=120)
                sandbox.wait(timeout=120)
        text = Path(out.name).read_text().strip()
        diagnostic = Path(err.name).read_text().strip()
        Path(out.name).unlink(missing_ok=True)
        Path(err.name).unlink(missing_ok=True)

        # Confirm, from the mediator's own process, that the credential the sandbox could not
        # find is nonetheless a live, gc-reachable object here. "Nothing found" is only a
        # result once this is true.
        mediator_hits = gc_find(CANARY_CREDENTIAL)
    except (SandboxFailed, OSError, TimeoutError) as err:
        return {"arm": "confined", "fatal": str(err)[:300]}
    finally:
        shutil.rmtree(root, ignore_errors=True)
        durable = durable_summary(mediator, audit_dir)

    if not text:
        tail = diagnostic.splitlines()
        return {"arm": "confined", "fatal": tail[-1][:300] if tail else "no output"}
    report = json.loads(text.splitlines()[-1])
    report["arm"] = "confined"
    report["durable"] = durable
    report["mediator_holds_credential"] = len(mediator_hits) > 0
    report["mediator_hit_count"] = len(mediator_hits)
    return report


def render(unconfined: dict, confined: dict) -> int:
    for arm in (unconfined, confined):
        if "fatal" in arm:
            print(f"{arm['arm']} arm failed: {arm['fatal']}")
            return 1

    print("§7.15 — Corno & Mannella's gc attack, with the credential real\n")
    print("  the published attack (§2.4.1): walk gc.get_objects(), read another component's "
          "live secret\n")

    print("  UNCONFINED — victim integration and adversary in one process")
    print(f"    victim's token reached by the heap walk : "
          f"{'YES — ' + str(unconfined['gc_hit_count']) + ' live objects held it' if unconfined['found_credential'] else 'no'}")
    if unconfined.get("gc_hits"):
        kinds = ", ".join(sorted({h[0] for h in unconfined["gc_hits"]}))
        print(f"    reached as                              : {kinds}")
    print()
    print("  CONFINED — credential in the mediator (S2), adversary in a sandbox (S1)")
    print(f"    adversary's heap                        : "
          f"{confined['heap_size']} objects, all its own")
    print(f"    token reached by the heap walk          : "
          f"{'YES — LEAK' if confined['found_credential'] else 'no'}")
    print(f"    same token live in the mediator process : "
          f"{'yes (' + str(confined['mediator_hit_count']) + ' refs)' if confined['mediator_holds_credential'] else 'NO — inconclusive'}")
    print()

    if not unconfined["found_credential"]:
        print("FAILED — the attack did not reach the credential unconfined. Corno & Mannella's")
        print("         result did not reproduce here, so the confined block proves nothing.")
        return 1
    if not confined["mediator_holds_credential"]:
        print("FAILED — the credential is not a live object in the mediator's process, so the")
        print("         adversary finding nothing is uninformative rather than a result.")
        return 1
    if confined["found_credential"]:
        print("FAILED — the adversary reached the credential from inside the sandbox.")
        return 1

    print("PASS — the published in-process attack succeeds unconfined and fails confined, with")
    print("       the credential proven live in the mediator throughout. S1 and S2 defeat the")
    print("       one result (§2.4.1) that forced them, measured here rather than only cited.")
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
    return render(unconfined, confined) or report_durable(confined.get("durable"))


if __name__ == "__main__":
    sys.exit(main())
