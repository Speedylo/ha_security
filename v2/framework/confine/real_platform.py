"""Step 5 against the house's real Home Assistant, (A), in place of `platform.Platform`'s dicts.

W1 step 2 (`notes/w1_step2_real_platform_prediction.md`). `ActingPolicy` calls five operations
on whatever platform it is given — `read`, `publish`, `write`, `call_service`, `watch` — and
reads `owners`; the mediator adds `listeners` and the file descriptor. Here each is a message on
one WebSocket connection to (A), authenticated with the mediator's long-lived token (§5.15.3):

    read          get_states, and the one entity asked for
    publish       confine_bridge/publish — a registry-backed entity, via the bridge in (A)
    write         confine_bridge/set_state — a state-machine write, for `entities.write`
    call_service  call_service — the real service, executed by (A)
    watch         subscribe_entities, re-issued over the set of every entity subscribed to

**Changes arrive on the same connection as answers.** (A) sends `subscribe_entities` events and
users' commands whenever it likes, including while the mediator waits for the answer to something
else. So every message read is sorted — answers to `_results` by id, events and commands to their
queues — and the queues are applied **only by `dispatch`, which the mediator calls from its own
loop, between requests**. Never from inside `call`.

That last rule is from the W1 review (2026-10-04). Until then `call` applied the queues itself once
the outermost call returned, which is inside whatever action made the call. A user's command that
arrived while a publish was in progress was therefore decided before that publish had recorded its
owner, and refused with "belongs to None" — reproduced with `adaptive_lighting`, whose sleep-mode
switch could not be operated. Applying them between requests means no action is ever interrupted by
another, and a listener that itself calls (A) cannot read someone else's answer.

**A call blocks the mediator for one round trip to (A).** The sandbox that asked is waiting for
the answer anyway; every other sandbox waits a few milliseconds. That is the head-of-line cost of
a single-threaded mediator, the same one §7.24's egress `connect` already pays, and it is measured
in §7.37 rather than assumed small.

**Ownership** (§6.10.3's first-publisher rule) needs to know what already exists in (A). An entity
the bridge created belongs to the integration named in its `unique_id`; every other entity in
(A)'s registry or state machine belongs to "the platform", so a confined integration cannot
publish `lock.front_door` and stand in for the house's own lock.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Callable

from .platform import PlatformRefused
from .ws import WebSocket, WebSocketError


class PlatformError(PlatformRefused):
    """(A) answered a call with `success: false`. A refusal, answered to the sandbox as one."""


class PlatformLost(RuntimeError):
    """The connection to (A) failed. Not a refusal: the mediator cannot act at all, and stops."""


class _Owners(dict):
    """`owners[entity_id] = integration` as on the stand-in, with (A)'s existing entities behind it."""

    def __init__(self, existing: dict[str, str]) -> None:
        super().__init__()
        self.existing = existing

    def get(self, entity_id, default=None):  # type: ignore[override]
        if entity_id in self:
            return self[entity_id]
        return self.existing.get(entity_id, default)


class RealPlatform:
    def __init__(self, host: str = "127.0.0.1", port: int = 8123,
                 token: str | None = None, token_file: Path | None = None) -> None:
        token = token or Path(token_file or Path.home() / ".config/capstone/house_a.token") \
            .read_text().strip()
        # Longer than any wait inside (A): the bridge waits up to 10 s for an entity to be added
        # and for a command's answer. At 10 s here the two raced, and a slow add would have made
        # the mediator's read give up first (W1 review, 2026-10-04).
        self.ws = WebSocket(host, port, timeout=30)
        greeting = self.ws.receive()[0]
        if greeting.get("type") != "auth_required":
            raise PlatformError(f"unexpected greeting from (A): {greeting}")
        self.ws.send({"type": "auth", "access_token": token})
        answer = self.ws.receive()[0]
        if answer.get("type") != "auth_ok":
            raise PlatformError(f"(A) refused the mediator's token: {answer.get('type')}")

        self.listeners: list[Callable[[str, str, dict], None]] = []
        #: Called with each user's command for a confined entity (W1 step 2b): a dict with
        #: `command`, `integration`, `entity_id`, `service` and `data`. The mediator handles it.
        self.command_handlers: list[Callable[[dict], None]] = []
        self._commands: deque = deque()
        self.calls: list[tuple[str, str, dict]] = []      # what (A) executed, for reports
        self.published: dict[tuple[str, str], str] = {}   # (integration, its id) -> id in (A)
        self._next = 1
        self._results: dict[int, dict] = {}
        self._events: deque = deque()
        self._depth = 0
        self._watched: set[str] = set()
        self._subscription: int | None = None
        self._cache: dict[str, tuple[str, dict]] = {}

        existing: dict[str, str] = {}
        for entry in self.call({"type": "config/entity_registry/list"}):
            unique_id = entry.get("unique_id") or ""
            existing[entry["entity_id"]] = (unique_id.partition(":")[0]
                                            if entry.get("platform") == "confine_bridge"
                                            else "the platform")
        for state in self.call({"type": "get_states"}):
            existing.setdefault(state["entity_id"], "the platform")
        self.owners = _Owners(existing)

        # The bridge's command stream. Subscribed once, at connect, because commands can arrive
        # for any confined entity at any time, not only for entities someone subscribed to.
        self._command_stream = self._next
        self.call({"type": "confine_bridge/commands"})

    # ---------------------------------------------------------------- the connection

    def fileno(self) -> int:
        return self.ws.fileno()

    def call(self, message: dict) -> object:
        """Send one command and return its result, sorting whatever else arrives meanwhile."""
        ident = self._next
        self._next += 1
        self._depth += 1
        try:
            self.ws.send({"id": ident, **message})
            while ident not in self._results:
                self._sort(self.ws.receive())
        except (OSError, WebSocketError) as err:
            raise PlatformLost(f"the connection to (A) failed: {err}") from err
        finally:
            self._depth -= 1
        answer = self._results.pop(ident)
        if not answer.get("success", False):
            raise PlatformError(f"{message.get('type')}: {answer.get('error')}")
        return answer.get("result")

    def pump(self) -> None:
        """The mediator's selector says (A)'s socket is readable: take what arrived, and queue it."""
        try:
            self._sort(self.ws.messages())
        except (OSError, WebSocketError) as err:
            raise PlatformLost(f"the connection to (A) failed: {err}") from err

    @property
    def pending(self) -> bool:
        return bool(self._commands or self._events)

    def dispatch(self) -> None:
        """Apply queued commands and changes. Called by the mediator between requests only."""
        if self._depth == 0:
            self._apply_events()

    def _sort(self, messages: list[dict]) -> None:
        for message in messages:
            if message.get("type") == "result":
                self._results[message["id"]] = message
            elif message.get("type") == "event" and message.get("id") == self._subscription:
                self._events.append(message["event"])
            elif message.get("type") == "event" and message.get("id") == self._command_stream:
                self._commands.append(message["event"])

    def _apply_events(self) -> None:
        """`subscribe_entities`' compressed format: `a` adds whole states, `c` changes, `r` removes.

        Commands are handed on here too, for the same reason: only once no call is in progress.
        """
        while self._commands:
            command = self._commands.popleft()
            for handler in list(self.command_handlers):
                handler(command)
        while self._events:
            event = self._events.popleft()
            changed: list[str] = []
            for entity_id, full in (event.get("a") or {}).items():
                self._cache[entity_id] = (full.get("s"), dict(full.get("a") or {}))
                changed.append(entity_id)
            for entity_id, diff in (event.get("c") or {}).items():
                state, attributes = self._cache.get(entity_id, (None, {}))
                plus, minus = diff.get("+") or {}, diff.get("-") or {}
                attributes = {**attributes, **(plus.get("a") or {})}
                for name in minus.get("a") or []:
                    attributes.pop(name, None)
                if "s" in plus or plus.get("a") or minus.get("a"):
                    self._cache[entity_id] = (plus.get("s", state), attributes)
                    changed.append(entity_id)
            for entity_id in event.get("r") or []:
                self._cache.pop(entity_id, None)
            for entity_id in changed:
                state, attributes = self._cache[entity_id]
                for listener in list(self.listeners):
                    listener(entity_id, state, attributes)

    def close(self) -> None:
        self.ws.close()

    # --------------------------------------------------------------- step 5's operations

    def read(self, entity_id: str) -> tuple[str | None, dict]:
        for state in self.call({"type": "get_states"}):
            if state["entity_id"] == entity_id:
                return state["state"], state.get("attributes") or {}
        return None, {}

    def publish(self, identity: str, entity_id: str, state: str, attributes: dict,
                naming: dict | None = None) -> None:
        result = self.call({"type": "confine_bridge/publish", "integration": identity,
                            "entity_id": entity_id, "state": state, "attributes": attributes,
                            "naming": naming or {}})
        self.published[(identity, entity_id)] = result["entity_id"]

    def write(self, entity_id: str, state: str, attributes: dict) -> None:
        self.call({"type": "confine_bridge/set_state", "entity_id": entity_id,
                   "state": state, "attributes": attributes})

    def call_service(self, domain: str, service: str, data: dict) -> None:
        self.call({"type": "call_service", "domain": domain, "service": service,
                   "service_data": data})
        self.calls.append((domain, service, data))

    def command_result(self, command: int, ok: bool, error: str | None = None) -> None:
        """The confined integration's answer, back to the bridge, which returns or raises."""
        self.call({"type": "confine_bridge/command_result", "command": command, "ok": ok,
                   "error": error})

    def watch(self, entity_id: str) -> None:
        """Widen (A)'s subscription to include `entity_id`. Only subscribed entities are asked for."""
        if entity_id in self._watched:
            return
        self._watched.add(entity_id)
        if self._subscription is not None:
            self.call({"type": "unsubscribe_events", "subscription": self._subscription})
        # `subscribe_entities` events carry the id of the command that subscribed, and the first
        # one can arrive before that command's result. So the id is recorded before sending:
        # recorded after, `_sort` would drop the initial states as belonging to nobody.
        self._subscription = self._next
        self.call({"type": "subscribe_entities", "entity_ids": sorted(self._watched)})

    @property
    def watched(self) -> list[str]:
        return sorted(self._watched)
