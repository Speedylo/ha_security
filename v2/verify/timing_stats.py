#!/usr/bin/env python3
"""Phase 3 timing and memory: each figure the report states, against every pass that has run.

The reference for each criterion is **the figure the report states**, with its section, because
that is the claim under test; committed logs vary around it (one shows 11.3 µs for §7.36's 10.9).
Criteria are the register's, fixed before any pass ran:

  T  timing   median of the passes within ±20% of the stated figure (or inside the recorded
              spread, whichever is wider); judged on the median across passes, every pass listed
  M  memory   within ±5% of the stated figure

With one pass this is a first look; the verdict is the one with three passes (sitting 3d).

Run from v2/:  python3 verify/timing_stats.py
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parent.parent
TIMING = V2 / "experiments" / "verify" / "results" / "phase3_timing"
L23 = V2 / "experiments" / "verify" / "results" / "phase2" / "l23"


def j(path: Path):
    return json.loads(path.read_text())


def log(path: Path, pattern: str, group: int = 1) -> float | None:
    if not path.exists():
        return None
    m = re.search(pattern, path.read_text(errors="replace"))
    return float(m.group(group)) if m else None


def level(data: dict, concurrency: int, key: str) -> float:
    return next(l[key] for l in data["levels"] if l["concurrency"] == concurrency)


#: (id, what, stated value, unit, kind, report section, extractor(pass_dir) -> value or None)
METRICS = [
    ("latency_1", "mediation latency, one client, median", 31.5, "µs", "T", "§7.19",
     lambda d: level(j(d / "latency_scale.json"), 1, "median")),
    ("latency_26_median", "mediation latency, 26 clients, median", None, "µs", "report",
     "§7.19", lambda d: level(j(d / "latency_scale.json"), 26, "median")),
    ("durability", "durable record with fsync, median", 3670.7, "µs", "T", "§7.20.1",
     lambda d: j(d / "durability.json")["durability"]["with fsync (as built)"]["median"]),
    ("footprint_single", "one sandbox, RSS at running", 161.3, "MB", "M", "§7.35",
     lambda d: j(d / "footprint_single.json")["questions"]["Q3_footprint"]["rss_at_running_mb"]),
    ("footprint_marginal", "marginal memory per added sandbox", 124.4, "MB", "M", "§7.35",
     lambda d: j(d / "footprint_scale.json")["settled"]["marginal_mb"]),
    ("depth_none", "PSS per sandbox, no components", 56.5, "MB", "M", "§7.35",
     lambda d: j(d / "depth_none.json")["pss_per_sandbox_mb"]),
    ("depth_ten", "PSS per sandbox, ten components", 135.6, "MB", "M", "§7.35",
     lambda d: j(d / "depth_ten.json")["pss_per_sandbox_mb"]),
    ("push_cost", "one delivered push, mediator cost", 10.9, "µs", "T", "§7.36",
     lambda d: log(d / "push_suite.log", r"([\d.]+) µs per push")),
    ("push_latency", "change in (A) to the mediator's push, median", 0.71, "ms", "T", "§7.37",
     lambda d: log(d / "real_platform.log", r"R5: .*?median ([\d.]+) ms")),
    ("command", "a user's command to the integration's code", 16.0, "ms", "T", "§7.38",
     lambda d: _command(d)),
    ("flood", "flood start to cut-off, on disk", 0.812, "s", "T", "§7.44",
     lambda d: log(d / "flood_disk.log", r"F2: flood start to cut-off ([\d.]+) s")),
    ("bytecode_default", "powercalc time to report, default install", 2.47, "s", "T", "§7.39",
     lambda d: j(d / "bytecode_default.json")[0]["bytecode"]["seconds_since_start"]),
    ("bytecode_compiled", "powercalc time to report, compiled install", 1.87, "s", "T", "§7.39",
     lambda d: j(d / "bytecode_compile.json")[0]["bytecode"]["seconds_since_start"]),
]


def _command(d: Path) -> float | None:
    """Pass 1's sample is phase 2's L3 run (same tag, same day); passes 2–3 run it themselves."""
    path = d / "e2e_real_adaptive.json"
    if not path.exists() and d.name == "pass1":
        path = L23 / "e2e_real_adaptive.json"
    if not path.exists():
        return None
    return j(path)[0]["command"]["outcome"]["seconds"] * 1000


def main() -> int:
    passes = sorted(p for p in TIMING.glob("pass*") if p.is_dir())
    print(f"{len(passes)} pass(es): {', '.join(p.name for p in passes)}\n")
    rows = []
    for mid, what, stated, unit, kind, section, get in METRICS:
        values = []
        for p in passes:
            try:
                values.append(get(p))
            except (FileNotFoundError, KeyError, IndexError, StopIteration, TypeError, ValueError):
                values.append(None)
        got = [v for v in values if v is not None]
        median = statistics.median(got) if got else None
        if stated is None or median is None:
            verdict = "reported" if median is not None else "MISSING"
        else:
            tolerance = 0.20 if kind == "T" else 0.05
            off = (median - stated) / stated
            verdict = f"{'within' if abs(off) <= tolerance else 'OUTSIDE'} {kind} ({off:+.1%})"
        shown = ", ".join("—" if v is None else f"{v:.3g}" for v in values)
        rows.append({"id": mid, "stated": stated, "values": values, "median": median,
                     "verdict": verdict, "section": section})
        print(f"  {what:<48} {section:<7} stated {stated if stated is not None else '—':>7} {unit:<3}"
              f" passes [{shown}]  → {verdict}")
    (TIMING / "stats.json").write_text(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
