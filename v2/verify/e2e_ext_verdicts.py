#!/usr/bin/env python3
"""Verdicts for the 2026-10-25 end-to-end extension (`notes/e2e_extension_prediction_20261025.md`).

Reads the two runs' JSON and checks each prediction as committed before the runs. It also records,
for every entity each integration published, whether the real bridge could stand in for it
(`notes/bridge_entity_types_20261025.md`): that is a record, not a criterion.

    python3 verify/e2e_ext_verdicts.py ALARMO.json WASTE.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# The bridge's own list (framework/ha_bridge/confine_bridge/const.py), read rather than copied.
CONST = Path(__file__).resolve().parent.parent / "framework/ha_bridge/confine_bridge/const.py"
SUPPORTED = next(eval(line.split("=", 1)[1]) for line in CONST.read_text().splitlines()
                 if line.startswith("SUPPORTED"))

ALARM = "alarm_control_panel.alarmo"
WET_EXPECTED = "on Tue, 27.10.2026"

results: list[tuple[bool, str, str]] = []


def check(ok: bool, what: str, detail: str = "") -> None:
    results.append((bool(ok), what, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {what}" + (f"   [{detail}]" if detail else ""))


def collapsed(history: list, entity: str) -> list[str]:
    out: list[str] = []
    for ent, state in history or []:
        if ent == entity and (not out or out[-1] != state):
            out.append(state)
    return out


def contains_in_order(seq: list[str], wanted: list[str]) -> bool:
    it = iter(seq)
    return all(any(s == w for s in it) for w in wanted)


def bridge_record(entities: list[str]) -> str:
    domains = sorted({e.partition(".")[0] for e in entities})
    return ", ".join(f"{d} ({'supported' if d in SUPPORTED else 'refused'})" for d in domains)


def alarmo(path: Path) -> None:
    reports = {r["arm"]: r for r in json.loads(path.read_text()) if r.get("variant") == "alarmo"}
    print(f"alarmo — {path.name}")
    for arm in ("unconfined", "confined"):
        r = reports.get(arm, {})
        check(r.get("loaded"), f"P1 {arm}: config entry LOADED",
              str(r.get("level") or r.get("error") or ""))
        seq = collapsed(r.get("history"), ALARM)
        check(bool(seq) and seq[0] == "disarmed", f"P2 {arm}: {ALARM} published, first 'disarmed'",
              str(seq))
        check(contains_in_order(seq, ["disarmed", "arming", "armed_away", "disarmed"]),
              f"P3 {arm}: disarmed → arming → armed_away → disarmed, in that order", str(seq))
        steps = r.get("steps") or []
        check(len(steps) == 2 and all(s.get("ok") for s in steps),
              f"P4 {arm}: both commands accepted", str([s.get("error") for s in steps]))
        published = sorted({e for e, _ in (r.get("history") or []) if e})
        print(f"        record — published types: {bridge_record(published)}")
    refused = [d for d in reports.get("confined", {}).get("decisions") or []
               if not d.get("allowed")]
    print(f"        record — confined arm's refused decisions: {len(refused)} "
          f"{[(d.get('op'), d.get('target')) for d in refused[:5]]}")


def waste(path: Path) -> None:
    print(f"\nwaste_collection_schedule — {path.name}")
    data = json.loads(path.read_text())
    reports = data.get("reports", data)

    def wet(report: dict):
        for e in report.get("published") or []:
            if str(e.get("entity", "")).startswith("sensor.") and "wet" in str(e.get("entity")):
                return e.get("state")
        return None
    a, b = reports.get("unconfined", {}), reports.get("confined_declared", {})
    check(wet(a) == WET_EXPECTED, f"P7 A: the WET sensor reads {WET_EXPECTED!r}", str(wet(a)))
    check(wet(b) == WET_EXPECTED, f"P7 B: the WET sensor reads {WET_EXPECTED!r}", str(wet(b)))
    for key in ("unconfined", "confined_declared"):
        published = [str(e.get("entity")) for e in reports.get(key, {}).get("published") or []
                     if key != "unconfined" or e.get("platform") == "waste_collection_schedule"]
        print(f"        record — {key} published types: {bridge_record(published)}")


if __name__ == "__main__":
    alarmo(Path(sys.argv[1]))
    waste(Path(sys.argv[2]))
    failed = [w for ok, w, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} held" +
          (f"; missed: {failed}" if failed else ""))
    sys.exit(1 if failed else 0)
