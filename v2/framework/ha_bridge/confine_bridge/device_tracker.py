"""Device trackers published by confined integrations (bridge batch B3, 2026-10-31).

Display only. A GPS tracker publishes coordinates, and (A) works out home or away from **its own
zones**: the sandbox's instance has none of the house's. A scanner (Bluetooth, router) publishes
home or not_home. Scanners are built on `BaseScannerEntity`, not `ScannerEntity`, which would
replace the bridge's unique id with the device's MAC and attach the entity to (A)'s network
devices; the IP, MAC and host name stay ordinary attributes
(`notes/bridge_kinds_b3_prediction_20261031.md`).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import (BaseScannerEntity, SourceType,
                                                     TrackerEntity)

from .entity import BridgedEntity, setup_platform

_NO_STATE = (None, "unknown", "unavailable")


def _source(value: Any, default: SourceType) -> SourceType:
    try:
        return SourceType(value)
    except ValueError:
        return default


class BridgedTracker(BridgedEntity, TrackerEntity):

    _described = frozenset({"source_type", "latitude", "longitude", "gps_accuracy",
                            "battery_level", "in_zones"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_source_type = _source(attributes.get("source_type"), SourceType.GPS)
        self._attr_latitude = attributes.get("latitude")
        self._attr_longitude = attributes.get("longitude")
        self._attr_location_accuracy = attributes.get("gps_accuracy") or 0
        self._attr_battery_level = attributes.get("battery_level")
        # No coordinates: the state is the integration's own place name, as it published it.
        self._attr_location_name = (str(state) if self._attr_latitude is None
                                    and state not in _NO_STATE else None)

    def _restorable_empty(self) -> bool:
        return False

    def _restore(self, state: str) -> None:
        pass


class BridgedScanner(BridgedEntity, BaseScannerEntity):

    _described = frozenset({"source_type", "battery_level"})
    _connected: bool | None = None
    _source_type = SourceType.ROUTER

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._source_type = _source(attributes.get("source_type"), SourceType.ROUTER)
        self._connected = None if state in _NO_STATE else state == "home"

    @property
    def source_type(self) -> SourceType:
        return self._source_type

    @property
    def is_connected(self) -> bool | None:
        # None while the integration does not know: (A) then shows no state, not "away".
        return self._connected

    def _restorable_empty(self) -> bool:
        return False

    def _restore(self, state: str) -> None:
        pass


def _tracker(definition: dict[str, Any], data) -> BridgedEntity:
    source = (definition.get("attributes") or {}).get("source_type")
    if source in (None, SourceType.GPS, "gps"):
        return BridgedTracker(definition, data)
    return BridgedScanner(definition, data)


async_setup_entry = setup_platform("device_tracker", _tracker)
