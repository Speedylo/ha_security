"""What the end-to-end harnesses need to run a confined arm against the house's real (A).

Bridge step 5 (`notes/bridge_types_step5_prediction_20261025.md`). Until this step every harness
but `endtoend` published to the stand-in (`platform.Platform`), which accepts any entity. Here the
same arms act on (A) through `RealPlatform` and the bridge, and these are the four things that
differ:

    reset_world      (A)'s world set to the stand-in's `WORLD` values before a run
    apply_step       a scripted world step as a real service call in (A)
    house_stopped    (A) stopped around an unconfined arm, which needs port 8123 (F56)
    in_house         after a run, what (A) holds for each entity the integration published
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from contextlib import contextmanager
from typing import Iterator

from .real_platform import RealPlatform

LIGHT = "light.living_room"


def _service(platform: RealPlatform, domain: str, service: str, data: dict) -> None:
    platform.call({"type": "call_service", "domain": domain, "service": service,
                   "service_data": data})   # a WebSocket call_service waits for the service


def reset_world(platform: RealPlatform) -> None:
    """(A)'s helpers to the stand-in's `WORLD`: 21.4 °C, 48 %, the light on at 180."""
    for helper, value in (("input_number.living_room_temperature", 21.4),
                          ("input_number.living_room_humidity", 48),
                          ("input_number.living_room_brightness", 180)):
        _service(platform, "input_number", "set_value", {"entity_id": helper, "value": value})
    _service(platform, "input_boolean", "turn_on",
             {"entity_id": "input_boolean.living_room_light"})


def apply_step(platform: RealPlatform, step: dict) -> None:
    """A scripted world step — the light on at a brightness, or off — as (A)'s own service."""
    if step["entity"] != LIGHT:
        raise ValueError(f"no real counterpart for a world step on {step['entity']}")
    if step["state"] == "on":
        brightness = (step.get("attributes") or {}).get("brightness")
        _service(platform, "light", "turn_on",
                 {"entity_id": LIGHT, **({"brightness": brightness} if brightness else {})})
    else:
        _service(platform, "light", "turn_off", {"entity_id": LIGHT})


def _house_a(*arguments: str) -> None:
    done = subprocess.run([sys.executable, "-m", "confine.house_a", *arguments],
                          capture_output=True, text=True, timeout=300)
    if done.returncode != 0:
        raise RuntimeError(f"house_a {' '.join(arguments)}: "
                           f"{(done.stderr or done.stdout).strip()[-200:]}")


@contextmanager
def house_stopped() -> Iterator[None]:
    """(A) down for an unconfined arm, which binds port 8123 itself (F56); up again after.

    Started again, not fresh: the bridge's entry, the mediator's user and the entities the
    confined arms already published stay, as they do in a house that restarts.
    """
    _house_a("down")
    try:
        yield
    finally:
        _house_a("up")


def _same(shown: str | None, published: str) -> bool:
    """Equal as strings, or as times when both are ISO date-times: (A) writes a timestamp with a
    `T`, and an integration may publish the same instant with a space (F67)."""
    if shown == published:
        return True
    try:
        return (shown is not None
                and datetime.fromisoformat(shown) == datetime.fromisoformat(published))
    except ValueError:
        return False


def in_house(platform: RealPlatform, identity: str, published: list[dict]) -> list[dict]:
    """For each entity the integration had accepted, what (A) holds for it at the end of the run.

    `published` is the sandbox's own record (`entity`, `state`, `accepted`), in order; the last
    accepted state of each entity is what (A) should show. A button's state in (A) is its last
    press there, not mirrored, so it is reported but not compared.
    """
    registry = {e["entity_id"]: e for e in platform.call({"type": "config/entity_registry/list"})}
    states = {s["entity_id"]: s["state"] for s in platform.call({"type": "get_states"})}
    last: dict[str, str] = {}
    for entry in published:
        if entry.get("accepted"):
            last[str(entry.get("entity"))] = str(entry.get("state"))
    rows = []
    for entity, state in last.items():
        landed = platform.published.get((identity, entity), "")
        row = registry.get(landed, {})
        domain = entity.partition(".")[0]
        rows.append({
            "entity": entity, "in_house": landed, "published_state": state,
            "house_state": states.get(landed),
            "owned_by_bridge": row.get("platform") == "confine_bridge"
                               and row.get("unique_id") == f"{identity}:{entity}",
            "same_domain": landed.partition(".")[0] == domain,
            "state_matches": True if domain == "button" else _same(states.get(landed), state),
        })
    return rows
