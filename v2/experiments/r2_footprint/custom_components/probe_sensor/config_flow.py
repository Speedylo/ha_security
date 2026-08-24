"""Config flow for the R2 probe.

Present because real integrations have one and because Home Assistant expects a handler for
a domain that declares `config_flow: true`. The experiment adds its entry directly, so this
handler is never actually walked through.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult


class ProbeConfigFlow(ConfigFlow, domain="probe_sensor"):
    """Handle a config flow for the probe."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title="probe", data=user_input)
