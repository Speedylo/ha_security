#!/usr/bin/env python3
"""What sits behind the supervisor: a stub house, or a real Home Assistant.

The supervisor's job is to decide whether an operation is permitted. Where the
entity states actually live is a separate question, and keeping the two apart is
the point of this module: swapping ``StubHouse`` for ``RestHouse`` changes what
the framework talks to and changes **nothing** about policy. Every manifest check
still happens in supervisor.py, before anything here is called.

That separation is also the project's central claim in executable form — the
framework runs against a *stock, unmodified* Home Assistant, reached only through
the REST API it already exposes to any client holding a token. Nothing upstream
has to change.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

# A stand-in for the rest of the house: the entities a real HA instance would
# expose to anything holding a token. None of it is a quota sensor's business.
DEFAULT_HOUSE = {
    "lock.front_door": ("locked", {"friendly_name": "Front door"}),
    "alarm_control_panel.home": ("armed_away", {"friendly_name": "Alarm"}),
    "device_tracker.younes": ("not_home", {"friendly_name": "Younes"}),
    "sensor.living_room_temperature": ("21.4", {"friendly_name": "Living room temperature"}),
    "camera.hallway": ("recording", {"friendly_name": "Hallway camera"}),
    "binary_sensor.holiday_mode": ("on", {"friendly_name": "Holiday mode"}),
}


class House:
    """The state store the supervisor mediates access to."""

    def get(self, entity_id: str) -> dict | None:
        raise NotImplementedError

    def all(self) -> list[dict]:
        raise NotImplementedError

    def set(self, entity_id: str, state: Any, attributes: dict) -> dict:
        raise NotImplementedError

    def remove(self, entity_id: str) -> bool:
        raise NotImplementedError

    def call_service(self, domain: str, service: str, data: dict) -> Any:
        raise NotImplementedError

    def describe(self) -> str:
        raise NotImplementedError


class StubHouse(House):
    """In-memory stand-in. What the spike used before a real HA was available."""

    def __init__(self, seed: dict | None = None) -> None:
        source = DEFAULT_HOUSE if seed is None else seed
        self._states = {
            entity_id: {"entity_id": entity_id, "state": state, "attributes": attributes}
            for entity_id, (state, attributes) in source.items()
        }

    def get(self, entity_id: str) -> dict | None:
        return self._states.get(entity_id)

    def all(self) -> list[dict]:
        return list(self._states.values())

    def set(self, entity_id: str, state: Any, attributes: dict) -> dict:
        record = {"entity_id": entity_id, "state": state, "attributes": attributes or {}}
        self._states[entity_id] = record
        return record

    def remove(self, entity_id: str) -> bool:
        return self._states.pop(entity_id, None) is not None

    def call_service(self, domain: str, service: str, data: dict) -> Any:
        # Nothing to actuate in a stub; the decision was the interesting part.
        return None

    def describe(self) -> str:
        return f"stub house ({len(self._states)} entities)"


class HomeAssistantError(RuntimeError):
    """A real HA instance refused or failed a request."""


class RestHouse(House):
    """A real, unmodified Home Assistant, reached over its public REST API.

    The supervisor holds the token; the sandboxed integration never sees it and
    has no route to HA except through the bridge. That is what makes the
    confused-deputy attack a policy question rather than a network question.
    """

    def __init__(self, base_url: str, token: str, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    # -- transport -------------------------------------------------------
    def _request(self, method: str, path: str, payload: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=body, method=method)
        request.add_header("Authorization", f"Bearer {self._token}")
        request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as err:
            if err.code == 404 and method == "GET":
                return None
            detail = err.read().decode("utf-8", "replace")[:200]
            raise HomeAssistantError(f"HA {method} {path} -> HTTP {err.code}: {detail}") from err
        except urllib.error.URLError as err:
            raise HomeAssistantError(f"HA unreachable at {self.base_url}: {err.reason}") from err

    # -- House -----------------------------------------------------------
    def get(self, entity_id: str) -> dict | None:
        return self._request("GET", f"/api/states/{entity_id}")

    def all(self) -> list[dict]:
        return self._request("GET", "/api/states") or []

    def set(self, entity_id: str, state: Any, attributes: dict) -> dict:
        # HA coerces states to strings; do it here so what the supervisor logs
        # matches what HA stores.
        return self._request(
            "POST",
            f"/api/states/{entity_id}",
            {"state": "" if state is None else str(state), "attributes": attributes or {}},
        )

    def remove(self, entity_id: str) -> bool:
        try:
            self._request("DELETE", f"/api/states/{entity_id}")
            return True
        except HomeAssistantError:
            return False

    def call_service(self, domain: str, service: str, data: dict) -> Any:
        return self._request("POST", f"/api/services/{domain}/{service}", data or {})

    def describe(self) -> str:
        return f"real Home Assistant at {self.base_url}"

    def check(self) -> str:
        """Confirm the token works before a run starts, with a clear message if not."""
        info = self._request("GET", "/api/config")
        if not info:
            raise HomeAssistantError("HA returned no config; is the token valid?")
        return f"{info.get('location_name', 'Home')} (HA {info.get('version', '?')})"
