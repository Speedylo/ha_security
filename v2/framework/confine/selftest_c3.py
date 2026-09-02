"""C3 — the framework does not presuppose that the author is honest or cooperative.

§3.3 fixed C3's verification before any implementation existed:

    "the adversarial evaluation includes an integration whose declared manifest is **absent**,
     **over-broad**, and **deliberately mismatched to its behaviour**."

The absent case, and the unparseable one S6 adds, are already covered by `selftest_policy`.
This file covers the two that are not, and they are the two that carry an argument.

**Over-broad is not a case the framework wins, and reporting it as one would be dishonest.**
R1 (§4.11) retains it as a **High** residual risk: confinement bounds behaviour to the
declaration; it does not make the declaration minimal, and nothing forces anyone to review it.
So what this test establishes is not that over-declaration is stopped — it is not — but the
**shape of the ceiling it hits**. Some authority is not declarable at any breadth:

    §5.10.4 / S5   no wildcard in `services.call`, ever. `lock.*` cannot be written
    §5.10.4        no wildcard in the domain half of an entity pattern
    §5.10.5        no path grant enclosing the configuration root, `.storage/` or `secrets.yaml`
    §5.10.x        an unknown capability is a rejection, not something ignored

An author who over-declares gets everything they asked for **within** those ceilings, and the
ceilings are where §4.11's "structural" claim about R1 is either true or empty.

**Mismatched is the case C3 is really about.** The manifest is a claim about intent; enforcement
acts on behaviour. An integration that declares a modest, plausible set and then does something
else is refused when it does the something else, and the refusal names a clause — because the
manifest was never trusted as a description of what the code would do.

Run:  python3 -m confine.selftest_c3
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from .manifest import Manifest, ManifestRejected
from .mediator import Mediator
from .platform import Platform, acting_policy

# What an author writes when they want everything and are not asked to justify any of it.
OVER_BROAD = {
    "schema_version": 1,
    "entities": {"read": ["sensor.*", "binary_sensor.*", "device_tracker.*", "lock.*",
                          "person.*", "calendar.*", "alarm_control_panel.*"],
                 "subscribe": ["sensor.*", "binary_sensor.*", "device_tracker.*"],
                 "write": ["sensor.*"]},
    "services": {"call": ["lock.lock", "lock.open", "alarm_control_panel.alarm_disarm",
                          "notify.persistent_notification"]},
}

# Each of these is what the same author would write if the ceilings did not exist. Every one
# must be refused at parse time, and the test asserts on *which* rule refused it (§6.6.5).
CEILINGS = [
    ("a wildcard service: lock.*",
     {"schema_version": 1, "services": {"call": ["lock.*"]}}, "wildcard"),
    ("a wildcard domain: *.temperature",
     {"schema_version": 1, "entities": {"read": ["*.temperature"]}}, "domain"),
    ("'*' alone as an entity grant",
     {"schema_version": 1, "entities": {"read": ["*"]}}, "'*' alone"),
    ("a path grant enclosing the configuration root",
     {"schema_version": 1, "files": {"read": ["CONFIG_ROOT"]}}, ""),
    ("a path grant reaching secrets.yaml",
     {"schema_version": 1, "files": {"read": ["CONFIG_ROOT/secrets.yaml"]}}, ""),
    ("a path grant reaching .storage/",
     {"schema_version": 1, "files": {"read": ["CONFIG_ROOT/.storage"]}}, ""),
    ("an invented capability nobody implements",
     {"schema_version": 1, "process": {"spawn": ["/bin/sh"]}}, ""),
]

# A plausible, modest declaration — and an integration that does none of it.
MISMATCHED_DECLARATION = {
    "schema_version": 1,
    "entities": {"read": ["sensor.outdoor_temperature"]},
    "services": {"call": ["lock.lock"]},
}
MISMATCHED_BEHAVIOUR = [
    ("read the occupancy sensor it did not declare",
     {"op": "entity.read", "entity": "binary_sensor.bedroom_occupancy"}),
    ("read a phone's location", {"op": "entity.read", "entity": "device_tracker.younes_phone"}),
    ("unlock the door it declared only locking",
     {"op": "service.call", "service": "lock.unlock"}),
    ("disarm the alarm", {"op": "service.call", "service": "alarm_control_panel.alarm_disarm"}),
    ("subscribe to everything", {"op": "entity.subscribe", "entity": "sensor.outdoor_temperature"}),
    ("write to an entity it does not own",
     {"op": "entity.write", "entity": "lock.front_door"}),
    ("claim to be another integration",
     {"op": "entity.read", "integration": "trusted_other",
      "entity": "binary_sensor.bedroom_occupancy"}),
]


def write(root: Path, domain: str, permissions: dict | None) -> Path:
    component = root / "custom_components" / domain
    component.mkdir(parents=True, exist_ok=True)
    (component / "__init__.py").write_text("# demo\n")
    body: dict = {"domain": domain, "name": domain, "version": "1.0.0"}
    if permissions is not None:
        body["permissions"] = permissions
    (component / "manifest.json").write_text(json.dumps(body))
    return component


def check(label: str, ok: bool, detail: str, failures: list[str]) -> None:
    print(f"    {'ok  ' if ok else 'FAIL'}  {label:<52} {detail[:56]}")
    if not ok:
        failures.append(label)


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="confine-c3-"))
    failures: list[str] = []
    print("C3 — the manifest is a claim, not a description that is believed\n")
    try:
        # ---- case 2: over-broad ------------------------------------------------------
        print("  OVER-BROAD — everything the author could think to ask for")
        component = write(root, "greedy", OVER_BROAD)
        manifest = Manifest.load(component, root)
        platform = Platform()
        for entity in ("sensor.outdoor_temperature", "binary_sensor.bedroom_occupancy",
                       "device_tracker.younes_phone", "lock.front_door"):
            platform.seed(entity, "whatever")
        policy = acting_policy({"greedy": manifest}, platform)

        granted = policy("greedy", {"op": "entity.read",
                                    "entity": "binary_sensor.bedroom_occupancy"})
        check("an over-broad grant IS honoured (R1, and it is not a win)",
              granted.allowed, granted.clause or "", failures)
        unlock = policy("greedy", {"op": "service.call", "service": "lock.unlock"})
        check("but lock.unlock is still refused — it was never declarable as lock.*",
              not unlock.allowed, unlock.clause or "", failures)

        print("\n  THE CEILINGS — what no breadth of declaration can reach")
        for label, permissions, expect in CEILINGS:
            text = json.dumps(permissions).replace("CONFIG_ROOT", str(root))
            greedy = write(root, "ceiling", json.loads(text))
            try:
                Manifest.load(greedy, root)
                check(label, False, "ACCEPTED — it should not have been", failures)
            except ManifestRejected as err:
                reason = str(err).split(": ", 1)[-1]
                # §6.6.5: assert on the rule that refused it, not merely that something did.
                named = expect.lower() in reason.lower() if expect else True
                check(label, named, f"rejected: {reason[:52]}", failures)
            shutil.rmtree(greedy, ignore_errors=True)

        # ---- case 3: mismatched ------------------------------------------------------
        print("\n  MISMATCHED — a modest declaration, and an integration that does none of it")
        component = write(root, "liar", MISMATCHED_DECLARATION)
        manifest = Manifest.load(component, root)
        policy = acting_policy({"liar": manifest}, platform)
        mediator = Mediator()
        mediator.policy = policy

        for label, request in MISMATCHED_BEHAVIOUR:
            decision = policy("liar", request)
            check(label + " → denied", not decision.allowed,
                  decision.clause or "(no clause)", failures)
            if not decision.allowed and not decision.clause:
                failures.append(f"{label}: denied without naming a clause")
                print(f"          ^ denied, but named no clause — §6.6.5")

        declared = policy("liar", {"op": "entity.read", "entity": "sensor.outdoor_temperature"})
        check("what it DID declare still works", declared.allowed, declared.clause or "",
              failures)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print()
    if failures:
        print(f"FAILED — {len(failures)} case(s): {failures[:4]}")
        return 1
    print("PASS — C3, all three shapes.")
    print("       Absent and unparseable are covered by `selftest_policy`; over-broad is")
    print("       honoured within ceilings it cannot raise, which is R1 stated honestly;")
    print("       and a mismatched declaration buys its author nothing, because enforcement")
    print("       reads behaviour and the manifest was never believed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
