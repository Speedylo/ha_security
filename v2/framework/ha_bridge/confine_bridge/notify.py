"""Notification targets published by confined integrations (bridge batch B3, 2026-10-31).

A message sent from (A) goes to the integration through the mediator, which never writes its text
to the log (decision 4). The state, the time a message was last sent, is (A)'s own. Integrations
whose notifications are the older notify service rather than an entity (`alexa_media`) are not
covered (decision 5, `notes/bridge_kinds_b3_prediction_20261031.md`).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.notify import NotifyEntity

from .entity import BridgedEntity, setup_platform


class BridgedNotify(BridgedEntity, NotifyEntity):

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        pass

    def _restorable_empty(self) -> bool:
        return False

    def _restore(self, state: str) -> None:
        pass

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        data = {"message": message}
        if title is not None:
            data["title"] = title
        await self._data.command(self._integration, self._published_id, "send_message", data)


async_setup_entry = setup_platform("notify", BridgedNotify)
