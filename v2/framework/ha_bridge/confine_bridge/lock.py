"""Locks published by confined integrations (bridge batch B1, 2026-10-31).

The state and the code format come from the integration's own instance. (A) checks a typed code
against the format, or adds the code stored as the lock's default in (A) when none was typed, and
the command reaches the integration through the mediator with that code, because the integration
checks its own codes. The mediator forwards it and never writes it to its log; the integration
receives a stored default code as it would unconfined (decided 2026-10-31,
`notes/bridge_kinds_b1_prediction_20261031.md`).
"""

from __future__ import annotations

import re
from typing import Any

from homeassistant.components.lock import LockEntity, LockEntityFeature

from .entity import BridgedEntity, setup_platform


def _pattern(value: Any) -> str | None:
    """The published code format, if it is a regular expression (A) can compile."""
    if not isinstance(value, str):
        return None
    try:
        re.compile(value)
    except re.error:
        return None
    return value


class BridgedLock(BridgedEntity, LockEntity):

    _described = frozenset({"code_format", "changed_by", "supported_features"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_is_locked = (None if state not in ("locked", "unlocked") else
                                state == "locked")
        self._attr_is_locking = state == "locking"
        self._attr_is_unlocking = state == "unlocking"
        self._attr_is_jammed = state == "jammed"
        self._attr_is_open = state == "open"
        self._attr_is_opening = state == "opening"
        self._attr_code_format = _pattern(attributes.get("code_format"))
        self._attr_changed_by = attributes.get("changed_by")
        self._attr_supported_features = LockEntityFeature(
            int(attributes.get("supported_features") or 0))

    def _restorable_empty(self) -> bool:
        return self.state is None

    def _restore(self, state: str) -> None:
        self._take_state(state, {})

    async def _send(self, service: str, code: str | None) -> None:
        await self._data.command(self._integration, self._published_id, service,
                                 {} if code is None else {"code": code})

    async def async_lock(self, **kwargs: Any) -> None:
        await self._send("lock", kwargs.get("code"))

    async def async_unlock(self, **kwargs: Any) -> None:
        await self._send("unlock", kwargs.get("code"))

    async def async_open(self, **kwargs: Any) -> None:
        await self._send("open", kwargs.get("code"))


async_setup_entry = setup_platform("lock", BridgedLock)
