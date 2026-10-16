#!/usr/bin/env python3
"""Verification 4.5: fault injection at the mediator, against the criteria in
`notes/fault_injection_prediction.md` (committed before this file).

Cases here run without (A) or a spawned sandbox. FI1 and FI4 need the house and the supervisor, and
are in `faults_pi.sh`. Two cases need a namespace and run in a child re-executed under `unshare`,
which needs no privilege:

    FI3  the audit log on a 24 KiB tmpfs that fills (`unshare -rm`)
    FI8  the egress broker in a network namespace with no route (`unshare -rn`)

Each line is a criterion from the note, judged as written: `ok` held, `FAIL` did not. `..` lines
report what was observed where the note made a prediction rather than a criterion.

Run from v2/framework:  python3 ../verify/faults.py [--json OUT]
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent.parent / "framework"))

from confine import mediator as mediator_module                       # noqa: E402
from confine.audit import AuditLog                                    # noqa: E402
from confine.channel import MAX_FRAME, Channel                        # noqa: E402
from confine.describe import approve_as_experimenter                   # noqa: E402
from confine.egress import EgressBroker                               # noqa: E402
from confine.manifest import Manifest                                 # noqa: E402
from confine.mediator import Decision, Mediator                       # noqa: E402
from confine.platform import ActingPolicy, Platform                   # noqa: E402

results: list[dict] = []


def check(case: str, claim: str, held: bool, detail: str = "") -> None:
    results.append({"case": case, "claim": claim, "held": held, "detail": detail})
    print(f"  {'ok  ' if held else 'FAIL'}  {case:<4} {claim}  — {detail}", flush=True)


def note(case: str, what: str, detail: str = "") -> None:
    results.append({"case": case, "observed": what, "detail": detail})
    print(f"  ..    {case:<4} {what}  — {detail}", flush=True)


def component(root: Path, domain: str, permissions: dict) -> Path:
    directory = root / "custom_components" / domain
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "__init__.py").write_text("# nothing\n")
    (directory / "manifest.json").write_text(json.dumps(
        {"domain": domain, "name": domain, "version": "1.0.0", "requirements": [],
         "permissions": {"schema_version": 1, **permissions}}))
    # F61: F57's gate refuses a registration with no approval on record, and this harness was
    # missed when the others were given this call. The experimenter approves what is on disk.
    approve_as_experimenter(directory)
    return directory


def pair(mediator: Mediator, domain: str, directory: Path) -> tuple[int, Channel, socket.socket]:
    ours, theirs = Channel.pair()
    mediator.register(domain, Channel(ours), component=directory)
    return ours.fileno(), Channel(theirs), theirs


# -- FI2 and FI6: the channel ---------------------------------------------------------------------

def channel_faults(root: Path) -> None:
    print("\nFI2, FI6 — a sandbox that dies mid-frame, and one that declares a frame too large\n")
    directory = component(root, "demo", {"entities": {"read": ["sensor.a"]}})
    platform = Platform()
    platform.seed("sensor.a", "1")
    log = AuditLog(path=root / "fi2.jsonl")
    m = Mediator(policy=ActingPolicy({"demo": Manifest.load(directory, root)}, platform), log=log)
    fd_dies, _, sock_dies = pair(m, "demo", directory)
    fd_big, _, sock_big = pair(m, "demo", directory)
    fd_ok, peer_ok, _ = pair(m, "demo", directory)

    sock_dies.sendall((200).to_bytes(4, "big") + b'{"op": "entity.read", "en')
    sock_dies.close()
    try:
        m._handle_ready(fd_dies)
        raised = None
    except Exception as err:  # noqa: BLE001 — what escapes is the observation
        raised = err
    records = log.records()
    check("FI2", "a frame cut off by the sandbox's death drops only that channel, recorded",
          raised is None and fd_dies not in m._by_fd
          and any(r.get("kind") == "protocol_error" and "truncated" in r.get("detail", "")
                  for r in records),
          f"escaped: {raised!r}; protocol_error records: "
          f"{[r.get('detail') for r in records if r.get('kind') == 'protocol_error']}")

    sock_big.sendall((MAX_FRAME + 1).to_bytes(4, "big"))
    started = time.perf_counter()
    try:
        m._handle_ready(fd_big)
        raised = None
    except Exception as err:  # noqa: BLE001
        raised = err
    took = time.perf_counter() - started
    records = log.records()
    check("FI6", "a frame declaring more than MAX_FRAME is refused before any read, recorded",
          raised is None and fd_big not in m._by_fd and took < 0.5
          and any("exceeds" in r.get("detail", "") for r in records
                  if r.get("kind") == "protocol_error"),
          f"{took * 1000:.1f} ms, nothing waited for; escaped: {raised!r}")

    peer_ok.send({"id": 1, "op": "entity.read", "entity": "sensor.a"})
    m._handle_ready(fd_ok)
    reply = peer_ok.recv()
    check("FI2", "and another sandbox is still served after both",
          reply.get("ok") is True and reply.get("state") == "1", str(reply))
    check("FI2", "the durable log still verifies", log.verify() == [], str(log.verify()[:2]))


# -- FI9: the clock -------------------------------------------------------------------------------

def clock_faults(root: Path) -> None:
    print("\nFI9 — the wall clock jumps an hour back, then two forward, during a flood\n")
    directory = component(root, "flooder", {"entities": {"read": ["sensor.a"]}})
    platform = Platform()
    platform.seed("sensor.a", "1")
    platform.seed("lock.door", "locked")
    log = AuditLog(path=root / "fi9.jsonl")
    m = Mediator(policy=ActingPolicy({"flooder": Manifest.load(directory, root)}, platform),
                 log=log, flood_limit=6, flood_window=10.0)
    fd, peer, _ = pair(m, "flooder", directory)
    real = time.time
    shifts = [0, -3600, -3600, 3600, 3600, 3600]
    answered = 0
    try:
        for shift in shifts:
            time.time = lambda s=shift: real() + s
            peer.send({"id": answered, "op": "entity.read", "entity": "lock.door"})
            m._handle_ready(fd)
            if fd in m._by_fd:
                peer.recv()
                answered += 1
    finally:
        time.time = real
    refusals = [r for r in log.records() if r.get("kind") == "decision"]
    check("FI9", "the cut-off comes after exactly the limit, whatever the wall clock did",
          "flooder" in m.cut_off and len(refusals) == 6 and answered == 5,
          f"{len(refusals)} refusals recorded, {answered} answered before the cut-off")
    check("FI9", "and the audit chain verifies across the jumps", log.verify() == [],
          str(log.verify()[:2]))
    times = [r["time"] for r in log.records()]
    note("FI9", "record times are not monotonic across a jump, as predicted (cosmetic)",
         f"min step {min(b - a for a, b in zip(times, times[1:])):+.0f} s")


# -- FI3: the audit log's disk fills (run inside `unshare -rm`) -----------------------------------

def disk_child(mount: Path, scratch: Path) -> int:
    subprocess.run(["mount", "-t", "tmpfs", "-o", "size=24k", "tmpfs", str(mount)], check=True)
    # Two pages held by a filler, deleted later to free space: a tmpfs cannot be remounted
    # larger from inside a user namespace.
    (mount / "filler").write_bytes(b"x" * 8192)
    print("\nFI3 — the audit log's filesystem fills (24 KiB tmpfs, 8 KiB of it held back)\n")
    directory = component(scratch, "demo", {})
    acted: list[int] = []
    log = AuditLog(path=mount / "audit.jsonl")

    def policy(identity: str, request: dict) -> Decision:
        def act() -> Decision:
            acted.append(log._seq)          # how many records were durable when it ran
            return Decision(True, "acted", clause="/permissions/services/call/0")
        return Decision(True, "granted", clause="/permissions/services/call/0", act=act)

    m = Mediator(policy=policy, log=log)
    fd, peer, _ = pair(m, "demo", directory)
    attempts, escaped = 0, None
    for i in range(200):
        peer.send({"id": i, "op": "service.call", "service": "light.turn_on"})
        attempts += 1
        try:
            m._handle_ready(fd)
            peer.recv()
        except OSError as err:
            escaped = err
            break
    text = (mount / "audit.jsonl").read_bytes()
    lines = text.split(b"\n")
    decisions_on_disk = sum(1 for l in lines if l.endswith(b"}") and b'"decision"' in l)
    check("FI3", "no act ran without its record durable first",
          all(seq >= 1 for seq in acted) and len(acted) == decisions_on_disk,
          f"{len(acted)} acts, {decisions_on_disk} complete decision records; filled after {attempts} requests")
    note("FI3", "what left the mediator when the write failed",
         f"{type(escaped).__name__}: {escaped}" if escaped else "nothing — the write never failed")
    partial = not text.endswith(b"\n")
    note("FI3", "the log's last line after the failure",
         "a partial record, cut off mid-line" if partial else "complete: the failed record left nothing")
    check("FI3", "the log still verifies after the failure", log.verify() == [],
          str([(b.seq, b.kind) for b in log.verify()[:2]]))

    # Space is freed, and the mediator is asked again.
    free_before = os.statvfs(mount).f_bavail
    (mount / "filler").unlink()
    note("FI3", "space freed by deleting the filler", f"{free_before} → {os.statvfs(mount).f_bavail} free blocks")
    try:
        peer.send({"id": 999, "op": "service.call", "service": "light.turn_on"})
        m._handle_ready(fd)
        after = peer.recv()
        note("FI3", "the next request after space is freed", str(after)[:120])
    except Exception as err:  # noqa: BLE001
        note("FI3", "the next request after space is freed", f"{type(err).__name__}: {err}")
    breaks = log.verify()
    check("FI3", "and the log verifies once records are written again", breaks == [],
          str([(b.seq, b.kind, b.detail[:40]) for b in breaks[:3]]))
    print("RESULTS " + json.dumps(results))
    return 0


# -- FI8: the network is gone (run inside `unshare -rn`) ------------------------------------------

def net_child(scratch: Path) -> int:
    print("\nFI8 — an egress request with no network at all (empty network namespace)\n")
    directory = component(scratch, "demo", {"network": {"egress": ["api.example.org:443"]}})
    broker = EgressBroker(resolver=lambda host, port, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))])
    log = AuditLog(path=scratch / "fi8.jsonl")
    m = Mediator(policy=ActingPolicy({"demo": Manifest.load(directory, scratch)}, Platform(),
                                     broker=broker), log=log)
    fd, peer, _ = pair(m, "demo", directory)
    peer.send({"id": 1, "op": "network.egress", "host": "api.example.org", "port": 443})
    started = time.perf_counter()
    m._handle_ready(fd)
    reply = peer.recv()
    took = time.perf_counter() - started
    check("FI8", "refused with a stated reason, within the connect timeout",
          reply.get("ok") is False and took < broker.connect_timeout + 1,
          f"{took * 1000:.0f} ms: {reply.get('reason')}")
    records = [r for r in log.records() if r.get("kind") == "decision"]
    check("FI8", "recorded as granted, then refused when acting found no route",
          [r["allowed"] for r in records] == [True, False],
          str([(r["allowed"], r["reason"][:50]) for r in records]))
    print("RESULTS " + json.dumps(results))
    return 0


# -------------------------------------------------------------------------------------------------

def in_namespace(flags: str, *args: str) -> list[dict]:
    proc = subprocess.run(["unshare", flags, sys.executable, str(HERE), *args],
                          capture_output=True, text=True, timeout=120)
    sys.stdout.write("".join(l + "\n" for l in proc.stdout.splitlines() if not l.startswith("RESULTS ")))
    if proc.returncode != 0 or "RESULTS " not in proc.stdout:
        print(proc.stderr[-1500:])
        return [{"case": args[0], "claim": "the namespaced case ran", "held": False,
                 "detail": proc.stderr[-300:]}]
    return json.loads(proc.stdout.split("RESULTS ", 1)[1].splitlines()[0])


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "disk":
        return disk_child(Path(sys.argv[2]), Path(sys.argv[3]))
    if len(sys.argv) > 1 and sys.argv[1] == "net":
        return net_child(Path(sys.argv[2]))
    out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    with tempfile.TemporaryDirectory(prefix="faults-") as tmp:
        root = Path(tmp)
        channel_faults(root / "ch")
        clock_faults(root / "clock")
        (root / "mnt").mkdir()
        results.extend(in_namespace("-rm", "disk", str(root / "mnt"), str(root / "disk")))
        results.extend(in_namespace("-rn", "net", str(root / "net")))
    judged = [r for r in results if "held" in r]
    failed = [r for r in judged if not r["held"]]
    print(f"\n{len(judged) - len(failed)}/{len(judged)} criteria held")
    if out:
        Path(out).write_text(json.dumps(results, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
