"""The commands the mediator forwards from the household to a confined integration, per type.

Bridge step 2 (`notes/bridge_types_step2_prediction_20261025.md`). A user operating a confined
integration's entity in (A) becomes a command the mediator decides: the entity must be the
integration's own, the service one listed for the entity's type, and the data **exactly** the
listed keys with values of the listed kind. Anything else is refused, recorded, and never pushed.
This suite needs no (A): it drives `Mediator.command` with a stand-in that owns one entity of each
type, as `selftest_audit`'s F3 check does.

    K1   each listed command, with exactly its data, is pushed to the owning sandbox as it was
    K2   a service not listed for the entity's type is refused under COMMAND_SERVICES
    K3   data that is not exactly the listed keys, of the listed kind, is refused under COMMAND_DATA
    K4   a refused value is recorded by its type and length, never itself
    K6   climate and alarm-panel commands, each allowed shape, pushed exactly (bridge step 3)
    K7   data matching none of the allowed shapes is refused under COMMAND_DATA
    K8   a service of the other type is refused under COMMAND_SERVICES
    K9   an alarm code is never written to the durable log, allowed or refused
    K12  light, fan, cover and lock commands, each allowed shape, pushed exactly (batch B1)
    K13  B1 data matching no allowed shape is refused under COMMAND_DATA
    K14  B1 services worked out in (A), or of another kind, are refused under COMMAND_SERVICES
    K15  a lock code is never written to the durable log, allowed or refused

Run:  python3 -m confine.selftest_commands
"""

from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path

from .audit import AuditLog
from .channel import Channel, ProtocolError
from .mediator import AMBIENT, COMMAND_SERVICES, Mediator, deny_everything
from .selftest_push import component

try:
    from .mediator import COMMAND_DATA
except ImportError:  # before step 2 there is no such rule; every K3 case then fails, as predicted
    COMMAND_DATA = "(no COMMAND_DATA rule)"

results: list[bool] = []
OWNED = {"switch.demo_power": "demo", "button.demo_report": "demo", "text.demo_note": "demo",
         "select.demo_mode": "demo", "number.demo_target": "demo",
         "climate.demo_ac": "demo", "alarm_control_panel.demo_alarm": "demo",
         "light.demo_lamp": "demo", "fan.demo_fan": "demo", "cover.demo_blind": "demo",
         "lock.demo_door": "demo"}


def check(claim: str, condition: bool, detail: str = "") -> None:
    results.append(bool(condition))
    print(f"{'  ok  ' if condition else '  FAIL'}  {claim}{f'  — {detail}' if detail else ''}")


class House:
    """Enough of a platform for `Mediator.command`: who owns what, and what it was told."""

    def __init__(self) -> None:
        self.owners = dict(OWNED)
        self.results: list[tuple] = []

    def command_result(self, command: int, ok: bool, error: str | None = None) -> None:
        self.results.append((command, ok, error))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mediator = Mediator(policy=deny_everything, log=AuditLog(path=root / "commands.jsonl"))
        mediator._platform = House()  # type: ignore[assignment]
        mine, theirs = Channel.pair()
        mediator.register("demo", Channel(mine), component=component(root, "demo", []))
        sandbox = Channel(theirs)
        sandbox.sock.settimeout(0.5)
        ids = iter(range(1, 1000))

        def send(entity: str, service: str, data: dict | None = None) -> tuple[dict, dict | None]:
            """One user's command; the decision recorded for it, and what the sandbox received."""
            before = len(mediator.log.records())
            command = {"command": next(ids), "integration": "demo", "entity_id": entity,
                       "service": service}
            if data is not None:
                command["data"] = data
            mediator.command(command)
            records = [r for r in mediator.log.records()[before:]
                       if r.get("kind") == "decision" and r.get("op") == "entity.command"]
            try:
                pushed = sandbox.recv()
            except (TimeoutError, OSError, ProtocolError):
                pushed = None
            return (records[0] if records else {}), pushed

        print("\nK1 — each listed command is forwarded with exactly its data\n")
        for entity, service, data in (
                ("switch.demo_power", "turn_on", None),
                ("switch.demo_power", "turn_off", {}),
                ("button.demo_report", "press", None),
                ("text.demo_note", "set_value", {"value": "*.tmp; rm -rf /"}),
                ("select.demo_mode", "select_option", {"option": "away"}),
                ("number.demo_target", "set_value", {"value": 22}),
                ("number.demo_target", "set_value", {"value": 19.5})):
            record, pushed = send(entity, service, data)
            check(f"K1 {entity.partition('.')[0]}.{service} {data or ''}: allowed and pushed as sent",
                  record.get("allowed") is True and record.get("clause") == AMBIENT
                  and pushed is not None and pushed.get("entity") == entity
                  and pushed.get("service") == service and pushed.get("data") == (data or {}),
                  f"{record.get('clause')} {pushed}")

        print("\nK2 — a service not listed for the entity's type\n")
        for entity, service in (("number.demo_target", "turn_on"), ("switch.demo_power", "press"),
                                ("switch.demo_power", "unlock"), ("select.demo_mode", "set_value")):
            record, pushed = send(entity, service, None)
            check(f"K2 {entity.partition('.')[0]}.{service}: refused under COMMAND_SERVICES, "
                  "not pushed",
                  record.get("allowed") is False and record.get("clause") == COMMAND_SERVICES
                  and pushed is None, f"{record.get('clause')} {pushed}")

        print("\nK3 — data that is not exactly the listed keys, of the listed kind\n")
        for label, entity, service, data in (
                ("switch turn_on with any data", "switch.demo_power", "turn_on", {"brightness": 1}),
                ("text set_value redirected with entity_id", "text.demo_note", "set_value",
                 {"value": "x", "entity_id": "text.someone_else"}),
                ("text set_value with no value", "text.demo_note", "set_value", {}),
                ("text set_value with a dict", "text.demo_note", "set_value",
                 {"value": {"__class__": "x"}}),
                ("text set_value with 256 characters", "text.demo_note", "set_value",
                 {"value": "x" * 256}),
                ("number set_value with a string", "number.demo_target", "set_value",
                 {"value": "22"}),
                ("number set_value with a boolean", "number.demo_target", "set_value",
                 {"value": True}),
                ("number set_value with NaN", "number.demo_target", "set_value",
                 {"value": math.nan}),
                ("number set_value with infinity", "number.demo_target", "set_value",
                 {"value": math.inf}),
                ("select select_option with a list", "select.demo_mode", "select_option",
                 {"option": ["away"]})):
            record, pushed = send(entity, service, data)
            check(f"K3 {label}: refused under COMMAND_DATA, not pushed",
                  record.get("allowed") is False and record.get("clause") == COMMAND_DATA
                  and pushed is None, f"{record.get('clause')} {pushed}")

        print("\nK4 — a refused value is recorded by its kind, never itself\n")
        hostile = "A" * 10_000
        record, pushed = send("text.demo_note", "set_value", {"value": hostile})
        log_text = (root / "commands.jsonl").read_text()
        check("K4 a 10,000-character value is refused under COMMAND_DATA",
              record.get("allowed") is False and record.get("clause") == COMMAND_DATA
              and pushed is None, str(record.get("clause")))
        check("K4 and the durable record holds its type and length, not the value",
              hostile not in log_text and "10000" in str(record.get("requested")),
              str(record.get("requested"))[:120])

        print("\nK6 — climate and alarm panel: each allowed shape (bridge step 3)\n")
        AC, ALARM = "climate.demo_ac", "alarm_control_panel.demo_alarm"
        for entity, service, data in (
                (AC, "turn_on", None), (AC, "turn_off", None),
                (AC, "set_hvac_mode", {"hvac_mode": "cool"}),
                (AC, "set_temperature", {"temperature": 23.0}),
                (AC, "set_temperature", {"temperature": 21, "hvac_mode": "heat"}),
                (AC, "set_temperature", {"target_temp_low": 19.0, "target_temp_high": 24.0}),
                (AC, "set_fan_mode", {"fan_mode": "auto"}),
                (AC, "set_preset_mode", {"preset_mode": "eco"}),
                (AC, "set_swing_mode", {"swing_mode": "vertical"}),
                (AC, "set_humidity", {"humidity": 45}),
                (ALARM, "alarm_disarm", {"code": "1234"}),
                (ALARM, "alarm_arm_away", None), (ALARM, "alarm_arm_home", None),
                (ALARM, "alarm_arm_night", None), (ALARM, "alarm_arm_vacation", None),
                (ALARM, "alarm_arm_custom_bypass", None), (ALARM, "alarm_trigger", None)):
            record, pushed = send(entity, service, data)
            check(f"K6 {entity.partition('.')[0]}.{service} {data or ''}: allowed and pushed as sent",
                  record.get("allowed") is True and record.get("clause") == AMBIENT
                  and pushed is not None and pushed.get("service") == service
                  and pushed.get("data") == (data or {}), f"{record.get('clause')} {pushed}")

        print("\nK7 — data matching none of the allowed shapes\n")
        for label, entity, service, data in (
                ("hvac_mode plasma", AC, "set_hvac_mode", {"hvac_mode": "plasma"}),
                ("temperature and a range together", AC, "set_temperature",
                 {"temperature": 22, "target_temp_low": 19, "target_temp_high": 24}),
                ("a low without a high", AC, "set_temperature", {"target_temp_low": 19}),
                ("a string temperature", AC, "set_temperature", {"temperature": "22"}),
                ("a NaN temperature", AC, "set_temperature", {"temperature": math.nan}),
                ("an extra key on set_fan_mode", AC, "set_fan_mode",
                 {"fan_mode": "auto", "speed": 3}),
                ("a numeric code", ALARM, "alarm_disarm", {"code": 1234}),
                ("a 65-character code", ALARM, "alarm_disarm", {"code": "9" * 65}),
                ("disarm redirected with entity_id", ALARM, "alarm_disarm",
                 {"code": "1234", "entity_id": "alarm_control_panel.other"})):
            record, pushed = send(entity, service, data)
            check(f"K7 {label}: refused under COMMAND_DATA, not pushed",
                  record.get("allowed") is False and record.get("clause") == COMMAND_DATA
                  and pushed is None, f"{record.get('clause')} {pushed}")

        print("\nK8 — a service of the other type\n")
        for entity, service in ((AC, "alarm_disarm"), (ALARM, "set_temperature"),
                                (ALARM, "turn_on")):
            record, pushed = send(entity, service, None)
            check(f"K8 {entity.partition('.')[0]}.{service}: refused under COMMAND_SERVICES",
                  record.get("allowed") is False and record.get("clause") == COMMAND_SERVICES
                  and pushed is None, f"{record.get('clause')} {pushed}")

        record, _ = send(ALARM, "alarm_arm_away_now", {"note": "secret-note"})
        check("K8 a command refused for its service has its data recorded by kind",
              record.get("allowed") is False
              and "secret-note" not in (root / "commands.jsonl").read_text(),
              str((record.get("requested") or {}).get("data")))

        print("\nK9 — an alarm code never reaches the durable log\n")
        allowed_record, allowed_pushed = send(ALARM, "alarm_disarm", {"code": "4917"})
        long_code = "7" * 65
        refused_record, _ = send(ALARM, "alarm_disarm", {"code": long_code})
        log_text = (root / "commands.jsonl").read_text()
        check("K9 the allowed disarm reached the sandbox with its code",
              allowed_record.get("allowed") is True
              and (allowed_pushed or {}).get("data") == {"code": "4917"}, str(allowed_pushed))
        # Searched for as JSON values, in quotes: a bare "4917" also turns up by chance inside the
        # log's hex hashes and microsecond timestamps (about one run in four on the Pi, 2026-10-25),
        # and a quote cannot appear in either.
        check("K9 neither code is in the log file",
              '"4917"' not in log_text and f'"{long_code}"' not in log_text
              and '"1234"' not in log_text)
        check("K9 and both records say the code was withheld",
              (allowed_record.get("requested") or {}).get("data") == {"code": "(withheld)"}
              and (refused_record.get("requested") or {}).get("data") == {"code": "(withheld)"},
              f"{(allowed_record.get('requested') or {}).get('data')} "
              f"{(refused_record.get('requested') or {}).get('data')}")

        # Batch B1 (`notes/bridge_kinds_b1_prediction_20261031.md`): what reaches each entity's
        # method in (A), as Home Assistant 2026.8.3 processes the call. Colours arrive as lists.
        LAMP, FAN, BLIND, DOOR = "light.demo_lamp", "fan.demo_fan", "cover.demo_blind", "lock.demo_door"
        print("\nK12 — light, fan, cover and lock: each allowed shape (batch B1)\n")
        for entity, service, data in (
                (LAMP, "turn_on", None),
                (LAMP, "turn_on", {"brightness": 128}),
                (LAMP, "turn_on", {"brightness": 200, "rgb_color": [255, 0, 0], "transition": 2}),
                (LAMP, "turn_on", {"color_temp_kelvin": 2700}),
                (LAMP, "turn_on", {"hs_color": [30.0, 80.0]}),
                (LAMP, "turn_on", {"rgb_color": [255, 128, 0]}),
                (LAMP, "turn_on", {"rgbw_color": [255, 128, 0, 10]}),
                (LAMP, "turn_on", {"rgbww_color": [255, 128, 0, 10, 20]}),
                (LAMP, "turn_on", {"xy_color": [0.3, 0.4]}),
                (LAMP, "turn_on", {"white": 150}),
                (LAMP, "turn_on", {"white": None}),
                (LAMP, "turn_on", {"effect": "colorloop"}),
                (LAMP, "turn_on", {"flash": "short"}),
                (LAMP, "turn_off", None),
                (LAMP, "turn_off", {"transition": 1.5}),
                (LAMP, "turn_off", {"flash": "long"}),
                (FAN, "turn_on", None),
                (FAN, "turn_on", {"percentage": 50}),
                (FAN, "turn_on", {"preset_mode": "sleep"}),
                (FAN, "turn_on", {"percentage": 50, "preset_mode": "sleep"}),
                (FAN, "turn_off", None),
                (FAN, "set_percentage", {"percentage": 75}),
                (FAN, "set_preset_mode", {"preset_mode": "auto"}),
                (FAN, "oscillate", {"oscillating": True}),
                (FAN, "set_direction", {"direction": "reverse"}),
                (BLIND, "open_cover", None), (BLIND, "close_cover", None),
                (BLIND, "stop_cover", None), (BLIND, "open_cover_tilt", None),
                (BLIND, "close_cover_tilt", None), (BLIND, "stop_cover_tilt", None),
                (BLIND, "set_cover_position", {"position": 40}),
                (BLIND, "set_cover_tilt_position", {"tilt_position": 60}),
                (DOOR, "lock", None), (DOOR, "lock", {"code": "1234"}),
                (DOOR, "unlock", None), (DOOR, "unlock", {"code": "1234"}),
                (DOOR, "open", None), (DOOR, "open", {"code": "1234"})):
            record, pushed = send(entity, service, data)
            check(f"K12 {entity.partition('.')[0]}.{service} {data or ''}: allowed and pushed as sent",
                  record.get("allowed") is True and record.get("clause") == AMBIENT
                  and pushed is not None and pushed.get("entity") == entity
                  and pushed.get("service") == service and pushed.get("data") == (data or {}),
                  f"{record.get('clause')} {pushed}")

        print("\nK13 — B1 data matching no allowed shape\n")
        for label, entity, service, data in (
                ("light profile (resolved in (A), never reaches the entity)", LAMP, "turn_on",
                 {"profile": "relax"}),
                ("light color_name (resolved in (A))", LAMP, "turn_on", {"color_name": "red"}),
                ("light brightness_pct (resolved in (A))", LAMP, "turn_on", {"brightness_pct": 50}),
                ("light brightness_step (resolved in (A))", LAMP, "turn_on", {"brightness_step": 10}),
                ("light rgb_color of 2 numbers", LAMP, "turn_on", {"rgb_color": [255, 0]}),
                ("light rgb_color of 4 numbers", LAMP, "turn_on", {"rgb_color": [255, 0, 0, 0]}),
                ("light a string in a colour", LAMP, "turn_on", {"hs_color": ["30", 80]}),
                ("light flash medium", LAMP, "turn_on", {"flash": "medium"}),
                ("light NaN brightness", LAMP, "turn_on", {"brightness": math.nan}),
                ("light a 256-character effect", LAMP, "turn_on", {"effect": "e" * 256}),
                ("light turn_off with a brightness", LAMP, "turn_off", {"brightness": 10}),
                ("light turn_on redirected with entity_id", LAMP, "turn_on",
                 {"brightness": 10, "entity_id": "light.someone_else"}),
                ("fan set_percentage with no percentage", FAN, "set_percentage", {}),
                ("fan oscillate 'yes'", FAN, "oscillate", {"oscillating": "yes"}),
                ("fan set_direction with no direction", FAN, "set_direction", {}),
                ("cover set_cover_position with a string", BLIND, "set_cover_position",
                 {"position": "40"}),
                ("cover open_cover with a position", BLIND, "open_cover", {"position": 40}),
                ("lock a numeric code", DOOR, "unlock", {"code": 1234}),
                ("lock a 65-character code", DOOR, "unlock", {"code": "8" * 65})):
            record, pushed = send(entity, service, data)
            check(f"K13 {label}: refused under COMMAND_DATA, not pushed",
                  record.get("allowed") is False and record.get("clause") == COMMAND_DATA
                  and pushed is None, f"{record.get('clause')} {pushed}")

        print("\nK14 — services worked out in (A), or of another kind\n")
        for entity, service in ((LAMP, "toggle"), (FAN, "toggle"), (FAN, "increase_speed"),
                                (FAN, "decrease_speed"), (BLIND, "toggle"),
                                (BLIND, "toggle_tilt"), (DOOR, "turn_on"),
                                (LAMP, "set_percentage")):
            record, pushed = send(entity, service, None)
            check(f"K14 {entity.partition('.')[0]}.{service}: refused under COMMAND_SERVICES",
                  record.get("allowed") is False and record.get("clause") == COMMAND_SERVICES
                  and pushed is None, f"{record.get('clause')} {pushed}")

        print("\nK15 — a lock code never reaches the durable log\n")
        allowed_record, allowed_pushed = send(DOOR, "unlock", {"code": "5820"})
        long_lock_code = "6" * 65
        refused_record, _ = send(DOOR, "unlock", {"code": long_lock_code})
        log_text = (root / "commands.jsonl").read_text()
        check("K15 the allowed unlock reached the sandbox with its code",
              allowed_record.get("allowed") is True
              and (allowed_pushed or {}).get("data") == {"code": "5820"}, str(allowed_pushed))
        check("K15 neither code is in the log file",
              '"5820"' not in log_text and f'"{long_lock_code}"' not in log_text)
        check("K15 and both records say the code was withheld",
              (allowed_record.get("requested") or {}).get("data") == {"code": "(withheld)"}
              and (refused_record.get("requested") or {}).get("data") == {"code": "(withheld)"},
              f"{(allowed_record.get('requested') or {}).get('data')} "
              f"{(refused_record.get('requested') or {}).get('data')}")
        check("every chain verifies", mediator.log.verify() == [])

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
