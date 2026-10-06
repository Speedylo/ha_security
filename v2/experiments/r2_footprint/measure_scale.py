#!/usr/bin/env python3
"""How many R2 sandboxes fit on this machine?

measure.py reports one sandbox's resident memory. That number overstates the cost of N
sandboxes, and badly: most of a sandbox is the Python interpreter and the Home Assistant
library, which are read-only pages the kernel maps into every process from the same
physical memory. Ten sandboxes do not cost ten times one.

So the figure that decides C4 is the *marginal* cost — what the second and subsequent
sandboxes add — and this script measures it three ways, because each has a failure mode:

    RSS      per process, counts shared pages once per process — an over-estimate
    PSS      per process, divides each shared page by the number of sharers — the honest
             per-process figure, and what to quote
    MemAvailable  measured across the whole machine before and after — the ground truth,
             and the one that cannot be argued with, but noisy on a busy host

Run:  python measure_scale.py --count 5 [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "framework"))
from confine.provenance import record_run  # noqa: E402  (F14)

HERE = Path(__file__).parent


def meminfo_kb(field: str) -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(f"{field}:"):
            return int(line.split()[1])
    return -1


def proc_mem_kb(pid: int) -> dict[str, int]:
    """RSS and PSS for one process, from smaps_rollup (cheap; one line each)."""
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=5, help="sandboxes to start")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--builder", choices=["original", "corrected"], default="original")
    args = ap.parse_args()

    python = sys.executable
    print(f"R2 scale — {platform.machine()}, Python {platform.python_version()}, "
          f"{args.count} sandboxes, {args.builder} builder")

    total_kb = meminfo_kb("MemTotal")
    avail_before = meminfo_kb("MemAvailable")

    procs: list[subprocess.Popen] = []
    per_sandbox: list[dict] = []
    try:
        for i in range(args.count):
            p = subprocess.Popen(
                [python, str(HERE / "measure.py"), "--serve", "--builder", args.builder],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            )
            procs.append(p)
            line = p.stdout.readline()          # blocks until this sandbox says READY
            if not line.startswith("READY"):
                print(f"sandbox {i} failed to start: {line!r}", file=sys.stderr)
                return 1
            time.sleep(0.3)                     # let it settle before reading /proc
            mem = proc_mem_kb(p.pid)
            avail_now = meminfo_kb("MemAvailable")
            per_sandbox.append({
                "n": i + 1,
                "pid": p.pid,
                "rss_mb": round(mem["rss_kb"] / 1024, 1),
                "pss_mb": round(mem["pss_kb"] / 1024, 1),
                "machine_used_mb": round((avail_before - avail_now) / 1024, 1),
            })
            s = per_sandbox[-1]
            print(f"  sandbox {i + 1}: RSS {s['rss_mb']:6.1f} MB   "
                  f"PSS {s['pss_mb']:6.1f} MB   machine +{s['machine_used_mb']:6.1f} MB")

        # Re-read every sandbox now that all are up: PSS falls as sharers appear, so the
        # figures taken while starting are stale for the earlier processes.
        settled = [proc_mem_kb(p.pid) for p in procs]
        pss_total = sum(m["pss_kb"] for m in settled) / 1024
        rss_total = sum(m["rss_kb"] for m in settled) / 1024
        avail_after = meminfo_kb("MemAvailable")
        machine_delta = (avail_before - avail_after) / 1024

        first = per_sandbox[0]["machine_used_mb"]
        marginal = ((machine_delta - first) / (args.count - 1)) if args.count > 1 else None

        print()
        print(f"  sum of RSS               {rss_total:8.1f} MB   (counts shared pages "
              f"{args.count}x — over-estimate)")
        print(f"  sum of PSS               {pss_total:8.1f} MB   (shared pages divided "
              f"among sharers)")
        print(f"  machine memory consumed  {machine_delta:8.1f} MB   (MemAvailable delta)")
        print(f"  first sandbox            {first:8.1f} MB")
        if marginal is not None:
            print(f"  MARGINAL per sandbox     {marginal:8.1f} MB   <- the figure that "
                  f"decides C4")
            budget = total_kb / 1024 * 0.6
            capacity = int((budget - first) / marginal) + 1 if marginal > 0 else 0
            print()
            print(f"  host has {total_kb / 1024:.0f} MB; in 60% of it ({budget:.0f} MB) "
                  f"about {capacity} sandboxes fit")

        result = {
            "host": {"machine": platform.machine(),
                     "python": platform.python_version(),
                     "node": platform.node(),
                     "mem_total_mb": round(total_kb / 1024)},
            "count": args.count,
            "builder": args.builder,
            "per_sandbox": per_sandbox,
            "settled": {"sum_rss_mb": round(rss_total, 1),
                        "sum_pss_mb": round(pss_total, 1),
                        "machine_delta_mb": round(machine_delta, 1),
                        "first_sandbox_mb": round(first, 1),
                        "marginal_mb": round(marginal, 1) if marginal else None},
        }
        if args.json:
            args.json.write_text(json.dumps(result, indent=2) + "\n")
            record_run(args.json)  # F14: how this result was produced, beside it
            print(f"\nwrote {args.json}")
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
