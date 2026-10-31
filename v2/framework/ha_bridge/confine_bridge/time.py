"""Times of day published by confined integrations (bridge batch B3, 2026-10-31).

Setting one sends it to the integration as "HH:MM:SS", which its own instance parses again; the
time it settled on arrives back as a publish (`notes/bridge_kinds_b3_prediction_20261031.md`).
"""

from __future__ import annotations

from datetime import time as dt_time
from typing import Any

from homeassistant.components.time import TimeEntity

from .entity import BridgedEntity, setup_platform


def _clock(value: Any) -> dt_time | None:
    try:
        return dt_time.fromisoformat(str(value))
    except ValueError:
        return None


class BridgedTime(BridgedEntity, TimeEntity):

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_native_value = _clock(state)

    def _restorable_empty(self) -> bool:
        return self._attr_native_value is None

    def _restore(self, state: str) -> None:
        self._attr_native_value = _clock(state)

    async def async_set_value(self, value: dt_time) -> None:
        await self._data.command(self._integration, self._published_id, "set_value",
                                 {"time": value.isoformat()})


async_setup_entry = setup_platform("time", BridgedTime)
