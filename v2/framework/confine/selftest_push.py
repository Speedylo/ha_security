"""W1 step 1 — the push loop, at the decision layer. S3's subscription half, delivered and filtered.

§7.14.4 could only say that a confined integration receives no undeclared change because it
receives no change at all: "an absent feature, not a demonstrated filter". This suite is the
filter. It runs the real `Mediator`, the real `ActingPolicy` and the stand-in `Platform`, with the
sandbox's own `Channel` class from `sandbox_runtime` on the far end of each socket, and asks what
crosses. Predictions: `notes/w1_push_loop_prediction.md` §4.

What each case checks:

    P5   a change reaches a channel only if that channel's subscription was granted; changes to
         undeclared entities are delivered nowhere
    P5   the mutation: with the table bypassed, the same changes ARE seen, so the zero above
         comes from the filter and not from an observer that cannot see
    A    the subscription is a recorded decision, and a refused one is recorded too
    wire a push that arrives while a request waits for its reply is handed to `on_push`, and
         the reply still comes back as the reply
    P7   a sandbox that never reads neither blocks the mediator nor delays another sandbox,
         and what the mediator holds for it is bounded by its subscriptions
    #14  a respawn starts with no subscriptions and has to be granted each one again
    P8   what one delivered push costs the mediator (reported; judged on the Pi)

**Layer.** No sandbox is spawned: identity comes from the socket exactly as it does in a real
run, and namespaces would add a root requirement without touching what is measured. The
spawned version, with a real integration's listener firing, is P4's run on the Pi.

Run:  python3 -m confine.selftest_push
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
from pathlib import Path

from .audit import AuditLog
from .channel import Channel
from .manifest import Manifest
from .mediator import Mediator
from .platform import ActingPolicy, Platform
from .sandbox_runtime import Channel as SandboxChannel

PASS, FAIL = "  ok  ", "  FAIL"
results: list[bool] = []

DECLARED = "sensor.living_room_temperature"
UNDECLARED = ["sensor.bedroom_occupancy", "lock.front_door", "person.younes"]


def check(claim: str, condition: bool, detail: str = "") -> None:
    results.append(condition)
    print(f"{PASS if condition else FAIL}  {claim}{f'  — {detail}' if detail else ''}")


def component(root: Path, domain: str, subscribe: list[str]) -> Path:
    directory = root / "custom_components" / domain
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "__init__.py").write_text("")
    (directory / "manifest.json").write_text(json.dumps(
        {"domain": domain, "name": domain, "version": "1.0.0", "requirements": [],
         "permissions": {"schema_version": 1,
                         "entities": {"read": subscribe, "subscribe": subscribe}
                         if subscribe else {}}}))
    return directory


class Sandbox:
    """The far end of one channel, holding the sandbox's own `Channel` and a list of pushes."""

    def __init__(self, mediator: Mediator, domain: str, directory: Path) -> None:
        ours, theirs = Channel.pair()
        mediator.register(domain, Channel(ours), component=directory)
        self.channel = SandboxChannel(theirs.detach())
        self.received: list[dict] = []
        self.channel.on_push = self.received.append
        self.mediator = mediator

    def ask(self, message: dict) -> dict:
        """One request, served on a helper thread so this one can play the sandbox."""
        server = threading.Thread(target=self.mediator.serve, kwargs={"timeout": 0.3})
        server.start()
        answer = self.channel.request(message)
        server.join()
        return answer

    def drain(self) -> None:
        self.channel.poll()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        platform = Platform()
        for entity in [DECLARED, *UNDECLARED]:
            platform.seed(entity, "0")

        log = AuditLog(path=root / "audit" / "decisions.jsonl")
        policy = ActingPolicy({}, platform)
        mediator = Mediator(policy=policy, log=log)
        platform.listeners.append(mediator.push)

        reader = Sandbox(mediator, "thermal", component(root, "thermal", [DECLARED]))
        other = Sandbox(mediator, "weather", component(root, "weather", []))

        print("\nA — a subscription is a recorded decision\n")
        granted = reader.ask({"op": "entity.subscribe", "entity": DECLARED})
        check("a declared subscription is granted with a clause pointer",
              granted.get("ok") is True
              and granted.get("clause") == "/permissions/entities/subscribe/0",
              f"clause={granted.get('clause')}")
        refused = [reader.ask({"op": "entity.subscribe", "entity": e}) for e in UNDECLARED]
        check("every undeclared subscription is refused",
              all(r.get("ok") is False for r in refused))
        nothing = other.ask({"op": "entity.subscribe", "entity": DECLARED})
        check("an integration that declares no subscriptions is refused the same entity",
              nothing.get("ok") is False, nothing.get("reason", ""))
        subscribes = [r for r in log.records()
                      if r["kind"] == "decision" and r["op"] == "entity.subscribe"]
        check("all five decisions are on disk, the grant and the four refusals",
              len(subscribes) == 5 and sum(r["allowed"] for r in subscribes) == 1,
              f"{len(subscribes)} records, {sum(r['allowed'] for r in subscribes)} allowed")

        print("\nP5 — what crosses, and what does not\n")
        for value in ("21.5", "21.7"):
            platform.set_state(DECLARED, value, {"unit_of_measurement": "°C"})
        for entity in UNDECLARED:
            platform.set_state(entity, "on")
        reader.drain()
        other.drain()
        seen = [(m["entity"], m["state"]) for m in reader.received]
        check("the subscribed entity's changes arrive, in order",
              seen == [(DECLARED, "21.5"), (DECLARED, "21.7")], f"{seen}")
        check("no change to an undeclared entity arrives",
              not any(m["entity"] in UNDECLARED for m in reader.received),
              f"0 of {len(UNDECLARED)} undeclared changes delivered")
        check("and the integration with no grant receives nothing at all",
              other.received == [], f"{len(other.received)} received")
        check("the attributes travel with the state",
              reader.received[-1]["attributes"] == {"unit_of_measurement": "°C"})
        check("no delivery wrote a record: the subscription is the record (decision A)",
              len([r for r in log.records() if r["kind"] == "decision"]) == 5)

        # The mutation. If the observer could not see an undeclared change, the zero above
        # would be the same absence §7.14.4 described. So deliver past the table, once, and
        # check that the same observer sees it.
        saved = {fd: set(entities) for fd, entities in mediator._subscriptions.items()}
        for entities in mediator._subscriptions.values():
            entities.update(UNDECLARED)
        for entity in UNDECLARED:
            platform.set_state(entity, "leaked")
        reader.drain()
        other.drain()
        leaked = {m["entity"] for m in reader.received + other.received if m["state"] == "leaked"}
        check("mutation: with the table bypassed, the same observer sees every undeclared change",
              leaked == set(UNDECLARED), f"{len(leaked)} of {len(UNDECLARED)} seen")
        mediator._subscriptions.clear()
        mediator._subscriptions.update(saved)
        reader.received.clear()
        other.received.clear()

        print("\nwire — a push that arrives while a request waits for its reply\n")
        platform.set_state(DECLARED, "22.0")          # written to the socket, not yet read
        answer = reader.ask({"op": "entity.read", "entity": DECLARED})
        check("the reply is still the reply", answer.get("ok") is True
              and answer.get("state") == "22.0", f"state={answer.get('state')}")
        check("and the push read on the way is handed to on_push, not lost",
              [m["state"] for m in reader.received] == ["22.0"])
        reader.received.clear()

        print("\nP7 — a sandbox that stops reading\n")
        stalled = Sandbox(mediator, "stalled", component(root, "stalled", [DECLARED]))
        stalled.ask({"op": "entity.subscribe", "entity": DECLARED})
        changes = 20_000
        start = time.perf_counter()
        for n in range(changes):
            platform.set_state(DECLARED, str(n))
            if n % 50 == 0:
                reader.drain()            # the honest sandbox keeps up; `stalled` never reads
        elapsed = time.perf_counter() - start
        reader.drain()
        stalled_fd = next(fd for fd, (who, _) in mediator._by_fd.items() if who == "stalled")
        outbox = mediator._out[stalled_fd]
        check(f"{changes} changes with one sandbox never reading: the mediator never blocked",
              True, f"{elapsed:.2f} s")
        check("what it holds for that sandbox is one state per subscribed entity",
              len(outbox.pushes) <= 1, f"{len(outbox.pushes)} queued, "
              f"{mediator.pushes_coalesced.get('stalled', 0)} replaced unsent")
        check("the sandbox that reads got the last value", reader.received
              and reader.received[-1]["state"] == str(changes - 1),
              f"last={reader.received[-1]['state'] if reader.received else None}")
        # The first run of this suite expected one frame here and found 278. Coalescing starts
        # only once `send` says EAGAIN, so before that the kernel's socket buffer takes frames
        # as fast as they come. The bound is that buffer plus one state per entity, not one.
        stalled.drain()
        backlog = len(stalled.received)
        mediator.serve(timeout=0.2)           # writable again: the coalesced state goes out
        stalled.drain()
        check("when the stalled one reads at last it gets a bounded backlog, then the latest",
              backlog < changes // 10 and stalled.received
              and stalled.received[-1]["state"] == str(changes - 1),
              f"{backlog} frames held by the kernel's socket buffer for {changes} changes, "
              f"then the latest")

        print("\n#14 — a respawn has to be granted its subscriptions again\n")
        reader.channel.sock.close()
        mediator.serve(timeout=0.2)
        check("the closed channel's subscriptions are gone",
              "thermal" not in mediator.subscribers(DECLARED),
              f"subscribers={mediator.subscribers(DECLARED)}")
        respawn = Sandbox(mediator, "thermal", component(root, "thermal", [DECLARED]))
        platform.set_state(DECLARED, "23.0")
        respawn.drain()
        check("a respawn receives nothing until it subscribes", respawn.received == [])
        respawn.ask({"op": "entity.subscribe", "entity": DECLARED})
        platform.set_state(DECLARED, "23.5")
        respawn.drain()
        check("and receives again once the subscription is granted anew",
              [m["state"] for m in respawn.received] == ["23.5"])

        print("\nP8 — what one delivered push costs the mediator\n")
        stalled.channel.sock.close()
        mediator.serve(timeout=0.2)
        # Every push written, none coalesced: the reader drains after each one, and only the
        # mediator's own call is timed. The first version of this case let a reader thread race
        # the loop, so 98% of pushes were coalesced and the figure was the cost of replacing a
        # dictionary entry, not of delivering a state.
        count = 5_000
        before = mediator.pushes_sent.get("thermal", 0)
        spent = 0.0
        for n in range(count):
            start = time.perf_counter()
            mediator.push(DECLARED, str(n), {"unit_of_measurement": "°C"})
            spent += time.perf_counter() - start
            respawn.drain()
        per_push = spent / count
        sent = mediator.pushes_sent.get("thermal", 0) - before
        check("every push was written, so the figure is a delivery and not a coalesce",
              sent == count, f"{sent} of {count} written")
        check("one delivered push costs the mediator well under a millisecond, no fsync on it",
              per_push < 1e-3, f"{per_push * 1e6:.1f} µs per push — against 3.67 ms per "
              f"recorded decision (§7.20.1)")

        check("every chain verifies", log.verify() == [])

    print()
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
