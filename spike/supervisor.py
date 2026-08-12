#!/usr/bin/env python3
"""Supervisor: the trusted side of the sandbox boundary.

Holds the Home Assistant credentials, owns the socket, and decides every
operation an integration asks for against that integration's declared manifest.
The sandboxed process holds no token and has no other route to HA.

The house state here is a stand-in for a real HA instance. Swapping it for a
REST/WebSocket client against a live HA is the next step and does not change the
policy layer, which is the part being demonstrated.

Usage:
    python3 supervisor.py --manifest manifest.yaml --integration target/custom_components/andrews_arnold_quota
    python3 supervisor.py --verify audit/<run>.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent

# A stand-in for the rest of the house: the entities a real HA instance would
# expose to anything holding a token. None of it is this integration's business.
DEFAULT_HOUSE = {
    "lock.front_door": ("locked", {"friendly_name": "Front door"}),
    "alarm_control_panel.home": ("armed_away", {"friendly_name": "Alarm"}),
    "device_tracker.younes": ("not_home", {"friendly_name": "Younes"}),
    "sensor.living_room_temperature": ("21.4", {"friendly_name": "Living room temperature"}),
    "camera.hallway": ("recording", {"friendly_name": "Hallway camera"}),
    "binary_sensor.holiday_mode": ("on", {"friendly_name": "Holiday mode"}),
}


class Manifest:
    """The security contract an integration ships with."""

    def __init__(self, data: dict) -> None:
        self.name: str = data.get("name", "unknown")
        self.version: str = str(data.get("version", "0"))
        self.publishes: list[str] = list(data.get("publishes") or [])
        self.reads_entities: list[str] = list(data.get("reads_entities") or [])
        self.calls_services: list[str] = list(data.get("calls_services") or [])
        self.network: list[str] = list(data.get("network") or [])
        self.subscribes: list[str] = list(data.get("subscribes") or [])

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        with path.open(encoding="utf-8") as handle:
            return cls(yaml.safe_load(handle) or {})

    @staticmethod
    def _matches(value: str, patterns: list[str]) -> bool:
        return any(fnmatch(value, pattern) for pattern in patterns)

    def may_publish(self, entity_id: str) -> bool:
        return self._matches(entity_id, self.publishes)

    def may_read(self, entity_id: str) -> bool:
        # Publishing an entity implies being able to read it back.
        return self._matches(entity_id, self.reads_entities) or self.may_publish(entity_id)

    def may_call(self, domain: str, service: str) -> bool:
        return self._matches(f"{domain}.{service}", self.calls_services)

    def may_connect(self, host: str) -> bool:
        return self._matches(host, self.network)

    def may_subscribe(self, event_type: str) -> bool:
        return self._matches(event_type, self.subscribes)


class AuditLog:
    """Append-only, hash-chained decision log.

    Each record commits to the one before it, so a compromised integration that
    later gains write access to the log cannot remove or reorder a decision
    without breaking every hash after it. Cheap, local, and verifiable — the
    decentralised attestation layer is out of scope.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8")
        self._lock = threading.Lock()
        self._seq = 0
        self._prev = "0" * 64

    @staticmethod
    def _digest(prev: str, record: dict) -> str:
        payload = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256((prev + payload).encode("utf-8")).hexdigest()

    def append(self, integration: str, op: str, params: dict, allowed: bool, reason: str) -> None:
        with self._lock:
            record = {
                "seq": self._seq,
                "ts": datetime.now(timezone.utc).isoformat(),
                "integration": integration,
                "op": op,
                "params": params,
                "decision": "allow" if allowed else "DENY",
                "reason": reason,
            }
            record["prev"] = self._prev
            record["hash"] = self._digest(self._prev, record)
            self._prev = record["hash"]
            self._seq += 1
            self._handle.write(json.dumps(record, default=str) + "\n")
            self._handle.flush()

    def close(self) -> None:
        self._handle.close()

    @staticmethod
    def verify(path: Path) -> tuple[bool, str]:
        prev = "0" * 64
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                record = json.loads(line)
                stored_hash = record.pop("hash")
                if record.get("prev") != prev:
                    return False, f"line {line_number}: chain broken (prev mismatch)"
                if AuditLog._digest(prev, record) != stored_hash:
                    return False, f"line {line_number}: record altered (hash mismatch)"
                prev = stored_hash
        return True, f"chain intact ({line_number} records)"


class Supervisor:
    """Policy enforcement for one sandboxed integration."""

    def __init__(self, manifest: Manifest, audit: AuditLog, quiet: bool = False) -> None:
        self.manifest = manifest
        self.audit = audit
        self.quiet = quiet
        self.house = {
            entity_id: {"entity_id": entity_id, "state": state, "attributes": attributes}
            for entity_id, (state, attributes) in DEFAULT_HOUSE.items()
        }
        self.published: dict[str, dict] = {}
        self.allowed_count = 0
        self.denied_count = 0

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------
    def decide(self, message: dict) -> tuple[bool, str, dict]:
        """Return (allowed, reason, response payload)."""
        op = message.get("op")

        if op == "set_state":
            entity_id = str(message.get("entity_id", ""))
            if not self.manifest.may_publish(entity_id):
                return False, f"{entity_id} not in manifest publishes", {}
            self.published[entity_id] = {
                "entity_id": entity_id,
                "state": message.get("state"),
                "attributes": message.get("attributes") or {},
            }
            self.house[entity_id] = self.published[entity_id]
            return True, f"publishes matches {entity_id}", {}

        if op == "get_state":
            entity_id = str(message.get("entity_id", ""))
            if not self.manifest.may_read(entity_id):
                return False, f"{entity_id} not in manifest reads_entities", {"state": None}
            return True, f"reads_entities matches {entity_id}", {"state": self.house.get(entity_id)}

        if op == "list_states":
            # The firehose. Real HA's /api/states hands back the entire house;
            # the bridge returns only the declared subset.
            visible = [
                state for entity_id, state in self.house.items() if self.manifest.may_read(entity_id)
            ]
            hidden = len(self.house) - len(visible)
            return True, f"{len(visible)} visible, {hidden} withheld", {"states": visible}

        if op == "remove_state":
            entity_id = str(message.get("entity_id", ""))
            if not self.manifest.may_publish(entity_id):
                return False, f"{entity_id} not owned by this integration", {"removed": False}
            self.house.pop(entity_id, None)
            self.published.pop(entity_id, None)
            return True, f"removed {entity_id}", {"removed": True}

        if op == "call_service":
            domain = str(message.get("domain", ""))
            service = str(message.get("service", ""))
            if not self.manifest.may_call(domain, service):
                return False, f"{domain}.{service} not in manifest calls_services", {}
            return True, f"calls_services matches {domain}.{service}", {"response": None}

        if op == "register_service":
            domain = str(message.get("domain", ""))
            service = str(message.get("service", ""))
            if domain != self.manifest.name:
                return False, f"may only register services in its own domain, not {domain}", {}
            return True, f"registered {domain}.{service}", {}

        if op == "subscribe_events":
            event_type = str(message.get("event_type", ""))
            if not self.manifest.may_subscribe(event_type):
                return False, f"{event_type} not in manifest subscribes", {}
            return True, f"subscribes matches {event_type}", {}

        if op == "fire_event":
            event_type = str(message.get("event_type", ""))
            if not event_type.startswith(f"{self.manifest.name}_"):
                return False, f"may only fire events prefixed {self.manifest.name}_", {}
            return True, f"fired {event_type}", {}

        if op == "net_request":
            host = str(message.get("host", ""))
            if not self.manifest.may_connect(host):
                return False, f"{host} not in manifest network allowlist", {}
            return True, f"network allowlist matches {host}", {}

        return False, f"unknown operation {op!r}", {}

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------
    def handle_connection(self, conn: socket.socket) -> None:
        with conn, conn.makefile("r", encoding="utf-8") as reader:
            for line in reader:
                line = line.strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    conn.sendall(b'{"ok": false, "reason": "malformed request"}\n')
                    continue

                try:
                    allowed, reason, payload = self.decide(message)
                except Exception as err:  # noqa: BLE001 - never let a bad request kill the supervisor
                    allowed, reason, payload = False, f"supervisor error: {err}", {}

                params = {key: value for key, value in message.items() if key != "op"}
                self.audit.append(self.manifest.name, str(message.get("op")), params, allowed, reason)
                self._trace(message, allowed, reason)

                if allowed:
                    self.allowed_count += 1
                    reply = {"ok": True, **payload}
                else:
                    self.denied_count += 1
                    reply = {"ok": False, "reason": reason, **payload}
                conn.sendall((json.dumps(reply, default=str) + "\n").encode("utf-8"))

    def _trace(self, message: dict, allowed: bool, reason: str) -> None:
        if self.quiet:
            return
        mark = "ALLOW" if allowed else "DENY "
        detail = (
            message.get("entity_id")
            or message.get("host")
            or (f"{message.get('domain')}.{message.get('service')}" if message.get("domain") else "")
            or message.get("event_type")
            or ""
        )
        print(f"  [{mark}] {message.get('op'):<18} {str(detail):<44} {reason}", flush=True)


def run(args: argparse.Namespace) -> int:
    manifest = Manifest.load(Path(args.manifest))
    integration_dir = Path(args.integration).resolve()
    domain = integration_dir.name
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    audit = AuditLog(HERE / "audit" / f"{domain}-{run_id}.jsonl")
    supervisor = Supervisor(manifest, audit, quiet=args.quiet)

    print(f"supervisor: integration '{manifest.name}' v{manifest.version}")
    print(f"  publishes      : {manifest.publishes or '(none)'}")
    print(f"  reads_entities : {manifest.reads_entities or '(none)'}")
    print(f"  calls_services : {manifest.calls_services or '(none)'}")
    print(f"  network        : {manifest.network or '(none)'}")
    print(f"  audit log      : {audit.path.relative_to(HERE)}")
    print()

    tmpdir = tempfile.mkdtemp(prefix="hacs-sandbox-")
    socket_path = os.path.join(tmpdir, "bridge.sock")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(socket_path)
    os.chmod(socket_path, 0o600)
    server.listen(4)

    env = dict(os.environ)
    env.update(
        {
            "HACS_BRIDGE_SOCKET": socket_path,
            "HACS_INTEGRATION_DIR": str(integration_dir),
            "HACS_DOMAIN": domain,
            "HACS_ENTRY_DATA": args.entry_data,
            "HACS_SANDBOX_DIR": tmpdir,
            "HACS_PROBE": "1" if args.probe else "0",
            # No HA token in the child's environment: the supervisor holds it.
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    if args.egress_rewrite:
        env["HACS_EGRESS_REWRITE"] = args.egress_rewrite

    child = subprocess.Popen(
        [sys.executable, str(HERE / "runner.py")],
        env=env,
        cwd=tmpdir,
    )

    threads: list[threading.Thread] = []
    server.settimeout(0.5)
    try:
        while child.poll() is None:
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            thread = threading.Thread(target=supervisor.handle_connection, args=(conn,), daemon=True)
            thread.start()
            threads.append(thread)
        child.wait(timeout=10)
    except KeyboardInterrupt:
        child.terminate()
    finally:
        server.close()
        for thread in threads:
            thread.join(timeout=1)
        time.sleep(0.05)
        audit.close()
        try:
            os.unlink(socket_path)
            os.rmdir(tmpdir)
        except OSError:
            pass

    print()
    print(f"supervisor: {supervisor.allowed_count} allowed, {supervisor.denied_count} denied")
    print("published entities:")
    for entity_id, state in sorted(supervisor.published.items()):
        unit = state["attributes"].get("unit_of_measurement", "")
        print(f"  {entity_id:<52} = {state['state']} {unit}".rstrip())

    ok, detail = AuditLog.verify(audit.path)
    print(f"audit chain    : {'OK' if ok else 'BROKEN'} — {detail}")
    return child.returncode or 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", default=str(HERE / "manifest.yaml"))
    parser.add_argument(
        "--integration",
        default=str(HERE / "target" / "custom_components" / "andrews_arnold_quota"),
        help="path to the custom_components/<domain> directory",
    )
    parser.add_argument(
        "--entry-data",
        default='{"username": "sandbox@example.org", "password": "not-a-real-password"}',
        help="JSON config entry data, as the config flow would have produced",
    )
    parser.add_argument(
        "--egress-rewrite",
        default="",
        help="test harness only: host=http://127.0.0.1:PORT redirection, checked after policy",
    )
    parser.add_argument("--probe", action="store_true", help="run the adversarial probe after setup")
    parser.add_argument("--quiet", action="store_true", help="suppress the per-decision trace")
    parser.add_argument("--verify", metavar="AUDIT_LOG", help="verify an audit log's hash chain and exit")
    args = parser.parse_args()

    if args.verify:
        ok, detail = AuditLog.verify(Path(args.verify))
        print(f"{'OK' if ok else 'BROKEN'}: {detail}")
        return 0 if ok else 1

    return run(args)


if __name__ == "__main__":
    sys.exit(main())
