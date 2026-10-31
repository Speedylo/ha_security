"""Vacuums published by confined integrations (bridge batch B2, 2026-10-31).

The state is the activity (cleaning, docked, ...); the attributes give the fan speeds and the
supported features. Every command goes to the integration through the mediator, raw commands
included, their parameters bounded in size but not in content (decision 1). Cleaning by room from
(A) does not work confined: (A) turns the rooms into the integration's segment ids, a call no
service in the sandbox takes (decision 4, `notes/bridge_kinds_b2_prediction_20261031.md`).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.vacuum import (StateVacuumEntity, VacuumActivity,
                                             VacuumEntityFeature)

from .entity import BridgedEntity, setup_platform


def _activity(value: Any) -> VacuumActivity | None:
    try:
        return VacuumActivity(value)
    except ValueError:
        return None


class BridgedVacuum(BridgedEntity, StateVacuumEntity):

    _described = frozenset({"fan_speed", "fan_speed_list", "battery_level", "battery_icon",
                            "supported_features"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_activity = _activity(state)
        self._attr_fan_speed = attributes.get("fan_speed")
        self._attr_fan_speed_list = attributes.get("fan_speed_list") or []
        self._attr_battery_level = attributes.get("battery_level")
        self._attr_supported_features = VacuumEntityFeature(
            int(attributes.get("supported_features") or 0))

    def _restorable_empty(self) -> bool:
        return self._attr_activity is None

    def _restore(self, state: str) -> None:
        self._attr_activity = _activity(state)

    async def _send(self, service: str, data: dict[str, Any] | None = None) -> None:
        await self._data.command(self._integration, self._published_id, service, data or {})

    async def async_start(self) -> None:
        await self._send("start")

    async def async_pause(self) -> None:
        await self._send("pause")

    async def async_stop(self, **kwargs: Any) -> None:
        await self._send("stop")

    async def async_return_to_base(self, **kwargs: Any) -> None:
        await self._send("return_to_base")

    async def async_clean_spot(self, **kwargs: Any) -> None:
        await self._send("clean_spot")

    async def async_locate(self, **kwargs: Any) -> None:
        await self._send("locate")

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        await self._send("set_fan_speed", {"fan_speed": fan_speed})

    async def async_send_command(self, command: str,
                                 params: dict[str, Any] | list[Any] | None = None,
                                 **kwargs: Any) -> None:
        data: dict[str, Any] = {"command": command}
        if params is not None:
            data["params"] = params
        await self._send("send_command", data)


async_setup_entry = setup_platform("vacuum", BridgedVacuum)
