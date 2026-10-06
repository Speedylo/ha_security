#!/usr/bin/env python3
"""F45, arm P: is a per-domain policy enforced when one exists? (notes/f45_prediction.md)

Home Assistant 2026.8.3's permission model can express "this user may read and control the `sensor`
domain and nothing else", but no screen creates such a group: it has to be written into
`.storage/auth` by hand. This tests whether the platform enforces it once written. It never touches
the house's live configuration. It copies (A)'s configuration to a scratch directory, gives the
copy its own port, writes the group there, puts the ordinary test user `f45-other` (made by
`selftest_real_platform`) in it, runs that copy, asks it questions with that user's token, stops it,
and deletes the copy.

Run on the Pi, with (A) up, from v2/framework:  python3 ../verify/f45_policy.py --json OUT
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "framework"))
from confine import house_a  # noqa: E402
from confine.ws import WebSocket  # noqa: E402

SOURCE = Path.home() / "r2exp" / "houseA"
SCRATCH = Path.home() / "r2exp" / "f45policy"
PORT = 8124
GROUP = {"id": "f45-sensor-only", "name": "F45: sensor only",
         "policy": {"entities": {"domains": {"sensor": True}}}}
TOKEN = house_a.MEDIATOR_TOKEN_FILE.with_name("house_a_f45_other.token")


def call(token: str, message: dict) -> dict:
    ws = WebSocket("127.0.0.1", PORT, timeout=30)
    try:
        ws.receive()
        ws.send({"type": "auth", "access_token": token})
        if ws.receive()[0].get("type") != "auth_ok":
            return {"success": False, "error": {"code": "auth_refused"}}
        ws.send({"id": 1, **message})
        answer: list = []
        while not answer:
            answer = [m for m in ws.receive() if m.get("id") == 1]
        return answer[0]
    finally:
        ws.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, required=True)
    args = ap.parse_args()
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    config = SCRATCH / "config"
    shutil.copytree(SOURCE, config, ignore=shutil.ignore_patterns(
        "home-assistant.log*", "hass.stdout", "hass.pid", "*.db-shm", "*.db-wal"))
    yaml = (config / "configuration.yaml").read_text()
    assert "server_port: 8123" in yaml
    (config / "configuration.yaml").write_text(yaml.replace("server_port: 8123",
                                                            f"server_port: {PORT}"))
    auth_path = config / ".storage" / "auth"
    auth = json.loads(auth_path.read_text())
    auth["data"]["groups"].append(GROUP)
    users = [u for u in auth["data"]["users"] if u.get("name") == "f45-other"]
    assert len(users) == 1, "run selftest_real_platform first: it makes f45-other"
    users[0]["group_ids"] = [GROUP["id"]]
    auth_path.write_text(json.dumps(auth, indent=2))

    log = open(SCRATCH / "hass.stdout", "wb")
    proc = subprocess.Popen([str(house_a.HASS), "-c", str(config), "--skip-pip", "--log-no-color"],
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                            env={**os.environ, "PYTHONPATH": str(house_a.DEPS)})
    token = TOKEN.read_text().strip()
    results: dict = {}
    try:
        for _ in range(120):
            try:
                if (call(token, {"type": "get_config"}).get("result") or {}).get("state") == "RUNNING":
                    break
            except OSError:
                pass
            time.sleep(2)
        else:
            raise SystemExit("the scratch copy did not start")

        states = call(token, {"type": "get_states"}).get("result") or []
        results["domains_readable"] = sorted({s["entity_id"].split(".")[0] for s in states})
        registry = call(token, {"type": "config/entity_registry/list"}).get("result") or []
        results["registry_rows_visible"] = len(registry)
        results["registry_domains_visible"] = sorted({r["entity_id"].split(".")[0] for r in registry})

        def service(domain: str, name: str, data: dict) -> dict:
            answer = call(token, {"type": "call_service", "domain": domain, "service": name,
                                  "service_data": data})
            return {"success": answer.get("success"),
                    "error": (answer.get("error") or {}).get("message")}

        results["update_entity_sensor"] = service("homeassistant", "update_entity",
                                                  {"entity_id": "sensor.living_room_temperature"})
        results["update_entity_switch"] = service("homeassistant", "update_entity",
                                                  {"entity_id": "switch.other_switch"})
        results["switch_turn_on"] = service("switch", "turn_on", {"entity_id": "switch.other_switch"})
        results["no_entity_target"] = service("persistent_notification", "create",
                                              {"message": "F45 policy probe", "notification_id": "f45"})
    finally:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=60)
        log.close()
        shutil.rmtree(SCRATCH)

    checks = [
        ("reads are limited to the domain the policy grants",
         results["domains_readable"] == ["sensor"], results["domains_readable"]),
        ("an entity service on a granted entity is accepted",
         results["update_entity_sensor"]["success"] is True, results["update_entity_sensor"]),
        ("the same service on an ungranted entity is refused",
         results["update_entity_switch"]["success"] is False, results["update_entity_switch"]),
        ("the ungranted domain's own service is refused",
         results["switch_turn_on"]["success"] is False, results["switch_turn_on"]),
    ]
    notes = [
        ("a service with no entity target is not covered by the entity policy",
         results["no_entity_target"]),
        ("the entity registry is not filtered by the policy",
         f"{results['registry_rows_visible']} rows, domains {results['registry_domains_visible']}"),
    ]
    for label, ok, detail in checks:
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}  — {detail}")
    for label, detail in notes:
        print(f"  note  {label}  — {detail}")
    args.json.write_text(json.dumps({"results": results,
                                     "checks": [(l, ok) for l, ok, _ in checks]}, indent=2))
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
