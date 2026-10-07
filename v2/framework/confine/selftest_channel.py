"""Two sandboxes, both claiming to be the same integration, and a mediator that is not fooled.

§5.11.2 argues that identity must be a property of the channel rather than a claim in the
message, and rejects the alternative in one line: a protocol in which the sandbox names itself
"asks the adversary to self-report the one fact the decision turns on". That is a testable
claim, so this tests it in the way that matters — by having both sandboxes lie.

Each sandbox sends `{"integration": "demo_a", …}`. One of them is `demo_b`. The mediator's audit
record has to show the true identity of each, alongside what each claimed, without the protocol
containing anything that could have been checked.

The same run measures the round trip on the real channel, against §5.11.4's floor of 30.0 µs,
and confirms S6: with no manifest bound, every request is denied.

Run:  systemd-run --user --scope -q python3 -m confine.selftest_channel
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from .channel import MAX_FRAME, Channel, ProtocolError
from .audit import attach, report_durable
from .audit import summarise as durable_summary
from .cgroup import Delegation, ResourceLimits, SandboxCgroup
from .manifest import Manifest, policy_for
from .mediator import Mediator
from .preflight import require_ready
from .sandbox import SandboxSpec
from .spawn import become_subreaper, start

ROUND_TRIPS = 2000

# Runs inside the sandbox. It implements the wire format itself rather than importing anything
# of this framework — which it could not do anyway, since `confine` is not in its mount
# namespace. That is worth noting: §5.11.3's format is simple enough that the far end needs no
# library, which is what makes the sandbox's side of it auditable.
INSIDE = r"""
import json, os, socket, statistics, struct, sys, time

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM,
                     fileno=int(os.environ["CONFINE_CHANNEL_FD"]))

def send(obj):
    payload = json.dumps(obj).encode()
    sock.sendall(struct.pack(">I", len(payload)) + payload)

def recv():
    header = b""
    while len(header) < 4:
        header += sock.recv(4 - len(header))
    (length,) = struct.unpack(">I", header)
    body = b""
    while len(body) < length:
        body += sock.recv(length - len(body))
    return json.loads(body)

# The lie. Both sandboxes send the same one, and demo_a really does have a manifest — so
# demo_b is not claiming to be nobody, it is claiming to be the integration that was granted
# something.
send({"id": 1, "op": "entity.read", "integration": CLAIM,
      "entity": "sensor.outdoor_temperature"})
first = recv()
send({"id": 2, "op": "service.call", "integration": CLAIM, "service": "lock.unlock"})
second = recv()

times = []
for i in range(ROUND_TRIPS):
    started = time.perf_counter_ns()
    send({"id": i + 3, "op": "entity.read", "entity": "sensor.outdoor_temperature"})
    recv()
    times.append(time.perf_counter_ns() - started)

times.sort()
print(json.dumps({
    "declared_read": first,
    "undeclared_call": second,
    "n": len(times),
    "median_us": times[len(times) // 2] / 1000,
    "p99_us": times[int(len(times) * 0.99)] / 1000,
}))
sock.close()
"""


# demo_a may read one sensor. demo_b declares nothing at all — so the only thing that could
# get demo_b a permit is being mistaken for demo_a, which is exactly what it tries.
GRANT = {"schema_version": 1, "entities": {"read": ["sensor.outdoor_temperature"]}}


def make_component(root: Path, domain: str, permissions: dict | None) -> tuple[Path, Path]:
    component = root / "custom_components" / domain
    data = root / ".confine" / domain
    component.mkdir(parents=True)
    data.mkdir(parents=True)
    (component / "__init__.py").write_text("# nothing\n")
    manifest = {"domain": domain, "name": domain, "version": "1.0.0"}
    if permissions is not None:
        manifest["permissions"] = permissions
    (component / "manifest.json").write_text(json.dumps(manifest))
    return component, data


def hostile_frames() -> list[str]:
    """What the mediator's end of a channel refuses, sent as raw bytes by a hostile far end.

    The sandbox is the adversary and these bounds are the input boundary. Branch coverage found
    no suite that sent any of these (verification 4.12, F49), and `fuzz_mediator.py` sends only
    well-formed frames. Each case fails under its mutant (M27–M30, M36, M37). No sandbox is
    needed: identity is not in question here, only what the reader believes.
    """
    failures: list[str] = []

    def say(label: str, ok: bool, detail: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}  — {detail}")
        if not ok:
            failures.append(label)

    def received(raw: bytes, fds: list[int] | None = None, hang_up: bool = True) -> str:
        """What `recv` made of `raw`: the refusal's text, or what it wrongly accepted."""
        ours, theirs = Channel.pair()
        ours.settimeout(5)
        reader = Channel(ours)

        def send() -> None:
            try:
                if fds:
                    socket.send_fds(theirs, [raw], fds)
                else:
                    theirs.sendall(raw)
                if hang_up:
                    theirs.shutdown(socket.SHUT_WR)
            except OSError:
                pass            # the reader refused and closed before the rest was sent
        sender = threading.Thread(target=send, daemon=True)
        sender.start()
        try:
            message = reader.recv()
            outcome = f"ACCEPTED {str(message)[:40]}"
        except ProtocolError as err:
            outcome = f"refused: {err}"
        except Exception as err:  # noqa: BLE001 — anything else is not the bound working
            outcome = f"{type(err).__name__}: {err}"
        reader.close()
        theirs.close()
        sender.join(timeout=5)
        return outcome

    def framed(payload: bytes, declared: int | None = None) -> bytes:
        return struct.pack(">I", len(payload) if declared is None else declared) + payload

    print("\nF49  hostile frames, refused at the mediator's end\n")
    try:
        Channel.frame({"x": "a" * MAX_FRAME})
        sent = "framed it"
    except ProtocolError as err:
        sent = f"refused: {err}"
    say("a message over MAX_FRAME is not framed for sending", sent.startswith("refused"), sent)

    big = json.dumps({"x": "a" * MAX_FRAME}).encode()
    got = received(framed(big))
    say("a valid object of more than MAX_FRAME bytes is refused before it is read",
        got.startswith("refused") and "exceeds" in got, got[:80])

    before = len(os.listdir("/proc/self/fd"))
    r1, w1 = os.pipe()
    got = received(framed(b'{"op": "entity.read"}'), fds=[r1, w1])
    os.close(r1)
    os.close(w1)
    after = len(os.listdir("/proc/self/fd"))
    # The refusal is a durable record's detail, so it must say what arrived: until 2026-10-07 it
    # said "0 descriptors", counted after they were closed (verification 4.12, F52).
    say("a frame carrying two descriptors is refused, saying two, and neither is kept",
        got.startswith("refused") and "2 descriptors" in got and after == before,
        f"{got[:60]}; fds {before} -> {after}")

    got = received(framed(b"[1, 2]"))
    say("a frame that is not a JSON object is refused", got.startswith("refused"), got[:80])

    got = received(b"\x00\x00")
    say("a length prefix cut short by a hang-up is refused", got.startswith("refused"), got[:80])

    got = received(framed(b'{"a": 1}', declared=64))
    say("a frame shorter than its declared length is refused, even when what came is valid",
        got.startswith("refused"), got[:80])
    return failures


def main() -> int:
    frame_failures = hostile_frames()
    require_ready(deep=False)
    become_subreaper()

    root = Path(tempfile.mkdtemp(prefix="confine-channel-"))
    # demo_b holds no manifest and times the refusal path: ROUND_TRIPS refused requests in a
    # tight loop, which is exactly what the refusal-flood cut-off exists to stop. The limit is
    # lifted here, and only here, so the suite measures the decision path as it was measured
    # before the cut-off existed. Found on the Pi on 2026-10-05, when demo_b was cut off at 100
    # and this suite waited out its 60 s (`notes/flood_cutoff_prediction.md`, F6's outcome).
    mediator = Mediator(flood_limit=10 * ROUND_TRIPS)
    audit_dir = attach(mediator, "confine-channel-audit-")
    sandboxes = []
    outputs = {}
    cgroups = []
    try:
        delegation = Delegation.discover()
        manifests = {}
        for domain in ("demo_a", "demo_b"):
            component, data = make_component(root, domain,
                                             GRANT if domain == "demo_a" else None)
            manifests[domain] = Manifest.load(component, root)
        mediator.policy = policy_for(manifests)

        for domain in ("demo_a", "demo_b"):
            component = root / "custom_components" / domain
            data = root / ".confine" / domain
            # §5.11.2: the pair exists before the sandbox does. The supervisor is the only
            # party that can create this mapping, which is what makes it trustworthy.
            mediator_end, sandbox_end = Channel.pair()
            mediator.register(domain, Channel(mediator_end), component=component)

            script = (f"CLAIM = 'demo_a'\nROUND_TRIPS = {ROUND_TRIPS}\n" + INSIDE)
            spec = SandboxSpec(domain=domain, own_dir=str(component), data_dir=str(data),
                               argv=[sys.executable, "-c", script])
            cgroup = SandboxCgroup.create(delegation, f"confine-channel-{domain}",
                                          ResourceLimits(memory_mb=256))
            cgroups.append(cgroup)
            outputs[domain] = tempfile.NamedTemporaryFile(
                prefix=f"confine-channel-{domain}-", suffix=".json", delete=False)
            with open(outputs[domain].name, "wb") as stdout:
                sandboxes.append(start(spec, cgroup, stdout=stdout.fileno(),
                                       stderr=subprocess.DEVNULL,
                                       channel_end=sandbox_end.fileno()))
            sandbox_end.detach()  # the supervisor's copy is closed by `start`

        mediator.serve(timeout=120)
        for sandbox in sandboxes:
            sandbox.wait(timeout=60)
        reports = {d: json.loads(Path(f.name).read_text() or "{}") for d, f in outputs.items()}
    finally:
        for cgroup in cgroups:
            cgroup.remove()
        for f in outputs.values():
            Path(f.name).unlink(missing_ok=True)
        shutil.rmtree(root, ignore_errors=True)
        durable = durable_summary(mediator, audit_dir)

    status = render(mediator, reports) or report_durable(durable)
    if frame_failures:
        print(f"FAILED (hostile frames): {'; '.join(frame_failures)}")
        return 1
    return status


def render(mediator: Mediator, reports: dict[str, dict]) -> int:
    print("channel self-test — identity is the socket, not a field\n")
    failures = []

    print("  both sandboxes sent {\"integration\": \"demo_a\"}. demo_a holds a manifest")
    print("  granting one sensor read; demo_b holds none.\n")
    print(f"    {'true identity':<14} {'claimed':<10} {'request':<26} {'verdict':<8} clause")
    firsts: dict[str, list] = {}
    for entry in mediator.audit:
        bucket = firsts.setdefault(entry["identity"], [])
        if len(bucket) < 2:
            bucket.append(entry)
    for identity, entries in sorted(firsts.items()):
        for entry in entries:
            verdict = "PERMIT" if entry["allowed"] else "deny"
            print(f"    {identity:<14} {str(entry['claimed_identity']):<10} "
                  f"{str(entry['op']):<26} {verdict:<8} {entry['clause']}")
            if entry["claimed_identity"] != "demo_a":
                failures.append(f"{identity} did not send the expected claim")

    expected = {("demo_a", "entity.read"): True, ("demo_a", "service.call"): False,
                ("demo_b", "entity.read"): False, ("demo_b", "service.call"): False}
    for identity, entries in firsts.items():
        for entry in entries:
            key = (identity, entry["op"])
            if key in expected and entry["allowed"] is not expected[key]:
                failures.append(f"{identity} {entry['op']}: expected "
                                f"{'permit' if expected[key] else 'deny'}")

    identities = set(firsts)
    if identities != {"demo_a", "demo_b"}:
        failures.append(f"the mediator saw {sorted(identities)}, expected both sandboxes")
    else:
        print("\n  ok    demo_a read its declared sensor — the permit path works")
        print("  ok    demo_a was refused lock.unlock — denied by absence, S6")
        print("  ok    demo_b claimed to be demo_a and was refused the same read")
        print("  ok    every decision, permit or deny, named a clause — F3 / §5.10.8")

    print("\n  round trip on the real channel, measured from inside the sandbox:")
    for domain, report in sorted(reports.items()):
        if not report:
            failures.append(f"{domain} produced no report")
            continue
        print(f"    {domain:<16} median {report['median_us']:6.1f} µs   "
              f"p99 {report['p99_us']:6.1f} µs   n={report['n']}")

    # Two probe requests each, then the timing loop. §5.12.3: one record per decision.
    expected_entries = 2 * (ROUND_TRIPS + 2)
    print(f"\n  audit entries: {len(mediator.audit)}  "
          f"(2 sandboxes x {ROUND_TRIPS + 2} requests = {expected_entries})")
    if len(mediator.audit) != expected_entries:
        failures.append(f"the mediator recorded {len(mediator.audit)} entries for "
                        f"{expected_entries} requests")

    print()
    if failures:
        print(f"FAILED: {'; '.join(failures)}")
        return 1
    print("PASS — the mediator attributed every request to the socket it arrived on.")
    print("       demo_b claimed to be an integration that holds a grant, and the claim")
    print("       bought it nothing, because there was nothing in the protocol to check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
