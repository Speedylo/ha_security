"""The mediator's side of the channel: who is asking, and what happens to the answer.

§5.11.3 fixes the order in which one request is handled, and the order is not an implementation
detail:

    1. Identity   — from the socket the request arrived on (§5.11.2)
    2. Manifest   — the manifest bound to that integration's content hash (§5.9.6)
    3. Decision   — match against the clauses; absent a match, deny (S6)
    4. Record     — decision, clause and identity to the audit log (§5.12)
    5. Act        — only now, and only with the mediator's own credential (S2)

Steps 2, 4 and 5 belong to §6.6, §6.8 and the bridge respectively and are not implemented here.
What is implemented is steps 1 and 3, and step 3's **default**, which is the whole of S6: a
mediator holding no manifest denies everything. That is worth building first rather than last,
because it is the behaviour every later addition has to preserve, and a default-deny that
arrives after the permit path is one that has already been forgotten once.
"""

from __future__ import annotations

import selectors
from dataclasses import dataclass, field
from typing import Callable

from .audit import AuditLog
from .channel import Channel, ProtocolError


@dataclass(frozen=True)
class Decision:
    """What the mediator decided, and the clause that decided it (§5.11.3)."""

    allowed: bool
    reason: str
    clause: str | None = None
    data: dict | None = None

    def as_response(self, request_id: object) -> dict:
        response: dict = {"id": request_id, "ok": self.allowed, "reason": self.reason}
        # §5.11.3: every response carries the clause that decided it, so that attribution is
        # a property of the protocol rather than something reconstructed from logs later.
        response["clause"] = self.clause
        if self.data:
            response.update(self.data)
        return response


def deny_everything(identity: str, request: dict) -> Decision:
    """S6, as a function. No manifest, therefore no grant, therefore no."""
    return Decision(False, "no manifest is bound to this integration", clause=None)


@dataclass
class Mediator:
    """Holds one end of every sandbox's socket, and never asks a sandbox who it is."""

    policy: Callable[[str, dict], Decision] = deny_everything
    audit: list[dict] = field(default_factory=list)
    log: AuditLog | None = None
    _runs: dict[str, str] = field(default_factory=dict)
    _by_fd: dict[int, tuple[str, Channel]] = field(default_factory=dict)
    _selector: selectors.BaseSelector = field(default_factory=selectors.DefaultSelector)

    def register(self, identity: str, channel: Channel, run_id: str = "") -> None:
        """Bind one socket to one integration. The only place identity is ever established."""
        self._by_fd[channel.fileno()] = (identity, channel)
        self._runs[identity] = run_id
        self._selector.register(channel.sock, selectors.EVENT_READ)

    def unregister(self, fd: int) -> None:
        identity, channel = self._by_fd.pop(fd, (None, None))
        if channel is not None:
            try:
                self._selector.unregister(channel.sock)
            except (KeyError, ValueError):
                pass
            channel.close()

    @property
    def open_channels(self) -> int:
        return len(self._by_fd)

    def serve(self, timeout: float | None = None) -> None:
        """Answer requests until every sandbox has closed its end."""
        while self._by_fd:
            events = self._selector.select(timeout)
            if not events:
                return
            for key, _mask in events:
                self._handle_ready(key.fileobj.fileno())  # type: ignore[union-attr]

    def _handle_ready(self, fd: int) -> None:
        identity, channel = self._by_fd[fd]
        try:
            request = channel.recv()
        except ProtocolError as err:
            # A sandbox that sends rubbish loses its channel and nothing else. §5.15.4 names
            # the supervisor as the component nothing checks; the least this side can do is
            # not let one sandbox's malformed frame reach any other sandbox.
            self.audit.append({"identity": identity, "event": "protocol_error",
                               "detail": str(err)})
            self.unregister(fd)
            return
        if request is None:
            self.unregister(fd)
            return

        # Step 1. Identity comes from `identity`, which came from the socket. Whatever the
        # request claims about itself is data, and is recorded as a claim rather than believed.
        decision = self.policy(identity, request)

        # Step 4 before step 5: the record is written before anything is acted on, so an
        # action that succeeds and then crashes the mediator is still attributable. The
        # durable write happens here too — a record still in a buffer is not a record.
        self.audit.append({
            "identity": identity,
            "op": request.get("op"),
            "claimed_identity": request.get("integration"),
            "allowed": decision.allowed,
            "clause": decision.clause,
            "reason": decision.reason,
        })
        if self.log is not None:
            self.log.decision(self._runs.get(identity, ""), identity, request,
                              decision.allowed, decision.clause, decision.reason)
        try:
            channel.send(decision.as_response(request.get("id")))
        except OSError:
            self.unregister(fd)
