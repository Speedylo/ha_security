"""The bridge's entity types beyond sensor, binary sensor and switch, against the house's (A).

Step 1 of extending the bridge (`notes/bridge_types_step1_prediction_20261025.md`): button, text,
select and number. Each published entity must become a registry-backed entity **of its own type**
in (A), described well enough for Home Assistant to draw its control. Operating them is step 2, so
a command on one is still refused by the mediator, and that refusal must reach the user.

    T1   each of the four publishes to an entity-registry row of its domain, owned by the bridge
    T2   (A) holds the state and the attributes that describe the control
    T3   a republish from the sandbox changes the state in (A)
    T4   a command on one is refused by the mediator, recorded, and fails the user's call
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
from .mediator import COMMAND_SERVICES, Mediator
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

        print("\nT4 — operating one is step 2: refused, recorded, and the user is told\n")
        user = User()
        pressed = user.press(landed["number.selftest_target"] or "number.selftest_target",
                             "set_value", {"value": 22})
        serve_until(mediator, lambda: not pressed.is_alive(), seconds=15)
        pressed.join()
        user.close()
        refused = [r for r in log.records() if r["kind"] == "decision"
                   and r["op"] == "entity.command" and not r["allowed"]]
        check("T4 the user's call fails, at once, with the mediator's reason",
              user.outcome.get("success") is False and user.outcome.get("seconds", 99) < 2
              and "set_value" in str(user.outcome.get("error")),
              f"{user.outcome.get('seconds', 0):.1f} s: {user.outcome.get('error')}")
        check("T4 and it is a recorded refusal under the command rule",
              len(refused) == 1 and refused[0].get("clause") == COMMAND_SERVICES,
              f"{[(r.get('target'), r.get('clause')) for r in refused]}")
        check("T4 and the value in (A) is unchanged",
              platform.read(landed["number.selftest_target"])[0] == UPDATES["number.selftest_target"]
              if landed["number.selftest_target"] else False)

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
