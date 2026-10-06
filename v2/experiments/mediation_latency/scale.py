#!/usr/bin/env python3
"""What does a mediated request cost when twenty-six sandboxes are asking?

§6.5.3 measured two clients and found the median moved 19% while p99 moved **85%** — queueing,
not work. §6.3.2's budget is **26 sandboxes**, and two clients say nothing about twenty-six.
§7.6's P4 predicted the shape before this ran: *median within 2× of the single-client figure,
p99 an order of magnitude worse.*

**This measures the real mediator, not the socket floor.** `experiments/mediation_latency/
measure.py` timed framing alone, which is the right figure to establish viability and the wrong
one for this question. Here every request goes through `confine.Mediator` with a real `Manifest`
bound and `acting_policy` deciding it, so what is timed is identity, decision, clause and reply
— steps 1, 2, 3 and 5 of §5.11.3. The audit write is **not** included, which §6.8.3 flags as
the open question and §7.10 schedules separately.

The mediator is single-threaded by design (§5.11.2: identity is the socket, and one selector
loop owns every socket), so contention here is queueing behind a serial server. That is the
property under test.

Run:  systemd-run --user --scope -q python3 scale.py --json results/pi5_scale.json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "framework"))

from confine.channel import Channel                      # noqa: E402
from confine.manifest import Manifest                    # noqa: E402
from confine.mediator import Mediator                    # noqa: E402
from confine.platform import Platform, acting_policy     # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "framework"))
from confine.provenance import record_run  # noqa: E402  (F14)

ENTITY = "sensor.outdoor_temperature"
GRANT = {"schema_version": 1, "entities": {"read": [ENTITY]}}


def client(sock_fd: int, iterations: int, out_fd: int) -> None:
    """One sandbox's side: ask, wait, record. Exits, which closes its channel."""
    import socket as _socket

    sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM, fileno=sock_fd)
    samples: list[float] = []
    payload = json.dumps({"op": "entity.read", "entity": ENTITY}).encode()
    frame = struct.pack(">I", len(payload)) + payload
    for _ in range(iterations):
        start = time.perf_counter_ns()
        sock.sendall(frame)
        header = b""
        while len(header) < 4:
            chunk = sock.recv(4 - len(header))
            if not chunk:
                break
            header += chunk
        if len(header) < 4:
            break
        (length,) = struct.unpack(">I", header)
        body = b""
        while len(body) < length:
            chunk = sock.recv(length - len(body))
            if not chunk:
                break
            body += chunk
        samples.append((time.perf_counter_ns() - start) / 1000.0)   # microseconds
    sock.close()
    os.write(out_fd, json.dumps(samples).encode())
    os.close(out_fd)
    os._exit(0)


def percentiles(samples: list[float]) -> dict:
    samples = sorted(samples)

    def pct(p: float) -> float:
        if not samples:
            return 0.0
        return samples[min(len(samples) - 1, int(p * len(samples)))]

    return {"n": len(samples),
            "median": round(statistics.median(samples), 1) if samples else 0.0,
            "p95": round(pct(0.95), 1), "p99": round(pct(0.99), 1),
            "max": round(samples[-1], 1) if samples else 0.0}


def run(concurrency: int, iterations: int, manifest: Manifest) -> dict:
    platform_stub = Platform()
    platform_stub.seed(ENTITY, "17.4", unit_of_measurement="°C")
    mediator = Mediator()
    mediator.policy = acting_policy({f"s{i}": manifest for i in range(concurrency)},
                                    platform_stub)

    children, readers = [], []
    for index in range(concurrency):
        mediator_end, sandbox_end = Channel.pair()
        mediator.register(f"s{index}", Channel(mediator_end))
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            client(sandbox_end.detach(), iterations, write_fd)
        os.close(write_fd)
        sandbox_end.close()
        children.append(pid)
        readers.append(read_fd)

    started = time.perf_counter()
    mediator.serve(timeout=300)
    elapsed = time.perf_counter() - started

    samples: list[float] = []
    for read_fd in readers:
        with os.fdopen(read_fd, "rb") as handle:
            raw = handle.read()
        if raw:
            samples += json.loads(raw.decode())
    for pid in children:
        os.waitpid(pid, 0)

    result = percentiles(samples)
    result["concurrency"] = concurrency
    result["wall_s"] = round(elapsed, 2)
    result["throughput_rps"] = round(len(samples) / elapsed) if elapsed else 0
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=2000,
                    help="requests per client; total work grows with concurrency, which is "
                         "the point — a real installation's request rate rises with the "
                         "number of integrations, it is not divided among them")
    ap.add_argument("--levels", default="1,2,4,8,16,26",
                    help="26 is §6.3.2's measured budget")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent / "_manifest"
    component = root / "custom_components" / "bench"
    component.mkdir(parents=True, exist_ok=True)
    (component / "__init__.py").write_text("# bench\n")
    (component / "manifest.json").write_text(json.dumps(
        {"domain": "bench", "name": "bench", "version": "1.0.0", "permissions": GRANT}))
    manifest = Manifest.load(component, root)

    print(f"mediated request latency against sandbox count — {platform.machine()}, "
          f"Python {platform.python_version()}")
    print(f"  real mediator: identity, manifest decision, clause, reply. No audit write.\n")
    print(f"  {'sandboxes':>10}{'median µs':>12}{'p95':>10}{'p99':>10}{'max':>10}"
          f"{'req/s':>10}")

    results = []
    baseline = None
    for level in [int(x) for x in args.levels.split(",")]:
        row = run(level, args.iterations, manifest)
        results.append(row)
        if baseline is None:
            baseline = row
        print(f"  {row['concurrency']:>10}{row['median']:>12}{row['p95']:>10}"
              f"{row['p99']:>10}{row['max']:>10}{row['throughput_rps']:>10}")

    last = results[-1]
    print(f"\n  §7.6 P4 predicted: median within 2× of one client, p99 an order of magnitude "
          f"worse.")
    print(f"    median  {baseline['median']} → {last['median']} µs  "
          f"({last['median'] / baseline['median']:.1f}×)")
    print(f"    p99     {baseline['p99']} → {last['p99']} µs  "
          f"({last['p99'] / baseline['p99']:.1f}×)")

    if args.json:
        args.json.write_text(json.dumps(
            {"host": platform.machine(), "python": platform.python_version(),
             "iterations_per_client": args.iterations, "levels": results}, indent=2) + "\n")
        record_run(args.json)  # F14: how this result was produced, beside it
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
