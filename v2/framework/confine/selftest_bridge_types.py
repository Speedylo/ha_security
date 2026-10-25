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

Requires (A) running: `python3 -m confine.house_a up --fresh` on the Pi.

Run:  python3 -m confine.selftest_bridge_types
"""

from __future__ import annotations

import sys
import tempfile
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
            check(f"T2 {domain}: (A) holds the state and the attributes that describe it",
                  shown == state and not missing, f"{shown!r} {missing or ''}")

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
