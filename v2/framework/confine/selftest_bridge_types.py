"""The bridge's entity types beyond sensor, binary sensor and switch, against the house's (A).

Step 1 of extending the bridge (`notes/bridge_types_step1_prediction_20261025.md`): button, text,
select and number. Each published entity must become a registry-backed entity **of its own type**
in (A), described well enough for Home Assistant to draw its control. Operating them is step 2
(`notes/bridge_types_step2_prediction_20261025.md`).

    T1   each of the four publishes to an entity-registry row of its domain, owned by the bridge
    T2   (A) holds the state and the attributes that describe the control
    T3   a republish from the sandbox changes the state in (A)
    T4'  each is operated from a user in (A): the command reaches the sandbox with exactly
         its data, and the result shows in (A) (bridge step 2)
    T4'' a value (A) rejects never reaches the mediator
    T5   a type still unsupported (light) is refused at publish
    T6   a climate and an alarm panel are entities of their own type in (A), described (step 3)
    T7'  each is operated from a user in (A), its data reaching the sandbox exactly
    T8   a house in US customary units sends a climate temperature to the sandbox in °C
    T9   an alarm code typed in (A) is not in the durable log
    W1   a calendar and a weather are entities of their own type in (A), described (step 4)
    W2   a calendar's events, asked for in (A), come from the sandbox's answer
    W3   a weather's forecast, asked for in (A), comes from the sandbox's answer
    W4   a malformed answer fails the question, and nothing of it reaches (A)
    W5   the events' titles are not in the durable log
    U1   a numeric sensor published `unknown` is accepted and shows `unknown` in (A) (F66)
    U2   then a number, then `unavailable`, each shown as such
    U3   a switch published `unavailable` shows `unavailable`
    V1   a timestamp sensor published with a space shows the same instant in (A) (F67)
    V2   one published with a `T` shows it; then `unknown`
    V3   a date sensor shows its date

Requires (A) running: `python3 -m confine.house_a up --fresh` on the Pi.

Run:  python3 -m confine.selftest_bridge_types
"""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime
from pathlib import Path

from . import house_a
from .audit import AuditLog
from .house_a import User
from .mediator import Mediator
from .platform import ActingPolicy
from .real_platform import RealPlatform
from .selftest_push import Sandbox
from .selftest_real_platform import check, manifest, registry, results, serve_until

# One entity of each type, as an integration would publish it: the state, and the attributes its
# own Home Assistant gives it. `watchman`'s button and text are the shapes the end-to-end set uses.
ENTITIES = {
    "button.selftest_report": ("unknown", {"friendly_name": "Selftest report"}),
    "text.selftest_ignored": ("*.tmp", {"friendly_name": "Selftest ignored files",
                                        "min": 0, "max": 255, "pattern": None, "mode": "text"}),
    "select.selftest_mode": ("eco", {"friendly_name": "Selftest mode",
                                     "options": ["comfort", "eco", "away"]}),
    "number.selftest_target": ("21.5", {"friendly_name": "Selftest target", "min": 5.0,
                                        "max": 30.0, "step": 0.5, "mode": "slider",
                                        "unit_of_measurement": "°C"}),
}
# What (A) must show for each, beyond the state: the attributes that draw the control.
DESCRIBED = {
    "text.selftest_ignored": {"min": 0, "max": 255, "mode": "text"},
    "select.selftest_mode": {"options": ["comfort", "eco", "away"]},
    "number.selftest_target": {"min": 5.0, "max": 30.0, "step": 0.5, "mode": "slider",
                               "unit_of_measurement": "°C"},
}
UPDATES = {"text.selftest_ignored": "*.bak", "select.selftest_mode": "away",
           "number.selftest_target": "19.0"}


def _iso_time(value: object) -> bool:
    try:
        datetime.fromisoformat(str(value))
    except ValueError:
        return False
    return True


def main() -> int:
    if not house_a.running():
        print("(A) is not running: python3 -m confine.house_a up --fresh")
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        platform = RealPlatform()
        log = AuditLog(path=root / "audit" / "decisions.jsonl")
        mediator = Mediator(policy=ActingPolicy({}, platform), log=log)
        mediator.attach_platform(platform)
        sandbox = Sandbox(mediator, "selftest", manifest(root, "selftest", {}))

        print("\nT1, T2 — each type is an entity of its own type in (A), described\n")
        landed: dict[str, str] = {}
        for entity, (state, attributes) in ENTITIES.items():
            answer = sandbox.ask({"op": "entity.publish", "entity": entity, "state": state,
                                  "attributes": attributes})
            landed[entity] = platform.published.get(("selftest", entity)) or ""
            row = registry(platform).get(landed[entity], {})
            domain = entity.partition(".")[0]
            check(f"T1 {domain}: published, and a registry row of its domain owned by the bridge",
                  answer.get("ok") is True and row.get("platform") == "confine_bridge"
                  and landed[entity].startswith(f"{domain}.")
                  and row.get("unique_id") == f"selftest:{entity}",
                  answer.get("reason") or landed[entity])
            shown, shown_attributes = platform.read(landed[entity]) if landed[entity] else (None, {})
            wanted = DESCRIBED.get(entity, {})
            missing = {k: (v, (shown_attributes or {}).get(k)) for k, v in wanted.items()
                       if (shown_attributes or {}).get(k) != v}
            # A button's state is the time it was last pressed in (A), which (A) keeps: `unknown`
            # only until the first press. A second run against the same (A) finds that time (the
            # step-2 run inside suites_all did, 2026-10-25).
            if domain == "button":
                held = shown == "unknown" or _iso_time(shown)
            else:
                held = shown == state
            check(f"T2 {domain}: (A) holds the state and the attributes that describe it",
                  held and not missing, f"{shown!r} {missing or ''}")

        print("\nT3 — a republish changes the state in (A)\n")
        for entity, state in UPDATES.items():
            sandbox.ask({"op": "entity.publish", "entity": entity, "state": state,
                         "attributes": ENTITIES[entity][1]})
            shown = platform.read(landed[entity])[0] if landed[entity] else None
            check(f"T3 {entity.partition('.')[0]}: now {state}", shown == state, f"{shown!r}")

        print("\nT4' — operating each one, from a user in (A) (step 2)\n")
        # The happy path, played by hand as `selftest_real_platform` does: the in-process sandbox
        # receives the command, publishes what its own handler would have set, and answers.
        for entity, service, data, after in (
                ("button.selftest_report", "press", {}, None),
                ("text.selftest_ignored", "set_value", {"value": "*.log"}, "*.log"),
                ("select.selftest_mode", "select_option", {"option": "comfort"}, "comfort"),
                ("number.selftest_target", "set_value", {"value": 22}, "22.0")):
            domain = entity.partition(".")[0]
            sandbox.received.clear()
            user = User()
            pressed = user.press(landed[entity] or entity, service, data)
            arrived = serve_until(mediator, lambda: (sandbox.drain(), [
                m for m in sandbox.received if m.get("push") == "entity.command"])[1])
            command = next((m for m in sandbox.received if m.get("push") == "entity.command"), {})
            sent = command.get("data")
            check(f"T4' {domain}.{service}: reaches the sandbox with exactly its data",
                  bool(arrived) and command.get("entity") == entity
                  and command.get("service") == service
                  and (sent == data if domain != "number" else sent == {"value": 22.0}),
                  f"{command}")
            if after is not None:
                sandbox.ask({"op": "entity.publish", "entity": entity, "state": after,
                             "attributes": ENTITIES[entity][1]})
            sandbox.ask({"op": "entity.command_result", "command": command.get("command"),
                         "ok": True})
            serve_until(mediator, lambda: not pressed.is_alive())
            pressed.join()
            user.close()
            shown = platform.read(landed[entity])[0] if landed[entity] else None
            check(f"T4' {domain}.{service}: the user's call succeeds and (A) shows the result",
                  user.outcome.get("success") is True
                  and (shown == after if after is not None
                       else shown not in (None, "unknown", "unavailable")),
                  f"{user.outcome.get('error') or ''} {shown!r}")

        print("\nT4'' — a value (A) rejects never reaches the mediator\n")
        before = len([r for r in log.records() if r.get("op") == "entity.command"])
        user = User()
        pressed = user.press(landed["number.selftest_target"] or "number.selftest_target",
                             "set_value", {"value": 99})
        serve_until(mediator, lambda: not pressed.is_alive(), seconds=15)
        pressed.join()
        user.close()
        after_count = len([r for r in log.records() if r.get("op") == "entity.command"])
        check("T4'' number.set_value 99 (range 5-30) fails in (A)",
              user.outcome.get("success") is False, str(user.outcome.get("error")))
        check("T4'' and no command decision was recorded: it never left (A)",
              after_count == before, f"{after_count - before} new")

        print("\nT6 — a climate and an alarm panel, described (step 3)\n")
        AC, ALARM = "climate.selftest_ac", "alarm_control_panel.selftest_alarm"
        ac_attributes = {"friendly_name": "Selftest AC", "hvac_modes": ["off", "cool", "heat", "auto"],
                         "min_temp": 16, "max_temp": 30, "target_temp_step": 0.5,
                         "current_temperature": 24.5, "temperature": 22, "fan_modes":
                         ["auto", "low", "high"], "fan_mode": "auto", "hvac_action": "cooling",
                         # TARGET_TEMPERATURE | FAN_MODE | TURN_OFF | TURN_ON
                         "supported_features": 1 | 8 | 128 | 256}
        alarm_attributes = {"friendly_name": "Selftest alarm", "code_format": "number",
                            "changed_by": None, "code_arm_required": True,
                            # ARM_HOME | ARM_AWAY | ARM_NIGHT | TRIGGER | CUSTOM_BYPASS | VACATION
                            "supported_features": 63}
        for entity, state, attributes, wanted in (
                (AC, "cool", ac_attributes,
                 {"hvac_modes": ["off", "cool", "heat", "auto"], "min_temp": 16, "max_temp": 30,
                  "current_temperature": 24.5, "temperature": 22,
                  "fan_modes": ["auto", "low", "high"]}),
                (ALARM, "disarmed", alarm_attributes, {"code_format": "number"})):
            answer = sandbox.ask({"op": "entity.publish", "entity": entity, "state": state,
                                  "attributes": attributes})
            landed[entity] = platform.published.get(("selftest", entity)) or ""
            row = registry(platform).get(landed[entity], {})
            domain = entity.partition(".")[0]
            check(f"T6 {domain}: a registry row of its domain owned by the bridge",
                  answer.get("ok") is True and row.get("platform") == "confine_bridge"
                  and landed[entity].startswith(f"{domain}."),
                  answer.get("reason") or landed[entity])
            shown, shown_attributes = platform.read(landed[entity]) if landed[entity] else (None, {})
            missing = {k: (v, (shown_attributes or {}).get(k)) for k, v in wanted.items()
                       if (shown_attributes or {}).get(k) != v}
            check(f"T6 {domain}: (A) holds its state and the attributes that describe it",
                  shown == state and not missing, f"{shown!r} {missing or ''}")

        print("\nT7' — operating them from a user in (A)\n")
        for entity, service, data, expected, state, attributes in (
                (AC, "set_temperature", {"temperature": 23}, {"temperature": 23.0}, "cool",
                 {**ac_attributes, "temperature": 23}),
                (AC, "set_hvac_mode", {"hvac_mode": "heat"}, {"hvac_mode": "heat"}, "heat",
                 {**ac_attributes, "temperature": 23}),
                (ALARM, "alarm_arm_away", {"code": "4917"}, {"code": "4917"}, "armed_away",
                 alarm_attributes),
                (ALARM, "alarm_trigger", {}, {}, "triggered", alarm_attributes)):
            domain = entity.partition(".")[0]
            sandbox.received.clear()
            user = User()
            pressed = user.press(landed[entity] or entity, service, data)
            arrived = serve_until(mediator, lambda: (sandbox.drain(), [
                m for m in sandbox.received if m.get("push") == "entity.command"])[1])
            command = next((m for m in sandbox.received if m.get("push") == "entity.command"), {})
            check(f"T7' {domain}.{service}: reaches the sandbox as {expected}",
                  bool(arrived) and command.get("service") == service
                  and command.get("data") == expected, f"{command or user.outcome}")
            if arrived:
                sandbox.ask({"op": "entity.publish", "entity": entity, "state": state,
                             "attributes": attributes})
                sandbox.ask({"op": "entity.command_result", "command": command.get("command"),
                             "ok": True})
            serve_until(mediator, lambda: not pressed.is_alive())
            pressed.join()
            user.close()
            shown = platform.read(landed[entity])[0] if landed[entity] else None
            check(f"T7' {domain}.{service}: the call succeeds and (A) shows {state}",
                  user.outcome.get("success") is True and shown == state,
                  f"{user.outcome.get('error') or ''} {shown!r}")

        print("\nT8 — a house in °F sends the sandbox °C\n")
        admin = house_a.TOKEN_FILE.read_text().strip()
        switched = house_a._ws_call(admin, {"type": "config/core/update",
                                            "unit_system": "us_customary"})
        try:
            sandbox.received.clear()
            user = User()
            pressed = user.press(landed[AC] or AC, "set_temperature", {"temperature": 73.4})
            arrived = serve_until(mediator, lambda: (sandbox.drain(), [
                m for m in sandbox.received if m.get("push") == "entity.command"])[1])
            command = next((m for m in sandbox.received if m.get("push") == "entity.command"), {})
            sent = (command.get("data") or {}).get("temperature")
            check("T8 73.4 °F typed in (A) reaches the sandbox as 23.0 °C",
                  bool(switched.get("success")) and isinstance(sent, (int, float))
                  and abs(sent - 23.0) < 0.01, f"{sent!r} {switched.get('error') or ''}")
            if arrived:
                sandbox.ask({"op": "entity.command_result", "command": command.get("command"),
                             "ok": True})
            serve_until(mediator, lambda: not pressed.is_alive())
            pressed.join()
            user.close()
        finally:
            restored = house_a._ws_call(admin, {"type": "config/core/update",
                                                "unit_system": "metric"})
        check("T8 and (A) is back in metric units", bool(restored.get("success")),
              str(restored.get("error") or ""))

        print("\nT9 — the alarm code is not in the durable log\n")
        # As a JSON value, in quotes: a bare 4917 can turn up by chance in the log's hex hashes and
        # timestamps (step 4, 2026-10-25), and a quote cannot.
        check("T9 '4917' appears nowhere in the run's durable log",
              '"4917"' not in (root / "audit" / "decisions.jsonl").read_text())

        print("\nW1 — a calendar and a weather, described (step 4)\n")
        CAL, WEATHER = "calendar.selftest_bins", "weather.selftest_home"
        cal_attributes = {"friendly_name": "Selftest bins", "message": "Bio bin", "all_day": True,
                          "start_time": "2026-10-28 00:00:00", "end_time": "2026-10-29 00:00:00",
                          "location": "", "description": ""}
        weather_attributes = {"friendly_name": "Selftest home", "temperature": 12.5,
                              "temperature_unit": "°C", "humidity": 80, "pressure": 1012,
                              "pressure_unit": "hPa", "wind_speed": 14.4,
                              "wind_speed_unit": "km/h", "visibility_unit": "km",
                              "precipitation_unit": "mm",
                              # FORECAST_DAILY | FORECAST_HOURLY
                              "supported_features": 1 | 2}
        for entity, state, attributes, wanted in (
                (CAL, "off", cal_attributes, {"message": "Bio bin"}),
                (WEATHER, "rainy", weather_attributes,
                 {"temperature": 12.5, "temperature_unit": "°C"})):
            answer = sandbox.ask({"op": "entity.publish", "entity": entity, "state": state,
                                  "attributes": attributes})
            landed[entity] = platform.published.get(("selftest", entity)) or ""
            row = registry(platform).get(landed[entity], {})
            domain = entity.partition(".")[0]
            check(f"W1 {domain}: a registry row of its domain owned by the bridge",
                  answer.get("ok") is True and row.get("platform") == "confine_bridge"
                  and landed[entity].startswith(f"{domain}."),
                  answer.get("reason") or landed[entity])
            shown, shown_attributes = platform.read(landed[entity]) if landed[entity] else (None, {})
            missing = {k: (v, (shown_attributes or {}).get(k)) for k, v in wanted.items()
                       if (shown_attributes or {}).get(k) != v}
            check(f"W1 {domain}: (A) holds its state and the attributes that describe it",
                  shown == state and not missing, f"{shown!r} {missing or ''}")

        def question(entity: str, service: str, data: dict, payload: object) -> tuple[dict, dict]:
            """A user in (A) asks; the in-process sandbox answers with `payload`."""
            sandbox.received.clear()
            user = User()
            pressed = user.press(landed[entity] or entity, service, data, return_response=True)
            arrived = serve_until(mediator, lambda: (sandbox.drain(), [
                m for m in sandbox.received if m.get("push") == "entity.command"])[1])
            asked = next((m for m in sandbox.received if m.get("push") == "entity.command"), {})
            if arrived:
                sandbox.ask({"op": "entity.command_result", "command": asked.get("command"),
                             "ok": True, "answer": payload})
            serve_until(mediator, lambda: not pressed.is_alive())
            pressed.join()
            user.close()
            return asked, user.outcome

        print("\nW2 — a calendar's events come from the sandbox's answer\n")
        events = [{"summary": "Dentist, Dr Example", "start": "2026-10-27T09:00:00+01:00",
                   "end": "2026-10-27T10:00:00+01:00", "location": "Darmstadt"},
                  {"summary": "Bio bin", "start": "2026-10-28", "end": "2026-10-29"}]
        asked, outcome = question(CAL, "get_events",
                                  {"start_date_time": "2026-10-26 00:00:00",
                                   "end_date_time": "2026-11-02 00:00:00"}, events)
        check("W2 the sandbox is asked get_events with a start and an end, and nothing else",
              asked.get("service") == "get_events"
              and set(asked.get("data") or {}) == {"start", "end"}, f"{asked or outcome}")
        listed = ((outcome.get("response") or {}).get(landed[CAL] or CAL) or {}).get("events") or []
        check("W2 the user's response lists the two events the sandbox answered",
              outcome.get("success") is True
              and [e.get("summary") for e in listed] == ["Dentist, Dr Example", "Bio bin"],
              f"{outcome.get('error') or ''} {listed}")

        print("\nW3 — a weather's forecast comes from the sandbox's answer\n")
        forecast = [{"datetime": "2026-10-26T12:00:00+00:00", "condition": "rainy",
                     "temperature": 12.5, "templow": 6.0, "precipitation": 3.2},
                    {"datetime": "2026-10-27T12:00:00+00:00", "condition": "cloudy",
                     "temperature": 11.0, "templow": 5.0},
                    {"datetime": "2026-10-28T12:00:00+00:00", "condition": "sunny",
                     "temperature": 14.0, "templow": 7.5}]
        asked, outcome = question(WEATHER, "get_forecasts", {"type": "daily"}, forecast)
        check("W3 the sandbox is asked get_forecasts {type: daily}",
              asked.get("service") == "get_forecasts" and asked.get("data") == {"type": "daily"},
              f"{asked or outcome}")
        entries = ((outcome.get("response") or {}).get(landed[WEATHER] or WEATHER)
                   or {}).get("forecast") or []
        check("W3 the user's response has the three entries, with their temperatures",
              outcome.get("success") is True
              and [e.get("temperature") for e in entries] == [12.5, 11.0, 14.0],
              f"{outcome.get('error') or ''} {entries}")

        print("\nW4 — a malformed answer fails the question\n")
        asked, outcome = question(CAL, "get_events",
                                  {"start_date_time": "2026-10-26 00:00:00",
                                   "end_date_time": "2026-11-02 00:00:00"},
                                  [{**events[1], "script": "alert(1)"}])
        check("W4 the user's call fails, and the answer did not reach (A)",
              bool(asked) and outcome.get("success") is False
              and "alert(1)" not in str(outcome), f"{outcome}")

        print("\nW5 — the events' titles are not in the durable log\n")
        check("W5 'Dentist, Dr Example' appears nowhere in the run's durable log",
              "Dentist, Dr Example" not in (root / "audit" / "decisions.jsonl").read_text())

        print("\nU — unknown and unavailable states (F66)\n")
        POWER = "sensor.selftest_lamp_power"
        power_attributes = {"friendly_name": "Selftest lamp power", "device_class": "power",
                            "state_class": "measurement", "unit_of_measurement": "W"}
        answer = sandbox.ask({"op": "entity.publish", "entity": POWER, "state": "unknown",
                              "attributes": power_attributes})
        landed[POWER] = platform.published.get(("selftest", POWER)) or ""
        shown = platform.read(landed[POWER])[0] if landed[POWER] else None
        check("U1 a numeric sensor published 'unknown' is accepted, and (A) shows unknown",
              answer.get("ok") is True and shown == "unknown",
              f"{answer.get('reason') or ''} {shown!r}")
        for state in ("12.5", "unavailable"):
            sandbox.ask({"op": "entity.publish", "entity": POWER, "state": state,
                         "attributes": power_attributes})
            shown = platform.read(landed[POWER])[0] if landed[POWER] else None
            check(f"U2 republished {state!r}, (A) shows it", shown == state, f"{shown!r}")
        DOWN = "switch.selftest_unreachable"
        answer = sandbox.ask({"op": "entity.publish", "entity": DOWN, "state": "unavailable"})
        landed[DOWN] = platform.published.get(("selftest", DOWN)) or ""
        shown = platform.read(landed[DOWN])[0] if landed[DOWN] else None
        check("U3 a switch published 'unavailable' shows unavailable in (A)",
              answer.get("ok") is True and shown == "unavailable", f"{shown!r}")

        print("\nV — timestamp and date sensors (F67)\n")
        for entity, device_class, state, expected in (
                ("sensor.selftest_forecast_time", "timestamp", "2026-10-25 15:00:00+00:00",
                 "2026-10-25T15:00:00+00:00"),
                ("sensor.selftest_measured_time", "timestamp", "2026-10-25T18:00:00+00:00",
                 "2026-10-25T18:00:00+00:00"),
                ("sensor.selftest_next_collection", "date", "2026-10-28", "2026-10-28")):
            answer = sandbox.ask({"op": "entity.publish", "entity": entity, "state": state,
                                  "attributes": {"device_class": device_class}})
            landed[entity] = platform.published.get(("selftest", entity)) or ""
            shown = platform.read(landed[entity])[0] if landed[entity] else None
            label = "V1" if "forecast" in entity else "V2" if "measured" in entity else "V3"
            check(f"{label} a {device_class} sensor published {state!r} shows {expected!r} in (A)",
                  answer.get("ok") is True and shown == expected, f"{shown!r}")
        MEASURED = "sensor.selftest_measured_time"
        sandbox.ask({"op": "entity.publish", "entity": MEASURED, "state": "unknown",
                     "attributes": {"device_class": "timestamp"}})
        shown = platform.read(landed[MEASURED])[0] if landed[MEASURED] else None
        check("V2 republished 'unknown', (A) shows unknown", shown == "unknown", f"{shown!r}")

        print("\nT5 — a type still unsupported is refused\n")
        light = sandbox.ask({"op": "entity.publish", "entity": "light.selftest_probe",
                             "state": "on"})
        check("T5 a light is refused at publish", light.get("ok") is False,
              light.get("reason", ""))
        check("every chain verifies", log.verify() == [])
        platform.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
