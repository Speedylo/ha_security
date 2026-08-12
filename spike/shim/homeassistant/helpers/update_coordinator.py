"""Shim of homeassistant.helpers.update_coordinator.

``DataUpdateCoordinator`` appeared in 100% of the polling-sensor sample, so it is
the single highest-value symbol in the shim. Integrations depend on more than its
signature: the refresh/listener protocol, the ConfigEntryNotReady contract of
``async_config_entry_first_refresh``, and the fact that ``self.config_entry`` is
populated for them from the setup context.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from logging import Logger
from typing import Any, Callable, Generic, TypeVar

from ..config_entries import ConfigEntry, current_entry
from ..core import HomeAssistant, callback
from ..exceptions import ConfigEntryAuthFailed, ConfigEntryError, ConfigEntryNotReady, HomeAssistantError
from .entity import Entity

_DataT = TypeVar("_DataT")

REQUEST_REFRESH_DEFAULT_COOLDOWN = 10


class UpdateFailed(HomeAssistantError):
    """Raised by ``_async_update_data`` when a poll fails."""


class BaseDataUpdateCoordinatorProtocol:
    """Marker base, as in HA."""


class DataUpdateCoordinator(BaseDataUpdateCoordinatorProtocol, Generic[_DataT]):
    """Fetches data on a schedule and fans it out to entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: Logger,
        *,
        name: str,
        update_interval: timedelta | None = None,
        update_method: Callable | None = None,
        request_refresh_debouncer: Any = None,
        always_update: bool = True,
        config_entry: ConfigEntry | None = None,
        setup_method: Callable | None = None,
    ) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.update_method = update_method
        self.setup_method = setup_method
        self.always_update = always_update

        # HA populates this from the setup context when not passed explicitly.
        # Integrations read ``coordinator.config_entry`` having never set it.
        self.config_entry = config_entry if config_entry is not None else current_entry.get()

        self.data: _DataT | None = None
        self.last_update_success = True
        self.last_exception: Exception | None = None

        self._listeners: dict[Callable[[], None], tuple[Callable[[], None], Any]] = {}
        self._unschedule: asyncio.TimerHandle | None = None
        self._shutdown = False

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------
    @callback
    def async_add_listener(
        self, update_callback: Callable[[], None], context: Any = None
    ) -> Callable[[], None]:
        """Register an entity; returns the unsubscribe callable."""
        schedule = not self._listeners

        @callback
        def remove_listener() -> None:
            self._listeners.pop(update_callback, None)
            if not self._listeners:
                self._async_unschedule_refresh()

        self._listeners[update_callback] = (remove_listener, context)

        if schedule:
            self._schedule_refresh()

        return remove_listener

    @callback
    def async_update_listeners(self) -> None:
        for update_callback, _ in list(self._listeners.values()):
            pass
        for update_callback in list(self._listeners):
            update_callback()

    @callback
    def async_contexts(self) -> Any:
        return (context for _, context in self._listeners.values() if context is not None)

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------
    @callback
    def _schedule_refresh(self) -> None:
        if self.update_interval is None or self._shutdown:
            return
        self._async_unschedule_refresh()
        self._unschedule = self.hass.loop.call_later(
            self.update_interval.total_seconds(), self._handle_refresh_interval
        )

    @callback
    def _async_unschedule_refresh(self) -> None:
        if self._unschedule is not None:
            self._unschedule.cancel()
            self._unschedule = None

    @callback
    def _handle_refresh_interval(self) -> None:
        self._unschedule = None
        self.hass.async_create_task(
            self._async_refresh(log_failures=True, scheduled=True),
            name=f"{self.name} scheduled refresh",
        )

    # ------------------------------------------------------------------
    # Refreshing
    # ------------------------------------------------------------------
    async def _async_update_data(self) -> _DataT:
        if self.update_method is None:
            raise NotImplementedError("Update method not implemented")
        return await self.update_method()

    async def async_config_entry_first_refresh(self) -> None:
        """First refresh during setup.

        HA's contract: a failure here aborts setup with ConfigEntryNotReady (HA
        retries later) rather than leaving a half-configured integration.
        """
        await self._async_refresh(
            log_failures=False, raise_on_auth_failed=True, raise_on_entry_error=True
        )
        if self.last_update_success:
            return
        raise ConfigEntryNotReady(self.last_exception or f"{self.name}: first refresh failed")

    async def async_refresh(self) -> None:
        await self._async_refresh(log_failures=True)

    async def async_request_refresh(self) -> None:
        """HA debounces this; the spike refreshes immediately."""
        await self._async_refresh(log_failures=True)

    async def _async_refresh(
        self,
        log_failures: bool = True,
        raise_on_auth_failed: bool = False,
        scheduled: bool = False,
        raise_on_entry_error: bool = False,
    ) -> None:
        self._async_unschedule_refresh()

        previous_data = self.data
        try:
            self.data = await self._async_update_data()

        except ConfigEntryAuthFailed as err:
            self.last_update_success = False
            self.last_exception = err
            if raise_on_auth_failed:
                raise
            self.logger.error("%s: authentication failed: %s", self.name, err)

        except ConfigEntryError as err:
            self.last_update_success = False
            self.last_exception = err
            if raise_on_entry_error:
                raise
            self.logger.error("%s: config entry error: %s", self.name, err)

        except UpdateFailed as err:
            self.last_update_success = False
            self.last_exception = err
            if log_failures:
                self.logger.error("%s: update failed: %s", self.name, err)

        except Exception as err:  # noqa: BLE001 - HA is equally broad here
            self.last_update_success = False
            self.last_exception = err
            if log_failures:
                self.logger.exception("%s: unexpected error fetching data", self.name)

        else:
            if not self.last_update_success:
                self.last_update_success = True
                self.logger.info("%s: fetching data recovered", self.name)

        finally:
            if not scheduled:
                self._schedule_refresh()

        if self.always_update or self.data != previous_data or not self.last_update_success:
            self.async_update_listeners()

    @callback
    def async_set_updated_data(self, data: _DataT) -> None:
        """Push data in from elsewhere (used by push-style integrations)."""
        self.data = data
        self.last_update_success = True
        self._schedule_refresh()
        self.async_update_listeners()

    @callback
    def async_set_update_error(self, err: Exception) -> None:
        self.last_exception = err
        if self.last_update_success:
            self.last_update_success = False
            self.async_update_listeners()

    async def async_shutdown(self) -> None:
        self._shutdown = True
        self._async_unschedule_refresh()
        self._listeners.clear()


class TimestampDataUpdateCoordinator(DataUpdateCoordinator[_DataT]):
    """Coordinator that also records when the last successful update happened."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.last_update_success_time = None

    async def _async_refresh(self, *args: Any, **kwargs: Any) -> None:
        await super()._async_refresh(*args, **kwargs)
        if self.last_update_success:
            from datetime import datetime, timezone

            self.last_update_success_time = datetime.now(timezone.utc)


class CoordinatorEntity(Entity, Generic[_DataT]):
    """Entity driven by a coordinator."""

    def __init__(self, coordinator: DataUpdateCoordinator, context: Any = None) -> None:
        super().__init__()
        self.coordinator = coordinator
        self.coordinator_context = context

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(
                self._handle_coordinator_update, self.coordinator_context
            )
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Default: recompute state from coordinator data and publish it."""
        self.async_write_ha_state()

    async def async_update(self) -> None:
        await self.coordinator.async_request_refresh()


__all__ = [
    "BaseDataUpdateCoordinatorProtocol",
    "CoordinatorEntity",
    "DataUpdateCoordinator",
    "TimestampDataUpdateCoordinator",
    "UpdateFailed",
]
