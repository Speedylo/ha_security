"""The manifest, checked against the rules Chapter 5 said it would enforce.

Four things are tested, and each is a claim with a section number rather than a behaviour that
seemed worth checking:

    §5.10.4 / S5  a manifest permitting `lock.lock` does not permit `lock.unlock`
    §5.10.5       a declared path reaching the configuration root or `.storage/` is rejected
                  when the manifest is parsed, not when it is first used
    §5.9.4 / S6   no manifest means no mediated capability, and an unparseable one is not a
                  manifest
    §5.10.8 / F3  every decision, permit or deny, names the clause that decided it

Run:  python3 -m confine.selftest_policy
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from .manifest import Manifest, ManifestRejected, Provenance, policy_for

# §5.10.7's worked example, verbatim: a weather integration polling one API and reading one
# sensor for local calibration.
WORKED_EXAMPLE = {
    "schema_version": 1,
    "network": {"egress": ["api.example-weather.invalid:443"]},
    "entities": {"read": ["sensor.outdoor_temperature"]},
    "resources": {"memory_mb": 192, "max_processes": 8},
}


def write_component(root: Path, domain: str, permissions: dict | None) -> Path:
    component = root / "custom_components" / domain
    component.mkdir(parents=True, exist_ok=True)
    manifest = {"domain": domain, "name": domain, "version": "1.0.0"}
    if permissions is not None:
        manifest["permissions"] = permissions
    (component / "manifest.json").write_text(json.dumps(manifest))
    return component


def check(label: str, condition: bool, detail: str, failures: list[str]) -> None:
    print(f"  {'ok  ' if condition else 'FAIL'}  {label:<52}  {detail}")
    if not condition:
        failures.append(label)


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="confine-policy-"))
    failures: list[str] = []
    try:
        print("manifest self-test — the rules §5.10 said it would enforce\n")

        # ---- the worked example decides as §5.10.7 says it does ----------------------
        print("§5.10.7  the worked example, and the nine capabilities it never mentions")
        component = write_component(root, "example_weather", WORKED_EXAMPLE)
        manifest = Manifest.load(component, root)
        check("provenance is author-declared", manifest.provenance is Provenance.AUTHOR,
              str(manifest.provenance.value), failures)

        cases = [
            # host **and** port since §7.24.3 — a clause naming only a host granted every one
            # of the 65,535 ports on that machine, which no manifest intends.
            ("network.egress to the declared host and port", True,
             {"op": "network.egress", "host": "api.example-weather.invalid", "port": 443}),
            ("network.egress to the declared host on another port", False,
             {"op": "network.egress", "host": "api.example-weather.invalid", "port": 8080}),
            ("network.egress to any other host", False,
             {"op": "network.egress", "host": "evil.invalid", "port": 443}),
            ("entity.read of the declared sensor", True,
             {"op": "entity.read", "entity": "sensor.outdoor_temperature"}),
            ("entity.read of an undeclared sensor", False,
             {"op": "entity.read", "entity": "sensor.bedroom_occupancy"}),
            ("entity.write, never declared", False,
             {"op": "entity.write", "entity": "sensor.outdoor_temperature"}),
            ("service.call, never declared", False,
             {"op": "service.call", "service": "lock.unlock"}),
            ("config_entries.list, never declared", False, {"op": "config_entries.list"}),
        ]
        for label, expected, request in cases:
            decision = manifest.decide(request)
            check(label, decision.allowed is expected,
                  f"{'permit' if decision.allowed else 'deny'} · {decision.clause}", failures)
            if decision.clause is None:
                failures.append(f"{label}: no clause pointer (F3)")

        # ---- S5: the asymmetry rule -------------------------------------------------
        print("\n§5.10.4 / S5  a grant of lock.lock is not a grant of lock.unlock")
        component = write_component(root, "demo_lock", {
            "schema_version": 1, "services": {"call": ["lock.lock"]}})
        locks = Manifest.load(component, root)
        permitted = locks.decide({"op": "service.call", "service": "lock.lock"})
        refused = locks.decide({"op": "service.call", "service": "lock.unlock"})
        check("lock.lock is permitted", permitted.allowed, permitted.clause or "?", failures)
        check("lock.unlock is DENIED by the same manifest", not refused.allowed,
              f"{refused.reason}", failures)

        # ---- T07: a write is matched against its clause, not only against its absence ----
        # Every other write refusal in the suites is denial by absence (nothing declared under
        # entities.write), or the platform's ownership rule refusing it too. So with the
        # clause match removed (mutant M01) they all still passed, and nothing showed the
        # manifest's own check (verification 4.4, finding F39).
        print("\nT07  writes reach the declared entities only")
        component = write_component(root, "demo_writer", {
            "schema_version": 1, "entities": {"write": ["sensor.own_status"]}})
        writer = Manifest.load(component, root)
        own = writer.decide({"op": "entity.write", "entity": "sensor.own_status"})
        other = writer.decide({"op": "entity.write", "entity": "sensor.other_status"})
        check("entity.write to the declared entity is permitted", own.allowed,
              own.clause or "?", failures)
        check("entity.write to an undeclared entity of the same domain is DENIED",
              not other.allowed, f"{other.reason}", failures)

        # ---- declared grants of the capabilities no other case declares ------------------
        # Branch coverage found these decisions run by no suite (verification 4.12, F49): every
        # earlier case left `config_entries` and `events` undeclared, so only denial by absence
        # was ever exercised. Each check below fails under its mutant (M19, M20, M21).
        print("\nF49  declared config_entries and events, and an identity with no manifest")
        component = write_component(root, "demo_entries", {
            "schema_version": 1, "config_entries": {"read_all": True},
            "events": {"fire": ["my_event"]}})
        declared = Manifest.load(component, root)
        listed = declared.decide({"op": "config_entries.list"})
        check("config_entries.list with read_all: true is permitted", listed.allowed,
              listed.clause or "?", failures)
        component = write_component(root, "demo_entries_off", {
            "schema_version": 1, "config_entries": {"read_all": False}})
        off = Manifest.load(component, root).decide({"op": "config_entries.list"})
        check("config_entries.list with read_all: false is DENIED", not off.allowed,
              off.reason, failures)
        mine = declared.decide({"op": "event.fire", "event": "my_event"})
        theirs = declared.decide({"op": "event.fire", "event": "other_event"})
        check("event.fire of the declared event is permitted", mine.allowed,
              mine.clause or "?", failures)
        check("event.fire of another event is DENIED by the same manifest", not theirs.allowed,
              theirs.reason, failures)
        unbound = policy_for({"demo_entries": declared})(
            "demo_ghost", {"op": "entity.read", "entity": "sensor.x"})
        check("an identity with no manifest bound is DENIED, with a clause pointer (S6)",
              not unbound.allowed and unbound.clause is not None, unbound.reason, failures)

        # ---- rejections, all at parse time ------------------------------------------
        print("\n§5.10.4, §5.10.5, §5.10.1  what is refused when the manifest is read")
        rejections = [
            ("a wildcard in services.call",
             {"schema_version": 1, "services": {"call": ["lock.*"]}}),
            ("an entity pattern with no domain",
             {"schema_version": 1, "entities": {"read": ["*"]}}),
            ("a wildcarded entity domain",
             {"schema_version": 1, "entities": {"read": ["*.temperature"]}}),
            ("a wildcard in events.subscribe",
             {"schema_version": 1, "events": {"subscribe": ["*"]}}),
            ("an unknown capability",
             {"schema_version": 1, "telepathy": {"read": ["minds"]}}),
            ("an unknown member of a known capability",
             {"schema_version": 1, "entities": {"obliterate": ["light.kitchen"]}}),
            ("the wrong schema version", {"schema_version": 99}),
            ("a files grant reaching .storage",
             {"schema_version": 1, "files": {"read": [str(root / ".storage" / "x")]}}),
            ("a files grant reaching the configuration root",
             {"schema_version": 1, "files": {"read": [str(root)]}}),
            ("a files grant reaching secrets.yaml via ..",
             {"schema_version": 1,
              "files": {"read": [str(root / "shared" / ".." / "secrets.yaml")]}}),
        ]
        for label, permissions in rejections:
            component = write_component(root, "demo_bad", permissions)
            try:
                Manifest.load(component, root)
                check(label, False, "ACCEPTED — it should not have been", failures)
            except ManifestRejected as err:
                check(label, True, f"rejected: {str(err).split(': ', 1)[-1][:56]}", failures)

        # ---- S6 ----------------------------------------------------------------------
        print("\n§5.9.4 / S6  no manifest, and a manifest that is not a manifest")
        component = write_component(root, "demo_none", None)
        none = Manifest.load(component, root)
        check("no permissions key means provenance NONE",
              none.provenance is Provenance.NONE, none.provenance.value, failures)
        for op, request in (("entity.read", {"op": "entity.read", "entity": "sensor.x"}),
                            ("service.call", {"op": "service.call", "service": "lock.lock"}),
                            ("network.egress", {"op": "network.egress", "host": "a.invalid"})):
            decision = none.decide(request)
            check(f"{op} denied with a clause pointer",
                  not decision.allowed and decision.clause is not None,
                  f"{decision.clause}", failures)

        component = write_component(root, "demo_broken", None)
        (component / "manifest.json").write_text("{ this is not json")
        try:
            Manifest.load(component, root)
            check("an unparseable manifest is refused", False, "ACCEPTED", failures)
        except ManifestRejected as err:
            check("an unparseable manifest is refused", True,
                  str(err).split(": ", 1)[-1][:56], failures)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print()
    if failures:
        print(f"FAILED: {len(failures)} — {'; '.join(failures[:4])}")
        return 1
    print("PASS — S5's asymmetry holds, S6 denies by default, every path that reaches the")
    print("       configuration root is refused at parse time, and every decision names a clause.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
