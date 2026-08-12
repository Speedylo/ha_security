"""Shim of homeassistant.core.

The real ``HomeAssistant`` object hands an integration direct in-memory access to
every entity state and every registered service. Here it is a facade: each
operation becomes a bridge message the supervisor checks against the manifest.
"""

from __future__ import annotations

import asyncio
import functools
from datetime import datetime
from typing import Any, Callable, Coroutine

from ._bridge import Bridge, PermissionDenied

# Kept so integrations that compare against it behave as they would on real HA.
CALLBACK_TYPE = Callable[[], None]


def callback(func: Callable) -> Callable:
    """Mark a function as safe to run inside the event loop.

    On real HA this is a scheduling hint, not a wrapper; same here.
    """
    setattr(func, "_hass_callback", True)
    return func


def is_callback(func: Callable) -> bool:
    return getattr(func, "_hass_callback", False) is True


class State:
    """A single entity state, as returned by the supervisor."""

    def __init__(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any] | None = None,
        last_changed: datetime | None = None,
        last_updated: datetime | None = None,
    ) -> None:
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}
        self.last_changed = last_changed
        self.last_updated = last_updated

    @property
    def domain(self) -> str:
        return self.entity_id.split(".", 1)[0]

    @property
    def object_id(self) -> str:
        return self.entity_id.split(".", 1)[1]

    @property
    def name(self) -> str:
        return self.attributes.get("friendly_name") or self.object_id.replace("_", " ")

    def __repr__(self) -> str:
        return f"<State {self.entity_id}={self.state}>"


class Event:
    """An event on the (mediated) bus."""

    def __init__(self, event_type: str, data: dict | None = None) -> None:
        self.event_type = event_type
        self.data = data or {}


class ServiceCall:
    """An inbound service call."""

    def __init__(self, domain: str, service: str, data: dict | None = None) -> None:
        self.domain = domain
        self.service = service
        self.data = data or {}


class StateMachine:
    """hass.states — every read and write crosses the bridge.

    Reads matter as much as writes. ``async_all()`` on real HA returns every
    entity in the house; here the supervisor returns only what the manifest
    declares, which is the fix for the firehose leak.
    """

    def __init__(self, bridge: Bridge) -> None:
        self._bridge = bridge

    def async_set(
        self,
        entity_id: str,
        new_state: Any,
        attributes: dict | None = None,
        force_update: bool = False,
        context: Any = None,
    ) -> None:
        self._bridge.request(
            "set_state",
            entity_id=entity_id,
            state=new_state,
            attributes=attributes or {},
        )

    set = async_set

    def get(self, entity_id: str) -> State | None:
        reply = self._bridge.request("get_state", entity_id=entity_id)
        payload = reply.get("state")
        if payload is None:
            return None
        return State(payload["entity_id"], payload["state"], payload.get("attributes"))

    def is_state(self, entity_id: str, state: str) -> bool:
        current = self.get(entity_id)
        return current is not None and current.state == state

    def async_all(self, domain_filter: str | list[str] | None = None) -> list[State]:
        reply = self._bridge.request("list_states", domain_filter=domain_filter)
        return [
            State(item["entity_id"], item["state"], item.get("attributes"))
            for item in reply.get("states", [])
        ]

    all = async_all

    def async_entity_ids(self, domain_filter: str | list[str] | None = None) -> list[str]:
        return [state.entity_id for state in self.async_all(domain_filter)]

    def async_remove(self, entity_id: str, context: Any = None) -> bool:
        reply = self._bridge.request("remove_state", entity_id=entity_id)
        return bool(reply.get("removed"))


class ServiceRegistry:
    """hass.services — the confused-deputy chokepoint.

    An integration that never declared ``lock.unlock`` cannot reach it, even
    though the supervisor itself holds a fully privileged HA token.
    """

    def __init__(self, bridge: Bridge) -> None:
        self._bridge = bridge
        self._own: dict[tuple[str, str], Callable] = {}

    async def async_call(
        self,
        domain: str,
        service: str,
        service_data: dict | None = None,
        blocking: bool = False,
        context: Any = None,
        target: dict | None = None,
        return_response: bool = False,
    ) -> Any:
        reply = self._bridge.request(
            "call_service",
            domain=domain,
            service=service,
            data={**(service_data or {}), **(target or {})},
        )
        return reply.get("response") if return_response else None

    call = async_call

    def async_register(
        self,
        domain: str,
        service: str,
        service_func: Callable,
        schema: Any = None,
        supports_response: Any = None,
    ) -> None:
        """Register a service this integration itself provides."""
        self._own[(domain, service)] = service_func
        self._bridge.request("register_service", domain=domain, service=service)

    register = async_register

    def has_service(self, domain: str, service: str) -> bool:
        return (domain, service) in self._own


class EventBus:
    """hass.bus — subscriptions are filtered by the supervisor.

    ``subscribe_events`` with no filter is the streaming form of the firehose
    leak: every state change in the house, including the ones the integration
    was never allowed to read.
    """

    def __init__(self, bridge: Bridge) -> None:
        self._bridge = bridge
        self._listeners: dict[str, list[Callable]] = {}

    def async_listen(self, event_type: str, listener: Callable, event_filter: Any = None) -> CALLBACK_TYPE:
        self._bridge.request("subscribe_events", event_type=event_type)
        self._listeners.setdefault(event_type, []).append(listener)

        def remove() -> None:
            self._listeners.get(event_type, []).remove(listener)

        return remove

    listen = async_listen

    def async_fire(self, event_type: str, event_data: dict | None = None, context: Any = None) -> None:
        self._bridge.request("fire_event", event_type=event_type, data=event_data or {})

    fire = async_fire

    def async_dispatch(self, event: Event) -> None:
        """Deliver an event pushed in from the supervisor."""
        for listener in list(self._listeners.get(event.event_type, [])):
            listener(event)


class Config:
    """hass.config — deliberately thin.

    Real HA exposes ``config.path()``, which is how the 2021 HACS file-theft
    pattern reached ``/config/secrets.yaml``. Here paths resolve inside the
    integration's own directory and nowhere else.
    """

    def __init__(self, config_dir: str) -> None:
        self.config_dir = config_dir
        self.latitude = 0.0
        self.longitude = 0.0
        self.elevation = 0
        self.location_name = "Sandbox"
        self.time_zone = "UTC"
        self.units = None
        self.language = "en"

    def path(self, *path: str) -> str:
        import os

        return os.path.join(self.config_dir, *path)


class HomeAssistant:
    """The object handed to every integration."""

    def __init__(self, bridge: Bridge, config_dir: str) -> None:
        self._bridge = bridge
        self.data: dict[str, Any] = {}
        self.states = StateMachine(bridge)
        self.services = ServiceRegistry(bridge)
        self.bus = EventBus(bridge)
        self.config = Config(config_dir)
        self.loop = asyncio.get_event_loop()
        self._tasks: set[asyncio.Task] = set()

        # Imported lazily: config_entries imports core.
        from .config_entries import ConfigEntries

        self.config_entries = ConfigEntries(self)

    @property
    def is_running(self) -> bool:
        return True

    @property
    def is_stopping(self) -> bool:
        return False

    def async_create_task(
        self, target: Coroutine, name: str | None = None, eager_start: bool = True
    ) -> asyncio.Task:
        task = self.loop.create_task(target, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def async_create_background_task(
        self, target: Coroutine, name: str | None = None, eager_start: bool = True
    ) -> asyncio.Task:
        return self.async_create_task(target, name)

    def async_add_executor_job(self, target: Callable, *args: Any) -> asyncio.Future:
        return self.loop.run_in_executor(None, functools.partial(target, *args))

    add_executor_job = async_add_executor_job

    def async_run_job(self, target: Callable, *args: Any) -> Any:
        if asyncio.iscoroutinefunction(target):
            return self.async_create_task(target(*args))
        return target(*args)

    async def async_block_till_done(self) -> None:
        """Drain tasks the integration scheduled.

        Real HA's version is more careful about tasks that spawn tasks; this
        loops until the set stays empty, which is enough for setup.
        """
        for _ in range(100):
            pending = [task for task in self._tasks if not task.done()]
            if not pending:
                await asyncio.sleep(0)
                if not [task for task in self._tasks if not task.done()]:
                    return
                continue
            await asyncio.gather(*pending, return_exceptions=True)

    async def async_stop(self, exit_code: int = 0) -> None:
        for task in list(self._tasks):
            task.cancel()


class HassJob:
    """Shim of core.HassJob — HA wraps callables for scheduling; we just hold it."""

    def __init__(self, target: Callable, name: str | None = None, **kwargs: Any) -> None:
        self.target = target
        self.name = name


class Context:
    """Shim of core.Context."""

    def __init__(self, user_id: str | None = None, parent_id: str | None = None, id: str | None = None) -> None:
        self.user_id = user_id
        self.parent_id = parent_id
        self.id = id or "sandbox"


def valid_entity_id(entity_id: str) -> bool:
    import re

    return bool(re.match(r"^[a-z0-9_]+\.[a-z0-9_]+$", entity_id))


__all__ = [
    "CALLBACK_TYPE",
    "Config",
    "Context",
    "Event",
    "EventBus",
    "HassJob",
    "HomeAssistant",
    "PermissionDenied",
    "ServiceCall",
    "ServiceRegistry",
    "State",
    "StateMachine",
    "callback",
    "is_callback",
    "valid_entity_id",
]
