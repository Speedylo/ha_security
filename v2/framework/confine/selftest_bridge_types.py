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
    T5   a type the bridge does not stand in for (a to-do list; a light until B1, a vacuum until
         B2) is refused at publish
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
    X1   a switch published `triggered` (as `scheduler`'s is, after a slot fires) shows it in (A)
    X2   then `on`, `off`, `completed`, `unknown`, `triggered`, each shown as such
    X3   with `--restart`: after (A) restarts, the switch shows its last published state
    T11  a light, fan, cover and lock are entities of their own type in (A), described (batch B1)
    T12  each is operated from a user in (A), and the sandbox receives what (A) worked out:
         brightness_pct as brightness, a colour name as rgb_color, toggle as turn_off,
         increase_speed as set_percentage, a cover's toggle as open_cover, a lock code as typed
    T13  a fan preset mode the fan does not offer fails in (A) and never reaches the mediator
    T14  a lock code typed in (A) is not in the durable log
    T16  a default code stored for the lock in (A) reaches the sandbox, and not the log
    T17  a humidifier, water heater, vacuum, valve, siren and remote, described (batch B2)
    T18  each operated from a user in (A), the sandbox receiving what (A) worked out: away mode as
         set_away_mode, a positioned valve's open as position 100, a siren tone by name, a remote's
         command with (A)'s defaults, and a water heater's °F as °C
    T19  a humidity above the published maximum fails in (A) and never reaches the mediator
    T22  an update, time, notify, event, GPS tracker and scanner, described (batch B3)
    T23  (A) works out a GPS tracker's home or away from its own zones; a scanner shows its state
    T24  a published event fires once in (A); a republish does not fire it again
    T25  update skip and clear_skipped stay in (A); install, a time and a message reach the sandbox
    T26  a notification's text is not in the durable log

Requires (A) running: `python3 -m confine.house_a up --fresh` on the Pi.

Run:  python3 -m confine.selftest_bridge_types [--restart]
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from . import house_a
from .audit import AuditLog
from .house_a import User
from .mediator import Mediator
from .platform import ActingPolicy
from .real_platform import PlatformStarting, RealPlatform
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--restart", action="store_true",
                    help="also restart (A) and check the switch's state survives it (X3)")
    args = ap.parse_args()
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

        print("\nX — a switch shows the state its integration published\n")
        SCHEDULE = "switch.selftest_schedule"
        answer = sandbox.ask({"op": "entity.publish", "entity": SCHEDULE, "state": "triggered"})
        landed[SCHEDULE] = platform.published.get(("selftest", SCHEDULE)) or ""
        row = registry(platform).get(landed[SCHEDULE], {})
        shown = platform.read(landed[SCHEDULE])[0] if landed[SCHEDULE] else None
        check("X1 a switch published 'triggered' is the bridge's switch, and (A) shows triggered",
              answer.get("ok") is True and row.get("platform") == "confine_bridge"
              and landed[SCHEDULE].startswith("switch.") and shown == "triggered", f"{shown!r}")
        for state in ("on", "off", "completed", "unknown", "triggered"):
            sandbox.ask({"op": "entity.publish", "entity": SCHEDULE, "state": state})
            shown = platform.read(landed[SCHEDULE])[0] if landed[SCHEDULE] else None
            check(f"X2 republished {state!r}, (A) shows it", shown == state, f"{shown!r}")

        print("\nT11 — a light, fan, cover and lock, described (batch B1)\n")
        # `notes/bridge_kinds_b1_prediction_20261031.md`. Feature numbers from Home Assistant
        # 2026.8.3: fan SET_SPEED 1 | OSCILLATE 2 | DIRECTION 4 | PRESET_MODE 8 | TURN_OFF 16 |
        # TURN_ON 32; cover OPEN 1 | CLOSE 2 | SET_POSITION 4 | STOP 8. A light with no features
        # gets neither effect, flash nor transition from (A).
        LAMP, FAN = "light.selftest_lamp", "fan.selftest_fan"
        BLIND, DOOR = "cover.selftest_blind", "lock.selftest_door"
        lamp_attributes = {"friendly_name": "Selftest lamp", "supported_color_modes": ["rgb"],
                           "color_mode": "rgb", "brightness": 200, "rgb_color": [255, 255, 255],
                           "supported_features": 0}
        fan_attributes = {"friendly_name": "Selftest fan", "percentage": 50,
                          "percentage_step": 25.0, "preset_modes": ["auto", "sleep"],
                          "preset_mode": None, "oscillating": False, "direction": "forward",
                          "supported_features": 63}
        blind_attributes = {"friendly_name": "Selftest blind", "current_position": 0,
                            "supported_features": 15}
        door_attributes = {"friendly_name": "Selftest door", "code_format": "^\\d{4}$",
                           "supported_features": 0}
        for entity, state, attributes, wanted in (
                (LAMP, "on", lamp_attributes,
                 {"supported_color_modes": ["rgb"], "brightness": 200}),
                (FAN, "on", fan_attributes,
                 {"percentage": 50, "percentage_step": 25.0, "preset_modes": ["auto", "sleep"],
                  "oscillating": False, "direction": "forward"}),
                (BLIND, "closed", blind_attributes, {"current_position": 0}),
                (DOOR, "locked", door_attributes, {"code_format": "^\\d{4}$"})):
            answer = sandbox.ask({"op": "entity.publish", "entity": entity, "state": state,
                                  "attributes": attributes})
            landed[entity] = platform.published.get(("selftest", entity)) or ""
            row = registry(platform).get(landed[entity], {})
            domain = entity.partition(".")[0]
            check(f"T11 {domain}: a registry row of its domain owned by the bridge",
                  answer.get("ok") is True and row.get("platform") == "confine_bridge"
                  and landed[entity].startswith(f"{domain}."),
                  answer.get("reason") or landed[entity])
            shown, shown_attributes = platform.read(landed[entity]) if landed[entity] else (None, {})
            missing = {k: (v, (shown_attributes or {}).get(k)) for k, v in wanted.items()
                       if (shown_attributes or {}).get(k) != v}
            check(f"T11 {domain}: (A) holds its state and the attributes that describe it",
                  shown == state and not missing, f"{shown!r} {missing or ''}")

        def operate(entity: str, service: str, data: dict) -> tuple[dict, dict]:
            """A user in (A) calls `service`: what reached the sandbox, and the call in flight,
            which `finish` completes as the integration's own handler would."""
            sandbox.received.clear()
            user = User()
            pressed = user.press(landed[entity] or entity, service, data)
            arrived = serve_until(mediator, lambda: (sandbox.drain(), [
                m for m in sandbox.received if m.get("push") == "entity.command"])[1])
            command = next((m for m in sandbox.received if m.get("push") == "entity.command"), {})
            return command, {"user": user, "pressed": pressed, "arrived": bool(arrived)}

        def finish(entity: str, command: dict, pending: dict, state: str, attributes: dict) -> tuple:
            if pending["arrived"]:
                sandbox.ask({"op": "entity.publish", "entity": entity, "state": state,
                             "attributes": attributes})
                sandbox.ask({"op": "entity.command_result", "command": command.get("command"),
                             "ok": True})
            serve_until(mediator, lambda: not pending["pressed"].is_alive())
            pending["pressed"].join()
            pending["user"].close()
            shown = platform.read(landed[entity])[0] if landed[entity] else None
            return pending["user"].outcome, shown

        print("\nT12 — operating them: the sandbox receives what (A) worked out\n")
        for entity, service, data, expected_service, expected, state, attributes in (
                (LAMP, "turn_on", {"brightness_pct": 50}, "turn_on", {"brightness": 128}, "on",
                 {**lamp_attributes, "brightness": 128}),
                (LAMP, "turn_on", {"color_name": "red"}, "turn_on", {"rgb_color": [255, 0, 0]},
                 "on", {**lamp_attributes, "brightness": 128, "rgb_color": [255, 0, 0]}),
                (LAMP, "toggle", {}, "turn_off", {}, "off", lamp_attributes),
                (FAN, "increase_speed", {}, "set_percentage", {"percentage": 75}, "on",
                 {**fan_attributes, "percentage": 75}),
                (BLIND, "toggle", {}, "open_cover", {}, "open",
                 {**blind_attributes, "current_position": 100}),
                (DOOR, "unlock", {"code": "5820"}, "unlock", {"code": "5820"}, "unlocked",
                 door_attributes)):
            domain = entity.partition(".")[0]
            command, pending = operate(entity, service, data)
            check(f"T12 {domain}.{service} {data or ''}: reaches the sandbox as "
                  f"{expected_service} {expected}",
                  pending["arrived"] and command.get("entity") == entity
                  and command.get("service") == expected_service
                  and command.get("data") == expected, f"{command or pending['user'].outcome}")
            outcome, shown = finish(entity, command, pending, state, attributes)
            check(f"T12 {domain}.{service}: the call succeeds and (A) shows {state}",
                  outcome.get("success") is True and shown == state,
                  f"{outcome.get('error') or ''} {shown!r}")

        print("\nT13 — a preset the fan does not offer never reaches the mediator\n")
        before = len([r for r in log.records() if r.get("op") == "entity.command"])
        user = User()
        pressed = user.press(landed[FAN] or FAN, "set_preset_mode", {"preset_mode": "turbo"})
        serve_until(mediator, lambda: not pressed.is_alive(), seconds=15)
        pressed.join()
        user.close()
        after_count = len([r for r in log.records() if r.get("op") == "entity.command"])
        check("T13 fan.set_preset_mode turbo (offered: auto, sleep) fails in (A)",
              user.outcome.get("success") is False, str(user.outcome.get("error")))
        check("T13 and no command decision was recorded: it never left (A)",
              after_count == before, f"{after_count - before} new")

        print("\nT16 — a default code stored in (A) reaches the sandbox, not the log\n")
        # (A) adds the lock's stored default code to a command that has none, if it matches the
        # lock's code format (`lock/__init__.py`, `add_default_code`, `_async_read_entity_options`).
        stored = house_a._ws_call(admin, {"type": "config/entity_registry/update",
                                          "entity_id": landed[DOOR] or DOOR,
                                          "options_domain": "lock",
                                          "options": {"default_code": "5821"}})
        command, pending = operate(DOOR, "lock", {})
        check("T16 lock.lock with no code reaches the sandbox with the stored code",
              bool(stored.get("success")) and pending["arrived"]
              and command.get("service") == "lock" and command.get("data") == {"code": "5821"},
              f"{command or pending['user'].outcome} {stored.get('error') or ''}")
        outcome, shown = finish(DOOR, command, pending, "locked", door_attributes)
        check("T16 the call succeeds and (A) shows locked",
              outcome.get("success") is True and shown == "locked",
              f"{outcome.get('error') or ''} {shown!r}")

        print("\nT14 — the lock codes are not in the durable log\n")
        decisions = (root / "audit" / "decisions.jsonl").read_text()
        check("T14 '5820' (typed) and '5821' (stored) appear nowhere in the run's durable log",
              '"5820"' not in decisions and '"5821"' not in decisions)

        print("\nT17 — humidifier, water heater, vacuum, valve, siren, remote (batch B2)\n")
        # `notes/bridge_kinds_b2_prediction_20261031.md`. Features from Home Assistant 2026.8.3:
        # humidifier MODES 1; water heater TARGET_TEMPERATURE 1 | OPERATION_MODE 2 | AWAY_MODE 4 |
        # ON_OFF 8; vacuum PAUSE 4 | STOP 8 | RETURN_HOME 16 | FAN_SPEED 32 | SEND_COMMAND 256 |
        # LOCATE 512 | CLEAN_SPOT 1024 | STATE 4096 | START 8192; valve OPEN 1 | CLOSE 2 |
        # SET_POSITION 4 | STOP 8; siren TURN_ON 1 | TURN_OFF 2 | TONES 4 | VOLUME_SET 8 |
        # DURATION 16; remote ACTIVITY 4.
        AIR, BOILER = "humidifier.selftest_air", "water_heater.selftest_boiler"
        ROBOT, TAP = "vacuum.selftest_robot", "valve.selftest_tap"
        SIREN, TV = "siren.selftest_alarm", "remote.selftest_tv"
        air_attributes = {"friendly_name": "Selftest air", "min_humidity": 30, "max_humidity": 80,
                          "humidity": 50, "available_modes": ["normal", "eco"], "mode": "normal",
                          "supported_features": 1}
        boiler_attributes = {"friendly_name": "Selftest boiler", "min_temp": 40, "max_temp": 60,
                             "temperature": 45, "current_temperature": 44,
                             "operation_list": ["eco", "electric", "off"],
                             "operation_mode": "eco", "away_mode": "off",
                             "supported_features": 15}
        robot_attributes = {"friendly_name": "Selftest robot", "fan_speed": "standard",
                            "fan_speed_list": ["quiet", "standard", "turbo"],
                            "supported_features": 4 | 8 | 16 | 32 | 256 | 512 | 1024 | 4096 | 8192}
        tap_attributes = {"friendly_name": "Selftest tap", "current_position": 0,
                          "supported_features": 15}
        siren_attributes = {"friendly_name": "Selftest alarm",
                            "available_tones": {"1": "fire", "2": "burglar"},
                            "supported_features": 31}
        tv_attributes = {"friendly_name": "Selftest TV", "activity_list": ["TV", "Music"],
                         "current_activity": "TV", "supported_features": 4}
        for entity, state, attributes, wanted in (
                (AIR, "on", air_attributes, {"min_humidity": 30, "max_humidity": 80,
                                             "available_modes": ["normal", "eco"]}),
                (BOILER, "eco", boiler_attributes, {"operation_list": ["eco", "electric", "off"],
                                                    "temperature": 45}),
                (ROBOT, "docked", robot_attributes,
                 {"fan_speed_list": ["quiet", "standard", "turbo"], "fan_speed": "standard"}),
                (TAP, "closed", tap_attributes, {"current_position": 0}),
                (SIREN, "off", siren_attributes,
                 {"available_tones": {"1": "fire", "2": "burglar"}}),
                (TV, "on", tv_attributes, {"activity_list": ["TV", "Music"],
                                           "current_activity": "TV"})):
            answer = sandbox.ask({"op": "entity.publish", "entity": entity, "state": state,
                                  "attributes": attributes})
            landed[entity] = platform.published.get(("selftest", entity)) or ""
            row = registry(platform).get(landed[entity], {})
            domain = entity.partition(".")[0]
            check(f"T17 {domain}: a registry row of its domain owned by the bridge",
                  answer.get("ok") is True and row.get("platform") == "confine_bridge"
                  and landed[entity].startswith(f"{domain}."),
                  answer.get("reason") or landed[entity])
            shown, shown_attributes = platform.read(landed[entity]) if landed[entity] else (None, {})
            missing = {k: (v, (shown_attributes or {}).get(k)) for k, v in wanted.items()
                       if (shown_attributes or {}).get(k) != v}
            check(f"T17 {domain}: (A) holds its state and the attributes that describe it",
                  shown == state and not missing, f"{shown!r} {missing or ''}")

        print("\nT18 — operating them: the sandbox receives what (A) worked out\n")
        for entity, service, data, expected_service, expected, state, attributes in (
                (AIR, "set_humidity", {"humidity": 45}, "set_humidity", {"humidity": 45}, "on",
                 {**air_attributes, "humidity": 45}),
                (BOILER, "set_away_mode", {"away_mode": True}, "set_away_mode",
                 {"away_mode": True}, "eco", {**boiler_attributes, "away_mode": "on"}),
                (TAP, "open_valve", {}, "set_valve_position", {"position": 100}, "open",
                 {**tap_attributes, "current_position": 100}),
                (SIREN, "turn_on", {"tone": "fire"}, "turn_on", {"tone": "fire"}, "on",
                 siren_attributes),
                (ROBOT, "start", {}, "start", {}, "cleaning", robot_attributes),
                (TV, "send_command", {"command": "power"}, "send_command",
                 {"command": ["power"], "num_repeats": 1, "hold_secs": 0}, "on", tv_attributes)):
            domain = entity.partition(".")[0]
            command, pending = operate(entity, service, data)
            check(f"T18 {domain}.{service} {data or ''}: reaches the sandbox as "
                  f"{expected_service} {expected}",
                  pending["arrived"] and command.get("entity") == entity
                  and command.get("service") == expected_service
                  and command.get("data") == expected, f"{command or pending['user'].outcome}")
            outcome, shown = finish(entity, command, pending, state, attributes)
            check(f"T18 {domain}.{service}: the call succeeds and (A) shows {state}",
                  outcome.get("success") is True and shown == state,
                  f"{outcome.get('error') or ''} {shown!r}")

        switched = house_a._ws_call(admin, {"type": "config/core/update",
                                            "unit_system": "us_customary"})
        try:
            command, pending = operate(BOILER, "set_temperature", {"temperature": 122})
            sent = (command.get("data") or {}).get("temperature")
            check("T18 water_heater.set_temperature 122 °F reaches the sandbox as 50 °C",
                  bool(switched.get("success")) and command.get("service") == "set_temperature"
                  and isinstance(sent, (int, float)) and abs(sent - 50.0) < 0.01
                  and set(command.get("data") or {}) == {"temperature"},
                  f"{command or pending['user'].outcome} {switched.get('error') or ''}")
            finish(BOILER, command, pending, "eco", {**boiler_attributes, "temperature": 50})
        finally:
            restored = house_a._ws_call(admin, {"type": "config/core/update",
                                                "unit_system": "metric"})
        check("T18 and (A) is back in metric units", bool(restored.get("success")),
              str(restored.get("error") or ""))

        print("\nT19 — a humidity above the published maximum never reaches the mediator\n")
        before = len([r for r in log.records() if r.get("op") == "entity.command"])
        user = User()
        pressed = user.press(landed[AIR] or AIR, "set_humidity", {"humidity": 95})
        serve_until(mediator, lambda: not pressed.is_alive(), seconds=15)
        pressed.join()
        user.close()
        after_count = len([r for r in log.records() if r.get("op") == "entity.command"])
        check("T19 humidifier.set_humidity 95 (published 30-80) fails in (A)",
              user.outcome.get("success") is False, str(user.outcome.get("error")))
        check("T19 and no command decision was recorded: it never left (A)",
              after_count == before, f"{after_count - before} new")

        print("\nT22 — update, time, notify, event, trackers (batch B3)\n")
        # `notes/bridge_kinds_b3_prediction_20261031.md`. Update features from Home Assistant
        # 2026.8.3: INSTALL 1 | PROGRESS 4 | BACKUP 8 | RELEASE_NOTES 16 (the bridge drops 16).
        FIRMWARE, WAKE = "update.selftest_firmware", "time.selftest_wake"
        PANEL, BELL = "notify.selftest_panel", "event.selftest_doorbell"
        PHONE, TAG = "device_tracker.selftest_phone", "device_tracker.selftest_tag"
        firmware_attributes = {"friendly_name": "Selftest firmware", "installed_version": "1.0.0",
                               "latest_version": "1.1.0", "in_progress": False,
                               "release_summary": "Fixes", "auto_update": False,
                               "supported_features": 1 | 4 | 8 | 16}
        bell_attributes = {"friendly_name": "Selftest doorbell",
                           "event_types": ["press", "double_press"]}
        home = (house_a._ws_call(admin, {"type": "get_config"}).get("result") or {})
        home_lat, home_lon = home.get("latitude"), home.get("longitude")
        for entity, state, attributes, wanted, shown_state in (
                (FIRMWARE, "on", firmware_attributes,
                 {"installed_version": "1.0.0", "latest_version": "1.1.0",
                  "supported_features": 13}, "on"),
                (WAKE, "06:45:00", {"friendly_name": "Selftest wake"}, {}, "06:45:00"),
                (PANEL, "unknown", {"friendly_name": "Selftest panel"}, {}, "unknown"),
                (BELL, "unknown", bell_attributes, {"event_types": ["press", "double_press"]},
                 "unknown")):
            answer = sandbox.ask({"op": "entity.publish", "entity": entity, "state": state,
                                  "attributes": attributes})
            landed[entity] = platform.published.get(("selftest", entity)) or ""
            row = registry(platform).get(landed[entity], {})
            domain = entity.partition(".")[0]
            check(f"T22 {domain}: a registry row of its domain owned by the bridge",
                  answer.get("ok") is True and row.get("platform") == "confine_bridge"
                  and landed[entity].startswith(f"{domain}."),
                  answer.get("reason") or landed[entity])
            shown, shown_attributes = platform.read(landed[entity]) if landed[entity] else (None, {})
            missing = {k: (v, (shown_attributes or {}).get(k)) for k, v in wanted.items()
                       if (shown_attributes or {}).get(k) != v}
            check(f"T22 {domain}: (A) shows {shown_state} and the attributes that describe it",
                  shown == shown_state and not missing, f"{shown!r} {missing or ''}")

        print("\nT23 — trackers: (A) works out home or away from its own zones\n")
        for entity, state, attributes, expected in (
                (PHONE, "not_home", {"friendly_name": "Selftest phone", "source_type": "gps",
                                     "latitude": home_lat, "longitude": home_lon,
                                     "gps_accuracy": 10}, "home"),
                (PHONE, "home", {"friendly_name": "Selftest phone", "source_type": "gps",
                                 "latitude": (home_lat or 0) + 1, "longitude": home_lon,
                                 "gps_accuracy": 10}, "not_home"),
                (TAG, "home", {"friendly_name": "Selftest tag", "source_type": "bluetooth_le",
                               "mac": "AA:BB:CC:DD:EE:FF"}, "home"),
                (TAG, "not_home", {"friendly_name": "Selftest tag",
                                   "source_type": "bluetooth_le",
                                   "mac": "AA:BB:CC:DD:EE:FF"}, "not_home")):
            answer = sandbox.ask({"op": "entity.publish", "entity": entity, "state": state,
                                  "attributes": attributes})
            landed[entity] = platform.published.get(("selftest", entity)) or ""
            shown, shown_attributes = platform.read(landed[entity]) if landed[entity] else (None, {})
            check(f"T23 {attributes['source_type']} tracker published {state!r} at "
                  f"{attributes.get('latitude', '-')}: (A) shows {expected}",
                  answer.get("ok") is True and home_lat is not None and shown == expected,
                  f"{answer.get('reason') or ''} {shown!r}")
        row = registry(platform).get(landed[TAG], {})
        shown_attributes = platform.read(landed[TAG])[1] if landed[TAG] else {}
        check("T23 the scanner's MAC is an attribute, and its unique id is the bridge's",
              (shown_attributes or {}).get("mac") == "AA:BB:CC:DD:EE:FF"
              and row.get("unique_id") == f"selftest:{TAG}", f"{row.get('unique_id')}")

        print("\nT24 — events fire once in (A)\n")

        def bell(state: str, event_type: str) -> tuple[str | None, dict]:
            sandbox.ask({"op": "entity.publish", "entity": BELL, "state": state,
                         "attributes": {**bell_attributes, "event_type": event_type,
                                        "button": "1"}})
            shown, shown_attributes = platform.read(landed[BELL]) if landed[BELL] else (None, {})
            return shown, shown_attributes or {}

        first, first_attributes = bell("2026-10-31T13:00:00.000+00:00", "press")
        check("T24 a press event fires in (A): a new time, its type and its attribute",
              _iso_time(first) and first_attributes.get("event_type") == "press"
              and first_attributes.get("button") == "1", f"{first!r} {first_attributes}")
        again, _ = bell("2026-10-31T13:00:00.000+00:00", "press")
        check("T24 republishing the same event does not fire it again", again == first,
              f"{first!r} -> {again!r}")
        second, second_attributes = bell("2026-10-31T13:00:05.000+00:00", "double_press")
        check("T24 a later double_press fires again",
              _iso_time(second) and second != first
              and second_attributes.get("event_type") == "double_press",
              f"{second!r} {second_attributes.get('event_type')}")
        unlisted, _ = bell("2026-10-31T13:00:09.000+00:00", "triple_press")
        still = sandbox.ask({"op": "entity.publish", "entity": WAKE, "state": "06:50:00",
                             "attributes": {"friendly_name": "Selftest wake"}})
        check("T24 an event type the entity does not list leaves (A)'s state, and the bridge works",
              unlisted == second and still.get("ok") is True
              and platform.read(landed[WAKE])[0] == "06:50:00", f"{unlisted!r}")

        print("\nT25 — update skip stays in (A); install, a time and a message reach the sandbox\n")
        for service, state in (("skip", "off"), ("clear_skipped", "on")):
            before = len([r for r in log.records() if r.get("op") == "entity.command"])
            user = User()
            pressed = user.press(landed[FIRMWARE] or FIRMWARE, service, {})
            serve_until(mediator, lambda: not pressed.is_alive(), seconds=15)
            pressed.join()
            user.close()
            after_count = len([r for r in log.records() if r.get("op") == "entity.command"])
            shown = platform.read(landed[FIRMWARE])[0] if landed[FIRMWARE] else None
            check(f"T25 update.{service}: succeeds, (A) shows {state}, no command decision",
                  user.outcome.get("success") is True and shown == state
                  and after_count == before,
                  f"{user.outcome.get('error') or ''} {shown!r} {after_count - before} new")
        for entity, service, data, expected, state, attributes in (
                (FIRMWARE, "install", {}, {"backup": False}, "off",
                 {**firmware_attributes, "installed_version": "1.1.0"}),
                (WAKE, "set_value", {"time": "07:30"}, {"time": "07:30:00"}, "07:30:00",
                 {"friendly_name": "Selftest wake"}),
                (PANEL, "send_message", {"message": "Door left open", "title": "Home"},
                 {"message": "Door left open", "title": "Home"}, None,
                 {"friendly_name": "Selftest panel"})):
            domain = entity.partition(".")[0]
            command, pending = operate(entity, service, data)
            check(f"T25 {domain}.{service} {data or ''}: reaches the sandbox as {expected}",
                  pending["arrived"] and command.get("entity") == entity
                  and command.get("service") == service and command.get("data") == expected,
                  f"{command or pending['user'].outcome}")
            outcome, shown = finish(entity, command, pending, state or "unknown", attributes)
            # A notify entity's state is the time (A) last sent a message, kept by (A).
            check(f"T25 {domain}.{service}: the call succeeds and (A) shows "
                  f"{state or 'the time it was sent'}",
                  outcome.get("success") is True
                  and (shown == state if state else _iso_time(shown)),
                  f"{outcome.get('error') or ''} {shown!r}")

        print("\nT26 — the notification's text is not in the durable log\n")
        check("T26 'Door left open' appears nowhere in the run's durable log",
              "Door left open" not in (root / "audit" / "decisions.jsonl").read_text())

        print("\nT5 — a kind the bridge does not stand in for is refused\n")
        todo = sandbox.ask({"op": "entity.publish", "entity": "todo.selftest_probe",
                            "state": "3"})
        check("T5 a to-do list is refused at publish", todo.get("ok") is False,
              todo.get("reason", ""))
        check("every chain verifies", log.verify() == [])
        platform.close()

    if args.restart:
        print("\nX3 — (A) restarts, and the switch keeps its published state\n")
        time.sleep(6)  # past the bridge's delayed save of its roster (5 s)
        house_a.stop(house_a.DEFAULT_CONFIG)
        house_a.start(house_a.DEFAULT_CONFIG)
        time.sleep(5)
        # (A) answers before it has finished starting, and RealPlatform waits for it (F35 R7).
        for _ in range(60):
            try:
                after = RealPlatform()
                break
            except PlatformStarting:
                time.sleep(2)
        else:
            after = RealPlatform()
        shown = after.read(landed["switch.selftest_schedule"])[0]
        check("X3 after a restart (A) shows the switch triggered", shown == "triggered",
              f"{shown!r}")
        after.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
