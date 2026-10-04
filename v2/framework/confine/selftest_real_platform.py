"""W1 step 2 — the mediator acting on the house's real Home Assistant, (A), at the decision layer.

Requires (A) running: `python3 -m confine.house_a up --fresh` on the Pi. The far end of each
channel is `selftest_push`'s in-process sandbox — identity still comes from the socket — and the
platform is `RealPlatform`, so every step 5 here is a WebSocket message to a real instance.
Predictions: `notes/w1_step2_real_platform_prediction.md` §4.

    R1   a publish through the mediator becomes an entity-registry row in (A) — `unique_id`,
         `platform: confine_bridge`, a config entry, a device — and the same state posted to
         `/api/states` gets none: the spike's finding, re-measured rather than cited
    own  an integration cannot publish an entity id (A) already has (§6.10.3, against real data)
    R6   a permitted service call changes (A)'s state; a refused one never reaches (A)
    R4   a change to an unsubscribed entity in (A) is not delivered, and (A) is asked to send
         only the entities someone subscribed to
    R5   from a real `input_number.set_value` to the push reaching the sandbox, timed
    R2   with --restart: (A) is restarted, and the bridged entity is still registered and holds
         its last state before anything republishes it

Run:  python3 -m confine.selftest_real_platform [--restart]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

from . import house_a
from .audit import AuditLog
from .mediator import Mediator
from .platform import ActingPolicy
from .real_platform import RealPlatform
from .selftest_push import Sandbox, component

results: list[bool] = []
TEMP, HUMID = "sensor.living_room_temperature", "sensor.living_room_humidity"
PUBLISHED = "sensor.selftest_dew_point"


def check(claim: str, condition: bool, detail: str = "") -> None:
    results.append(condition)
    print(f"{'  ok  ' if condition else '  FAIL'}  {claim}{f'  — {detail}' if detail else ''}")


def manifest(root: Path, domain: str, permissions: dict) -> Path:
    directory = component(root, domain, [])
    (directory / "manifest.json").write_text(json.dumps(
        {"domain": domain, "name": domain, "version": "1.0.0", "requirements": [],
         "permissions": {"schema_version": 1, **permissions}}))
    return directory


def registry(platform: RealPlatform) -> dict[str, dict]:
    return {e["entity_id"]: e for e in platform.call({"type": "config/entity_registry/list"})}


def set_value(platform: RealPlatform, entity: str, value: float) -> None:
    platform.call({"type": "call_service", "domain": "input_number", "service": "set_value",
                   "service_data": {"entity_id": entity, "value": value}})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--restart", action="store_true",
                    help="R2: restart (A) at the end and check what survived")
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

        reader = Sandbox(mediator, "selftest", manifest(root, "selftest", {
            "entities": {"read": [TEMP], "subscribe": [TEMP]},
            "services": {"call": ["input_number.set_value"]}}))

        print("\nR1 — identity: a registry row, against a bare state\n")
        answer = reader.ask({"op": "entity.publish", "entity": PUBLISHED, "state": "9.96",
                             "attributes": {"unit_of_measurement": "°C",
                                            "device_class": "temperature",
                                            "friendly_name": "Selftest dew point"}})
        check("the publish is allowed as the integration's own entity",
              answer.get("ok") is True, answer.get("clause", ""))
        landed = platform.published.get(("selftest", PUBLISHED))
        rows = registry(platform)
        row = rows.get(landed or "", {})
        check("it has an entity-registry row in (A)", bool(row), f"entity_id={landed}")
        check("with the bridge as platform and a unique_id naming the integration",
              row.get("platform") == "confine_bridge"
              and row.get("unique_id") == f"selftest:{PUBLISHED}", f"{row.get('unique_id')}")
        check("and a config entry and a device", bool(row.get("config_entry_id"))
              and bool(row.get("device_id")))
        state, attributes = platform.read(landed or "")
        check("and (A) holds its state, with its unit", state == "9.96"
              and attributes.get("unit_of_measurement") == "°C", f"{state} {attributes}")

        token = house_a.TOKEN_FILE.read_text().strip()
        house_a.request("POST", "/api/states/sensor.selftest_bare",
                        {"state": "9.96", "attributes": {"unit_of_measurement": "°C"}},
                        token=token)
        check("the same state posted to /api/states exists in (A)",
              platform.read("sensor.selftest_bare")[0] == "9.96")
        check("but has no registry row at all — the spike's finding, re-measured",
              "sensor.selftest_bare" not in registry(platform))

        print("\nownership — against what (A) already has\n")
        spoof = reader.ask({"op": "entity.publish", "entity": TEMP, "state": "99"})
        check("publishing an entity id (A) already has is refused without entities.write",
              spoof.get("ok") is False and "the platform" in spoof.get("reason", ""),
              spoof.get("reason", ""))
        check("and (A)'s own entity is untouched", platform.read(TEMP)[0] != "99",
              f"{TEMP}={platform.read(TEMP)[0]}")

        print("\nR6 — service calls execute in (A), refusals never arrive\n")
        allowed = reader.ask({"op": "service.call", "service": "input_number.set_value",
                              "data": {"entity_id": "input_number.living_room_humidity",
                                       "value": 55}})
        time.sleep(0.5)
        check("a permitted call executes: (A)'s humidity is now 55",
              allowed.get("ok") is True
              and platform.read("input_number.living_room_humidity")[0] == "55.0",
              f"{platform.read('input_number.living_room_humidity')[0]}")
        refused = reader.ask({"op": "service.call", "service": "input_number.increment",
                              "data": {"entity_id": "input_number.living_room_humidity"}})
        time.sleep(0.5)
        check("a refused call never reaches (A): still 55",
              refused.get("ok") is False
              and platform.read("input_number.living_room_humidity")[0] == "55.0")
        check("and (A) executed exactly one call on the mediator's behalf",
              platform.calls == [("input_number", "set_value",
                                  {"entity_id": "input_number.living_room_humidity",
                                   "value": 55})], f"{platform.calls}")

        print("\nR4 — what (A) is asked to send, and what reaches the sandbox\n")
        granted = reader.ask({"op": "entity.subscribe", "entity": TEMP})
        check("the subscription is granted", granted.get("ok") is True)
        check("(A) is asked for exactly the subscribed entities",
              platform.watched == [TEMP], f"watched={platform.watched}")
        reader.received.clear()
        set_value(platform, "input_number.living_room_humidity", 60)
        set_value(platform, "input_number.living_room_temperature", 23.0)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not any(
                m["state"] == "23.0" for m in reader.received):
            mediator.serve(timeout=0.1)
            reader.drain()
        seen = {(m["entity"], m["state"]) for m in reader.received}
        check("the subscribed entity's real change arrives", (TEMP, "23.0") in seen, f"{seen}")
        check("the humidity change, unsubscribed, does not",
              not any(e == HUMID for e, _ in seen))

        # R5. From the service call leaving the mediator to (A)'s change reaching the mediator's
        # push: (A)'s service, its template re-render, the state_changed event, subscribe_entities,
        # and the mediator's read. Timestamped by a listener on the platform, where the push
        # starts. The first version timed the loop around `serve(timeout=0.05)` instead, and
        # reported 50.7 ms — its own polling interval, not (A).
        arrived: dict[str, float] = {}
        platform.listeners.append(
            lambda entity, state, _a: arrived.setdefault(state, time.perf_counter())
            if entity == TEMP else None)
        latencies = []
        for n in range(30):
            value = str(24.0 + n / 10)
            start = time.perf_counter()
            set_value(platform, "input_number.living_room_temperature", float(value))
            while value not in arrived and time.perf_counter() - start < 5:
                mediator.serve(timeout=0.002)
            reader.drain()
            if value in arrived:
                latencies.append(arrived[value] - start)
        median = statistics.median(latencies) if latencies else float("inf")
        check("R5: a real change reaches the mediator's push in milliseconds",
              len(latencies) == 30 and median < 0.5,
              f"median {median * 1e3:.2f} ms, max {max(latencies or [0]) * 1e3:.2f} ms "
              f"over {len(latencies)} changes")
        check("and each of the 30 changes reached the sandbox",
              {str(24.0 + n / 10) for n in range(30)}
              <= {m["state"] for m in reader.received})

        decisions = [r for r in log.records() if r["kind"] == "decision"]
        check("no delivery wrote a record; the log holds decisions only",
              len(decisions) == 5, f"{len(decisions)} decisions")
        check("every chain verifies", log.verify() == [])

        reader.channel.sock.close()
        platform.close()

    if args.restart:
        print("\nR2 — (A) restarts, and the bridged entity is still there\n")
        house_a.stop(house_a.DEFAULT_CONFIG)
        house_a.start(house_a.DEFAULT_CONFIG)
        time.sleep(5)
        after = RealPlatform()
        row = registry(after).get(landed or "", {})
        check("after a restart the entity is still registered to the bridge",
              row.get("unique_id") == f"selftest:{PUBLISHED}")
        check("and holds its last state before any sandbox has run again",
              after.read(landed or "")[0] == "9.96", f"{after.read(landed or '')[0]}")
        check("while the bare state posted over /api/states is gone",
              after.read("sensor.selftest_bare")[0] is None)
        after.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
