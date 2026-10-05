"""The refusal flood: a sandbox that keeps asking for what it may not have is cut off.

Every refusal is a durable, fsynced record, and before this nothing bounded how many a sandbox
could cause: W2 (a)'s arm C wrote 463,631 in 7.5 minutes (§7.40.4). The mediator now counts each
integration's refused requests and, past `FLOOD_LIMIT` within `FLOOD_WINDOW` seconds, records one
`cutoff`, closes the integration's channel, and will not register it again until it is
reinstated. Predictions: `notes/flood_cutoff_prediction.md` §5.

What each case checks:

    F1   a flood stops after exactly the limit: that many refusals on disk, then one `cutoff`,
         then nothing more from the flooder
    F1m  the mutation: with the limit out of reach, the same flood is still running at the
         deadline, so the stop above comes from the cut-off and not from the harness
    F3   a second sandbox is answered throughout the flood
    F4   a cut-off integration cannot register; reinstating is recorded before it can, and
         reinstating one that was never cut off writes nothing
    F5   a user's refused commands are recorded but not counted
    win  refusals spread more thinly than the window are never cut off
    note a house that cannot be told does not undo the cut-off, and says so
    S7   the durable log's chains verify and match the in-memory record, events included

**Layer.** No sandbox is spawned, as in `selftest_push`: identity comes from the socket, and the
flooding "sandbox" is the sandbox's own `Channel` class driven from a thread. The spawned run,
with a real integration flooding from inside its sandbox, is `experiments/flood/` on the Pi.

Run:  python3 -m confine.selftest_flood
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
from pathlib import Path

from .audit import AuditLog, reconcile
from .channel import Channel
from .mediator import FLOOD_LIMIT, CutOff, Mediator
from .platform import ActingPolicy, Platform
from .sandbox_runtime import Channel as SandboxChannel

PASS, FAIL = "  ok  ", "  FAIL"
results: list[bool] = []

DECLARED = "sensor.living_room_temperature"
#: What the flooder asks for, over and over: an entity it never declared.
UNDECLARED = "lock.front_door"


def check(claim: str, condition: bool, detail: str = "") -> None:
    results.append(condition)
    print(f"{PASS if condition else FAIL}  {claim}{f'  — {detail}' if detail else ''}")


def component(root: Path, domain: str, read: list[str]) -> Path:
    directory = root / "custom_components" / domain
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "__init__.py").write_text("")
    (directory / "manifest.json").write_text(json.dumps(
        {"domain": domain, "name": domain, "version": "1.0.0", "requirements": [],
         "permissions": {"schema_version": 1,
                         "entities": {"read": read} if read else {}}}))
    return directory


def connect(mediator: Mediator, domain: str, directory: Path) -> SandboxChannel:
    ours, theirs = Channel.pair()
    mediator.register(domain, Channel(ours), component=directory)
    return SandboxChannel(theirs.detach())


def flood(channel: SandboxChannel, outcome: dict) -> None:
    """Ask for the undeclared entity until the mediator stops answering."""
    sent = 0
    try:
        while True:
            channel.request({"op": "entity.read", "entity": UNDECLARED})
            sent += 1
    except (ConnectionError, OSError) as err:
        outcome["stopped"] = str(err)
    finally:
        outcome["sent"] = sent


def neighbour(channel: SandboxChannel, stop: threading.Event, outcome: dict) -> None:
    """Read a declared entity in a loop, timing each answer, until told to stop."""
    answers, worst = [], 0.0
    try:
        while not stop.is_set():
            started = time.perf_counter()
            answers.append(channel.request({"op": "entity.read", "entity": DECLARED}))
            worst = max(worst, time.perf_counter() - started)
    except (ConnectionError, OSError) as err:
        outcome["error"] = str(err)
    outcome["answers"], outcome["worst"] = answers, worst


class House:
    """Just enough of a platform for `Mediator.command`, and a record of what it was told."""

    def __init__(self, fail: bool = False) -> None:
        self.owners: dict[str, str] = {}
        self.results: list[tuple] = []
        self.told: list[tuple[str, str]] = []
        self.fail = fail

    def command_result(self, command: int, ok: bool, error: str | None = None) -> None:
        self.results.append((command, ok, error))

    def cut_off(self, identity: str, detail: str) -> None:
        if self.fail:
            raise ConnectionError("(A) is not reachable")
        self.told.append((identity, detail))


def mediator_for(root: Path, name: str, **knobs) -> tuple[Mediator, AuditLog, Platform]:
    platform = Platform()
    platform.seed(DECLARED, "21.4")
    platform.seed(UNDECLARED, "locked")
    log = AuditLog(path=root / name / "decisions.jsonl")
    return Mediator(policy=ActingPolicy({}, platform), log=log, **knobs), log, platform


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        flooder_dir = component(root, "flooder", [])
        reader_dir = component(root, "reader", [DECLARED])

        print(f"\nF1, F3 — a flood, with a neighbour, at the real limit ({FLOOD_LIMIT})\n")
        mediator, log, _ = mediator_for(root, "f1")
        flooder = connect(mediator, "flooder", flooder_dir)
        reader = connect(mediator, "reader", reader_dir)
        cut: list[str] = []
        mediator.on_cut_off.append(cut.append)
        flooded, read, stop = {}, {}, threading.Event()
        threads = [threading.Thread(target=flood, args=(flooder, flooded)),
                   threading.Thread(target=neighbour, args=(reader, stop, read))]
        started = time.monotonic()
        for thread in threads:
            thread.start()
        # Serve until the flooder is gone, then a little longer, so the neighbour is seen
        # being answered after the cut-off as well as during it.
        while "flooder" not in mediator.cut_off and time.monotonic() - started < 30:
            mediator.serve(timeout=0.2, until=time.monotonic() + 0.2)
        elapsed = time.monotonic() - started
        mediator.serve(timeout=0.2, until=time.monotonic() + 0.5)
        stop.set()
        mediator.serve(timeout=0.3, until=time.monotonic() + 1)
        for thread in threads:
            thread.join(timeout=5)

        records = log.records()
        mine = [r for r in records if r.get("integration") == "flooder"]
        refusals = [r for r in mine if r["kind"] == "decision" and not r["allowed"]]
        cutoffs = [r for r in mine if r["kind"] == "cutoff"]
        check("the flooder is cut off", "flooder" in mediator.cut_off and cut == ["flooder"],
              f"after {elapsed:.2f} s; supervisor told {cut}")
        check(f"exactly {FLOOD_LIMIT} refusals are on disk for it, and one cutoff",
              len(refusals) == FLOOD_LIMIT and len(cutoffs) == 1,
              f"{len(refusals)} refusals, {len(cutoffs)} cutoff: {cutoffs[0]['detail'] if cutoffs else '-'}")
        check("the cutoff is its last record: nothing was decided for it after",
              bool(mine) and mine[-1]["kind"] == "cutoff")
        check("its end of the channel was closed, and it noticed",
              "stopped" in flooded, f"{flooded.get('sent')} answers, then: {flooded.get('stopped')}")
        # F2 is a prediction about the Pi's disk, so it is reported here and judged from the Pi's
        # log, as `selftest_push` reports P8: each record is an fsync, the neighbour's grants
        # included, and a development machine's fsync is not the Pi's.
        print(f"  ..    F2: flood start to cut-off {elapsed:.3f} s, the neighbour's grants included "
              f"(predicted under 1 s on the Pi)")
        answers = read.get("answers") or []
        check("F3: the neighbour was answered throughout, every answer a grant",
              len(answers) > 0 and all(a.get("ok") for a in answers) and "error" not in read,
              f"{len(answers)} answers, worst {read.get('worst', 0) * 1000:.1f} ms")
        check("F3: and no answer to it took 1 s or more", read.get("worst", 9) < 1.0)
        check("the neighbour was not counted towards anything", "reader" not in mediator.cut_off
              and not any(r["kind"] == "cutoff" for r in records if r.get("integration") == "reader"))

        print("\nF1m — the mutation: the same flood with the limit out of reach\n")
        unbounded, log_m, _ = mediator_for(root, "f1m", flood_limit=10**9)
        channel = connect(unbounded, "flooder", flooder_dir)
        outcome: dict = {}
        thread = threading.Thread(target=flood, args=(channel, outcome), daemon=True)
        thread.start()
        # Served until it is well past the limit rather than for a fixed time: how many records a
        # second is a property of the disk, and the claim is about the count.
        deadline, written = time.monotonic() + 20, 0
        while written <= 2 * FLOOD_LIMIT and time.monotonic() < deadline:
            unbounded.serve(timeout=0.2, until=time.monotonic() + 0.2)
            written = sum(1 for r in log_m.records() if r["kind"] == "decision")
        still = unbounded.open_channels == 1 and "stopped" not in outcome
        check("is still running at twice the limit, with nothing cut off",
              still and written > 2 * FLOOD_LIMIT and not unbounded.cut_off,
              f"{written} refusals and counting")
        unbounded.unregister(next(iter(unbounded._by_fd)))
        thread.join(timeout=5)

        print("\nF4 — cut off stays cut off until reinstated\n")
        try:
            connect(mediator, "flooder", flooder_dir)
            refused, why = False, "registered"
        except CutOff as err:
            refused, why = True, str(err)
        check("a cut-off integration cannot be registered again", refused, why)
        check("reinstating one that was never cut off does nothing, and writes nothing",
              mediator.reinstate("reader", "the test") is False
              and not any(r["kind"] == "reinstate" for r in log.records()))
        back: list[str] = []
        mediator.on_reinstate.append(back.append)
        before = len(log.records())
        check("reinstating the flooder succeeds, and the supervisor is told",
              mediator.reinstate("flooder", "the test") and back == ["flooder"])
        again = connect(mediator, "flooder", flooder_dir)
        tail = log.records()[before:]
        check("the reinstatement is recorded before the new run record",
              [r["kind"] for r in tail[:2]] == ["reinstate", "run"]
              and tail[0]["detail"] == "reinstated by the test", f"{[r['kind'] for r in tail]}")
        outcome = {}
        thread = threading.Thread(target=flood, args=(again, outcome))
        thread.start()
        while "flooder" not in mediator.cut_off:
            mediator.serve(timeout=0.2, until=time.monotonic() + 0.2)
        thread.join(timeout=5)
        cutoffs = [r for r in log.records() if r["kind"] == "cutoff"]
        check("the count starts again from zero, and a second flood is cut off the same way",
              len(cutoffs) == 2 and outcome.get("sent") == FLOOD_LIMIT - 1,
              f"{outcome.get('sent')} answers before the second cut-off")

        print("\nF5 — a user's refused commands are not the sandbox's doing\n")
        users, log_u, _ = mediator_for(root, "f5", flood_limit=5)
        house = House()
        users._platform = house
        # The sandbox is running; what the user asks for is an entity it does not own, so every
        # command is refused for a reason that is not the sandbox's doing.
        connect(users, "flooder", flooder_dir)
        for command in range(1, 21):
            users.command({"command": command, "integration": "flooder",
                           "entity_id": "switch.misbehave", "service": "turn_on"})
        refused_to_user = [r for r in log_u.records() if r["kind"] == "decision"
                           and r["op"] == "entity.command"]
        check("twenty refused commands, each recorded and answered to the user",
              len(refused_to_user) == 20 and all(not ok for _, ok, _ in house.results)
              and len(house.results) == 20)
        check("and none of them counted: four times the limit, no cut-off",
              not users.cut_off and "flooder" not in users._refusals)

        print("\nwin — refusals more thinly spread than the window\n")
        thin, log_t, _ = mediator_for(root, "win", flood_limit=5, flood_window=0.5)
        channel = connect(thin, "flooder", flooder_dir)
        server = threading.Thread(target=lambda: thin.serve(timeout=3))
        server.start()
        answers = []
        for burst in range(3):
            answers += [channel.request({"op": "entity.read", "entity": UNDECLARED})
                        for _ in range(4)]
            time.sleep(0.6)
        channel.sock.close()
        server.join(timeout=10)
        check("three bursts of four, 0.6 s apart, against five in 0.5 s: never cut off",
              len(answers) == 12 and not thin.cut_off
              and not any(r["kind"] == "cutoff" for r in log_t.records()),
              f"{len(answers)} refusals answered")

        print("\nnote — the house cannot be told\n")
        quiet, log_q, _ = mediator_for(root, "note", flood_limit=5)
        quiet._platform = House(fail=True)
        channel = connect(quiet, "flooder", flooder_dir)
        outcome = {}
        thread = threading.Thread(target=flood, args=(channel, outcome))
        thread.start()
        quiet.serve(timeout=0.5, until=time.monotonic() + 5)
        thread.join(timeout=5)
        check("the cut-off stands, and the missing Repairs issue is reported",
              "flooder" in quiet.cut_off and quiet.open_channels == 0
              and len(quiet.undelivered) == 1, f"{quiet.undelivered}")
        told = House()
        polite, _, _ = mediator_for(root, "told", flood_limit=5)
        polite._platform = told
        channel = connect(polite, "flooder", flooder_dir)
        thread = threading.Thread(target=flood, args=(channel, {}))
        thread.start()
        polite.serve(timeout=0.5, until=time.monotonic() + 5)
        thread.join(timeout=5)
        check("a reachable house is told which integration, and why",
              told.told == [("flooder", "5 refusals within 10 s")], f"{told.told}")

        print("\nS7 — the durable record, events included\n")
        for name, m, lg in (("F1/F4", mediator, log), ("F5", users, log_u), ("win", thin, log_t),
                            ("note", quiet, log_q)):
            problems = reconcile(m.audit, lg.records())
            breaks = lg.verify()
            check(f"{name}: chains verify, and memory matches the disk entry by entry",
                  not problems and not breaks, "; ".join(problems[:3] + [str(b) for b in breaks[:2]]))

    passed = sum(results)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
