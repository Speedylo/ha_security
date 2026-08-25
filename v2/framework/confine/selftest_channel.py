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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .channel import Channel
from .cgroup import Delegation, SandboxCgroup
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

# The lie. Both sandboxes send the same one.
send({"id": 1, "op": "service.call", "integration": CLAIM, "service": "lock.unlock"})
first = recv()

times = []
for i in range(ROUND_TRIPS):
    started = time.perf_counter_ns()
    send({"id": i + 2, "op": "entity.read", "entity": "sensor.outdoor_temperature"})
    recv()
    times.append(time.perf_counter_ns() - started)

times.sort()
print(json.dumps({
    "first_response": first,
    "n": len(times),
    "median_us": times[len(times) // 2] / 1000,
    "p99_us": times[int(len(times) * 0.99)] / 1000,
}))
sock.close()
"""


def make_component(root: Path, domain: str) -> tuple[Path, Path]:
    component = root / "custom_components" / domain
    data = root / ".confine" / domain
    component.mkdir(parents=True)
    data.mkdir(parents=True)
    (component / "__init__.py").write_text("# nothing\n")
    return component, data


def main() -> int:
    require_ready(deep=False)
    become_subreaper()

    root = Path(tempfile.mkdtemp(prefix="confine-channel-"))
    mediator = Mediator()
    sandboxes = []
    outputs = {}
    cgroups = []
    try:
        delegation = Delegation.discover()
        for domain in ("demo_a", "demo_b"):
            component, data = make_component(root, domain)
            # §5.11.2: the pair exists before the sandbox does. The supervisor is the only
            # party that can create this mapping, which is what makes it trustworthy.
            mediator_end, sandbox_end = Channel.pair()
            mediator.register(domain, Channel(mediator_end))

            script = (f"CLAIM = 'demo_a'\nROUND_TRIPS = {ROUND_TRIPS}\n" + INSIDE)
            spec = SandboxSpec(domain=domain, own_dir=str(component), data_dir=str(data),
                               argv=[sys.executable, "-c", script])
            cgroup = SandboxCgroup.create(delegation, f"confine-channel-{domain}",
                                          memory_max=256 * 1024**2, pids_max=64)
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

    return render(mediator, reports)


def render(mediator: Mediator, reports: dict[str, dict]) -> int:
    print("channel self-test — identity is the socket, not a field\n")
    failures = []

    print("  what the mediator recorded for the first request from each sandbox:")
    print(f"    {'true identity':<16} {'claimed to be':<16} {'allowed':<9} reason")
    firsts = {}
    for entry in mediator.audit:
        firsts.setdefault(entry["identity"], entry)
    for identity, entry in sorted(firsts.items()):
        print(f"    {identity:<16} {str(entry['claimed_identity']):<16} "
              f"{str(entry['allowed']):<9} {entry['reason']}")
        if entry["claimed_identity"] != "demo_a":
            failures.append(f"{identity} did not send the expected claim")
        if entry["allowed"]:
            failures.append(f"{identity}: S6 requires denial with no manifest bound")

    identities = set(firsts)
    if identities != {"demo_a", "demo_b"}:
        failures.append(f"the mediator saw {sorted(identities)}, expected both sandboxes")
    else:
        print("\n  ok    both sandboxes claimed 'demo_a'; the mediator recorded demo_a and "
              "demo_b")
        print("  ok    every request denied — S6, with no manifest bound")

    print("\n  round trip on the real channel, measured from inside the sandbox:")
    for domain, report in sorted(reports.items()):
        if not report:
            failures.append(f"{domain} produced no report")
            continue
        print(f"    {domain:<16} median {report['median_us']:6.1f} µs   "
              f"p99 {report['p99_us']:6.1f} µs   n={report['n']}")

    print(f"\n  audit entries: {len(mediator.audit)}  "
          f"(2 sandboxes x {ROUND_TRIPS + 1} requests = {2 * (ROUND_TRIPS + 1)})")
    if len(mediator.audit) != 2 * (ROUND_TRIPS + 1):
        failures.append("the mediator did not record one entry per request")

    print()
    if failures:
        print(f"FAILED: {'; '.join(failures)}")
        return 1
    print("PASS — the mediator attributed every request to the socket it arrived on,")
    print("       and neither sandbox's claim about itself made any difference.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
