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
import threading
import os
import secrets
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
#: The mediator's own credential (finding F45): a long-lived token of an ordinary, non-admin user
#: the bridge has been told is the mediator. The owner's admin token above is for setup only. The
#: password is kept so the token can be minted again; both files are mode 600 and never printed.
MEDIATOR_TOKEN_FILE = Path.home() / ".config" / "capstone" / "house_a_mediator.token"
MEDIATOR_PASSWORD_FILE = Path.home() / ".config" / "capstone" / "house_a_mediator.password"
MEDIATOR_NAME = "confine-mediator"
HASS = Path.home() / "r2exp" / "ha314" / "bin" / "hass"
#: The frontend, installed apart from `ha314` so that the environment every other experiment uses
#: is not changed. (A) cannot run without it: bootstrap always sets up its default integrations,
#: `frontend` is the one it treats as critical, and if it fails to load Home Assistant enters
#: recovery mode — which disables every custom integration, the bridge included. Found on the
#: first start, 2026-10-04 (`notes/w1_step2_real_platform_prediction.md` §5).
#:
#: **What is in it, and how it is built** (recorded 2026-10-05; until then nothing said). The
#: frontend, and the pinned requirements of the components the frontend's `get_services` imports
#: (`helpers/service.py`'s `_base_components`, walked through their manifests' dependencies).
#: Without those, a browser's first `get_services` failed on `No module named 'hassil'` and the
#: interface stayed on "Loading" forever — found by Younes testing the refusal flood by hand. API
#: clients never send that command, so no suite saw it. `--no-deps` throughout, so nothing here
#: shadows a package `ha314` already has:
#:
#:     uv pip install --python ~/r2exp/ha314/bin/python --target ~/r2exp/houseA-deps --no-deps \
#:         home-assistant-frontend==20260729.7 hassil==3.11.0 home-assistant-intents==2026.7.30 \
#:         unicode-rbnf==2.4.0 PyTurboJPEG==1.8.3 numpy==2.3.2 ha-ffmpeg==3.2.2 mutagen==1.48.1 \
#:         pymicro-vad==1.0.1 pyspeex-noise==1.0.2 async-timeout==4.0.3
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
  # Bridge step 5 (2026-10-25): the light dims, as the stand-in's WORLD light does, so the
  # end-to-end set's scripted world (brightness 51, then off) is the same against (A).
  living_room_brightness:
    name: Living room brightness (state of the test)
    min: 0
    max: 255
    step: 1
    initial: 180

input_boolean:
  living_room_light:
    name: Living room light (state of the test)
    initial: true

template:
  - light:
      - name: Living room
        unique_id: house_a_living_room_light
        state: "{{ is_state('input_boolean.living_room_light', 'on') }}"
        level: "{{ states('input_number.living_room_brightness') | int }}"
        set_level:
          - action: input_number.set_value
            target:
              entity_id: input_number.living_room_brightness
            data:
              value: "{{ brightness }}"
          - action: input_boolean.turn_on
            target:
              entity_id: input_boolean.living_room_light
        turn_on:
          - action: input_boolean.turn_on
            target:
              entity_id: input_boolean.living_room_light
        turn_off:
          - action: input_boolean.turn_off
            target:
              entity_id: input_boolean.living_room_light
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


#: What `hass` exits with when asked to restart, from its own Settings → System → Restart or a
#: SIGHUP. It does not start itself again: it expects a process manager to, as Docker or systemd
#: does in a real installation (`homeassistant/__main__.py`, `const.RESTART_EXIT_CODE`).
RESTART_EXIT_CODE = 100


def wait_until_running(seconds: float = 180) -> None:
    """Wait until (A) says it has finished starting, not only that its API answers.

    The API answers while (A) is still setting up its integrations, and since verification 4.7
    (F35 R7) the mediator refuses to connect to it until then. So `up` waits for this too, and
    whatever is started after `up` returns can connect at once.
    """
    token = TOKEN_FILE.read_text().strip()
    deadline = time.monotonic() + seconds
    state = None
    while time.monotonic() < deadline:
        ws = WebSocket(HOST, PORT)
        try:
            ws.receive()
            ws.send({"type": "auth", "access_token": token})
            if ws.receive()[0].get("type") == "auth_ok":
                ws.send({"id": 1, "type": "get_config"})
                reply = [m for m in ws.receive() if m.get("id") == 1]
                state = (reply[0].get("result") or {}).get("state") if reply else None
                if state == "RUNNING":
                    return
        finally:
            ws.close()
        time.sleep(1)
    raise TimeoutError(f"(A) did not finish starting within {seconds:.0f} s (state {state})")


def start(config: Path) -> int:
    """Start `hass` detached, under `keep`, with its own log file. Returns the keeper's pid.

    Until 2026-10-06 this started `hass` itself, with nothing to start it again, so restarting the
    house's Home Assistant from its own interface stopped it for good (verification 4.11, finding
    F42). The pid file holds the keeper's pid, so `stop` ends both.
    """
    log = open(config / "hass.stdout", "ab")
    env = {**os.environ, "PYTHONPATH": str(HERE.parent)}
    proc = subprocess.Popen([sys.executable, "-m", "confine.house_a", "keep",
                             "--config", str(config)],
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                            env=env, cwd=str(HERE.parent))
    (config / "hass.pid").write_text(str(proc.pid))
    wait_until_up()
    return proc.pid


def keep(config: Path) -> int:
    """Run `hass`, and run it again each time it exits asking to be restarted.

    A SIGTERM is passed on to `hass`, and once it has exited this returns instead of starting it
    again, so `stop` still means stop.
    """
    env = {**os.environ, "PYTHONPATH": str(DEPS)}
    stopping = False
    child: subprocess.Popen | None = None

    def forward(signum, _frame) -> None:
        nonlocal stopping
        stopping = True
        if child is not None and child.poll() is None:
            child.send_signal(signum)
    signal.signal(signal.SIGTERM, forward)
    signal.signal(signal.SIGINT, forward)
    while True:
        child = subprocess.Popen([str(HASS), "-c", str(config), "--skip-pip", "--log-no-color"],
                                 env=env)
        code = child.wait()
        if stopping or code != RESTART_EXIT_CODE:
            return code
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} house_a keep: hass asked to be restarted; "
              f"starting it again", flush=True)


def alive(pid: int) -> bool:
    """Whether `pid` is a running process. A zombie has exited and is not (F69).

    `os.kill(pid, 0)` succeeds on a zombie. An end-to-end harness is a subreaper, so an (A) it
    restarted (bridge step 5) is re-parented to it and, once stopped, stays its zombie: `stop`
    waited its full 60 s for a process that had already exited, and raised. One that is this
    process's own child is reaped here.
    """
    try:
        with open(f"/proc/{pid}/stat") as stat:
            state = stat.read().rpartition(")")[2].split()[0]
    except (FileNotFoundError, ProcessLookupError, IndexError):
        return False
    if state != "Z":
        return True
    try:
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass
    return False


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
        if not alive(pid):
            break
        time.sleep(0.5)
    else:
        raise TimeoutError(f"(A), pid {pid}, did not stop within {seconds:.0f} s")
    pid_file.unlink()


def seed_onboarding(config: Path) -> None:
    """Record the wizard's later steps as done before (A)'s first start, so a browser is not sent
    back into it.

    `onboard` takes only the first step, creating the owner, on purpose (its comment says why).
    Until 2026-10-05 the others were simply never taken, and a person logging in through a browser
    was put back into the wizard at the step after it: `core_config` started the flows `onboard`
    avoids, and the analytics page then failed with "unknown command", because `analytics` is not
    loaded here. Found by Younes, testing the refusal flood by hand. Home Assistant reads this file
    once at start (`onboarding/__init__.py`), and the owner `onboard` creates completes the last
    step, so onboarding ends with none of the later steps' side effects. Written only when there
    is no record yet: an instance that already has one is left as it is.
    """
    store = config / ".storage" / "onboarding"
    if store.exists():
        return
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps({"version": 4, "minor_version": 1, "key": "onboarding",
                                 "data": {"done": ["core_config", "analytics", "integration"]}},
                                indent=2))


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


def confirm_http_config(token: str) -> bool:
    """Confirm the `http:` section, or (A) restarts itself five minutes after every fresh start.

    Since 2026.8, Home Assistant migrates an `http:` YAML section into a *pending* trial config
    and reverts it, with a restart, unless an administrator confirms it within five minutes
    (`homeassistant/components/http/config.py`, `async_schedule_revert_to_stable`). A restart
    means exiting for a supervisor to start it again, and nothing supervises this `hass`, so (A)
    simply stopped — found 2026-10-04, when it was down after a suite run. Returns whether a
    pending config was confirmed.
    """
    ws = WebSocket(HOST, PORT)
    try:
        ws.receive()
        ws.send({"type": "auth", "access_token": token})
        if ws.receive()[0].get("type") != "auth_ok":
            raise RuntimeError("(A) refused the token while confirming the HTTP config")
        ws.send({"id": 1, "type": "http/config"})
        current = [m for m in ws.receive() if m.get("id") == 1][0]
        if not (current.get("result") or {}).get("pending"):
            return False
        ws.send({"id": 2, "type": "http/config/promote"})
        promoted = [m for m in ws.receive() if m.get("id") == 2][0]
        if not promoted.get("success"):
            raise RuntimeError(f"(A) would not confirm its HTTP config: {promoted.get('error')}")
        return True
    finally:
        ws.close()


def _private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(mode=0o600)
    path.chmod(0o600)
    path.write_text(text)


def _ws_call(token: str, message: dict) -> dict:
    """One command over a fresh, authenticated connection; the full answer."""
    ws = WebSocket(HOST, PORT, timeout=30)
    try:
        ws.receive()
        ws.send({"type": "auth", "access_token": token})
        if ws.receive()[0].get("type") != "auth_ok":
            raise RuntimeError("(A) refused the token")
        ws.send({"id": 1, **message})
        answer: list = []
        while not answer:
            answer = [m for m in ws.receive() if m.get("id") == 1]
        return answer[0]
    finally:
        ws.close()


def ensure_user(admin_token: str, name: str, token_file: Path, password_file: Path) -> str:
    """Make sure an ordinary (`system-users`, local-only) user `name` exists with a long-lived token.

    Idempotent. The token and the password are written mode 600 and never printed. Returns the
    user's id.
    """
    users = _ws_call(admin_token, {"type": "config/auth/list"})["result"]
    found = [u for u in users if u.get("name") == name]
    if found:
        user_id = found[0]["id"]
    else:
        created = _ws_call(admin_token, {"type": "config/auth/create", "name": name,
                                         "group_ids": ["system-users"], "local_only": True})
        user_id = created["result"]["user"]["id"]
        password = secrets.token_urlsafe(32)
        made = _ws_call(admin_token, {"type": "config/auth_provider/homeassistant/create",
                                      "user_id": user_id, "username": name,
                                      "password": password})
        if not made.get("success"):
            raise RuntimeError(f"no credentials for {name}: {made.get('error')}")
        _private(password_file, password)
        token_file.unlink(missing_ok=True)
    if not token_file.exists():
        password = password_file.read_text().strip()
        flow = request("POST", "/auth/login_flow", {"client_id": CLIENT_ID,
                                                    "handler": ["homeassistant", None],
                                                    "redirect_uri": CLIENT_ID})
        done = request("POST", f"/auth/login_flow/{flow['flow_id']}",
                       {"client_id": CLIENT_ID, "username": name, "password": password})
        if done.get("type") != "create_entry":
            raise RuntimeError(f"{name}'s login did not complete: {done.get('errors')}")
        access = request("POST", "/auth/token", {"grant_type": "authorization_code",
                                                 "code": done["result"],
                                                 "client_id": CLIENT_ID}, form=True)["access_token"]
        minted = _ws_call(access, {"type": "auth/long_lived_access_token",
                                   "client_name": name, "lifespan": 3650})
        if not minted.get("success"):
            raise RuntimeError(f"no long-lived token for {name}: {minted.get('error')}")
        _private(token_file, minted["result"])
    return user_id


def ensure_mediator_user(admin_token: str) -> str:
    """The mediator's own non-admin user and token, designated in the bridge (finding F45).

    The user is in the built-in `system-users` group: it controls entities, as the mediator must,
    and is refused everything admin-only (users, integrations, configuration, restarting the house).
    """
    user_id = ensure_user(admin_token, MEDIATOR_NAME, MEDIATOR_TOKEN_FILE, MEDIATOR_PASSWORD_FILE)
    designated = _ws_call(admin_token, {"type": "confine_bridge/designate_mediator",
                                        "user_id": user_id})
    if not designated.get("success"):
        raise RuntimeError(f"the bridge would not designate the mediator: {designated.get('error')}")
    return user_id


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
    seed_onboarding(config)

    start(config)
    if not TOKEN_FILE.exists() or fresh:
        token = onboard()
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.touch(mode=0o600)
        TOKEN_FILE.write_text(token)
    token = TOKEN_FILE.read_text().strip()
    confirm_http_config(token)
    add_bridge_entry(token)
    wait_until_running()
    ensure_mediator_user(token)
    print(f"(A) up on {BASE}, config {config}, bridge entry present, admin token in {TOKEN_FILE}, "
          f"the mediator's own (non-admin) token in {MEDIATOR_TOKEN_FILE}")


class User:
    """A person in (A), on their own connection: what a dashboard button does, from a thread."""

    def __init__(self) -> None:
        # Longer than the bridge's 10 s command timeout, which C5 waits out. At 10 s the two
        # raced, and the user's read could give up just before (A)'s answer arrived.
        self.ws = WebSocket(HOST, PORT, timeout=30)
        self.ws.receive()
        self.ws.send({"type": "auth", "access_token": TOKEN_FILE.read_text().strip()})
        self.ws.receive()
        self.outcome: dict = {}

    def press(self, entity_id: str, service: str, data: dict | None = None,
              return_response: bool = False) -> threading.Thread:
        def run() -> None:
            start = time.perf_counter()
            self.ws.send({"id": 1, "type": "call_service", "domain": entity_id.partition(".")[0],
                          "service": service,
                          "service_data": {"entity_id": entity_id, **(data or {})},
                          **({"return_response": True} if return_response else {})})
            answer: list = []
            while not answer:
                answer = [m for m in self.ws.receive() if m.get("id") == 1]
            self.outcome = {"success": answer[0].get("success"),
                            "error": (answer[0].get("error") or {}).get("message"),
                            "response": (answer[0].get("result") or {}).get("response"),
                            "seconds": time.perf_counter() - start}
        thread = threading.Thread(target=run)
        thread.start()
        return thread

    def close(self) -> None:
        self.ws.close()



def main() -> int:
    ap = argparse.ArgumentParser()
    # `keep` is internal: what `start` runs, which keeps `hass` running across its own restarts.
    ap.add_argument("action", choices=["up", "down", "restart", "status", "keep"])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--fresh", action="store_true",
                    help="delete the config directory first and onboard from nothing")
    args = ap.parse_args()
    if args.action == "keep":
        return keep(args.config)
    if args.action == "up":
        up(args.config, args.fresh)
    elif args.action == "down":
        stop(args.config)
        print("(A) stopped")
    elif args.action == "restart":
        stop(args.config)
        start(args.config)
        wait_until_running()
        print("(A) restarted")
    else:
        print("up" if running() else "down")
    return 0


if __name__ == "__main__":
    sys.exit(main())
