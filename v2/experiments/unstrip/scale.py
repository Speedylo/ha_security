#!/usr/bin/env python3
"""How many un-stripped sandboxes fit on the C4 device?

§6.3.2 measured 26 sandboxes in 60% of the Pi's memory, using proportional set size across six
live sandboxes and a synthetic integration. §6.12 raises import-level compatibility from 46% to
70% by putting ten components back, and the question that decides Gate G3 is what that does to
the budget.

**Measured the same way as §6.3.2, deliberately.** Peak RSS is not comparable to PSS at rest —
the first includes page cache and transient allocation — so a successor figure taken any other
way would not be a successor. Sandboxes are started, held, and read from outside.

Run:  systemd-run --user --scope -q python3 scale.py --count 6 \
          --python <interp> --profile unstripped --platform-deps <dir>
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "framework"))

from confine.cgroup import Delegation, SandboxCgroup            # noqa: E402
from confine.channel import Channel                             # noqa: E402
from confine.compat import PLATFORM_DEPS, UNSTRIPPED            # noqa: E402
from confine.mediator import Mediator                           # noqa: E402
from confine.preflight import require_ready                     # noqa: E402
from confine.sandbox import SandboxSpec                         # noqa: E402
from confine.selftest_bridge import interpreter_trees           # noqa: E402
from confine.spawn import become_subreaper, start               # noqa: E402

RUNTIME = (Path(__file__).resolve().parents[2] / "framework" / "confine"
           / "sandbox_runtime.py")

INTEGRATION = {
    "__init__.py": "async def async_setup_entry(hass, entry):\n    return True\n",
    "manifest.json": json.dumps({"domain": "scale_probe", "name": "Scale Probe",
                                 "version": "1.0.0", "requirements": []}),
}


def proc_mem_kb(pid: int) -> dict[str, int]:
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


def meminfo_kb(field: str) -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(f"{field}:"):
            return int(line.split()[1])
    return -1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--python", required=True)
    ap.add_argument("--profile", choices=["minimal", "unstripped"], default="unstripped")
    ap.add_argument("--components", default="",
                    help="an explicit component list, for measuring what one integration's own "
                         "declaration costs rather than the blanket profile")
    ap.add_argument("--platform-deps", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    require_ready(deep=False)
    become_subreaper()
    delegation = Delegation.discover()
    sandbox_python = Path(args.python)

    total_kb = meminfo_kb("MemTotal")
    avail_before = meminfo_kb("MemAvailable")
    mediator = Mediator()
    roots, cgroups, sandboxes = [], [], []
    label = args.components or args.profile
    print(f"scale — {args.count} sandboxes, {label}\n")
    try:
        for index in range(args.count):
            root = Path(tempfile.mkdtemp(prefix=f"scale-{index}-"))
            roots.append(root)
            own = root / "custom_components" / "scale_probe"
            own.mkdir(parents=True)
            for name, body in INTEGRATION.items():
                (own / name).write_text(body)
            data = root / "data"
            data.mkdir()
            deps = root / "deps"
            deps.mkdir()

            mediator_end, sandbox_end = Channel.pair()
            mediator.register(f"scale_probe_{index}", Channel(mediator_end))
            spec_file = root / "spec.json"
            spec_file.write_text(json.dumps({
                "domain": "scale_probe", "mode": "idle", "entities": [], "services": [],
                "auth": args.profile == "unstripped" or bool(args.components),
                "setup_components": ([c.strip() for c in args.components.split(",") if c.strip()]
                                     if args.components
                                     else (UNSTRIPPED if args.profile == "unstripped" else []))}))

            spec = SandboxSpec(
                domain="scale_probe", own_dir=str(own), data_dir=str(data),
                argv=[str(sandbox_python), "/sandbox/runtime.py"],
                runtime_files={str(RUNTIME): "/sandbox/runtime.py",
                               str(spec_file): "/sandbox/spec.json", str(deps): "/sandbox/deps"},
                env={"PYTHONPATH": "/sandbox/deps"})
            if (args.profile == "unstripped" or args.components) and args.platform_deps:
                spec.runtime_files[str(args.platform_deps)] = PLATFORM_DEPS
                spec.env["PYTHONPATH"] = f"/sandbox/deps:{PLATFORM_DEPS}"
            for extra in (*interpreter_trees(sandbox_python), sys.base_prefix):
                if extra and extra not in spec.runtime_paths:
                    spec.runtime_paths.append(extra)

            cgroup = SandboxCgroup.create(delegation, f"scale-{index}",
                                          memory_max=768 * 1024**2, pids_max=64)
            cgroups.append(cgroup)
            out, errfile = root / "out.json", root / "err.txt"
            with open(out, "wb") as stdout, open(errfile, "wb") as stderr:
                try:
                    sandbox = start(spec, cgroup, stdout=stdout.fileno(),
                                    stderr=stderr.fileno(),
                                    channel_end=sandbox_end.fileno())
                except Exception:
                    print("  the sandbox said, on the way out:")
                    print("   " + "\n   ".join(
                        errfile.read_text().splitlines()[-12:]) or "   (nothing)")
                    raise
            sandbox_end.detach()
            sandboxes.append(sandbox)

            deadline = time.time() + 180
            while time.time() < deadline and "ready" not in out.read_text():
                time.sleep(0.5)
            if "ready" not in out.read_text():
                print(f"  sandbox {index + 1} never reported ready")
                return 1
            time.sleep(0.5)
            mem = proc_mem_kb(sandbox.pid)
            print(f"  sandbox {index + 1}: RSS {mem['rss_kb'] / 1024:6.1f} MB   "
                  f"PSS {mem['pss_kb'] / 1024:6.1f} MB   machine "
                  f"+{(avail_before - meminfo_kb('MemAvailable')) / 1024:6.1f} MB")

        settled = [proc_mem_kb(s.pid) for s in sandboxes]
        pss_total = sum(m["pss_kb"] for m in settled) / 1024
        rss_total = sum(m["rss_kb"] for m in settled) / 1024
        per_sandbox = pss_total / args.count
        budget = total_kb / 1024 * 0.6
        capacity = int(budget / per_sandbox)
        print(f"\n  sum of RSS            {rss_total:8.1f} MB")
        print(f"  sum of PSS            {pss_total:8.1f} MB")
        print(f"  PSS per sandbox       {per_sandbox:8.1f} MB   <- the §6.3.2 figure's successor")
        print(f"\n  {total_kb / 1024:.0f} MB machine; in 60% of it ({budget:.0f} MB), "
              f"about {capacity} sandboxes fit")
        if args.json:
            args.json.write_text(json.dumps({
                "profile": args.profile, "count": args.count,
                "sum_rss_mb": round(rss_total, 1), "sum_pss_mb": round(pss_total, 1),
                "pss_per_sandbox_mb": round(per_sandbox, 1), "capacity": capacity,
                "mem_total_mb": round(total_kb / 1024)}, indent=2) + "\n")
            print(f"\nwrote {args.json}")
    finally:
        for cgroup in cgroups:
            cgroup.remove()
        for root in roots:
            __import__("shutil").rmtree(root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
