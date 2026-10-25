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
        check("T9 '4917' appears nowhere in the run's durable log",
              "4917" not in (root / "audit" / "decisions.jsonl").read_text())

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
