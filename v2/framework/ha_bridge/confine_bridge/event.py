"""Events published by confined integrations (bridge batch B3, 2026-10-31).

An event's state is the time it happened, and Home Assistant sets it itself when an event is
triggered. So each new event the sandbox publishes is triggered here, stamped by (A) when it
arrives, and automations on it fire as on a native event (decision 3). The last event already seen
is not triggered again: not when the sandbox republishes it, nor when (A) rebuilds the entity from
its roster after a restart, when (A) restores the event itself
(`notes/bridge_kinds_b3_prediction_20261031.md`).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity

from .entity import BridgedEntity, setup_platform


class BridgedEvent(BridgedEntity, EventEntity):

    _described = frozenset({"event_type", "event_types"})
    _seen: Any = None

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_event_types = list(attributes.get("event_types") or [])
        # The event's own attributes are the event's, not the entity's.
        details = self._attr_extra_state_attributes
        self._attr_extra_state_attributes = {}
        if self.hass is None:  # built from a definition: whatever it holds was seen before
            self._seen = state
            return
        if state in (None, "unknown", "unavailable") or state == self._seen:
            return
        self._seen = state
        try:
            self._trigger_event(str(attributes.get("event_type")), details)
        except ValueError:
            pass  # an event type the entity does not list: (A) keeps its last event

    def _restorable_empty(self) -> bool:
        return False

    def _restore(self, state: str) -> None:
        pass


async_setup_entry = setup_platform("event", BridgedEvent)
