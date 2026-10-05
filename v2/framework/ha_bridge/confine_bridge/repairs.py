"""The way back after a cut-off: one button, in the Repairs panel, that restarts the integration.

The mediator stops a confined integration that floods it with refused requests, and keeps it
stopped until someone asks for it back (`notes/flood_cutoff_prediction.md`). That someone is a
member of the household, not an administrator, so the asking happens where Home Assistant already
asks them to fix things. The flow offers exactly one action, and it is a safe one: a restart runs
the integration again under the same manifest, so a user who confirms without reading cannot give
it anything it did not already have.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.repairs import RepairsFlow, RepairsFlowResult
from homeassistant.core import HomeAssistant

from .const import DOMAIN


class RestartRepairFlow(RepairsFlow):
    """Confirm, then ask the mediator to restart the integration."""

    def __init__(self, integration: str) -> None:
        self._integration = integration

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> RepairsFlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(
            self, user_input: dict[str, Any] | None = None) -> RepairsFlowResult:
        if user_input is not None:
            data = self.hass.data.get(DOMAIN)
            if data is None or not data.request_restart(self._integration):
                # Aborting keeps the issue: nothing was restarted, so the user still needs it.
                return self.async_abort(reason="not_connected")
            # Finishing the flow removes the issue (`RepairsFlowManager.async_finish_flow`).
            return self.async_create_entry(data={})
        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}),
                                    description_placeholders={"name": self._integration})


async def async_create_fix_flow(hass: HomeAssistant, issue_id: str,
                                data: dict[str, Any] | None) -> RepairsFlow:
    return RestartRepairFlow(str((data or {}).get("integration") or issue_id))
