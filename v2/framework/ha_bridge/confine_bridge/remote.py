"""Remotes published by confined integrations (bridge batch B2, 2026-10-31).

The activities come from the integration's own instance. (A) adds its defaults to a command (one
repeat, no hold) before the entity sees it; the commands, learning and deleting a command all go
to the integration through the mediator, which bounds each command at 4096 characters, at most 64
a call, because raw codes can be long (decisions 2 and 3,
`notes/bridge_kinds_b2_prediction_20261031.md`).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import RemoteEntity, RemoteEntityFeature

from .entity import BridgedEntity, setup_platform


def _pick(kwargs: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    data = {k: kwargs[k] for k in keys if kwargs.get(k) is not None}
    if "command" in data:
        data["command"] = list(data["command"])
    return data


class BridgedRemote(BridgedEntity, RemoteEntity):

    _described = frozenset({"activity_list", "current_activity", "supported_features"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_is_on = None if state not in ("on", "off") else state == "on"
        self._attr_activity_list = attributes.get("activity_list")
        self._attr_current_activity = attributes.get("current_activity")
        self._attr_supported_features = RemoteEntityFeature(
            int(attributes.get("supported_features") or 0))

    def _restorable_empty(self) -> bool:
        return self._attr_is_on is None

    def _restore(self, state: str) -> None:
        self._attr_is_on = None if state not in ("on", "off") else state == "on"

    async def _send(self, service: str, data: dict[str, Any]) -> None:
        await self._data.command(self._integration, self._published_id, service, data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send("turn_on", _pick(kwargs, ("activity",)))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send("turn_off", _pick(kwargs, ("activity",)))

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        await self._send("send_command", {"command": list(command), **_pick(
            kwargs, ("device", "num_repeats", "delay_secs", "hold_secs"))})

    async def async_learn_command(self, **kwargs: Any) -> None:
        await self._send("learn_command", _pick(
            kwargs, ("device", "command", "command_type", "alternative", "timeout")))

    async def async_delete_command(self, **kwargs: Any) -> None:
        await self._send("delete_command", _pick(kwargs, ("command", "device")))


async_setup_entry = setup_platform("remote", BridgedRemote)
