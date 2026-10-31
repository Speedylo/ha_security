"""Lights published by confined integrations (bridge batch B1, 2026-10-31).

The colour modes, the brightness and the colour come from the integration's own instance, so (A)
draws the same card and works out each command as the integration's instance would. By the time
`async_turn_on` is called, (A) has turned a percentage into a brightness, a colour name or profile
into a colour, and dropped what this light does not support (`light/__init__.py`, 2026.8.3); what
is left goes to the integration through the mediator, which forwards only those keys
(`notes/bridge_kinds_b1_prediction_20261031.md`).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity, LightEntityFeature

from .entity import BridgedEntity, setup_platform

# The state attribute each `_attr_` is published under, as Home Assistant's own light writes it.
_PLAIN = {"brightness": "_attr_brightness", "color_temp_kelvin": "_attr_color_temp_kelvin",
          "min_color_temp_kelvin": "_attr_min_color_temp_kelvin",
          "max_color_temp_kelvin": "_attr_max_color_temp_kelvin",
          "effect": "_attr_effect", "effect_list": "_attr_effect_list"}
_COLOURS = {"hs_color": "_attr_hs_color", "rgb_color": "_attr_rgb_color",
            "rgbw_color": "_attr_rgbw_color", "rgbww_color": "_attr_rgbww_color",
            "xy_color": "_attr_xy_color"}


def _mode(value: Any) -> ColorMode | None:
    try:
        return ColorMode(value)
    except ValueError:
        return None


class BridgedLight(BridgedEntity, LightEntity):

    _described = frozenset({*_PLAIN, *_COLOURS, "color_mode", "supported_color_modes",
                            "supported_features"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_is_on = None if state not in ("on", "off") else state == "on"
        modes = {m for m in map(_mode, attributes.get("supported_color_modes") or [])
                 if m is not None}
        self._attr_supported_color_modes = modes or {ColorMode.ONOFF}
        self._attr_color_mode = _mode(attributes.get("color_mode"))
        if self._attr_color_mode not in self._attr_supported_color_modes:
            self._attr_color_mode = (next(iter(self._attr_supported_color_modes))
                                     if len(self._attr_supported_color_modes) == 1 else None)
        for key, name in _PLAIN.items():
            if attributes.get(key) is not None:
                setattr(self, name, attributes[key])
        for key, name in _COLOURS.items():
            value = attributes.get(key)
            setattr(self, name, tuple(value) if isinstance(value, (list, tuple)) else None)
        self._attr_supported_features = LightEntityFeature(
            int(attributes.get("supported_features") or 0))

    def _restorable_empty(self) -> bool:
        return self._attr_is_on is None

    def _restore(self, state: str) -> None:
        self._attr_is_on = None if state not in ("on", "off") else state == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._data.command(self._integration, self._published_id, "turn_on", kwargs)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._data.command(self._integration, self._published_id, "turn_off", kwargs)


async_setup_entry = setup_platform("light", BridgedLight)
