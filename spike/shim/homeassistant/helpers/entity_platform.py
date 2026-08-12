"""Shim of homeassistant.helpers.entity_platform.

Real HA's EntityPlatform does registry bookkeeping, unique-id collision checks,
entity-id generation and the initial state write. Only the last two matter to an
integration that cannot tell the difference.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from ..core import HomeAssistant, callback
from .entity import Entity

# Type alias integrations annotate their platform setup with.
AddEntitiesCallback = Callable[..., None]
AddConfigEntryEntitiesCallback = AddEntitiesCallback


class EntityPlatform:
    """Owns the entities added by one platform module of one integration."""

    def __init__(self, hass: HomeAssistant, domain: str, platform: str) -> None:
        self.hass = hass
        self.domain = domain
        self.platform = platform
        self.entities: dict[str, Entity] = {}

    @callback
    def async_add_entities(
        self,
        new_entities: Iterable[Entity],
        update_before_add: bool = False,
        *,
        config_subentry_id: str | None = None,
    ) -> None:
        """The callback handed to a platform's ``async_setup_entry``.

        Sync on real HA too: it schedules the actual work. The generator the
        integration passes is consumed here so that any exception surfaces at
        setup rather than inside a background task.
        """
        entities = list(new_entities)
        self.hass.async_create_task(
            self._async_add_entities(entities, update_before_add),
            name=f"{self.domain}.{self.platform} add entities",
        )

    async def _async_add_entities(self, entities: list[Entity], update_before_add: bool) -> None:
        for entity in entities:
            entity.hass = self.hass
            entity._domain = self.domain
            entity._platform = self.platform
            entity.platform_name = self.domain

            if update_before_add:
                await entity.async_update()

            if entity.entity_id is None:
                entity.entity_id = entity._generate_entity_id(self.domain, self.platform)

            self.entities[entity.entity_id] = entity
            await entity.async_added_to_hass()
            entity.async_write_ha_state()

    async def async_reset(self) -> None:
        for entity in list(self.entities.values()):
            await entity.async_remove()
        self.entities.clear()


@callback
def async_get_current_platform() -> EntityPlatform | None:
    """Real HA resolves this from a ContextVar; unused in the spike."""
    return None
