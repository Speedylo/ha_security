"""(A): the house's real Home Assistant, started, onboarded and given the bridge.

W1 step 2. Everything before this ran the confined arm against `platform.py`'s stand-in. This
starts a real instance of the pinned release as its own process, so that the mediator has an
actual platform to act on. The instance is deliberately small and quiet:

  - **No `default_config`.** That would bring discovery (`zeroconf`, `ssdp`, `dhcp`, `bluetooth`)
    probing the network, which is noise in every measurement and nothing the mediator touches.
    What is loaded is what the experiment needs: `http` on loopback only, `api` and
    `websocket_api` for the mediator, `onboarding` and `config` to create the owner and the
    bridge's entry headlessly, and the house's own entities.
  - **The house's entities are real and change through real services.** Two `input_number`
    helpers, and template sensors over them carrying the device classes `thermal_comfort` needs.
    A pushed change is then caused by `input_number.set_value` — a service call into (A) — and
    not by a harness writing a dict (`notes/w1_step2_real_platform_prediction.md` §2).

**The credential.** Onboarding is a REST wizard that ends with a short-lived access token; a
long-lived one is issued only over the WebSocket API, so `ws.py` mints it — the first real use of
that client. The token is written to `TOKEN_FILE`, mode 600, and printed nowhere. It is the
mediator's credential of §5.15.3, unscoped, which is residual risk R3 exactly as stated.

Run (on the Pi):  python3 -m confine.house_a up | down | status
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
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .ws import WebSocket

HERE = Path(__file__).resolve().parent
BRIDGE = HERE.parent / "ha_bridge" / "confine_bridge"

DEFAULT_CONFIG = Path.home() / "r2exp" / "houseA"
TOKEN_FILE = Path.home() / ".config" / "capstone" / "house_a.token"
HASS = Path.home() / "r2exp" / "ha314" / "bin" / "hass"
#: The frontend, installed apart from `ha314` so that the environment every other experiment uses
#: is not changed. (A) cannot run without it: bootstrap always sets up its default integrations,
#: `frontend` is the one it treats as critical, and if it fails to load Home Assistant enters
#: recovery mode — which disables every custom integration, the bridge included. Found on the
#: first start, 2026-10-04 (`notes/w1_step2_real_platform_prediction.md` §5).
DEPS = Path.home() / "r2exp" / "houseA-deps"
HOST, PORT = "127.0.0.1", 8123
BASE = f"http://{HOST}:{PORT}"
CLIENT_ID = f"{BASE}/"
#: Local to a loopback-only instance that is rebuilt for each experiment, and never a real house.
OWNER = {"name": "Capstone", "username": "capstone", "password": "capstone-house-a"}

CONFIGURATION = """\
homeassistant:
  name: House A
  latitude: 52.37
  longitude: 4.89
  elevation: 0
  unit_system: metric
  time_zone: UTC
  currency: EUR
  country: NL

http:
  server_host: 127.0.0.1
  server_port: 8123

api:
websocket_api:
onboarding:
config:

input_number:
  living_room_temperature:
    name: Living room temperature (set point of the test)
    min: -20
    max: 50
    step: 0.1
    initial: 21.4
    unit_of_measurement: "°C"
  living_room_humidity:
    name: Living room humidity (set point of the test)
    min: 0
    max: 100
    step: 1
    initial: 48
    unit_of_measurement: "%"

template:
  - sensor:
      - name: Living room temperature
        unique_id: house_a_living_room_temperature
        state: "{{ states('input_number.living_room_temperature') }}"
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement
      - name: Living room humidity
        unique_id: house_a_living_room_humidity
        state: "{{ states('input_number.living_room_humidity') }}"
        unit_of_measurement: "%"
        device_class: humidity
        state_class: measurement
"""


def request(method: str, path: str, payload: dict | None = None, token: str | None = None,
            form: bool = False) -> object:
    if form:
        body = urllib.parse.urlencode(payload or {}).encode()
    else:
        body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=body, method=method)
    req.add_header("Content-Type",
                   "application/x-www-form-urlencoded" if form else "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
    return json.loads(raw) if raw.strip() else None


def running() -> bool:
    try:
        urllib.request.urlopen(f"{BASE}/api/", timeout=2)
    except urllib.error.HTTPError:
        return True          # 401: the API is up and wants a token
    except OSError:
        return False
    return True


def wait_until_up(seconds: float = 180) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if running():
            return
        time.sleep(1)
    raise TimeoutError(f"(A) did not answer on {BASE} within {seconds:.0f} s")


def start(config: Path) -> int:
    """Start `hass` detached, with its own log file. Returns its pid."""
    log = open(config / "hass.stdout", "ab")
    env = {**os.environ, "PYTHONPATH": str(DEPS)}
    proc = subprocess.Popen([str(HASS), "-c", str(config), "--skip-pip", "--log-no-color"],
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                            env=env)
    (config / "hass.pid").write_text(str(proc.pid))
    wait_until_up()
    return proc.pid


def stop(config: Path, seconds: float = 60) -> None:
    pid_file = config / "hass.pid"
    if not pid_file.exists():
        return
    pid = int(pid_file.read_text())
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pid_file.unlink()
        return
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.5)
    else:
        raise TimeoutError(f"(A), pid {pid}, did not stop within {seconds:.0f} s")
    pid_file.unlink()


def onboard() -> str:
    """Create the owner and return a long-lived token minted over WebSocket."""
    result = request("POST", "/api/onboarding/users",
                     {"client_id": CLIENT_ID, "language": "en", **OWNER})
    tokens = request("POST", "/auth/token", {"grant_type": "authorization_code",
                                             "code": result["auth_code"],
                                             "client_id": CLIENT_ID}, form=True)
    access = tokens["access_token"]
    # The wizard's later steps are not taken. `core_config` starts flows for the integrations a
    # new user is offered (weather, radio, text-to-speech), which add network traffic and
    # failures to (A) and nothing to any measurement; the API and the token do not need them.
    ws = WebSocket(HOST, PORT)
    try:
        greeting = ws.receive()[0]
        if greeting.get("type") != "auth_required":
            raise RuntimeError(f"unexpected greeting: {greeting}")
        ws.send({"type": "auth", "access_token": access})
        if ws.receive()[0].get("type") != "auth_ok":
            raise RuntimeError("(A) refused the onboarding token over WebSocket")
        ws.send({"id": 1, "type": "auth/long_lived_access_token",
                 "client_name": "confine-mediator", "lifespan": 3650})
        reply = ws.receive()[0]
    finally:
        ws.close()
    if not reply.get("success"):
        raise RuntimeError(f"no long-lived token: {reply}")
    return reply["result"]


def add_bridge_entry(token: str) -> None:
    entries = request("GET", "/api/config/config_entries/entry", token=token)
    if any(e.get("domain") == "confine_bridge" for e in entries):
        return
    flow = request("POST", "/api/config/config_entries/flow",
                   {"handler": "confine_bridge", "show_advanced_options": False}, token=token)
    if flow.get("type") != "create_entry":
        raise RuntimeError(f"the bridge's flow did not complete: {json.dumps(flow)[:300]}")


def up(config: Path, fresh: bool) -> None:
    if running():
        raise SystemExit(f"something already answers on {BASE}; run `down` first")
    if fresh and config.exists():
        shutil.rmtree(config)
    (config / "custom_components").mkdir(parents=True, exist_ok=True)
    (config / "configuration.yaml").write_text(CONFIGURATION)
    target = config / "custom_components" / "confine_bridge"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(BRIDGE, target, ignore=shutil.ignore_patterns("__pycache__"))

    start(config)
    if not TOKEN_FILE.exists() or fresh:
        token = onboard()
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.touch(mode=0o600)
        TOKEN_FILE.write_text(token)
    token = TOKEN_FILE.read_text().strip()
    add_bridge_entry(token)
    print(f"(A) up on {BASE}, config {config}, bridge entry present, token in {TOKEN_FILE}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["up", "down", "restart", "status"])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--fresh", action="store_true",
                    help="delete the config directory first and onboard from nothing")
    args = ap.parse_args()
    if args.action == "up":
        up(args.config, args.fresh)
    elif args.action == "down":
        stop(args.config)
        print("(A) stopped")
    elif args.action == "restart":
        stop(args.config)
        start(args.config)
        print("(A) restarted")
    else:
        print("up" if running() else "down")
    return 0


if __name__ == "__main__":
    sys.exit(main())
