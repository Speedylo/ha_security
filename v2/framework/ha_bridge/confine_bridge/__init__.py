"""The confined-integration bridge: the framework's only code inside the house's Home Assistant.

W1 step 2 (`notes/w1_step2_real_platform_prediction.md`). A confined integration runs in its
sandbox against a private, empty Home Assistant; the mediator decides what it may do; and this
component is where a permitted publish becomes an entity in the house's real instance — one with
a `unique_id`, an entity-registry row, a device, a config entry, and a state that survives a
restart. Publishing over `/api/states` gives none of those (§6.10.2), and 83% of integrations
publish through the path that does (§5.6.1).

Adapted from the 2026-08 spike's `sandbox_bridge` (`00_METHOD.md` §5 permits reusing its code;
its *finding* is re-measured in §7.37, not cited). Two changes from the spike:

  - **Publishing is a WebSocket command, not a service.** A service appears in the instance's
    service list, where any automation, script or dashboard button could call it and publish as a
    confined integration. A WebSocket command is reachable only by a client holding a token, and
    these admit only an admin or the one user an admin designated as the mediator. Until
    2026-10-06 they were admin-only, which forced the mediator to hold an admin token (F45).
  - **It answers with the entity id the registry actually assigned**, so the mediator knows where
    the entity landed if the integration's own id was already taken.

**Trust.** This component is trusted, and it loads, imports and executes nothing from any confined
integration. A state is stored as given and attributes as plain data. Every decision about whether
a publish is allowed was made by the mediator before this command was sent: the bridge decides
nothing, which is §5.3's reason for keeping enforcement out of the platform's process.
"""

from __future__ import annotations

import asyncio
import functools
import itertools
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .const import (COMMAND_TIMEOUT, DOMAIN, ISSUE_CUT_OFF, ISSUE_NOT_STARTED,
                    MAX_PENDING_COMMANDS, NOT_STARTED_REASONS,
                    SIGNAL_NEW_ENTITY, STORAGE_KEY, STORAGE_VERSION, SUPPORTED)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


#: The config entry key holding the user designated as the mediator (finding F45).
MEDIATOR_USER = "mediator_user"


def require_mediator(func):
    """Admit an admin, or the one user an admin designated as the mediator, and no one else.

    Until 2026-10-06 every bridge command required admin, so the mediator had to hold an admin
    token: a token that can also create users, install integrations and change the house's
    configuration. That was this component's choice, not the platform's (finding F45). Now the
    mediator runs as an ordinary user, and this gate lets that one user through. Naming it is an
    admin's act (`confine_bridge/designate_mediator`), so no other non-admin user can publish as a
    confined integration. Refused exactly as Home Assistant's own `require_admin` refuses.
    """
    @functools.wraps(func)
    def with_mediator(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                      msg: dict[str, Any]) -> None:
        user = connection.user
        entries = hass.config_entries.async_entries(DOMAIN)
        designated = entries[0].data.get(MEDIATOR_USER) if entries else None
        if user is None or not (user.is_admin or (designated and user.id == designated)):
            raise Unauthorized
        func(hass, connection, msg)
    return with_mediator


class BridgeData:
    """Every entity published so far, and the live objects standing in for them."""

    def __init__(self, store: Store) -> None:
        self.store = store
        self.roster: dict[str, dict[str, Any]] = {}       # unique_id -> definition
        self.live: dict[str, Any] = {}                     # unique_id -> entity
        self.waiting: dict[str, asyncio.Future] = {}       # unique_id -> its entity_id, once added
        # W1 step 2b: the mediator's command stream, and the commands waiting for an answer.
        self.commander: tuple[websocket_api.ActiveConnection, int] | None = None
        self.commands: dict[int, asyncio.Future] = {}
        self._ids = itertools.count(1)

    async def command(self, integration: str, entity_id: str, service: str,
                      data: dict[str, Any]) -> None:
        """Send a user's command to the confined integration, and wait for its answer.

        Raises `HomeAssistantError`, which the user sees, if no mediator is listening, if the
        integration refuses or fails, or if it does not answer in time — the way a native
        entity's failing service call surfaces.
        """
        if self.commander is None:
            raise HomeAssistantError(f"{entity_id}: the mediator is not connected")
        if len(self.commands) >= MAX_PENDING_COMMANDS:
            raise HomeAssistantError(f"{entity_id}: {MAX_PENDING_COMMANDS} commands are already "
                                     "waiting for an answer")
        connection, subscription = self.commander
        ident = next(self._ids)
        answer: asyncio.Future = asyncio.get_running_loop().create_future()
        self.commands[ident] = answer
        connection.send_message(websocket_api.event_message(subscription, {
            "command": ident, "integration": integration, "entity_id": entity_id,
            "service": service, "data": data}))
        try:
            result = await asyncio.wait_for(answer, timeout=COMMAND_TIMEOUT)
        except TimeoutError as err:
            raise HomeAssistantError(f"{entity_id}: the confined integration did not answer "
                                     f"within {COMMAND_TIMEOUT} s") from err
        finally:
            self.commands.pop(ident, None)
        if not result.get("ok"):
            raise HomeAssistantError(f"{entity_id}: {result.get('error') or 'refused'}")

    def request_restart(self, integration: str) -> bool:
        """Ask the mediator to let a cut-off integration run again. False if none is listening.

        Sent down the command stream, the one channel the mediator already holds open to this
        component. The mediator decides what a restart means; this only says a user asked.
        """
        return self.tell_supervisor({"restart": integration})

    def tell_supervisor(self, message: dict[str, Any]) -> bool:
        """Send a user's request down the command stream (F57c's Allow and Try again too).

        False if nothing is listening. The far end decides what the request means; this only
        says a user asked.
        """
        if self.commander is None:
            return False
        connection, subscription = self.commander
        connection.send_message(websocket_api.event_message(subscription, message))
        return True

    def save_soon(self) -> None:
        # Delayed, as Home Assistant's own integrations do: a sensor updating every few seconds
        # must not cost a disk write each time. A crash loses at most this window, and the
        # entity's own restored state covers it.
        self.store.async_delay_save(lambda: self.roster, 5)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "confine_bridge/designate_mediator",
    vol.Required("user_id"): cv.string,
})
@callback
def ws_designate_mediator(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                          msg: dict[str, Any]) -> None:
    """An admin names the user the mediator runs as (F45). Only an admin can, by design."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        connection.send_error(msg["id"], "not_set_up", "the bridge has no config entry")
        return
    if hass.auth.async_get_user(msg["user_id"]) is None:
        connection.send_error(msg["id"], "no_such_user", "no user has that id")
        return
    hass.config_entries.async_update_entry(
        entries[0], data={**entries[0].data, MEDIATOR_USER: msg["user_id"]})
    connection.send_result(msg["id"], {"designated": msg["user_id"]})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    websocket_api.async_register_command(hass, ws_designate_mediator)
    websocket_api.async_register_command(hass, ws_publish)
    websocket_api.async_register_command(hass, ws_set_state)
    websocket_api.async_register_command(hass, ws_commands)
    websocket_api.async_register_command(hass, ws_command_result)
    websocket_api.async_register_command(hass, ws_cut_off)
    websocket_api.async_register_command(hass, ws_not_started)
    websocket_api.async_register_command(hass, ws_started)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = BridgeData(Store(hass, STORAGE_VERSION, STORAGE_KEY))
    data.roster = await data.store.async_load() or {}
    hass.data[DOMAIN] = data
    _LOGGER.info("confine_bridge: restoring %d entities", len(data.roster))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.pop(DOMAIN, None)
    return unloaded


@require_mediator
@websocket_api.websocket_command({
    vol.Required("type"): "confine_bridge/publish",
    vol.Required("integration"): cv.string,
    vol.Required("entity_id"): cv.entity_id,
    vol.Required("state"): vol.Any(cv.string, int, float, bool, None),
    vol.Optional("attributes", default=dict): dict,
    vol.Optional("naming", default=dict): {
        vol.Optional("name"): vol.Any(cv.string, None),
        vol.Optional("device"): vol.Any(cv.string, None),
        vol.Optional("has_entity_name"): bool,
    },
})
@websocket_api.async_response
async def ws_publish(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                     msg: dict) -> None:
    """Create or update one registry-backed entity on a confined integration's behalf."""
    data: BridgeData | None = hass.data.get(DOMAIN)
    if data is None:
        connection.send_error(msg["id"], "not_ready", "the bridge has no config entry")
        return
    domain = msg["entity_id"].partition(".")[0]
    if domain not in SUPPORTED:
        connection.send_error(msg["id"], "unsupported",
                              f"the bridge cannot stand in for a {domain} entity")
        return

    unique_id = f"{msg['integration']}:{msg['entity_id']}"
    definition = {"integration": msg["integration"], "entity_id": msg["entity_id"],
                  "state": msg["state"], "attributes": msg["attributes"],
                  "naming": msg["naming"]}
    data.roster[unique_id] = definition
    data.save_soon()

    if (entity := data.live.get(unique_id)) is not None:
        entity.apply(definition)
        connection.send_result(msg["id"], {"entity_id": entity.entity_id,
                                           "unique_id": unique_id, "created": False})
        return

    added: asyncio.Future = hass.loop.create_future()
    data.waiting[unique_id] = added
    async_dispatcher_send(hass, SIGNAL_NEW_ENTITY.format(domain), definition)
    try:
        entity_id = await asyncio.wait_for(added, timeout=10)
    except TimeoutError:
        connection.send_error(msg["id"], "timeout", f"{unique_id} was not added in 10 s")
        return
    finally:
        data.waiting.pop(unique_id, None)
    connection.send_result(msg["id"], {"entity_id": entity_id, "unique_id": unique_id,
                                       "created": True})


@require_mediator
@websocket_api.websocket_command({
    vol.Required("type"): "confine_bridge/set_state",
    vol.Required("entity_id"): cv.entity_id,
    vol.Required("state"): vol.Any(cv.string, int, float, bool, None),
    vol.Optional("attributes", default=dict): dict,
})
@websocket_api.async_response
async def ws_set_state(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                       msg: dict) -> None:
    """`entities.write` (§5.10.3): set the state of an entity the integration does not own.

    This is what writing someone else's entity means inside Home Assistant itself — a state
    machine write, with no registry row of its own — and the mediator sends it only for a request
    an `entities.write` clause allowed.
    """
    hass.states.async_set(msg["entity_id"], str(msg["state"]), msg["attributes"])
    connection.send_result(msg["id"], {"entity_id": msg["entity_id"]})


@require_mediator
@websocket_api.websocket_command({vol.Required("type"): "confine_bridge/commands"})
@callback
def ws_commands(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                msg: dict) -> None:
    """The mediator subscribes here to receive users' commands for confined entities (W1 step 2b).

    One subscriber: the mediator. A second replaces the first, so a reconnecting mediator is not
    locked out by its own dead connection.
    """
    data: BridgeData | None = hass.data.get(DOMAIN)
    if data is None:
        connection.send_error(msg["id"], "not_ready", "the bridge has no config entry")
        return
    data.commander = (connection, msg["id"])

    @callback
    def unsubscribe() -> None:
        if data.commander == (connection, msg["id"]):
            data.commander = None
    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])


@require_mediator
@websocket_api.websocket_command({
    vol.Required("type"): "confine_bridge/command_result",
    vol.Required("command"): int,
    vol.Required("ok"): bool,
    vol.Optional("error"): vol.Any(cv.string, None),
})
@callback
def ws_command_result(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                      msg: dict) -> None:
    """The confined integration's answer to one command, relayed by the mediator."""
    data: BridgeData | None = hass.data.get(DOMAIN)
    answer = data.commands.get(msg["command"]) if data else None
    if answer is not None and not answer.done():
        answer.set_result({"ok": msg["ok"], "error": msg.get("error")})
    connection.send_result(msg["id"])


@require_mediator
@websocket_api.websocket_command({
    vol.Required("type"): "confine_bridge/cut_off",
    vol.Required("integration"): cv.string,
    vol.Optional("detail", default=""): cv.string,
})
@callback
def ws_cut_off(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
               msg: dict) -> None:
    """The mediator stopped a confined integration for flooding it with refused requests.

    Raised as a Repairs issue, because that is where Home Assistant already tells a household
    that something needs their attention, and in words that assume nothing technical
    (`notes/flood_cutoff_prediction.md` §3). The mediator's own reason — how many refusals in how
    long — is in its audit record, and is kept out of the user's sight on purpose. Persistent, so
    a restart of the house's instance does not lose the explanation while the integration is
    still stopped.
    """
    integration = msg["integration"]
    ir.async_create_issue(
        hass, DOMAIN, ISSUE_CUT_OFF.format(integration),
        data={"integration": integration},
        is_fixable=True, is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key="cut_off",
        translation_placeholders={"name": integration})
    _LOGGER.warning("confine_bridge: %s was cut off by the mediator (%s)", integration,
                    msg["detail"])
    connection.send_result(msg["id"])


@require_mediator
@websocket_api.websocket_command({
    vol.Required("type"): "confine_bridge/not_started",
    vol.Required("integration"): cv.string,
    vol.Required("reason"): vol.In(NOT_STARTED_REASONS),
    vol.Optional("details", default=""): str,
    vol.Optional("identity", default=""): str,
    vol.Optional("grant", default=""): str,
    vol.Optional("detail", default=""): str,
})
@callback
def ws_not_started(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                   msg: dict) -> None:
    """The supervisor did not start an integration: tell the household, in Repairs (F57c).

    Fixable. For `not_approved`, the screen behind the issue is what the integration asks for,
    rendered by `describe` (`details`), and its one button allows exactly that: the identity and
    grant digest the screen was rendered from go back with it, so an approval cannot outlive a
    change to what was shown. For `too_much_data`, the button only asks to try again. Persistent,
    like the cut-off, so a restart of the house's instance does not lose it.
    """
    integration = msg["integration"]
    ir.async_create_issue(
        hass, DOMAIN, ISSUE_NOT_STARTED.format(integration),
        data={"integration": integration, "reason": msg["reason"],
              "identity": msg["identity"], "grant": msg["grant"], "details": msg["details"]},
        is_fixable=True, is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key=msg["reason"],
        translation_placeholders={"name": integration})
    _LOGGER.warning("confine_bridge: %s was not started (%s) %s", integration, msg["reason"],
                    msg["detail"])
    connection.send_result(msg["id"])


@require_mediator
@websocket_api.websocket_command({
    vol.Required("type"): "confine_bridge/started",
    vol.Required("integration"): cv.string,
})
@callback
def ws_started(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
               msg: dict) -> None:
    """The integration is running: whatever said it was not started no longer applies."""
    ir.async_delete_issue(hass, DOMAIN, ISSUE_NOT_STARTED.format(msg["integration"]))
    connection.send_result(msg["id"])
