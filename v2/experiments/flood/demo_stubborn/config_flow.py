"""Nothing to configure."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult


class DemoStubbornConfigFlow(ConfigFlow, domain="demo_stubborn"):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id("demo_stubborn")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Demo Stubborn", data={})
