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
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .cgroup import Delegation
from .endtoend_egress import run_confined, run_unconfined
from .real_house import house_stopped
from .preflight import require_ready
from .spawn import become_subreaper
from .provenance import record_run

HERE = Path(__file__).resolve().parent
FAKES = HERE.parent.parent / "experiments" / "local_tcp"
MIDEA_SRC = Path.home() / "r2exp" / "t2" / "midea-src"


def _lan_address() -> str:
    """This host's address on the home network: the source of a route to a LAN-wide address.

    Was the literal `10.126.83.113` until 2026-10-25, when DHCP had moved the Pi to another address
    and the fake device could no longer bind (bridge step 5's first complete run). A UDP `connect`
    sends nothing; it only picks the route.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 9))
        return probe.getsockname()[0]
    finally:
        probe.close()


LAN = _lan_address()
DEVICE_ID = 151732605161920

SUBJECTS = {
    # W2 (a), §7.40: discovery by synchronous UDP, then blocking TCP to the device.
    "midea_ac_lan": {
        "flow_input": {
            "action": "manually", "name": "fake ac", "device_id": DEVICE_ID, "type": 0xAC,
            "ip_address": LAN, "port": 6444, "protocol": 2, "model": "00000000",
            "subtype": 0, "token": "", "key": "",
        },
        # Long enough for the integration's own device thread to connect and send queries.
        "settle": 40.0,
        "fake": ["fake_midea.py", "--bind", LAN],
        "declared": {"local": {"tcp": [6444], "udp": [6445, 20086]}},
    },
    # W2 (b): asyncio datagram endpoints listening for broadcasts. The evidence is the
    # integration's own record of what it discovered.
    "localtuya": {
        "flow_input": {"region": "eu", "username": "localtuya", "no_cloud": True},
        "settle": 30.0,
        "fake": ["fake_tuya.py", "--to", LAN],
        "declared": {"discover": {"listen": [6666, 6667]}},
        "report_attr": ["localtuya", "discovery", "devices"],
    },
}


def arms_for(subject: dict) -> dict:
    return {"unconfined": None,
            "confined_declared": {"schema_version": 1, "network": subject["declared"]},
            "confined_undeclared": {"schema_version": 1}}


def fake_device(subject: dict, log: Path, python: Path) -> subprocess.Popen:
    env = {**os.environ, "PYTHONPATH": str(MIDEA_SRC)}
    script, *rest = subject["fake"]
    proc = subprocess.Popen([str(python), str(FAKES / script), *rest, "--log", str(log),
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
        # Bridge step 5: what the confined arm published, and what (A) holds for it.
        "published": report.get("published"),
        "in_house": report.get("in_house"),
        "platform": report.get("platform"),
        "device_saw": {
            "udp": sum(e["kind"] == "udp" for e in events),
            "tcp_connections": sum(e["kind"] == "tcp_accept" for e in events),
            "tcp_bytes": sum(e["bytes"] for e in events if e["kind"] == "tcp_data"),
            "peers": sorted({e["peer"] for e in events if "peer" in e}),
            # The Tuya device only sends, so its log is of what it announced, not what it heard.
            "sent": sum(e["kind"] == "sent" for e in events),
        },
        "decisions": local,
        "published": report.get("published"),
        "probe": report.get("probe"),
        "audit_breaks": report.get("audit_breaks"),
        "reconcile": report.get("reconcile"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--python", type=Path, required=True)
    ap.add_argument("--uv", default=str(Path.home() / ".local/bin/uv"))
    ap.add_argument("--subject", default="midea_ac_lan", choices=sorted(SUBJECTS))
    ap.add_argument("--arms", default="unconfined,confined_declared,confined_undeclared")
    ap.add_argument("--platform", choices=["stand-in", "real"], default="stand-in",
                    help="bridge step 5: confined arms publish to the house's real (A)")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    real = args.platform == "real"

    require_ready(deep=False)
    become_subreaper()
    delegation = Delegation.discover()
    uv = args.uv if Path(args.uv).exists() else None
    platform_deps = Path.home() / "r2exp/platform-deps"
    platform_deps = platform_deps if platform_deps.is_dir() else None
    domain = args.subject
    subject = SUBJECTS[domain]
    arms = arms_for(subject)
    component = args.corpus / domain

    results = []
    for arm in args.arms.split(","):
        log = Path(tempfile.mkstemp(suffix=f"-{arm}.jsonl")[1])
        device = fake_device(subject, log, args.python)
        try:
            if arms[arm] is None and real:
                with house_stopped():   # F56: the unconfined arm binds port 8123 itself
                    report = run_unconfined(component, domain, subject, args.python, uv,
                                            platform_deps)
            elif arms[arm] is None:
                report = run_unconfined(component, domain, subject, args.python, uv,
                                        platform_deps)
            else:
                # Five minutes is far beyond setup and the 40 s settle; a confined arm still
                # running then is looping, as both baseline arms did.
                report = run_confined(component, domain, subject, arm, arms[arm],
                                      args.python, delegation, uv, platform_deps,
                                      max_seconds=300, real=real)
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
              f"from {saw['peers']}  probe={summary['probe']}", flush=True)
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
            record_run(args.json)  # F14: how this result was produced, beside it

    if args.json:
        args.json.write_text(json.dumps(results, indent=2, default=str) + "\n")
        record_run(args.json)  # F14: how this result was produced, beside it
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
