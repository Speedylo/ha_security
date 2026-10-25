"""Step 5 of §5.11.3 — acting, with the mediator's own credential — against a stand-in.

§5.11.3's fifth step is "act, only now, and only using the mediator's own platform credential
(S2)". Acting means reaching a real Home Assistant, and this stands in for one.

**Saying so is the point.** §5.8.2 makes the same concession about the lock: "what is under
test is the mediator's decision, not a physical lock … the hardware would add realism to the
demonstration and nothing to the evidence". The same holds here for the platform, and the same
limit applies — a stand-in shows that the mediator decides correctly and applies what it
decided, and shows nothing about what a real instance does with the result.

**What a real instance would add, and it is not nothing.** The prior feasibility work
(`~/capstone/spike/`, 2026-08) measured that publishing an entity over Home Assistant's states
API produces *states without identity*: no entity-registry row, no `unique_id`, no config
entry, no device, and nothing that survives a restart. Its `sandbox_bridge` component exists to
close that gap by owning a config entry and creating registry-backed entities on a sandboxed
integration's behalf. That finding is **orthogonal to the R1/R2 divergence** — it constrains
step 5 either way — and it is cited here as prior work with its date rather than relied on,
since the spike's findings are not carried into this project unchecked. Chapter 7 re-derives it
or drops it.

**One rule this file had to make explicit, which Chapter 5 implies but does not state.**
§5.10.2 makes an integration's own things ambient — its own config entry, its own storage,
registering *its own* services, "the risk is in calling others', not in offering one's own".
§5.10.3 makes `entities.write` — "setting state on entities it does not own" — declarable at
6.9%. Publishing an entity therefore splits on ownership, and ownership has to be recorded
somewhere: **the first integration to publish an entity id owns it, and any other integration
writing to it needs an `entities.write` clause.** Without that rule an integration could
publish `lock.front_door` and impersonate one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .audit import DEFAULT_LOG
from .manifest import Manifest, require_approval
from .egress import EgressRefused as _EgressRefused
from .mediator import Decision


class PlatformRefused(Exception):
    """The platform declined an action the mediator had already permitted and recorded.

    Not a crash: the real platform can refuse things the stand-in never would — the bridge stands
    in for a few domains only, and (A) can reject a service call. Such a refusal becomes a recorded
    refusal answered to the sandbox. Anything else an act raises is a crash and propagates, which is
    what §7.36.1's ordering test depends on. Until the W1 review (2026-10-04) a refusal crashed the
    mediator: one sandbox publishing a `light` stopped every sandbox's mediator.
    """


def _refusable(act: Callable[[], Decision], clause: str | None) -> Callable[[], Decision]:
    def run() -> Decision:
        try:
            return act()
        except PlatformRefused as err:
            return Decision(False, f"the platform refused: {err}", clause=clause)
    return run


@dataclass
class Platform:
    """A stand-in Home Assistant: entity states, their owners, and the calls made on it."""

    states: dict[str, tuple[str, dict]] = field(default_factory=dict)
    owners: dict[str, str] = field(default_factory=dict)
    calls: list[tuple[str, str, dict]] = field(default_factory=list)
    #: Called with `(entity_id, state, attributes)` after every change. The push loop's event
    #: source: the mediator listens here, and in step 2 `RealPlatform` calls the same listeners
    #: from the house's event bus. Every write goes through `set_state`, so a change one sandbox
    #: publishes reaches the others' subscriptions the same way a change in the house would.
    listeners: list[Callable[[str, str, dict], None]] = field(default_factory=list)

    def set_state(self, entity_id: str, state: str, attributes: dict | None = None) -> None:
        self.states[entity_id] = (state, dict(attributes or {}))
        for listener in list(self.listeners):
            listener(entity_id, state, dict(attributes or {}))

    def seed(self, entity_id: str, state: str, **attributes: object) -> None:
        """An entity that already exists — a device the user owns, not a sandbox's."""
        self.owners.setdefault(entity_id, "the platform")
        self.set_state(entity_id, state, attributes)

    # Step 5's four operations. `ActingPolicy` calls only these, so that `RealPlatform` (W1 step 2)
    # can stand behind the same policy: there they are WebSocket messages to the house's Home
    # Assistant, and here they are the dictionary writes they always were.

    def read(self, entity_id: str) -> tuple[str | None, dict]:
        return self.states.get(entity_id, (None, {}))

    def publish(self, identity: str, entity_id: str, state: str, attributes: dict,
                naming: dict | None = None) -> None:
        """An integration's own entity. The real platform gives it a registry row; here, a state.

        `naming` (the device's name and the entity's own, W1 step 2) is display only, and the
        stand-in has no registry to display it in."""
        self.set_state(entity_id, state, attributes)

    def write(self, entity_id: str, state: str, attributes: dict) -> None:
        """Someone else's entity, under an `entities.write` clause."""
        self.set_state(entity_id, state, attributes)

    def call_service(self, domain: str, service: str, data: dict) -> None:
        self.calls.append((domain, service, data))

    def watch(self, entity_id: str) -> None:
        """Start delivering this entity's changes. Every change already reaches the listeners here."""


class ActingPolicy:
    """Steps 2, 3 and 5. The mediator keeps 1 and 4, which is where identity and the record are.

    Ambient operations are handled before the manifest is consulted, because they are not
    permissions: an integration publishing its own entity is what being an integration *is*
    (§5.10.2), and asking a manifest about it would invite a clause that everyone must hold.

    **Step 5 is returned, not done.** Every operation that acts on the platform comes back as a
    `Decision` carrying an `act` closure, which the mediator runs after the record is durable.
    Before W1 this policy acted inside the decision, and the mediator recorded afterwards
    (`notes/w1_push_loop_prediction.md` §1 (1)).

    `manifests` is the binding from integration to declaration. `bind` replaces one entry from
    disk, and the mediator calls it at every registration (§8.7 #14).
    """

    def __init__(self, manifests: dict[str, Manifest], platform: Platform,
                 broker: object | None = None, relay: object | None = None,
                 config_root: Path | None = None, approvals: Path | None = None) -> None:
        self.manifests = manifests
        self.platform = platform
        self.broker = broker
        self.relay = relay
        self.config_root = config_root
        #: Where `describe --approve` wrote its approvals. None means `DEFAULT_LOG` under the
        #: configuration root, which is where `describe` writes by default.
        self.approvals = approvals

    def bind(self, identity: str, component: Path) -> None:
        """Re-read the declaration for one integration. Called per spawn, never per request.

        `config_root` defaults to the directory above `custom_components`, which is Home
        Assistant's own layout and every harness's. A manifest that no longer parses raises
        `ManifestRejected` here, so the spawn fails instead of running under the old grant.

        **And a manifest no one approved raises `NotApproved`, a `ManifestRejected`** (F57). This
        is the one place a grant is bound to a channel, so it is where the approval is checked:
        before F57 a derived grant was used unconfirmed and an author-declared one unseen.
        """
        root = self.config_root or component.parent.parent
        manifest = Manifest.load(component, root)
        require_approval(manifest, component, self.approvals or root / DEFAULT_LOG)
        self.manifests[identity] = manifest

    def __call__(self, identity: str, request: dict) -> Decision:
        platform = self.platform
        manifest = self.manifests.get(identity)
        if manifest is None:
            return Decision(False, f"no manifest is bound to {identity} (S6)",
                            clause="/permissions")

        operation = request.get("op")

        if operation == "entity.publish":
            entity_id = request.get("entity") or ""
            state = str(request.get("state"))
            attributes = dict(request.get("attributes") or {})
            naming = {k: v for k, v in dict(request.get("naming") or {}).items()
                      if k in ("name", "device", "has_entity_name")}
            owner = platform.owners.get(entity_id)
            if owner is None or owner == identity:
                def publish_own() -> Decision:
                    # Owner recorded only once the platform has the entity. Recorded first, a
                    # refused publish still left the sandbox owning the id (W1 review).
                    platform.publish(identity, entity_id, state, attributes, naming)
                    platform.owners[entity_id] = identity
                    return granted
                granted = Decision(True, "its own entity", clause="(ambient: §5.10.2)",
                                   act=_refusable(publish_own, "(ambient: §5.10.2)"))
                return granted
            # Someone else's entity. Now it is a permission, and §5.10.3 names which one.
            decision = manifest.decide({"op": "entity.write", "entity": entity_id})
            if not decision.allowed:
                return Decision(False, f"{entity_id} belongs to {owner}; {decision.reason}",
                                clause=decision.clause)

            def write_theirs() -> Decision:
                platform.write(entity_id, state, attributes)
                return decision
            return Decision(True, decision.reason, decision.clause,
                            act=_refusable(write_theirs, decision.clause))

        decision = manifest.decide(request)
        if not decision.allowed:
            return decision

        # Step 5, deferred. Only with the mediator's own view of the platform.
        if operation == "entity.read":
            entity_id = request.get("entity") or ""

            def read() -> Decision:
                state, attributes = platform.read(entity_id)
                return Decision(True, decision.reason, decision.clause,
                                data={"state": state, "attributes": attributes})
            return Decision(True, decision.reason, decision.clause,
                            act=_refusable(read, decision.clause))

        if operation == "service.call":
            service = request.get("service") or ""
            service_domain, _, service_name = service.partition(".")
            data = dict(request.get("data") or {})

            def call() -> Decision:
                platform.call_service(service_domain, service_name, data)
                return decision
            return Decision(True, decision.reason, decision.clause,
                            act=_refusable(call, decision.clause))

        # §7.24's egress path. The one capability whose step 5 produces a **kernel object**
        # rather than a value: the mediator resolves, re-checks the resolved address and
        # connects, and the connected descriptor rides back as ancillary data on the response
        # frame. `broker` and `relay` are optional so that every arm which does not grant
        # network keeps a policy with no network code in it at all — S6 by construction rather
        # than by a branch that has to remember to deny.
        if operation == "network.egress":
            broker = self.broker
            if broker is None:
                return Decision(False, "this framework was started without an egress broker",
                                clause=decision.clause)

            def connect() -> Decision:
                try:
                    fd, record = broker.open(identity, request, decision)
                except _EgressRefused as err:
                    return Decision(False, err.reason, err.clause)
                return Decision(True, decision.reason, decision.clause,
                                data={"host": record["host"], "port": record["port"]}, fd=fd)
            return Decision(True, decision.reason, decision.clause, act=connect)

        if operation == "network.tcp.local":
            broker = self.broker
            if broker is None:
                return Decision(False, "this framework was started without an egress broker",
                                clause=decision.clause)

            def connect_local() -> Decision:
                try:
                    fd, record = broker.open_local(identity, request, decision)
                except _EgressRefused as err:
                    return Decision(False, err.reason, err.clause)
                return Decision(True, decision.reason, decision.clause,
                                data={"address": record["address"], "port": record["port"]},
                                fd=fd)
            return Decision(True, decision.reason, decision.clause, act=connect_local)

        if operation in ("network.udp.send", "network.udp.recv",
                         "discover.scan", "discover.listen"):
            relay = self.relay
            if relay is None:
                return Decision(False, "this framework was started without a datagram relay",
                                clause=decision.clause)
            action = {"network.udp.send": relay.send, "network.udp.recv": relay.recv,
                      "discover.scan": relay.scan, "discover.listen": relay.listen}[operation]

            def datagrams() -> Decision:
                try:
                    answer = action(identity, request, decision)
                except _EgressRefused as err:
                    return Decision(False, err.reason, err.clause)
                # A socket the relay opened for this channel goes to the mediator to watch
                # (W2 (b)); it is never part of the answer.
                source = answer.pop("_source", None)
                return Decision(True, decision.reason, decision.clause,
                                data={k: v for k, v in answer.items()
                                      if k not in ("ok", "clause")}, source=source)
            return Decision(True, decision.reason, decision.clause, act=datagrams)

        # `entity.subscribe`: the mediator, which holds the channels, adds the entity to that
        # channel's subscriptions once this is allowed and recorded. Step 5 is asking the platform
        # to start sending that entity's changes — a no-op on the stand-in, and on the real
        # platform a widened `subscribe_entities`, so (A) sends only what someone subscribed to.
        if operation == "entity.subscribe":
            entity_id = request.get("entity") or ""

            def watch() -> Decision:
                platform.watch(entity_id)
                return decision
            return Decision(True, decision.reason, decision.clause,
                            act=_refusable(watch, decision.clause))

        return decision


def acting_policy(manifests: dict[str, Manifest], platform: Platform,
                  broker: object | None = None, relay: object | None = None,
                  approvals: Path | None = None) -> ActingPolicy:
    """The name every harness already calls. Kept so that none of them has to change."""
    return ActingPolicy(manifests, platform, broker, relay, approvals=approvals)
