"""Shim of homeassistant.helpers.typing."""

from __future__ import annotations

from typing import Any

ConfigType = dict[str, Any]
DiscoveryInfoType = dict[str, Any]
ServiceDataType = dict[str, Any]
StateType = str | int | float | None
TemplateVarsType = dict[str, Any] | None
EventType = Any
VolDictType = dict[Any, Any]
VolSchemaType = Any


class UndefinedType:
    """Sentinel type, as in HA."""

    def __repr__(self) -> str:  # pragma: no cover
        return "UNDEFINED"

    def __bool__(self) -> bool:
        return False


UNDEFINED = UndefinedType()
