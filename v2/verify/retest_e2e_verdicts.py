#!/usr/bin/env python3
"""Read the 2026-10-09 functional retest's predictions off its reports, one verdict per line.

The predictions are `notes/e2e_functional_retest_prediction.md` §3, committed before the harness
(`framework/confine/endtoend_function.py`) existed. Each check below names the prediction it
reads. Nothing is judged by eye: a value is in the report or the check fails.

Run from v2/:  python3 verify/retest_e2e_verdicts.py RESULTS.json [MORE.json ...]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

LIGHT = "light.living_room"
POWER = "sensor.lamp_power_power"
COLOUR_KEYS = {"color_temp_kelvin", "color_temp", "rgb_color", "xy_color", "hs_color"}


def final_states(report: dict) -> dict[str, tuple[str, dict]]:
    """The last state and attributes of each of the integration's own entities, in either arm."""
    out: dict[str, tuple[str, dict]] = {}
    for item in report.get("published") or []:
        out[item["entity"]] = (item["state"], item.get("attributes") or {})
    return out


def phases(report: dict, entity: str) -> list[str | None]:
    """The entity's value before the first world change and after each one, carried forward.

    A world change is the host's `<world>` marker confined, and the light's own state change
    unconfined, where the world's first states are set before the history starts.
    """
    marker = "<world>" if report["arm"] == "confined" else LIGHT
    values: list[str | None] = [None]
    for entity_id, state in report.get("history") or []:
        if entity_id == marker:
            values.append(values[-1])
        elif entity_id == entity:
            values[-1] = state
    return values


def check(label: str, ok: bool, detail: str) -> bool:
    print(f"  {'PASS' if ok else 'FAIL'}  {label:<58} {detail}")
    return ok


def service_decisions(report: dict) -> list:
    return [d for d in report.get("decisions") or [] if "service" in json.dumps(d)]


def p1(r: dict) -> list[bool]:
    v = r["variant"]
    got = phases(r, POWER)
    if v == "powercalc":
        return [check(f"P1 {r['arm']}: 8.06 -> 3.00 -> 0.00", got == ["8.06", "3.00", "0.00"],
                      str(got))]
    if v == "powercalc-no-subscribe":
        return [check("P1 withheld subscribe: 8.06 unchanged at b and c",
                      got == ["8.06", "8.06", "8.06"], str(got))]
    values = [s for e, s in r.get("history") or [] if e == POWER]
    numeric = [s for s in values if s.replace(".", "", 1).isdigit()]
    return [check("P1 withheld read: never a number", not numeric, str(values[:6]))]


def p2(r: dict) -> list[bool]:
    states = {k: s for k, (s, _a) in final_states(r).items()}
    if r["arm"] == "confined":
        states.update({k: v for k, v in (r.get("platform_states") or {}).items()
                       if k.startswith("sensor.watchman") or k.startswith("button.watchman")})
    expect_missing = 2 if (r["arm"] == "confined" and r["variant"] == "watchman") else 1
    label = f"P2 {r['variant']} {r['arm']}"
    status = states.get("sensor.watchman_status")
    processed = states.get("sensor.watchman_processed_files")
    return [
        check(f"{label}: scanned", status not in (None, "pending", "unknown"), f"status {status}"),
        check(f"{label}: processed_files >= 1",
              processed is not None and processed.isdigit() and int(processed) >= 1,
              f"{processed}"),
        check(f"{label}: missing_entities = {expect_missing}",
              states.get("sensor.watchman_missing_entities") == str(expect_missing),
              f"{states.get('sensor.watchman_missing_entities')}"),
        check(f"{label}: missing_actions = 1",
              states.get("sensor.watchman_missing_actions") == "1",
              f"{states.get('sensor.watchman_missing_actions')}"),
    ]


def adaptive_settings(r: dict) -> dict:
    for _entity, (_state, attributes) in final_states(r).items():
        if "brightness_pct" in attributes:
            return attributes
    return {}


def p3(r: dict, other: dict | None) -> list[bool]:
    settings = adaptive_settings(r)
    pct = settings.get("brightness_pct")
    calls = [c for c in r.get("calls") or [] if c["service"] == "light.turn_on"]
    label = f"P3 {r['variant']} {r['arm']}"
    out = [check(f"{label}: brightness_pct and color_temp_kelvin attributes",
                 pct is not None and settings.get("color_temp_kelvin") is not None,
                 f"{pct} %, {settings.get('color_temp_kelvin')} K")]
    if r["variant"].endswith("no-service"):
        out.append(check(f"{label}: zero calls reach the platform", not calls, f"{len(calls)}"))
        out.append(check(f"{label}: zero service decisions recorded",
                         not service_decisions(r), f"{len(service_decisions(r))}"))
        return out
    want = round(255 * pct / 100) if pct is not None else None
    lit = [c for c in calls if LIGHT in json.dumps(c["data"])]
    out.append(check(f"{label}: >= 1 light.turn_on for {LIGHT}", bool(lit), f"{len(calls)} calls"))
    if lit:
        data = lit[-1]["data"]
        out.append(check(f"{label}: brightness = round(255 x pct / 100) +-1",
                         want is not None and abs(int(data.get("brightness", -99)) - want) <= 1,
                         f"sent {data.get('brightness')}, from attribute {want}"))
        out.append(check(f"{label}: no colour, no transition",
                         not (COLOUR_KEYS & set(data)) and "transition" not in data,
                         str(sorted(data))))
    if other is not None and r["arm"] == "confined":
        theirs = adaptive_settings(other)
        if theirs.get("brightness_pct") is not None and pct is not None:
            out.append(check("P3 arms agree: brightness within 2 points, colour within 50 K",
                             abs(theirs["brightness_pct"] - pct) <= 2 and
                             abs(theirs["color_temp_kelvin"] - settings["color_temp_kelvin"]) <= 50,
                             f"{theirs['brightness_pct']}/{pct} %, "
                             f"{theirs['color_temp_kelvin']}/{settings['color_temp_kelvin']} K"))
    return out


def p4(r: dict) -> list[bool]:
    label = f"P4 {r['variant']} {r['arm']}"
    schedules = {k: s for k, (s, _a) in final_states(r).items() if k.startswith("switch.schedule")}
    seen = [s for e, s in (r.get("history") or []) if e.startswith("switch.schedule")]
    seen += [p["state"] for p in r.get("published") or [] if p["entity"].startswith("switch.schedule")]
    out = [check(f"{label}: a switch.schedule_* published, 'on' after add",
                 "on" in seen, f"{sorted(schedules)} seen {seen[:4]}")]
    calls = [c for c in r.get("calls") or [] if c["service"] == "light.turn_on"]
    if r["variant"].endswith("no-service"):
        out.append(check(f"{label}: zero calls reach the platform", not calls, f"{len(calls)}"))
        out.append(check(f"{label}: zero service decisions recorded",
                         not service_decisions(r), f"{len(service_decisions(r))}"))
        return out
    start = next((s.get("start") for s in r.get("steps") or [] if s.get("start")), None)
    out.append(check(f"{label}: exactly one light.turn_on, brightness 200, for {LIGHT}",
                     len(calls) == 1 and LIGHT in json.dumps(calls[0]["data"])
                     and int(calls[0]["data"].get("brightness", -1)) == 200,
                     json.dumps([c["data"] for c in calls])[:120]))
    if calls and start:
        lag = (datetime.fromisoformat(calls[0]["utc"])
               - datetime.fromisoformat(start)).total_seconds()
        out.append(check(f"{label}: at the start time +-5 s, not before", -0.5 <= lag <= 5,
                         f"{lag:+.1f} s after {start}"))
    out.append(check(f"{label}: switch 'off' after a single run (least certain)",
                     bool(schedules) and all(s == "off" for s in schedules.values()),
                     str(schedules)))
    return out


def p5(r: dict) -> list[bool]:
    states = {k: s for k, (s, _a) in final_states(r).items()}
    dew = states.get("sensor.living_room_dew_point")
    own = [k for k in states if k.startswith("sensor.living_room_")]
    out = [check(f"P5 {r['arm']}: dew point 9.96",
                 dew is not None and round(float(dew), 2) == 9.96, f"{dew}")]
    if r["arm"] == "confined":
        out.append(check("P5 confined: 15 entities", len(own) == 15, f"{len(own)}"))
    return out


def main() -> int:
    reports = [r for path in sys.argv[1:] for r in json.load(open(path))]
    by = {(r["variant"], r["arm"]): r for r in reports}
    results: list[bool] = []
    for r in reports:
        if r.get("level"):
            results.append(check(f"{r['variant']} {r['arm']} ran", False, r.get("error", "")[:80]))
            continue
        domain = r["variant"].split("-")[0]
        if domain == "powercalc":
            results += p1(r)
        elif domain == "watchman":
            results += p2(r)
        elif domain == "adaptive_lighting":
            results += p3(r, by.get((r["variant"], "unconfined")))
        elif domain == "scheduler":
            results += p4(r)
        elif domain == "thermal_comfort":
            results += p5(r)
    print(f"\n  {sum(results)} of {len(results)} predictions held")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
