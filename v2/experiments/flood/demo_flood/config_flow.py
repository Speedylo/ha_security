"""Nothing to configure."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult


class DemoFloodConfigFlow(ConfigFlow, domain="demo_flood"):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id("demo_flood")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Demo Flood", data={})
