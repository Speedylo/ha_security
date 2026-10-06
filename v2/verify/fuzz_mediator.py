#!/usr/bin/env python3
"""Verification 4.7: every operation, every field the mediator reads, every awkward JSON value.

The manual review found a sandbox-supplied `timeout` that crashed the mediator. This looks for the
rest of that class by brute force: each request is one operation with one field set to one odd
value, sent through a mediator whose manifest grants every capability (so the request reaches the
code that acts, not just the policy). Anything that escapes `_handle_ready` is a crash of the
mediator, and with it of every sandbox it serves.

Run from v2/framework:  python3 ../verify/fuzz_mediator.py [--json OUT]
"""

from __future__ import annotations

import json
import socket
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "framework"))

from confine.channel import Channel                       # noqa: E402
from confine.egress import EgressBroker                   # noqa: E402
from confine.manifest import OPERATIONS, Manifest         # noqa: E402
from confine.mediator import Mediator                     # noqa: E402
from confine.platform import ActingPolicy, Platform       # noqa: E402
from confine.udp_relay import UdpRelay                    # noqa: E402

OPS = sorted(OPERATIONS) + ["entity.publish", "entity.command_result", "no.such.op"]
FIELDS = ["entity", "service", "data", "host", "port", "address", "timeout", "state",
          "attributes", "event", "domain", "service_name", "command", "ok", "error", "unique_id"]
VALUES = [None, [], {}, 0, -1, 10 ** 30, 1e308, float("nan"), True, "", "x" * 100_000,
          "../../secrets.yaml", ["sensor.a"], {"a": 1}, "sensor.a", "lock.unlock"]
BASE = {"entity": "sensor.a", "service": "light.turn_on", "host": "api.example.org",
        "port": 6666, "address": "127.0.0.1", "data": "", "timeout": 0.01, "state": "1"}

PERMISSIONS = {
    "entities": {"read": ["sensor.*"], "subscribe": ["sensor.*"], "write": ["sensor.*"]},
    "services": {"call": ["light.turn_on"]},
    "events": {"subscribe": ["x"], "fire": ["x"]},
    "network": {"egress": ["api.example.org:443"],
                "local": {"udp": [6666], "tcp": [6668]},
                "discover": {"scan": [6666], "listen": [6666]}},
}


def mediator(root: Path) -> tuple[Mediator, int, Channel]:
    d = root / "custom_components" / "fuzz"
    d.mkdir(parents=True, exist_ok=True)
    (d / "__init__.py").write_text("")
    (d / "manifest.json").write_text(json.dumps(
        {"domain": "fuzz", "name": "f", "version": "1",
         "permissions": {"schema_version": 1, **PERMISSIONS}}))
    platform = Platform()
    platform.seed("sensor.a", "1")
    broker = EgressBroker(resolver=lambda host, port, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))])
    m = Mediator(policy=ActingPolicy({"fuzz": Manifest.load(d, root)}, platform,
                                     broker=broker, relay=UdpRelay(allow_loopback=True)),
                 flood_limit=10 ** 9)
    ours, theirs = Channel.pair()
    m.register("fuzz", Channel(ours))
    return m, ours.fileno(), Channel(theirs)


def main() -> int:
    out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    escapes: dict[tuple, str] = {}
    sent = 0
    with tempfile.TemporaryDirectory() as tmp:
        m, fd, peer = mediator(Path(tmp))
        for op in OPS + [None, 7, ["entity.read"]]:
            for field in FIELDS:
                for value in VALUES:
                    request = {"id": sent, "op": op, **BASE, field: value}
                    sent += 1
                    try:
                        peer.send(request)
                    except Exception:  # noqa: BLE001 — unsendable (frame too large): not a case
                        continue
                    try:
                        m._handle_ready(fd)
                        if fd in m._by_fd:
                            peer.recv()
                    except Exception as err:  # noqa: BLE001 — the finding
                        key = (str(op), field, type(err).__name__)
                        escapes.setdefault(key, f"{value!r:.40}: {err!s:.120}")
                    if fd not in m._by_fd:
                        m, fd, peer = mediator(Path(tmp) / str(sent))
    print(f"{sent} requests; {len(escapes)} distinct (operation, field, exception) escapes")
    for (op, field, kind), example in sorted(escapes.items()):
        print(f"  ESCAPE  {op:<22} {field:<12} {kind:<18} {example}")
    if out:
        Path(out).write_text(json.dumps([{"op": k[0], "field": k[1], "exception": k[2],
                                          "example": v} for k, v in sorted(escapes.items())],
                                        indent=1))
    return 1 if escapes else 0


if __name__ == "__main__":
    sys.exit(main())
