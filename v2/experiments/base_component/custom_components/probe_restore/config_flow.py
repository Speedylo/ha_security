"""Config flow for the restore probe — present because the manifest declares one."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult


class RestoreProbeConfigFlow(ConfigFlow, domain="probe_restore"):
    """Handle a config flow for the restore probe."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title="restore probe", data=user_input)
