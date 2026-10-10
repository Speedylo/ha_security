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

  W1 step 2b, commands from (A) into a sandbox (`notes/w1_step2b_commands_prediction.md`):

    C2   a user's command reaches only the owning integration's sandbox
    C3   each command is a durable `entity.command` decision, written before it is pushed
    C4   a command for an integration whose sandbox has gone fails to the user at once
    C5   a sandbox that never answers fails the user's call at the bridge's timeout, and the
         mediator keeps answering other sandboxes meanwhile
    C7   an answer to a command the channel was never sent is refused and recorded

  Found in the W1 review: a publish (A) refuses is answered as a refusal, and does not stop the
  mediator or leave the sandbox owning the entity.

  The refusal flood (`notes/flood_cutoff_prediction.md`), the household's half:

    F7   a cut-off raises a Repairs issue in (A) within 1 s, fixable, in plain words; confirming
         it over the same HTTP API the interface uses reinstates the integration, recorded, and
         the issue is gone

Run:  python3 -m confine.selftest_real_platform [--restart]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path

from . import house_a
from .house_a import User
from .audit import AuditLog
from .mediator import Mediator
from .platform import ActingPolicy
from .real_platform import PlatformError, PlatformStarting, RealPlatform
from .describe import approve_as_experimenter
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
    # F57: approved after the rewrite, because `component` approved the manifest it wrote.
    approve_as_experimenter(directory)
    return directory


def registry(platform: RealPlatform) -> dict[str, dict]:
    return {e["entity_id"]: e for e in platform.call({"type": "config/entity_registry/list"})}


def set_value(platform: RealPlatform, entity: str, value: float) -> None:
    platform.call({"type": "call_service", "domain": "input_number", "service": "set_value",
                   "service_data": {"entity_id": entity, "value": value}})


def commands_of(sandbox: Sandbox) -> list[dict]:
    return [m for m in sandbox.received if m.get("push") == "entity.command"]


def serve_until(mediator: Mediator, condition, seconds: float = 12) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        mediator.serve(timeout=0.01)
    return condition()


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

        print("\nW1 step 2b — commands from (A) into a sandbox\n")
        SWITCH, OTHER_SWITCH = "switch.selftest_sleep_mode", "switch.other_switch"
        other = Sandbox(mediator, "other", manifest(root, "other", {}))
        reader.ask({"op": "entity.publish", "entity": SWITCH, "state": "off"})
        other.ask({"op": "entity.publish", "entity": OTHER_SWITCH, "state": "off"})
        a_switch = platform.published[("selftest", SWITCH)]
        check("a published switch is a switch entity in (A), owned through the bridge",
              registry(platform).get(a_switch, {}).get("platform") == "confine_bridge",
              a_switch)

        # The happy path, played by hand: the in-process sandbox does what `sandbox_runtime`
        # does — runs the command, publishes what changed, answers.
        user = User()
        reader.received.clear()
        other.received.clear()
        pressed = user.press(a_switch, "turn_on")
        arrived = serve_until(mediator, lambda: (reader.drain(), commands_of(reader))[1])
        command = commands_of(reader)[0] if arrived else {}
        check("C2: the user's command reaches the owning sandbox",
              command.get("entity") == SWITCH and command.get("service") == "turn_on",
              f"{command}")
        other.drain()
        check("C2: and not the other sandbox", commands_of(other) == [])
        records = [r for r in log.records() if r["kind"] == "decision"
                   and r["op"] == "entity.command"]
        check("C3: the command is a durable decision, written before the push arrived",
              len(records) == 1 and records[0]["allowed"]
              and records[0]["integration"] == "selftest"
              and records[0]["requested"].get("service") == "switch.turn_on",
              f"{[(r['target'], r['requested'], r['allowed']) for r in records]}")
        reader.ask({"op": "entity.publish", "entity": SWITCH, "state": "on"})
        answered = reader.ask({"op": "entity.command_result",
                               "command": command.get("command"), "ok": True})
        serve_until(mediator, lambda: not pressed.is_alive())
        pressed.join()
        check("C1 (in process): the user's call succeeds once the sandbox answers",
              answered.get("ok") is True and user.outcome.get("success") is True,
              f"{user.outcome}")
        check("and the switch reads on in (A), published back the ordinary way",
              platform.read(a_switch)[0] == "on")

        print()
        forged = reader.ask({"op": "entity.command_result", "command": 424242, "ok": True})
        errors = [r for r in log.records() if r["kind"] == "protocol_error"]
        check("C7: an answer to a command never sent is refused",
              forged.get("ok") is False, forged.get("reason", ""))
        check("C7: and recorded, and the channel survives it",
              len(errors) == 1 and reader.ask({"op": "entity.read", "entity": TEMP})
              .get("ok") is True)

        # C5: a sandbox that never answers. The user's call must fail at the bridge's timeout,
        # and meanwhile the mediator must keep answering everyone else.
        user2 = User()
        pressed = user2.press(a_switch, "turn_off")
        serve_until(mediator, lambda: (reader.drain(), commands_of(reader)[1:])[1])
        # Timed from the request's own thread, until its answer — not with `Sandbox.ask`, whose
        # helper waits out `serve(timeout=0.3)` and reported 301 ms the first time: its own idle
        # period, not the mediator's (§7.37's R5 again).
        meanwhile: dict = {}

        def ask_other() -> None:
            start = time.perf_counter()
            meanwhile.update(other.channel.request(
                {"op": "entity.publish", "entity": OTHER_SWITCH, "state": "on"}))
            meanwhile["seconds"] = time.perf_counter() - start
        asking = threading.Thread(target=ask_other)
        asking.start()
        serve_until(mediator, lambda: not asking.is_alive())
        asking.join()
        responsive = meanwhile.get("seconds", 99.0)
        serve_until(mediator, lambda: not pressed.is_alive(), seconds=15)
        pressed.join()
        check("C5: a sandbox that never answers fails the user's call at the timeout",
              user2.outcome.get("success") is False
              and 9 <= user2.outcome.get("seconds", 0) <= 12,
              f"{user2.outcome.get('seconds', 0):.1f} s: {user2.outcome.get('error')}")
        check("C5: while the mediator kept answering another sandbox",
              meanwhile.get("ok") is True and responsive < 1, f"{responsive * 1e3:.1f} ms")

        # C4: the owning sandbox goes away. Its unanswered command, and any new one, fail at once.
        reader.channel.sock.close()
        mediator.serve(timeout=0.2)
        user3 = User()
        pressed = user3.press(a_switch, "turn_on")
        serve_until(mediator, lambda: not pressed.is_alive())
        pressed.join()
        check("C4: a command for an integration with no sandbox fails at once",
              user3.outcome.get("success") is False and user3.outcome.get("seconds", 9) < 1,
              f"{user3.outcome.get('seconds', 0) * 1e3:.0f} ms: {user3.outcome.get('error')}")
        refused = [r for r in log.records() if r["kind"] == "decision"
                   and r["op"] == "entity.command" and not r["allowed"]]
        check("C4: and the refusal is recorded too", len(refused) == 1, f"{len(refused)}")
        print("\nW1 review — a refusal by (A) is a refusal, not a crash\n")
        # Found reviewing W1 (2026-10-04): the bridge refuses domains it cannot stand in for, the
        # refusal reached the mediator as an exception nothing caught, and one sandbox publishing
        # a light stopped the mediator for every sandbox — after recording it as the light's owner.
        refused_publish = other.ask({"op": "entity.publish", "entity": "light.probe",
                                     "state": "on"})
        check("a publish (A) refuses is answered to the sandbox as a refusal",
              refused_publish.get("ok") is False
              and "platform refused" in refused_publish.get("reason", ""),
              refused_publish.get("reason", ""))
        check("and the mediator still serves", other.ask(
            {"op": "entity.publish", "entity": OTHER_SWITCH, "state": "off"}).get("ok") is True)
        check("and the sandbox is not recorded as owning what was never published",
              platform.owners.get("light.probe") is None)
        both = [r["allowed"] for r in log.records() if r["kind"] == "decision"
                and r.get("target") == "light.probe"]
        check("the log shows the grant and then the refusal, so the refusal is the last word",
              both == [True, False], f"{both}")

        print("\nF7 — a cut-off reaches the household, and the way back\n")
        # The limit is lowered for speed: what is under test here is the path through (A), and
        # `selftest_flood` covers the limit itself at its real value.
        limit, mediator.flood_limit = mediator.flood_limit, 5
        flooder = Sandbox(mediator, "flooder", manifest(root, "flooder", {}))
        issue_id = "cut_off_flooder"

        def issue() -> dict:
            return next((i for i in platform.call({"type": "repairs/list_issues"})["issues"]
                         if i["domain"] == "confine_bridge" and i["issue_id"] == issue_id), {})

        for _ in range(4):
            flooder.ask({"op": "entity.read", "entity": "lock.front_door"})
        # The fifth by hand: `Sandbox.ask` would raise before joining its server thread, and
        # that thread is the one telling (A), on the connection this one is about to poll.
        started = time.perf_counter()
        server = threading.Thread(target=mediator.serve, kwargs={"timeout": 0.3})
        server.start()
        try:
            flooder.channel.request({"op": "entity.read", "entity": "lock.front_door"})
        except (ConnectionError, OSError):
            pass
        server.join()
        raised = {}
        while time.perf_counter() - started < 5 and not raised:
            raised = issue()
        seen = time.perf_counter() - started
        mediator.flood_limit = limit
        check("the fifth refusal cuts the integration off, and (A) is not left untold",
              "flooder" in mediator.cut_off and not mediator.undelivered,
              f"{mediator.undelivered}")
        check("F7: a Repairs issue for it is in (A) within 1 s of the cut-off",
              bool(raised) and seen < 1.0, f"{seen * 1000:.0f} ms")
        check("an error the user can fix, worded from the bridge's own strings, naming it",
              raised.get("is_fixable") is True and raised.get("severity") == "error"
              and raised.get("translation_key") == "cut_off"
              and (raised.get("translation_placeholders") or {}).get("name") == "flooder",
              f"{ {k: raised.get(k) for k in ('severity', 'translation_key')} }")

        token = house_a.TOKEN_FILE.read_text().strip()
        flow = house_a.request("POST", "/api/repairs/issues/fix",
                               {"handler": "confine_bridge", "issue_id": issue_id}, token=token)
        check("opening it shows one confirm step, as the Repairs panel would",
              flow.get("type") == "form" and flow.get("step_id") == "confirm", f"{flow}")
        done = house_a.request("POST", f"/api/repairs/issues/fix/{flow['flow_id']}", {},
                               token=token)
        back = serve_until(mediator, lambda: "flooder" not in mediator.cut_off)
        check("submitting it reinstates the integration in the mediator",
              done.get("type") == "create_entry" and back, f"{done.get('type')}")
        reinstated = [r for r in log.records() if r["kind"] == "reinstate"]
        check("the reinstatement is durable, and says it came from the user",
              len(reinstated) == 1
              and reinstated[0]["detail"] == "reinstated by a user, from the Repairs panel",
              reinstated[0]["detail"] if reinstated else "none")
        check("and the issue is gone from (A)", issue() == {})
        again = Sandbox(mediator, "flooder", manifest(root, "flooder", {}))
        check("the integration can be registered again", mediator.open_channels >= 1
              and "flooder" not in mediator.cut_off)
        again.channel.sock.close()

        check("every chain still verifies", log.verify() == [])
        for person in (user, user2, user3):
            person.close()

        other.channel.sock.close()
        platform.close()

    # F45: the mediator runs as an ordinary user, not as the house's admin. Every call above was
    # made with its token, so those results already show it can do its job. These show what it
    # cannot do, which is the point: a compromised mediator gets an ordinary user's power, not the
    # house's configuration, users or integrations.
    print("\nF45 — the mediator's token is an ordinary user's\n")
    probe = RealPlatform()
    me = probe.call({"type": "auth/current_user"})
    check("the mediator's user is not an admin", isinstance(me, dict) and not me.get("is_admin"),
          f"{(me or {}).get('name')}, is_admin={(me or {}).get('is_admin')}")
    admin_only = [
        ("list the house's users", {"type": "config/auth/list"}),
        ("see integrations being added", {"type": "config_entries/flow/progress"}),
        ("subscribe to every service call", {"type": "subscribe_events",
                                             "event_type": "call_service"}),
        ("call an admin-only service (check_config)",
         {"type": "call_service", "domain": "homeassistant", "service": "check_config",
          "service_data": {}}),
    ]
    for label, message in admin_only:
        try:
            probe.call(message)
            refused, why = False, "allowed"
        except PlatformError as err:
            refused, why = True, str(err)[:70]
        check(f"it may not {label}", refused, why)
    probe.close()
    other = house_a.ensure_user(house_a.TOKEN_FILE.read_text().strip(), "f45-other",
                                house_a.MEDIATOR_TOKEN_FILE.with_name("house_a_f45_other.token"),
                                house_a.MEDIATOR_TOKEN_FILE.with_name("house_a_f45_other.password"))
    try:
        RealPlatform(token_file=house_a.MEDIATOR_TOKEN_FILE.with_name("house_a_f45_other.token"))
        gated, why = False, "the bridge let it subscribe to commands"
    except PlatformError as err:
        gated, why = True, str(err)[:70]
    check("another ordinary user, not the designated one, is refused by the bridge", gated,
          f"user {other[:8]}…: {why}")
    # Naming the mediator is an admin's act. Without this check, a bridge that let any user
    # designate itself passed every suite (mutant M18c, 2026-10-07): the user above would be
    # refused only until it named itself the mediator.
    other_token = house_a.MEDIATOR_TOKEN_FILE.with_name("house_a_f45_other.token").read_text().strip()
    seized = house_a._ws_call(other_token, {"type": "confine_bridge/designate_mediator",
                                            "user_id": other})
    if seized.get("success"):  # put the real mediator back, so the checks after this one still run
        house_a.ensure_mediator_user(house_a.TOKEN_FILE.read_text().strip())
    check("and it may not designate itself as the mediator", not seized.get("success"),
          (seized.get("error") or {}).get("code", "it was accepted"))

    if args.restart:
        print("\nR2 — (A) restarts, and the bridged entity is still there\n")
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
