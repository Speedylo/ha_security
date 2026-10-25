#!/usr/bin/env python3
"""Verdicts E1 and E2 for bridge step 5 (`notes/bridge_types_step5_prediction_20261025.md`).

Reads every end-to-end result in a run directory and, for each integration's confined arm(s) run
against (A), checks that every publish was accepted (E1) and that every accepted entity is in (A),
owned by the bridge, of its own domain, in the state last published (E2; a button is not
compared, its state being its last press in (A)). E3 is the existing verdict scripts and each
harness's own checks; E4 is `suites_all.sh`.

    python3 verify/bridge_step5_verdicts.py RUN_DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

results: list[tuple[bool, str]] = []


def check(ok: bool, what: str, detail: str = "") -> None:
    results.append((bool(ok), what))
    print(f"  {'PASS' if ok else 'FAIL'}  {what}" + (f"   [{detail}]" if detail else ""))


def confined_arms(path: Path) -> list[tuple[str, dict, bool]]:
    """(label, report, declared) for each confined arm in one result file, whatever its harness."""
    data = json.loads(path.read_text())
    arms: list[tuple[str, dict, bool]] = []
    if isinstance(data, dict):                                  # endtoend_egress
        for key, report in (data.get("reports", data) or {}).items():
            if isinstance(report, dict) and key.startswith("confined"):
                arms.append((f"{path.stem} {key}", report, key == "confined_declared"))
    else:
        for report in data:
            if report.get("arm") == "confined":                 # endtoend_function
                arms.append((f"{path.stem} {report['variant']}", report,
                             "-" not in report["variant"]))
            elif str(report.get("arm", "")).startswith("confined"):   # endtoend_local
                arms.append((f"{path.stem} {report['arm']}", report,
                             report["arm"] == "confined_declared"))
            elif "run" in report and report.get("in_house") is not None:   # endtoend_oauth
                records = report.get("published_records") or []
                arms.append((f"{path.stem} {report['run']}", {**report, "published": records},
                             True))
    return arms


def main(directory: Path) -> int:
    for path in sorted(directory.glob("*.json")):
        if path.name.endswith(".run.json"):
            continue
        for label, report, declared in confined_arms(path):
            if report.get("platform") != "real":
                continue
            published = report.get("published") or []
            refused = [p.get("entity") for p in published if p.get("accepted") is False]
            rows = report.get("in_house") or []
            wrong = [r for r in rows if not (r["owned_by_bridge"] and r["same_domain"]
                                             and r["state_matches"])]
            types = sorted({str(p.get("entity")).partition(".")[0] for p in published})
            if declared:
                check(not refused, f"E1 {label}: every publish accepted by (A)",
                      f"{len(published)} publishes, types {types}; refused {refused}")
                check(not wrong, f"E2 {label}: every accepted entity in (A), owned, same domain "
                      "and state", f"{len(rows)} entities; wrong "
                      f"{[(r['entity'], r['in_house'], r['house_state'], r['published_state']) for r in wrong]}")
            else:
                print(f"        record — {label} (a withheld-clause arm): {len(published)} "
                      f"publishes, refused {refused}, entities in (A) not as published "
                      f"{[r['entity'] for r in wrong]}")
    failed = [w for ok, w in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} held"
          + (f"; missed: {failed}" if failed else ""))
    return 1 if failed or not results else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
