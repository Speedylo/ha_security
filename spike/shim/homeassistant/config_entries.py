"""Shim of homeassistant.config_entries."""

from __future__ import annotations

import importlib
import uuid
from contextvars import ContextVar
from enum import StrEnum
from typing import Any, Callable

from .core import HomeAssistant, callback
from .data_entry_flow import FlowResult, FlowResultType

# Upstream renamed FlowResult to ConfigFlowResult for config flows and kept both
# importable. Integrations annotate with whichever name matched the HA release
# they were written against, so both have to resolve.
ConfigFlowResult = FlowResult

# Real HA sets this while a config entry is being set up, so helpers constructed
# during setup (notably DataUpdateCoordinator) can find their own entry without
# being passed it. Integrations rely on the side effect: this target reads
# ``coordinator.config_entry.entry_id`` having never assigned it.
current_entry: ContextVar["ConfigEntry | None"] = ContextVar("current_entry", default=None)

SOURCE_USER = "user"
SOURCE_IMPORT = "import"
SOURCE_REAUTH = "reauth"
SOURCE_RECONFIGURE = "reconfigure"
SOURCE_ZEROCONF = "zeroconf"
SOURCE_DISCOVERY = "discovery"


class ConfigEntryState(StrEnum):
    LOADED = "loaded"
    SETUP_ERROR = "setup_error"
    MIGRATION_ERROR = "migration_error"
    SETUP_RETRY = "setup_retry"
    NOT_LOADED = "not_loaded"
    FAILED_UNLOAD = "failed_unload"
    SETUP_IN_PROGRESS = "setup_in_progress"


class ConfigEntry:
    """One configured instance of an integration."""

    def __init__(
        self,
        *,
        domain: str,
        title: str = "",
        data: dict | None = None,
        options: dict | None = None,
        entry_id: str | None = None,
        version: int = 1,
        minor_version: int = 1,
        source: str = SOURCE_USER,
        unique_id: str | None = None,
    ) -> None:
        self.domain = domain
        self.title = title
        self.data = dict(data or {})
        self.options = dict(options or {})
        self.entry_id = entry_id or uuid.uuid4().hex
        self.version = version
        self.minor_version = minor_version
        self.source = source
        self.unique_id = unique_id
        self.state = ConfigEntryState.NOT_LOADED
        self.runtime_data: Any = None
        self.pref_disable_new_entities = False
        self.pref_disable_polling = False
        self._on_unload: list[Callable] = []
        self._update_listeners: list[Callable] = []

    @callback
    def async_on_unload(self, func: Callable) -> None:
        self._on_unload.append(func)

    @callback
    def add_update_listener(self, listener: Callable) -> Callable:
        self._update_listeners.append(listener)

        def remove() -> None:
            self._update_listeners.remove(listener)

        return remove

    def async_create_task(self, hass: HomeAssistant, target: Any, name: str | None = None) -> Any:
        return hass.async_create_task(target, name)

    def async_create_background_task(
        self, hass: HomeAssistant, target: Any, name: str | None = None
    ) -> Any:
        return hass.async_create_task(target, name)

    async def _async_run_unload(self) -> None:
        for func in reversed(self._on_unload):
            result = func()
            if hasattr(result, "__await__"):
                await result
        self._on_unload.clear()

    def as_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "domain": self.domain,
            "title": self.title,
            "data": self.data,
            "options": self.options,
            "version": self.version,
            "source": self.source,
        }

    def __repr__(self) -> str:
        return f"<ConfigEntry {self.domain}:{self.entry_id[:8]}>"


class ConfigEntries:
    """hass.config_entries.

    Platform forwarding is the interesting part: it is how ``sensor.py`` gets
    loaded and handed an ``async_add_entities`` callback.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._entries: dict[str, ConfigEntry] = {}

    def _register(self, entry: ConfigEntry) -> None:
        self._entries[entry.entry_id] = entry

    async def async_forward_entry_setups(self, entry: ConfigEntry, platforms: list[str]) -> None:
        from .helpers.entity_platform import EntityPlatform

        for platform in platforms:
            module_name = f"custom_components.{entry.domain}.{platform}"
            module = importlib.import_module(module_name)
            setup = getattr(module, "async_setup_entry", None)
            if setup is None:
                continue
            entity_platform = EntityPlatform(self._hass, entry.domain, str(platform))
            await setup(self._hass, entry, entity_platform.async_add_entities)

    async def async_forward_entry_setup(self, entry: ConfigEntry, platform: str) -> bool:
        await self.async_forward_entry_setups(entry, [platform])
        return True

    async def async_unload_platforms(self, entry: ConfigEntry, platforms: list[str]) -> bool:
        await entry._async_run_unload()
        return True

    async def async_reload(self, entry_id: str) -> bool:
        entry = self._entries.get(entry_id)
        if entry is None:
            return False
        module = importlib.import_module(f"custom_components.{entry.domain}")
        unload = getattr(module, "async_unload_entry", None)
        setup = getattr(module, "async_setup_entry", None)
        if unload:
            await unload(self._hass, entry)
        if setup:
            await setup(self._hass, entry)
        return True

    @callback
    def async_update_entry(
        self,
        entry: ConfigEntry,
        *,
        data: dict | None = None,
        options: dict | None = None,
        title: str | None = None,
        unique_id: str | None = None,
        version: int | None = None,
        minor_version: int | None = None,
    ) -> bool:
        if data is not None:
            entry.data = dict(data)
        if options is not None:
            entry.options = dict(options)
        if title is not None:
            entry.title = title
        if unique_id is not None:
            entry.unique_id = unique_id
        if version is not None:
            entry.version = version
        if minor_version is not None:
            entry.minor_version = minor_version
        return True

    @callback
    def async_get_entry(self, entry_id: str) -> ConfigEntry | None:
        return self._entries.get(entry_id)

    @callback
    def async_entries(self, domain: str | None = None) -> list[ConfigEntry]:
        entries = list(self._entries.values())
        if domain is None:
            return entries
        return [entry for entry in entries if entry.domain == domain]

    @callback
    def async_entry_for_domain_unique_id(self, domain: str, unique_id: str) -> ConfigEntry | None:
        for entry in self.async_entries(domain):
            if entry.unique_id == unique_id:
                return entry
        return None


class ConfigFlow:
    """Base class for an integration's config flow.

    The flow never runs in the sandbox in normal operation — the supervisor owns
    onboarding, since a flow that could talk to arbitrary hosts before a manifest
    is agreed would be a hole. It is shimmed because integrations import it at
    module scope (``__init__.py`` imports CONFIG_VERSION from config_flow).
    """

    VERSION = 1
    MINOR_VERSION = 1
    domain: str | None = None

    def __init_subclass__(cls, domain: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if domain is not None:
            cls.domain = domain

    def __init__(self) -> None:
        self.hass: HomeAssistant | None = None
        self.context: dict[str, Any] = {}
        self.unique_id: str | None = None

    @callback
    def async_show_form(
        self,
        *,
        step_id: str,
        data_schema: Any = None,
        errors: dict | None = None,
        description_placeholders: dict | None = None,
        last_step: bool | None = None,
    ) -> FlowResult:
        return {
            "type": FlowResultType.FORM,
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors or {},
            "description_placeholders": description_placeholders,
        }

    @callback
    def async_create_entry(
        self, *, title: str, data: dict, description: str | None = None, options: dict | None = None
    ) -> FlowResult:
        return {
            "type": FlowResultType.CREATE_ENTRY,
            "title": title,
            "data": data,
            "options": options or {},
        }

    @callback
    def async_abort(self, *, reason: str, description_placeholders: dict | None = None) -> FlowResult:
        return {"type": FlowResultType.ABORT, "reason": reason}

    @callback
    def _async_current_entries(self, include_ignore: bool = False) -> list[ConfigEntry]:
        if self.hass is None or self.domain is None:
            return []
        return self.hass.config_entries.async_entries(self.domain)

    @callback
    def _async_abort_entries_match(self, match_dict: dict | None = None) -> None:
        return None

    async def async_set_unique_id(self, unique_id: str | None, *, raise_on_progress: bool = True) -> ConfigEntry | None:
        self.unique_id = unique_id
        if self.hass is None or self.domain is None:
            return None
        return self.hass.config_entries.async_entry_for_domain_unique_id(self.domain, unique_id or "")

    @callback
    def _abort_if_unique_id_configured(self, updates: dict | None = None, reload_on_update: bool = True) -> None:
        return None

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        raise NotImplementedError


class OptionsFlow:
    """Base class for an options flow."""

    def __init__(self) -> None:
        self.hass: HomeAssistant | None = None
        self._config_entry: ConfigEntry | None = None

    @property
    def config_entry(self) -> ConfigEntry | None:
        return self._config_entry

    @config_entry.setter
    def config_entry(self, entry: ConfigEntry) -> None:
        self._config_entry = entry

    async_show_form = ConfigFlow.async_show_form
    async_create_entry = ConfigFlow.async_create_entry
    async_abort = ConfigFlow.async_abort


class OptionsFlowWithConfigEntry(OptionsFlow):
    """Deprecated in HA but still widely imported."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        super().__init__()
        self._config_entry = config_entry
        self._options = dict(config_entry.options)

    @property
    def options(self) -> dict:
        return self._options


class ConfigEntryChange(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    UPDATED = "updated"


__all__ = [
    "ConfigEntries",
    "ConfigEntry",
    "ConfigEntryChange",
    "ConfigEntryState",
    "ConfigFlow",
    "OptionsFlow",
    "OptionsFlowWithConfigEntry",
    "SOURCE_IMPORT",
    "SOURCE_REAUTH",
    "SOURCE_USER",
    "current_entry",
]
