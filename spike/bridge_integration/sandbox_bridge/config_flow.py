"""Config flow for the sandboxed-integration bridge.

There is nothing to configure: the bridge exists so that entities published by
the supervisor have a config entry to belong to. A single instance is enough, and
the flow's only real job is to create that entry.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class SandboxBridgeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Single-instance flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Sandboxed Integration Bridge", data={})
