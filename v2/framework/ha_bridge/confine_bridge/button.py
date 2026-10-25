"""Buttons published by confined integrations (bridge step 1, 2026-10-25).

A button has no state of its own to mirror: Home Assistant's state for one is the time it was last
pressed **in this instance** (`ButtonEntity.state` is final). Pressing it sends the press to the
confined integration, through the mediator, as a switch's turn_on does.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity

from .entity import BridgedEntity, setup_platform


class BridgedButton(BridgedEntity, ButtonEntity):

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        pass

    def _restorable_empty(self) -> bool:
        # ButtonEntity restores its own last-pressed time.
        return False

    def _restore(self, state: str) -> None:
        pass

    async def async_press(self) -> None:
        await self._data.command(self._integration, self._published_id, "press", {})


async_setup_entry = setup_platform("button", BridgedButton)
