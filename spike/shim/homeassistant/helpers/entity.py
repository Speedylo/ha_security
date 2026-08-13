"""Shim of homeassistant.helpers.entity.

The important method is ``async_write_ha_state``: on real HA it writes straight
into the in-process state machine, and on the way it decides which attributes
become visible. Here it is the point where an entity leaves the sandbox, so it
is also the point the supervisor checks against the manifest's ``publishes``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..const import ATTR_ATTRIBUTION, EntityCategory, STATE_UNAVAILABLE, STATE_UNKNOWN
from ..core import HomeAssistant, callback
from ..util import slugify
from ..util.frozen_dataclass_compat import FrozenOrThawed

# Populated by the runner from the integration's translations/<lang>.json, so
# friendly names match what HA would render. Keyed by (domain, platform, key).
_TRANSLATIONS: dict[str, dict] = {}


def set_translations(domain: str, data: dict) -> None:
    _TRANSLATIONS[domain] = data


def _translated_name(domain: str, platform: str, translation_key: str | None) -> str | None:
    if not translation_key:
        return None
    entry = (
        _TRANSLATIONS.get(domain, {})
        .get("entity", {})
        .get(platform, {})
        .get(translation_key, {})
    )
    return entry.get("name")


class DeviceInfo(dict):
    """Shim of helpers.entity.DeviceInfo (a TypedDict on real HA)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**{key: value for key, value in kwargs.items() if value is not None})


class EntityDescription(metaclass=FrozenOrThawed, frozen_or_thawed=True):
    """Description of an entity.

    Not a dataclass itself, deliberately — see
    ``homeassistant.util.frozen_dataclass_compat``. That is what lets one
    integration subclass this with a plain ``@dataclass`` and mutate the result
    while another subclasses it with ``@dataclass(frozen=True)``.
    """

    key: str
    device_class: str | None = None
    entity_category: EntityCategory | None = None
    entity_registry_enabled_default: bool = True
    entity_registry_visible_default: bool = True
    force_update: bool = False
    icon: str | None = None
    has_entity_name: bool = False
    name: str | None = None
    translation_key: str | None = None
    translation_placeholders: dict[str, str] | None = None
    unit_of_measurement: str | None = None


class Entity:
    """Base entity."""

    # Set by the entity platform when the entity is added.
    hass: HomeAssistant | None = None
    platform_name: str = ""
    entity_id: str | None = None
    entity_description: EntityDescription | None = None

    _attr_name: str | None = None
    _attr_unique_id: str | None = None
    _attr_icon: str | None = None
    _attr_available: bool = True
    _attr_device_info: DeviceInfo | None = None
    _attr_attribution: str | None = None
    _attr_entity_category: EntityCategory | None = None
    _attr_has_entity_name: bool = False
    _attr_should_poll: bool = True
    _attr_extra_state_attributes: dict[str, Any] | None = None
    _attr_translation_key: str | None = None
    _attr_translation_placeholders: dict[str, str] | None = None
    _attr_unit_of_measurement: str | None = None

    def __init__(self) -> None:
        self._on_remove: list[Callable] = []

    # ------------------------------------------------------------------
    # Properties integrations override
    # ------------------------------------------------------------------
    @property
    def should_poll(self) -> bool:
        return self._attr_should_poll

    @property
    def unique_id(self) -> str | None:
        return self._attr_unique_id

    @property
    def name(self) -> str | None:
        if self._attr_name is not None:
            return self._attr_name
        description = self.entity_description
        if description is not None:
            if description.name is not None:
                return description.name
            translated = _translated_name(self._domain, self._platform, description.translation_key)
            if translated:
                placeholders = (
                    self._attr_translation_placeholders
                    or description.translation_placeholders
                    or {}
                )
                try:
                    return translated.format(**placeholders)
                except (KeyError, IndexError):
                    return translated
            if description.key:
                return description.key.replace("_", " ").capitalize()
        return None

    @property
    def state(self) -> Any:
        return STATE_UNKNOWN

    @property
    def available(self) -> bool:
        return self._attr_available

    @property
    def icon(self) -> str | None:
        if self._attr_icon is not None:
            return self._attr_icon
        return self.entity_description.icon if self.entity_description else None

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._attr_device_info

    @property
    def device_class(self) -> str | None:
        if self.entity_description is not None:
            return self.entity_description.device_class
        return None

    @property
    def entity_category(self) -> EntityCategory | None:
        if self._attr_entity_category is not None:
            return self._attr_entity_category
        return self.entity_description.entity_category if self.entity_description else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        return self._attr_extra_state_attributes

    @property
    def has_entity_name(self) -> bool:
        return self._attr_has_entity_name

    @property
    def unit_of_measurement(self) -> str | None:
        return self._attr_unit_of_measurement

    @property
    def attribution(self) -> str | None:
        return self._attr_attribution

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def async_added_to_hass(self) -> None:
        """Called once the entity is registered."""

    async def async_will_remove_from_hass(self) -> None:
        """Called before the entity goes away."""

    async def async_update(self) -> None:
        """Poll for new data (unused by coordinator-driven entities)."""

    @callback
    def async_on_remove(self, func: Callable) -> None:
        if not hasattr(self, "_on_remove"):
            self._on_remove = []
        self._on_remove.append(func)

    async def async_remove(self, *, force_remove: bool = False) -> None:
        await self.async_will_remove_from_hass()
        for func in reversed(getattr(self, "_on_remove", [])):
            func()

    # ------------------------------------------------------------------
    # State writing — the sandbox boundary
    # ------------------------------------------------------------------
    @callback
    def async_write_ha_state(self) -> None:
        if self.hass is None or self.entity_id is None:
            raise RuntimeError(
                f"Entity {type(self).__name__} tried to write state before being added"
            )

        if not self.available:
            state: Any = STATE_UNAVAILABLE
            attributes: dict[str, Any] = {}
        else:
            state = self.state
            if state is None:
                state = STATE_UNKNOWN
            attributes = self._build_attributes()

        self.hass.states.async_set(self.entity_id, state, attributes)

    def _build_attributes(self) -> dict[str, Any]:
        attributes: dict[str, Any] = {}
        if (extra := self.extra_state_attributes) is not None:
            attributes.update(extra)
        if (name := self.name) is not None:
            attributes["friendly_name"] = name
        if (unit := self.unit_of_measurement) is not None:
            attributes["unit_of_measurement"] = unit
        if (icon := self.icon) is not None:
            attributes["icon"] = icon
        if (device_class := self.device_class) is not None:
            attributes["device_class"] = device_class
        if (attribution := self.attribution) is not None:
            attributes[ATTR_ATTRIBUTION] = attribution
        return attributes

    @callback
    def schedule_update_ha_state(self, force_refresh: bool = False) -> None:
        self.async_write_ha_state()

    async def async_update_ha_state(self, force_refresh: bool = False) -> None:
        if force_refresh:
            await self.async_update()
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Internals used by the entity platform
    # ------------------------------------------------------------------
    _domain: str = ""
    _platform: str = ""

    def _generate_entity_id(self, domain: str, platform: str) -> str:
        basis = self.name or self.unique_id or type(self).__name__
        return f"{platform}.{slugify(f'{domain}_{basis}')}"

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.entity_id}>"


class ToggleEntity(Entity):
    """Base for on/off entities."""

    _attr_is_on: bool | None = None

    @property
    def is_on(self) -> bool | None:
        return self._attr_is_on

    @property
    def state(self) -> str | None:
        if (is_on := self.is_on) is None:
            return None
        return "on" if is_on else "off"

    async def async_turn_on(self, **kwargs: Any) -> None:
        raise NotImplementedError

    async def async_turn_off(self, **kwargs: Any) -> None:
        raise NotImplementedError


@callback
def async_generate_entity_id(
    entity_id_format: str,
    name: str | None,
    current_ids: list[str] | None = None,
    hass: HomeAssistant | None = None,
) -> str:
    """Shim of helpers.entity.async_generate_entity_id."""
    preferred = entity_id_format.format(slugify(name or "unnamed"))
    if not current_ids:
        return preferred
    if preferred not in current_ids:
        return preferred
    index = 2
    while f"{preferred}_{index}" in current_ids:
        index += 1
    return f"{preferred}_{index}"


__all__ = [
    "DeviceInfo",
    "Entity",
    "EntityCategory",
    "EntityDescription",
    "ToggleEntity",
    "async_generate_entity_id",
    "set_translations",
]
