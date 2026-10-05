#!/usr/bin/env python3
"""Phase 3a: each Tier B headline, recomputed from the raw records of the golden and the new run.

Exact criteria (register Tier B, kind E): counts, sets and verdicts must be equal. This prints both
sides of every headline and says EQUAL or DIFFERS; `compare.py` gives the field-by-field detail
behind any DIFFERS.

Run from v2/:  python3 verify/check_3a.py
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parent.parent
EXP = V2 / "experiments"
import os
NEW = Path(os.environ.get("VERIFY_NEW", EXP / "verify" / "results" / "phase3a"))
GOLD = json.loads((V2 / "verify" / "golden_3a.json").read_text())
results: list[bool] = []


def golden(name: str) -> Path:
    return (EXP / GOLD[name]["golden"]).resolve()


def line(label: str, old, new) -> None:
    same = old == new
    results.append(same)
    if same:
        shown = f"{len(old)} items" if isinstance(old, list) and len(str(old)) > 120 else old
        print(f"  EQUAL   {label}: {shown}")
    elif isinstance(old, list) and isinstance(new, list):
        print(f"  DIFFERS {label}: only golden {sorted(set(map(str, old)) - set(map(str, new)))}; "
              f"only new {sorted(set(map(str, new)) - set(map(str, old)))}")
    else:
        print(f"  DIFFERS {label}: {old}  →  {new}")


def compat(name: str) -> None:
    def summary(path: Path) -> dict:
        d = json.loads(path.read_text())
        out = {}
        for arm, rows in d.items():
            if not isinstance(rows, list):
                continue
            levels = collections.Counter(r.get("level") for r in rows)
            out[arm] = {"n": len(rows), "clean": levels.get("platforms_clean", 0),
                        "failing": sorted((r["domain"], r.get("level")) for r in rows
                                          if r.get("level") != "platforms_clean"),
                        "source_changed": sum(1 for r in rows
                                              if (r.get("integrity") or {}).get("source_changed"))}
        if "c1" in d:
            out["c1"] = {k: d["c1"].get(k) for k in ("integrations_checked", "source_changed",
                                                      "total_diff_lines", "lines_unknown")}
        return out
    old, new = summary(golden(name)), summary(NEW / name)
    print(f"\n{name}")
    for arm in sorted(set(old) | set(new)):
        o, n = old.get(arm, {}), new.get(arm, {})
        if arm == "c1":
            line("C1 integrity", o, n)
            continue
        line(f"{arm} clean / total", f"{o.get('clean')}/{o.get('n')}", f"{n.get('clean')}/{n.get('n')}")
        line(f"{arm} failing set, with level", o.get("failing"), n.get("failing"))
        line(f"{arm} source trees changed", o.get("source_changed"), n.get("source_changed"))


def visibility() -> None:
    old = json.loads(golden("pi5_s3.json").read_text())
    new = json.loads((NEW / "pi5_s3.json").read_text())
    print("\nentity visibility (S3)")
    for arm in ("unconfined", "confined"):
        line(f"{arm} entities visible", len(old[arm]["visible"]), len(new[arm]["visible"]))
        line(f"{arm} which", sorted(old[arm]["visible"]), sorted(new[arm]["visible"]))
    refused = lambda d: sorted(e for e, r in d["confined"]["reads"].items() if not r.get("ok"))
    line("confined reads refused", refused(old), refused(new))


def gc_attack() -> None:
    old = json.loads(golden("pi5_s1.json").read_text())
    new = json.loads((NEW / "pi5_s1.json").read_text())
    print("\ngarbage-collector attack (S1)")
    for arm, keys in (("unconfined", ("gc_hit_count", "found_credential")),
                      ("confined", ("gc_hit_count", "found_credential", "mediator_holds_credential",
                                    "mediator_hit_count"))):
        for key in keys:
            line(f"{arm} {key}", old[arm].get(key), new[arm].get(key))
    print(f"  (reported, not judged) confined heap_size: {old['confined'].get('heap_size')} → "
          f"{new['confined'].get('heap_size')}")


def outcomes(path: Path) -> list[str]:
    """Each attack as (verdict, name), and the suite's summary counts verbatim.

    What an attack found varies by run (temporary paths, what a sweep listed), and the criterion is
    about the verdict, so only the verdict and the attack's name are kept; temporary paths in a name
    become <tmp>. The summary line ("BLOCKED 21   DENY 6 …") is kept with its numbers, because the
    counts are part of the claim.
    """
    verdict = re.compile(r"^\s*(?:ok|FAIL|LEAK)?\s*(BLOCKED|DENY|EMPTY|LEAKED|PERMIT|UNMEDIATED|"
                         r"NOT RUN)\s{2,}(.+?)(?:\s{2,}|$)")
    summary = re.compile(r"^\s*((?:BLOCKED|DENY|EMPTY|LEAKED|PERMIT|NOT RUN|UNMEDIATED)\s+\d+\s*){2,}$")
    out = []
    for raw in path.read_text(errors="replace").splitlines():
        if summary.match(raw):
            out.append("counts: " + " ".join(raw.split()))
        elif m := verdict.match(raw):
            out.append(f"{m.group(1)}: {re.sub(r'/tmp/[^/ ]+', '<tmp>', m.group(2).strip())}")
    return out


def adversary() -> None:
    print("\nadversary pair (S2, S8, T14, T15)")
    for name in ("adversary_confined.log", "adversary_unconfined.log"):
        old, new = outcomes(golden(name)), outcomes(NEW / name)
        line(f"{name} outcome lines ({len(old)} golden)", sorted(old), sorted(new))


def main() -> int:
    for name in ("c1_baseline.json", "c1_declared_core.json", "uniform_baseline.json",
                 "uniform_confined.json", "compat_minimal.json",
                 "compat_unstripped_currentdeps.json"):
        compat(name)
    visibility()
    gc_attack()
    adversary()
    print(f"\n{sum(results)}/{len(results)} headline comparisons equal")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
