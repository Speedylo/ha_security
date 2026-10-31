"""Sirens published by confined integrations (bridge batch B2, 2026-10-31).

(A) checks a tone against the published `available_tones` and drops what the siren does not
support. When the tones are a mapping, (A) hands the entity the tone's key; but the keys crossed as
JSON, so a numeric key arrives as a string the integration's own instance would reject. The tone
therefore goes on by name, which the integration's instance maps back to its own key (decision 5,
`notes/bridge_kinds_b2_prediction_20261031.md`).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.siren import SirenEntity, SirenEntityFeature

from .entity import BridgedEntity, setup_platform


class BridgedSiren(BridgedEntity, SirenEntity):

    _described = frozenset({"available_tones", "supported_features"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_is_on = None if state not in ("on", "off") else state == "on"
        tones = attributes.get("available_tones")
        self._attr_available_tones = tones if isinstance(tones, (dict, list)) else None
        self._attr_supported_features = SirenEntityFeature(
            int(attributes.get("supported_features") or 0))

    def _restorable_empty(self) -> bool:
        return self._attr_is_on is None

    def _restore(self, state: str) -> None:
        self._attr_is_on = None if state not in ("on", "off") else state == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        data = {k: v for k, v in kwargs.items() if k in ("tone", "duration", "volume_level")}
        tones = self._attr_available_tones
        if isinstance(tones, dict) and data.get("tone") in tones:
            data["tone"] = tones[data["tone"]]
        await self._data.command(self._integration, self._published_id, "turn_on", data)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._data.command(self._integration, self._published_id, "turn_off", {})


async_setup_entry = setup_platform("siren", BridgedSiren)
