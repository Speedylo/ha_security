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

*2026-10-04 (W1): the paragraph above describes the first version. Step 4 is now here (`_record`,
with the durable log), and step 5 is run here too, after the record, from the `act` a policy
returns; the push loop's subscription table and outbox are also here. See
`notes/w1_push_loop_prediction.md`.*
"""

from __future__ import annotations

import array
import os
import selectors
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .audit import AuditLog, Identity
from .channel import Channel, ProtocolError


@dataclass(frozen=True)
class Decision:
    """What the mediator decided, and the clause that decided it (§5.11.3)."""

    allowed: bool
    reason: str
    clause: str | None = None
    data: dict | None = None
    #: A connected descriptor to hand across with the response, for the one capability whose
    #: result is a kernel object rather than a value (§7.24's egress path). Deliberately kept
    #: out of `data`: `data` is JSON that goes on the wire, and a descriptor travels as
    #: ancillary data instead. The mediator closes its copy once the frame is sent — the
    #: sandbox has its own by then, and holding both would leak one per connection.
    fd: int | None = None
    #: Step 5, deferred. A policy that must *act* — write a state, place a call, open a
    #: connection — returns the act as a closure instead of doing it, and the mediator runs it
    #: only after step 4's record is durable. Until W1 the acting policy acted inside the
    #: decision, so the record came after the action in every case §5.11.3 wrote the ordering
    #: for (`notes/w1_push_loop_prediction.md` §1 (1)). The closure returns the decision that
    #: actually went out: the same grant with its data or descriptor, or a refusal found while
    #: acting, such as an egress name that now resolves to a private address.
    act: Callable[[], "Decision"] | None = field(default=None, compare=False)

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
class _Outbox:
    """What the mediator still owes one sandbox, and the bound on how much that can be.

    Until W1 the mediator only ever replied, to a sandbox that had just asked and was waiting,
    so a blocking `sendall` was safe. A push is sent to a sandbox that asked for nothing and
    may not be reading, and a blocking send to it would stop the mediator's only thread, and
    with it every other sandbox (`notes/w1_push_loop_prediction.md` §1 (4)). So nothing here
    blocks. What is owed waits in three places, each bounded:

      - **at most one reply**, because the mediator stops reading a sandbox's requests while
        it owes that sandbox a reply. A sandbox that asks without reading stalls only itself;
      - **at most one state per subscribed entity**, because a newer state *replaces* an
        unsent one instead of queueing behind it. A state is a value, not an event, so only
        the latest is worth sending (decision B, 2026-10-04);
      - **at most one frame part-written**, which must finish before anything else starts,
        or two frames would interleave on the wire.
    """

    reply: tuple[bytes, int | None] | None = None
    pushes: dict[str, dict] = field(default_factory=dict)
    inflight: bytearray = field(default_factory=bytearray)
    inflight_fd: int | None = None
    inflight_is_reply: bool = False

    @property
    def owes_reply(self) -> bool:
        return self.reply is not None or (bool(self.inflight) and self.inflight_is_reply)

    @property
    def empty(self) -> bool:
        return not self.inflight and self.reply is None and not self.pushes

    def drain(self, sock) -> int:
        """Write as much as the socket takes without blocking. Returns pushes fully sent.

        Raises `OSError` if the far end has gone; the caller drops the channel.
        """
        completed = 0
        while True:
            if not self.inflight:
                if self.reply is not None:
                    data, self.inflight_fd = self.reply
                    self.reply = None
                    self.inflight, self.inflight_is_reply = bytearray(data), True
                elif self.pushes:
                    message = self.pushes.pop(next(iter(self.pushes)))
                    self.inflight = bytearray(Channel.frame(message))
                    self.inflight_is_reply = False
                else:
                    return completed
            try:
                if self.inflight_fd is not None:
                    # The descriptor rides with the first byte (see `Channel.send`). Once any
                    # byte has gone, the sandbox holds its own copy and this one is closed.
                    rights = array.array("i", [self.inflight_fd])
                    sent = sock.sendmsg([bytes(self.inflight)],
                                        [(socket.SOL_SOCKET, socket.SCM_RIGHTS, rights)],
                                        socket.MSG_DONTWAIT)
                    os.close(self.inflight_fd)
                    self.inflight_fd = None
                else:
                    sent = sock.send(self.inflight, socket.MSG_DONTWAIT)
            except BlockingIOError:
                return completed
            del self.inflight[:sent]
            if not self.inflight and not self.inflight_is_reply:
                completed += 1

    def discard(self) -> None:
        """Close any descriptor still owed. A dropped channel must not leave a connection open."""
        for fd in (self.inflight_fd, self.reply[1] if self.reply else None):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        self.inflight_fd, self.reply = None, None


@dataclass
class Mediator:
    """Holds one end of every sandbox's socket, and never asks a sandbox who it is."""

    policy: Callable[[str, dict], Decision] = deny_everything
    audit: list[dict] = field(default_factory=list)
    log: AuditLog | None = None
    #: Push frames fully written, per integration. Counted in memory and not recorded: the
    #: record is the `entity.subscribe` decision that allowed them (decision A, 2026-10-04),
    #: the way the egress record is the connect and not the bytes that follow it.
    pushes_sent: dict[str, int] = field(default_factory=dict)
    #: Unsent states replaced by a newer one before they left. Non-zero means a sandbox was
    #: not keeping up, and it is the number P7 reads.
    pushes_coalesced: dict[str, int] = field(default_factory=dict)
    _runs: dict[str, str] = field(default_factory=dict)
    _by_fd: dict[int, tuple[str, Channel]] = field(default_factory=dict)
    #: What each **channel** has subscribed to. Keyed by channel rather than by integration:
    #: a subscription belongs to one spawn, and goes when that spawn's channel does, so a
    #: respawn under a new manifest starts with none and must be granted each one again.
    _subscriptions: dict[int, set[str]] = field(default_factory=dict)
    _out: dict[int, _Outbox] = field(default_factory=dict)
    _selector: selectors.BaseSelector = field(default_factory=selectors.DefaultSelector)

    def register(self, identity: str, channel: Channel, run_id: str = "", *,
                 component: Path | None = None, provenance: str = "author-declared") -> None:
        """Bind one socket to one integration. The only place identity is ever established.

        **With a durable log attached, this is also where the run record is written** (T4).
        §5.12.2 requires one per sandbox construction, carrying the full identity, so that every
        decision names the code that asked for it. Until T4 nothing outside two self-tests ever
        wrote one: `run_id` defaulted to `""`, no harness passed one, and every durable decision
        named a run no record carried. A mediator with a log now refuses to register a sandbox
        without the directory its identity is computed from — the same move `ResourceLimits`
        made for `SandboxCgroup.create`: no way to reach this with the record quietly skipped.

        **And this is where the declaration is re-read (§8.7 #14).** Until W1 a manifest was
        re-checked per version only because every harness built a fresh mediator per run, and
        `selftest_t12` could not tell that from a trigger. A mediator that outlives its
        sandboxes, which the push loop needs, would have kept deciding by the first manifest it
        was given. So a policy that can `bind` is asked to re-load the manifest here, at every
        registration, which is to say at every spawn — and only here, so a file edit never
        re-binds a sandbox that is already running.
        """
        bind = getattr(self.policy, "bind", None)
        if bind is not None and component is not None:
            bind(identity, Path(component))
        if self.log is not None and not run_id:
            if component is None:
                raise ValueError(f"{identity}: a mediator with a durable log must be told which "
                                 f"component it is running, so the run can be recorded")
            run_id = self.log.run(Identity.compute(Path(component)), provenance, identity)
        fd = channel.fileno()
        self._by_fd[fd] = (identity, channel)
        self._runs[identity] = run_id
        self._subscriptions[fd] = set()
        self._out[fd] = _Outbox()
        self._selector.register(channel.sock, selectors.EVENT_READ)

    def unregister(self, fd: int) -> None:
        identity, channel = self._by_fd.pop(fd, (None, None))
        self._subscriptions.pop(fd, None)
        outbox = self._out.pop(fd, None)
        if outbox is not None:
            outbox.discard()
        if channel is not None:
            try:
                self._selector.unregister(channel.sock)
            except (KeyError, ValueError):
                pass
            channel.close()

    @property
    def open_channels(self) -> int:
        return len(self._by_fd)

    def subscribers(self, entity_id: str) -> list[str]:
        """Which integrations a change to `entity_id` would be pushed to. For tests and reports."""
        return [self._by_fd[fd][0] for fd, entities in self._subscriptions.items()
                if entity_id in entities]

    def serve(self, timeout: float | None = None) -> None:
        """Answer requests and deliver pushes until every sandbox has closed its end."""
        while self._by_fd:
            events = self._selector.select(timeout)
            if not events:
                return
            for key, mask in events:
                fd = key.fileobj.fileno()  # type: ignore[union-attr]
                if fd in self._by_fd and mask & selectors.EVENT_WRITE:
                    self._flush(fd)
                if fd in self._by_fd and mask & selectors.EVENT_READ:
                    self._handle_ready(fd)

    # ------------------------------------------------------------------- the push loop

    def push(self, entity_id: str, state: object, attributes: dict | None = None) -> None:
        """A state changed on the platform. Send it to every channel subscribed to it, and no other.

        **The subscription table is S3's filter.** Each entry in it was put there by an
        `entity.subscribe` the manifest allowed and the log recorded, so an entity is delivered
        only where a recorded decision said it could be. Before W1 nothing was delivered at all,
        and §7.14.4 had to call the confined arm's zero an absent feature rather than a filter.
        """
        message = {"push": "entity.state", "entity": entity_id, "state": state,
                   "attributes": dict(attributes or {})}
        for fd, entities in list(self._subscriptions.items()):
            if entity_id not in entities:
                continue
            identity = self._by_fd[fd][0]
            outbox = self._out[fd]
            if entity_id in outbox.pushes:
                self.pushes_coalesced[identity] = self.pushes_coalesced.get(identity, 0) + 1
            outbox.pushes[entity_id] = message
            self._flush(fd)

    def _flush(self, fd: int) -> None:
        identity, channel = self._by_fd[fd]
        outbox = self._out[fd]
        try:
            sent = outbox.drain(channel.sock)
        except OSError:
            self.unregister(fd)
            return
        if sent:
            self.pushes_sent[identity] = self.pushes_sent.get(identity, 0) + sent
        # Read requests unless a reply is still owed; ask to hear about writability while
        # anything is still owed. Never neither: owing a reply means the outbox is not empty.
        events = (0 if outbox.owes_reply else selectors.EVENT_READ) \
            | (0 if outbox.empty else selectors.EVENT_WRITE)
        self._selector.modify(channel.sock, events)

    # --------------------------------------------------------------- requests, §5.11.3

    def _record(self, identity: str, request: dict, decision: Decision) -> None:
        """Step 4. Durable before the next line runs — a record still in a buffer is not one."""
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
            if self.log is not None:
                self.log.protocol_error(self._runs.get(identity, ""), identity, str(err))
            self.unregister(fd)
            return
        if request is None:
            self.unregister(fd)
            return

        # Steps 1–3. Identity comes from `identity`, which came from the socket. Whatever the
        # request claims about itself is data, and is recorded as a claim rather than believed.
        decision = self.policy(identity, request)

        # Step 4, then step 5. The record is durable before the policy's act runs, so an act
        # that succeeds and then crashes the mediator is still attributable. If acting turns up
        # a refusal the decision could not see — a name that now resolves to a private
        # address — that refusal is recorded too, so the log never shows a grant as the last
        # word on a request that was in fact refused.
        self._record(identity, request, decision)
        if decision.allowed and decision.act is not None:
            outcome = decision.act()
            if not outcome.allowed:
                self._record(identity, request, outcome)
            decision = outcome

        if decision.allowed and request.get("op") == "entity.subscribe":
            self._subscriptions[fd].add(str(request.get("entity")))

        try:
            frame = Channel.frame(decision.as_response(request.get("id")))
        except ProtocolError as err:
            frame = Channel.frame(Decision(False, f"the answer was too large: {err}",
                                           decision.clause).as_response(request.get("id")))
            if decision.fd is not None:
                os.close(decision.fd)
            decision = Decision(False, "", decision.clause)
        self._out[fd].reply = (frame, decision.fd)
        self._flush(fd)
