"""Switches published by confined integrations, and operable from the house (W1 step 2b).

Turning one on or off does not change its state here. It sends the command to the confined
integration, through the mediator, and waits for the integration's own handler to answer. The
new state then arrives the ordinary way, as a publish. So the switch shows what the integration
did, not what the user asked for, which is how a native integration's switch behaves.

Its state is the one published, as it is. Home Assistant declares a switch `on` or `off`, but an
integration may report more: `scheduler`'s is `triggered` for a minute after a slot fires, and
showing that as `off` showed the opposite of what was happening
(`notes/switch_state_mirror_prediction_20261026.md`).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity

from .entity import BridgedEntity, setup_platform


class BridgedSwitch(BridgedEntity, SwitchEntity):

    _published: str | None = None

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._published = None if state in (None, "unknown", "unavailable") else str(state)
        self._attr_is_on = None if self._published is None else self._published == "on"

    @property
    def state(self) -> str | None:  # type: ignore[override]
        # Overrides ToggleEntity's `@final` state, as `scheduler`'s own switch does; `@final` is
        # not enforced at run time.
        return self._published

    def _restorable_empty(self) -> bool:
        return self._published is None

    def _restore(self, state: str) -> None:
        self._take_state(state, {})

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._data.command(self._integration, self._published_id, "turn_on", kwargs)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._data.command(self._integration, self._published_id, "turn_off", kwargs)


async_setup_entry = setup_platform("switch", BridgedSwitch)
