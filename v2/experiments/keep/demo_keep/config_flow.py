"""Nothing to ask: the entry it stores stands for an OAuth login's token."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult


class DemoKeepConfigFlow(ConfigFlow, domain="demo_keep"):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id("demo_keep")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Demo Keep", data={"token": "login", "refreshes": 0})
