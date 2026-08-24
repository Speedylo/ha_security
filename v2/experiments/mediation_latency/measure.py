#!/usr/bin/env python3
"""What does one mediated request cost?

§5.11 routes every mediated request over a Unix domain socket between the sandbox and the
mediator. N1 requires the overhead be small enough not to change how the platform is used,
and "small" is not a claim a design chapter should make without a number.

This measures the **floor**: a request/response round trip over the same socket type, with
JSON framing of a realistic message, and nothing else happening. A real mediated call adds
the manifest check and the audit write on top; those are Chapter 6's to measure. The floor is
what says whether the architecture is viable at all, and it is the figure a reader should be
given before being asked to accept the design.

Two shapes are timed because §5.11 uses both:

    request/response   the sandbox asks, the mediator answers  (entity read, service call)
    push               the mediator sends without being asked   (a mirrored state update)

Run:  python3 measure.py [--iterations 20000] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import platform
import socket
import statistics
import struct
import sys
import time
from pathlib import Path

# A realistic mediated request and its reply, so framing and parsing cost is included
# rather than measured away with an empty payload.
REQUEST = {
    "v": 1, "id": 1234, "op": "entity.read",
    "target": "sensor.outdoor_temperature",
}
REPLY = {
    "v": 1, "id": 1234, "ok": True,
    "state": "17.4",
    "attributes": {"unit_of_measurement": "°C", "device_class": "temperature"},
    "clause": "/permissions/entities/read/0",
}


def send(sock: socket.socket, obj: dict) -> None:
    """Length-prefixed JSON: the framing §5.11 specifies."""
    body = json.dumps(obj).encode()
    sock.sendall(struct.pack("!I", len(body)) + body)


def recv(sock: socket.socket) -> dict | None:
    header = sock.recv(4, socket.MSG_WAITALL)
    if len(header) < 4:
        return None
    (length,) = struct.unpack("!I", header)
    return json.loads(sock.recv(length, socket.MSG_WAITALL))


def mediator(sock: socket.socket, iterations: int) -> None:
    """Stand-in for the mediator: answer every request, then push the same count."""
    for _ in range(iterations):
        if recv(sock) is None:
            return
        send(sock, REPLY)
    for _ in range(iterations):
        send(sock, REPLY)
    sock.close()


def percentiles(samples: list[float]) -> dict:
    s = sorted(samples)
    def pct(p: float) -> float:
        return s[min(len(s) - 1, int(len(s) * p))]
    return {
        "n": len(s),
        "mean_us": round(statistics.fmean(s), 1),
        "median_us": round(pct(0.50), 1),
        "p95_us": round(pct(0.95), 1),
        "p99_us": round(pct(0.99), 1),
        "max_us": round(s[-1], 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=20000)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    # socketpair, not a bound path: §5.11's channel is an inherited file descriptor, and
    # measuring the thing the design actually uses matters more than convenience here.
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)

    proc = mp.Process(target=mediator, args=(child, args.iterations), daemon=True)
    proc.start()
    child.close()

    print(f"mediation latency — {platform.machine()}, Python {platform.python_version()}, "
          f"{args.iterations} iterations")

    # Warm up: first calls pay import and allocation costs that steady state does not.
    for _ in range(200):
        send(parent, REQUEST)
        recv(parent)

    round_trip: list[float] = []
    for i in range(args.iterations - 200):
        t = time.perf_counter_ns()
        send(parent, REQUEST)
        recv(parent)
        round_trip.append((time.perf_counter_ns() - t) / 1000)

    push: list[float] = []
    for _ in range(args.iterations):
        t = time.perf_counter_ns()
        if recv(parent) is None:
            break
        push.append((time.perf_counter_ns() - t) / 1000)

    parent.close()
    proc.join(timeout=5)

    rt, pu = percentiles(round_trip), percentiles(push)
    print(f"\n{'shape':<22} {'median':>9} {'mean':>9} {'p95':>9} {'p99':>9}")
    print(f"{'request/response':<22} {rt['median_us']:>8.1f}µ {rt['mean_us']:>8.1f}µ "
          f"{rt['p95_us']:>8.1f}µ {rt['p99_us']:>8.1f}µ")
    print(f"{'push (receive only)':<22} {pu['median_us']:>8.1f}µ {pu['mean_us']:>8.1f}µ "
          f"{pu['p95_us']:>8.1f}µ {pu['p99_us']:>8.1f}µ")

    per_sec = 1_000_000 / rt["median_us"]
    print(f"\n  a sandbox can make about {per_sec:,.0f} mediated requests/second at the median")
    print(f"  a 30-second polling integration reading 10 entities spends "
          f"{10 * rt['median_us'] / 1000:.2f} ms per cycle in mediation")

    result = {
        "host": {"machine": platform.machine(), "node": platform.node(),
                 "python": platform.python_version()},
        "iterations": args.iterations,
        "request_response_us": rt,
        "push_us": pu,
        "note": "floor only: excludes manifest evaluation and audit write",
    }
    if args.json:
        args.json.write_text(json.dumps(result, indent=2) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
