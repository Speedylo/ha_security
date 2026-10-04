"""Config flow for the bridge. There is nothing to configure: the entry exists so that published
entities have a config entry to belong to, which is half of what the registry row means."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class ConfineBridgeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Single instance."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Confined Integration Bridge", data={})
