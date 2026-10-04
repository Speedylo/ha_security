"""W2 (a): a real integration reaching a device on the home network, confined.

`midea_ac_lan`, unmodified, against `experiments/local_tcp/fake_midea.py` on the Pi's LAN address.
Its manual setup discovers the device by synchronous UDP and connects by blocking TCP, so one run
exercises the raw-socket stack, `network.tcp.local`, and the UDP relay in real namespaces.
Predictions: `notes/w2a_local_tcp_prediction.md`.

Three arms, each against a fresh fake device with its own log:

    A  unconfined                                        the control: is the fake device enough?
    B  confined, network.local declared                  the measurement
    C  confined, nothing declared                        refused, and the device sees nothing

**The fake device's log is the evidence that does not come from the framework.** What it records
is what actually arrived on the LAN, and from which address. In arm B every peer must be the
host's own, because the sandbox has no route and only the mediator can reach the device.

Run:  systemd-run --user --scope -q python3 -m confine.endtoend_local --corpus ~/r2exp/corpus \\
          --python ~/r2exp/ha314/bin/python --json out.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .cgroup import Delegation
from .endtoend_egress import run_confined, run_unconfined
from .preflight import require_ready
from .spawn import become_subreaper

HERE = Path(__file__).resolve().parent
FAKE = HERE.parent.parent / "experiments" / "local_tcp" / "fake_midea.py"
MIDEA_SRC = Path.home() / "r2exp" / "t2" / "midea-src"
LAN = "10.126.83.113"
DEVICE_ID = 151732605161920

SUBJECT = {
    "flow_input": {
        "action": "manually", "name": "fake ac", "device_id": DEVICE_ID, "type": 0xAC,
        "ip_address": LAN, "port": 6444, "protocol": 2, "model": "00000000", "subtype": 0,
        "token": "", "key": "",
    },
    # Long enough for the integration's own device thread to connect and send its queries.
    "settle": 40.0,
}

ARMS = {
    "unconfined": None,
    "confined_declared": {"schema_version": 1,
                          "network": {"local": {"tcp": [6444], "udp": [6445, 20086]}}},
    "confined_undeclared": {"schema_version": 1},
}


def fake_device(log: Path, python: Path) -> subprocess.Popen:
    env = {**os.environ, "PYTHONPATH": str(MIDEA_SRC)}
    proc = subprocess.Popen([str(python), str(FAKE), "--bind", LAN, "--log", str(log),
                             "--seconds", "900"], stdout=subprocess.PIPE, text=True, env=env)
    ready = proc.stdout.readline() if proc.stdout else ""
    if '"ready": true' not in ready:
        proc.kill()
        raise RuntimeError(f"the fake device did not start: {ready!r}")
    return proc


def summarise(arm: str, report: dict, events: list[dict]) -> dict:
    logged = report.get("logged") or []
    local = [d for d in logged if str(d.get("op", "")).startswith(("network.tcp.local",
                                                                 "network.udp",
                                                                 "discover."))]
    return {
        "arm": arm,
        "level": report.get("level"),
        "timed_out": report.get("timed_out"),
        "loaded": report.get("loaded"),
        "flow": (report.get("flow") or {}),
        "error": report.get("error"),
        "device_saw": {
            "udp": sum(e["kind"] == "udp" for e in events),
            "tcp_connections": sum(e["kind"] == "tcp_accept" for e in events),
            "tcp_bytes": sum(e["bytes"] for e in events if e["kind"] == "tcp_data"),
            "peers": sorted({e["peer"] for e in events}),
        },
        "decisions": local,
        "published": report.get("published"),
        "audit_breaks": report.get("audit_breaks"),
        "reconcile": report.get("reconcile"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--python", type=Path, required=True)
    ap.add_argument("--uv", default=str(Path.home() / ".local/bin/uv"))
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    require_ready(deep=False)
    become_subreaper()
    delegation = Delegation.discover()
    uv = args.uv if Path(args.uv).exists() else None
    platform_deps = Path.home() / "r2exp/platform-deps"
    platform_deps = platform_deps if platform_deps.is_dir() else None
    component = args.corpus / "midea_ac_lan"

    results = []
    for arm in args.arms.split(","):
        log = Path(tempfile.mkstemp(suffix=f"-{arm}.jsonl")[1])
        device = fake_device(log, args.python)
        try:
            if ARMS[arm] is None:
                report = run_unconfined(component, "midea_ac_lan", SUBJECT, args.python, uv,
                                        platform_deps)
            else:
                # Five minutes is far beyond setup and the 40 s settle; a confined arm still
                # running then is looping, as both baseline arms did.
                report = run_confined(component, "midea_ac_lan", SUBJECT, arm, ARMS[arm],
                                      args.python, delegation, uv, platform_deps,
                                      max_seconds=300)
        finally:
            time.sleep(1)
            device.terminate()
            device.wait(timeout=10)
        events = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
        log.unlink()
        summary = summarise(arm, report, events)
        results.append(summary)
        saw = summary["device_saw"]
        print(f"  {arm:<20} loaded={summary['loaded']} timed_out={summary['timed_out']}  "
              f"device saw: udp {saw['udp']}, "
              f"tcp {saw['tcp_connections']} conns / {saw['tcp_bytes']} bytes, "
              f"from {saw['peers']}", flush=True)
        counts: dict = {}
        for d in summary["decisions"]:
            key = (d.get("op"), str(d.get("target")), d.get("allowed"), d.get("clause"))
            counts[key] = counts.get(key, 0) + 1
        for (op, target, allowed, clause), n in counts.items():
            print(f"      {n:>6} × {op:<20} {target:<8} allowed={allowed}  {clause}", flush=True)
        if summary["error"]:
            print(f"      error: {str(summary['error'])[:200]}", flush=True)
        # After every arm, not only at the end: the baseline lost arm A's report because the
        # run was stopped during arm C.
        if args.json:
            args.json.write_text(json.dumps(results, indent=2, default=str) + "\n")

    if args.json:
        args.json.write_text(json.dumps(results, indent=2, default=str) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
