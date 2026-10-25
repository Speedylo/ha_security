"""The house the end-to-end runs act on, (A), as their scripted world expects it.

Bridge step 5 (`notes/bridge_types_step5_prediction_20261025.md`). The stand-in's `WORLD` has a
living-room light that can be dimmed; (A)'s template light could only be switched until this step.

    H1   (A)'s light dims: brightness 180 at the start, 51 when set, off when switched off; the
         reset puts the world back at the stand-in's values
    H2   (A) can be stopped, freeing port 8123 for an unconfined arm, and started again keeping
         its bridge entry and the mediator's user

Requires (A) running: `python3 -m confine.house_a up --fresh` on the Pi. Leaves it running.

Run:  python3 -m confine.selftest_real_house
"""

from __future__ import annotations

import socket
import subprocess
import sys

from . import house_a
from .real_platform import RealPlatform

LIGHT = "light.living_room"
results: list[bool] = []


def check(claim: str, condition: bool, detail: str = "") -> None:
    results.append(bool(condition))
    print(f"{'  ok  ' if condition else '  FAIL'}  {claim}{f'  — {detail}' if detail else ''}")


def port_free(port: int = 8123) -> bool:
    probe = socket.socket()
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        probe.bind(("0.0.0.0", port))
    except OSError:
        return False
    finally:
        probe.close()
    return True


def main() -> int:
    if not house_a.running():
        print("(A) is not running: python3 -m confine.house_a up --fresh")
        return 2
    platform = RealPlatform()

    def light() -> tuple[str | None, dict]:
        return platform.read(LIGHT)

    def service(domain: str, name: str, data: dict) -> None:
        platform.call({"type": "call_service", "domain": domain, "service": name,
                       "service_data": data})   # a WebSocket call_service waits for the service

    print("\nH1 — (A)'s light dims\n")
    state, attributes = light()
    check("H1 the light's colour mode is brightness, and it starts on at 180",
          attributes.get("supported_color_modes") == ["brightness"] and state == "on"
          and attributes.get("brightness") == 180, f"{state} {attributes}")
    service("light", "turn_on", {"entity_id": LIGHT, "brightness": 51})
    state, attributes = light()
    check("H1 turned on at brightness 51, it is on at 51", state == "on"
          and attributes.get("brightness") == 51, f"{state} {attributes.get('brightness')}")
    service("light", "turn_off", {"entity_id": LIGHT})
    check("H1 turned off, it is off", light()[0] == "off", str(light()[0]))
    try:
        from .real_house import reset_world
        reset_world(platform)
        state, attributes = light()
        temperature = platform.read("sensor.living_room_temperature")[0]
        humidity = platform.read("sensor.living_room_humidity")[0]
        check("H1 the reset puts the world back: light on at 180, 21.4 °C, 48 %",
              state == "on" and attributes.get("brightness") == 180
              # As numbers: (A) writes a value set by `input_number.set_value` as 48.0 (step 5).
              and float(temperature or "nan") == 21.4 and float(humidity or "nan") == 48,
              f"{state} {attributes.get('brightness')} {temperature} {humidity}")
    except ImportError as err:
        check("H1 the reset puts the world back: light on at 180, 21.4 °C, 48 %", False, str(err))
    platform.close()

    print("\nH2 — (A) stops for an unconfined arm and starts again\n")
    down = subprocess.run([sys.executable, "-m", "confine.house_a", "down"],
                          capture_output=True, text=True, timeout=120)
    check("H2 stopping (A) frees port 8123", down.returncode == 0 and port_free(),
          (down.stderr or down.stdout).strip()[-120:])
    up = subprocess.run([sys.executable, "-m", "confine.house_a", "up"],
                        capture_output=True, text=True, timeout=300)
    again = RealPlatform() if up.returncode == 0 and house_a.running() else None
    # The config entries are an administrator's to list, not the mediator's.
    entries = (house_a._ws_call(house_a.TOKEN_FILE.read_text().strip(),
                                {"type": "config_entries/get", "domain": "confine_bridge"})
               .get("result") if again else [])
    check("H2 started again (not fresh), it has its bridge entry and accepts the mediator",
          again is not None and len(entries or []) == 1, (up.stderr or up.stdout).strip()[-120:])
    if again is not None:
        again.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
