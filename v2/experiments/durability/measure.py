#!/usr/bin/env python3
"""Two Phase C obligations that share a harness: what durability costs, and what S9 costs.

**§6.8.3 — is `fsync` per decision affordable?** §5.11.3 orders the audit write *before* the
action, and that ordering is worth nothing unless the record is durable when the action happens.
`audit.py` already calls `os.fsync` on every decision, so the question is not whether to pay but
what is already being paid — and §7.19.3's headroom figure explicitly excludes it, so this is
what turns that upper bound into a number.

**§6.9.4 / §7.6's P5 — what does `resources.memory_mb` cost a *legitimate* integration?**
cgroup v2 charges page cache to the cgroup that faulted it in, so a memory limit bounds file
*reading* as well as allocation. An integration processing a large local dataset is
indistinguishable, to this control, from one searching the disk for secrets. P5 predicted this is
reproducible and a genuine usability cost rather than a theoretical one.

Run:  systemd-run --user --scope -q python3 measure.py --json results/pi5.json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "framework"))

from confine.audit import AuditLog                        # noqa: E402
from confine.cgroup import (Delegation, ResourceLimits, SandboxCgroup,  # noqa: E402
                            spawn_confined)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "framework"))
from confine.provenance import record_run  # noqa: E402  (F14)


def percentiles(samples: list[float]) -> dict:
    samples = sorted(samples)

    def pct(p: float) -> float:
        return samples[min(len(samples) - 1, int(p * len(samples)))] if samples else 0.0

    return {"n": len(samples), "median": round(statistics.median(samples), 1),
            "p95": round(pct(0.95), 1), "p99": round(pct(0.99), 1),
            "max": round(samples[-1], 1)}


def measure_durability(iterations: int, scratch: Path) -> dict:
    """The real `AuditLog.decision` path, with its fsync and with it removed.

    **`scratch` must be on real storage.** The first run of this put it under `tempfile`'s
    default, which is `/tmp`, which is **tmpfs** on this host — RAM. `fsync` on tmpfs is a
    no-op, so the measurement returned "durability costs -0.1 µs", i.e. nothing, which is not
    a result about durability but about where the file was. An audit log lives beside the
    configuration on real storage, so that is where it is measured.
    """
    root = Path(tempfile.mkdtemp(prefix="durability-", dir=str(scratch)))
    request = {"op": "entity.read", "entity": "sensor.outdoor_temperature"}
    try:
        results = {}
        for label, patched in (("with fsync (as built)", False), ("without fsync", True)):
            log = AuditLog(root / f"{label.split()[0]}.jsonl", key=b"k" * 32)
            real = os.fsync
            if patched:
                os.fsync = lambda fd: None            # noqa: E731 — restored below
            samples = []
            try:
                for index in range(iterations):
                    start = time.perf_counter_ns()
                    log.decision(f"run{index}", "demo", request, True,
                                 "/permissions/entities/read/0", "declared")
                    samples.append((time.perf_counter_ns() - start) / 1000.0)
            finally:
                os.fsync = real
            results[label] = percentiles(samples)
        return results
    finally:
        shutil.rmtree(root, ignore_errors=True)


READER = r'''
import sys
path, chunk = sys.argv[1], 1 << 20
total = 0
with open(path, "rb") as handle:
    while True:
        block = handle.read(chunk)
        if not block:
            break
        total += len(block)
print(total)
'''


def measure_page_cache(cap_mb: int, file_mb: int, scratch: Path) -> dict:
    """A legitimate integration streaming a file larger than its memory cap.

    Nothing is retained: the reader discards each block. Anything charged to the cgroup is
    therefore page cache alone, which is the property §6.9.4 says makes S9 bound reading.
    """
    # Real storage again, and for a second reason: a 512 MB file on tmpfs *is* memory, so
    # reading it would measure the wrong thing even if fsync did not matter.
    root = Path(tempfile.mkdtemp(prefix="pagecache-", dir=str(scratch)))
    try:
        data = root / "dataset.bin"
        with data.open("wb") as handle:
            for _ in range(file_mb):
                handle.write(os.urandom(1 << 20))
        script = root / "reader.py"
        script.write_text(READER)

        delegation = Delegation.discover()
        outcome: dict = {"cap_mb": cap_mb, "file_mb": file_mb}
        with SandboxCgroup.create(delegation, f"durability-pc-{cap_mb}",
                                  ResourceLimits(memory_mb=cap_mb,
                                                 max_processes=32)) as cgroup:
            # `spawn_confined`, not Popen-then-place. §6.4.1: the child writes its own pid
            # immediately before exec, which is the only ordering that leaves no uncapped
            # window. The first run of this called a `cgroup.add` that does not exist, caught
            # the AttributeError, recorded it in a field it never printed, and reported a peak
            # of 0.0 MB — a process that was never in the cgroup at all.
            proc = spawn_confined([sys.executable, str(script), str(data)], cgroup,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(timeout=300)
            outcome["returncode"] = proc.returncode
            outcome["oom_kill"] = cgroup.event_count("oom_kill")
            outcome["peak_mb"] = round(cgroup.peak_memory() / 2**20, 1)
            outcome["read_bytes"] = (stdout or b"").decode(errors="replace").strip()[:40]
            outcome["stderr"] = (stderr or b"").decode(errors="replace").strip()[-160:]
        outcome["killed"] = outcome["returncode"] != 0 or outcome["oom_kill"] > 0
        return outcome
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=2000)
    ap.add_argument("--scratch", type=Path, default=Path.home() / "r2exp",
                    help="a directory on REAL storage; /tmp is tmpfs on the C4 device and "
                         "makes both measurements meaningless")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)

    print(f"Phase C — durability and the cost of S9  ({platform.machine()}, "
          f"Python {platform.python_version()})")
    print(f"  scratch: {args.scratch}  (must not be tmpfs)\n")

    print("  §6.8.3 — what one audited decision costs, durable and not")
    durability = measure_durability(args.iterations, args.scratch)
    print(f"    {'':<24}{'median µs':>12}{'p95':>10}{'p99':>10}{'max':>10}")
    for label, row in durability.items():
        print(f"    {label:<24}{row['median']:>12}{row['p95']:>10}{row['p99']:>10}"
              f"{row['max']:>10}")
    a = durability["with fsync (as built)"]["median"]
    b = durability["without fsync"]["median"]
    print(f"    durability costs {a - b:.1f} us per decision ({a / b:.0f}x the "
          f"non-durable write)")

    print("\n  §6.9.4 / P5 — a legitimate integration reading a file larger than its cap")
    page = []
    for cap_mb, file_mb in ((64, 512), (128, 512), (256, 512)):
        row = measure_page_cache(cap_mb, file_mb, args.scratch)
        page.append(row)
        verdict = "KILLED" if row["killed"] else "completed"
        print(f"    cap {cap_mb:>4} MB, file {file_mb} MB   {verdict:<10} "
              f"peak {row['peak_mb']:>6} MB   rc={row['returncode']}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(
            {"host": platform.machine(), "python": platform.python_version(),
             "durability": durability, "page_cache": page}, indent=2) + "\n")
        record_run(args.json)  # F14: how this result was produced, beside it
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
