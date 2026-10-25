"""Alarm panels published by confined integrations (bridge step 3, 2026-10-25).

The state is the alarm state. Arming, disarming and triggering go to the integration through the
mediator, with the code the user typed, because the integration checks its own codes (`alarmo`
does). The mediator forwards the code and never writes it to its log.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.alarm_control_panel import (AlarmControlPanelEntity,
                                                          AlarmControlPanelEntityFeature,
                                                          AlarmControlPanelState, CodeFormat)

from .entity import BridgedEntity, setup_platform


class BridgedAlarmPanel(BridgedEntity, AlarmControlPanelEntity):

    _described = frozenset({"code_format", "code_arm_required", "changed_by",
                            "supported_features"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        try:
            self._attr_alarm_state = AlarmControlPanelState(state)
        except ValueError:
            self._attr_alarm_state = None
        try:
            self._attr_code_format = (CodeFormat(attributes["code_format"])
                                      if attributes.get("code_format") else None)
        except ValueError:
            self._attr_code_format = None
        self._attr_code_arm_required = bool(attributes.get("code_arm_required", True))
        self._attr_changed_by = attributes.get("changed_by")
        self._attr_supported_features = AlarmControlPanelEntityFeature(
            int(attributes.get("supported_features") or 0))

    def _restorable_empty(self) -> bool:
        return self._attr_alarm_state is None

    def _restore(self, state: str) -> None:
        try:
            self._attr_alarm_state = AlarmControlPanelState(state)
        except ValueError:
            pass

    async def _send(self, service: str, code: str | None) -> None:
        await self._data.command(self._integration, self._published_id, service,
                                 {} if code is None else {"code": code})

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        await self._send("alarm_disarm", code)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        await self._send("alarm_arm_home", code)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        await self._send("alarm_arm_away", code)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        await self._send("alarm_arm_night", code)

    async def async_alarm_arm_vacation(self, code: str | None = None) -> None:
        await self._send("alarm_arm_vacation", code)

    async def async_alarm_arm_custom_bypass(self, code: str | None = None) -> None:
        await self._send("alarm_arm_custom_bypass", code)

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        await self._send("alarm_trigger", code)


async_setup_entry = setup_platform("alarm_control_panel", BridgedAlarmPanel)
