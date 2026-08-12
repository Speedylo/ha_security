"""Shim of homeassistant.helpers.device_registry.

Device registry writes are not yet mediated. Devices are metadata rather than
capability, so this is deliberately a stub for the spike; a full version should
route registrations through the supervisor so a device's identifiers cannot be
used to squat on another integration's device.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .entity import DeviceInfo  # noqa: F401  (re-exported; integrations import it from here)


class DeviceEntryType(StrEnum):
    SERVICE = "service"


@dataclass
class DeviceEntry:
    """A registered device."""

    id: str = ""
    identifiers: set[tuple[str, str]] = field(default_factory=set)
    connections: set[tuple[str, str]] = field(default_factory=set)
    name: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    sw_version: str | None = None
    hw_version: str | None = None
    via_device_id: str | None = None
    entry_type: DeviceEntryType | None = None


class DeviceRegistry:
    """In-sandbox registry; not shared with real HA."""

    def __init__(self) -> None:
        self.devices: dict[str, DeviceEntry] = {}

    def async_get_or_create(self, *, config_entry_id: str = "", **kwargs: Any) -> DeviceEntry:
        identifiers = kwargs.get("identifiers") or set()
        key = str(sorted(identifiers))
        if key not in self.devices:
            self.devices[key] = DeviceEntry(
                id=key,
                identifiers=set(identifiers),
                name=kwargs.get("name"),
                manufacturer=kwargs.get("manufacturer"),
                model=kwargs.get("model"),
                sw_version=kwargs.get("sw_version"),
                entry_type=kwargs.get("entry_type"),
            )
        return self.devices[key]

    def async_get_device(self, identifiers: set | None = None, connections: set | None = None) -> DeviceEntry | None:
        return self.devices.get(str(sorted(identifiers or [])))


_REGISTRY = DeviceRegistry()


def async_get(hass: Any) -> DeviceRegistry:
    return _REGISTRY


def format_mac(mac: str) -> str:
    cleaned = mac.replace(":", "").replace("-", "").replace(".", "").lower()
    if len(cleaned) == 12:
        return ":".join(cleaned[index : index + 2] for index in range(0, 12, 2))
    return mac.lower()
