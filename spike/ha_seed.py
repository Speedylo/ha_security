#!/usr/bin/env python3
"""Give the real Home Assistant a house worth protecting.

A fresh HA contains a sun sensor and little else, which makes the adversarial
probe look easy — there is nothing interesting to steal. This creates the kind of
entities a real home has, so that "the integration could read every one of these
and the supervisor stopped it" is a claim about something.

These are states, not device integrations: creating them needs no hardware and no
custom components, and `/api/states` returns them exactly as it returns real ones,
which is all the firehose test depends on.

    ./ha_seed.py                  # seed the standard house
    ./ha_seed.py --list           # show what is there now
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOKEN_FILE = HERE / ".ha_token"

# The entities a weather widget or a quota sensor has no business seeing.
HOUSE = {
    "lock.front_door": ("locked", {"friendly_name": "Front door", "device_class": "lock"}),
    "lock.back_door": ("locked", {"friendly_name": "Back door", "device_class": "lock"}),
    "alarm_control_panel.home": ("armed_away", {"friendly_name": "Alarm"}),
    "device_tracker.younes": ("not_home", {"friendly_name": "Younes", "source_type": "gps"}),
    "camera.hallway": ("recording", {"friendly_name": "Hallway camera"}),
    "binary_sensor.holiday_mode": ("on", {"friendly_name": "Holiday mode"}),
    "binary_sensor.front_door_motion": ("off", {"friendly_name": "Front door motion", "device_class": "motion"}),
    "sensor.living_room_temperature": (
        "21.4",
        {"friendly_name": "Living room temperature", "unit_of_measurement": "°C", "device_class": "temperature"},
    ),
    "sensor.electricity_meter": (
        "8422.6",
        {"friendly_name": "Electricity meter", "unit_of_measurement": "kWh", "device_class": "energy"},
    ),
}


def request(url: str, token: str, method: str = "GET", payload: dict | None = None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw.strip() else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8123")
    parser.add_argument("--list", action="store_true", help="list current states and exit")
    args = parser.parse_args()

    if not TOKEN_FILE.exists():
        print("no .ha_token — run ./ha_onboard.py first", file=sys.stderr)
        return 1
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()

    if args.list:
        for state in sorted(request(f"{args.url}/api/states", token), key=lambda s: s["entity_id"]):
            print(f"  {state['entity_id']:48s} = {state['state']}")
        return 0

    for entity_id, (state, attributes) in HOUSE.items():
        request(
            f"{args.url}/api/states/{entity_id}",
            token,
            method="POST",
            payload={"state": state, "attributes": attributes},
        )
        print(f"  seeded {entity_id:44s} = {state}")

    total = len(request(f"{args.url}/api/states", token))
    print(f"\n{len(HOUSE)} entities seeded; {total} entities in the house")
    return 0


if __name__ == "__main__":
    sys.exit(main())
