"""The way back after a cut-off, or a start that did not happen: one button, in the Repairs panel.

The mediator stops a confined integration that floods it with refused requests, and keeps it
stopped until someone asks for it back (`notes/flood_cutoff_prediction.md`). That someone is
whoever administers Home Assistant (only an administrator can use a Repairs action), and the asking
happens in Home Assistant's own screens, where it already asks them to fix things, never in a
terminal. The flow offers exactly one action, and it is a safe one: a restart runs
the integration again under the same manifest, so a user who confirms without reading cannot give
it anything it did not already have.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.repairs import RepairsFlow, RepairsFlowResult
from homeassistant.core import HomeAssistant

from .const import DOMAIN, ISSUE_NOT_STARTED


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


class NotStartedRepairFlow(RepairsFlow):
    """The way to start an integration the supervisor did not start (F57c).

    One screen and one button, and the button says what it does. Not approved: the screen is
    what the integration asks for, and **Allow and start** approves exactly that, by sending back
    the identity and grant digest the screen was rendered from; the supervisor records nothing if
    either has moved since. Too much stored data: **Try again** only asks the supervisor to check
    again, and grants nothing. Closing the window does nothing at all.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        self._integration = str(data.get("integration", ""))
        self._reason = str(data.get("reason", ""))

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> RepairsFlowResult:
        if self._reason == "not_approved":
            return await self.async_step_allow()
        return await self.async_step_retry()

    async def async_step_allow(
            self, user_input: dict[str, Any] | None = None) -> RepairsFlowResult:
        if user_input is not None:
            return self._send({"approve": self._integration,
                               "identity": self._data.get("identity", ""),
                               "grant": self._data.get("grant", "")})
        return self.async_show_form(
            step_id="allow", data_schema=vol.Schema({}),
            description_placeholders={"name": self._integration,
                                      "details": str(self._data.get("details", ""))})

    async def async_step_retry(
            self, user_input: dict[str, Any] | None = None) -> RepairsFlowResult:
        if user_input is not None:
            return self._send({"retry": self._integration})
        return self.async_show_form(step_id="retry", data_schema=vol.Schema({}),
                                    description_placeholders={"name": self._integration})

    def _send(self, message: dict[str, Any]) -> RepairsFlowResult:
        data = self.hass.data.get(DOMAIN)
        if data is None or not data.tell_supervisor(message):
            # Aborting keeps the issue: nothing was sent, so the household still needs it.
            return self.async_abort(reason="not_connected")
        # Finishing removes the issue. If the start is refused again, the supervisor raises it
        # again, with the screen as things now stand.
        return self.async_create_entry(data={})


async def async_create_fix_flow(hass: HomeAssistant, issue_id: str,
                                data: dict[str, Any] | None) -> RepairsFlow:
    if issue_id.startswith(ISSUE_NOT_STARTED.format("")):
        return NotStartedRepairFlow(data or {})
    return RestartRepairFlow(str((data or {}).get("integration") or issue_id))
