#!/usr/bin/env python3
"""Verdicts for F65 (`notes/f65_source_ip_prediction_20261025.md`), Q3–Q5.

Compares a `compat --egress` run with the final rerun's, which installed no shim, and reads the
waste-collection run after the fix.

    python3 verify/f65_verdicts.py pre  PRE.json
    python3 verify/f65_verdicts.py post POST.json WASTE.json WASTE.log
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

FINAL = (Path(__file__).resolve().parent.parent
         / "experiments/verify/results/final_20261016/step05_compat/c1_declared_core.json")
MESSAGE = "Could not determine source ip"

results: list[tuple[bool, str, str]] = []


def check(ok: bool, what: str, detail: str = "") -> None:
    results.append((bool(ok), what, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {what}" + (f"   [{detail}]" if detail else ""))


def rows(path: Path) -> dict[str, dict]:
    return {r["domain"]: r for r in json.loads(path.read_text())["arm_a"]}


def http_set_up(final: dict[str, dict]) -> list[str]:
    """The integrations whose `http` the final rerun set up — successfully — without the shim."""
    return sorted(d for d, r in final.items()
                  if (r.get("components_setup") or {}).get("http") is True)


def pre(path: Path) -> None:
    final, run = rows(FINAL), rows(path)
    wanted = http_set_up(final)
    print(f"Q3 — before the fix, with the shim: {path.name} ({len(wanted)} set up http in the final rerun)")
    failed = [d for d in wanted if (run.get(d, {}).get("components_setup") or {}).get("http") is not True]
    check(failed == wanted, f"Q3 http fails in all {len(wanted)}",
          f"{len(failed)}/{len(wanted)} failed; set up: {sorted(set(wanted) - set(failed))}")
    said = [d for d in failed if any(MESSAGE in line for line in
                                     (run[d].get("setup_log") or {}).get("http", []))]
    check(said == failed, f"Q3 each with {MESSAGE!r} in its setup log",
          f"{len(said)}/{len(failed)}; without it: {sorted(set(failed) - set(said))}")
    record_levels(final, run)


def post(path: Path, waste_json: Path, waste_log: Path) -> None:
    final, run = rows(FINAL), rows(path)
    wanted = http_set_up(final)
    print(f"Q4 — after the fix, with the shim: {path.name}")
    up = [d for d in wanted if (run.get(d, {}).get("components_setup") or {}).get("http") is True]
    check(up == wanted, f"Q4 http sets up in all {len(wanted)}",
          f"{len(up)}/{len(wanted)}; not: {sorted(set(wanted) - set(up))}")
    differ = record_levels(final, run)
    check(not differ and len(run) == len(final),
          f"Q4 all {len(final)} reach the final rerun's level", str(differ))

    print(f"\nQ5 — waste_collection_schedule after the fix: {waste_json.name}")
    data = json.loads(waste_json.read_text())
    reports = data.get("reports", data)
    confined = [str(e.get("entity")) for e in reports.get("confined_declared", {}).get("published") or []]
    calendars = [e for e in confined if e.startswith("calendar.")]
    check(bool(calendars), "Q5 the confined arm publishes the calendar entity", str(calendars))
    log = waste_log.read_text(errors="replace")
    check(MESSAGE not in log, f"Q5 no {MESSAGE!r} in its log")
    harness = [line.strip() for line in log.splitlines() if line.startswith(("  ok ", "  FAIL"))]
    failed = [line for line in harness if line.startswith("FAIL")]
    check(bool(harness) and not failed, "Q5 the harness's own checks all pass",
          f"{len(harness) - len(failed)}/{len(harness)}")


def record_levels(final: dict[str, dict], run: dict[str, dict]) -> list:
    differ = [(d, final[d].get("level"), run.get(d, {}).get("level")) for d in sorted(final)
              if final[d].get("level") != run.get(d, {}).get("level")]
    print(f"        record — levels that differ from the final rerun: {differ or 'none'}")
    return differ


if __name__ == "__main__":
    if sys.argv[1] == "pre":
        pre(Path(sys.argv[2]))
    else:
        post(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    failed = [w for ok, w, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} held" +
          (f"; missed: {failed}" if failed else ""))
    sys.exit(1 if failed else 0)
