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
per `00_METHOD.md` §2. Chapter 7 re-derives it or drops it.

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

from .manifest import Manifest
from .mediator import Decision


@dataclass
class Platform:
    """A stand-in Home Assistant: entity states, their owners, and the calls made on it."""

    states: dict[str, tuple[str, dict]] = field(default_factory=dict)
    owners: dict[str, str] = field(default_factory=dict)
    calls: list[tuple[str, str, dict]] = field(default_factory=list)

    def seed(self, entity_id: str, state: str, **attributes: object) -> None:
        """An entity that already exists — a device the user owns, not a sandbox's."""
        self.states[entity_id] = (state, dict(attributes))
        self.owners.setdefault(entity_id, "the platform")


def acting_policy(manifests: dict[str, Manifest], platform: Platform):
    """Steps 2, 3 and 5. The mediator keeps 1 and 4, which is where identity and the record are.

    Ambient operations are handled before the manifest is consulted, because they are not
    permissions: an integration publishing its own entity is what being an integration *is*
    (§5.10.2), and asking a manifest about it would invite a clause that everyone must hold.
    """
    def policy(identity: str, request: dict) -> Decision:
        manifest = manifests.get(identity)
        if manifest is None:
            return Decision(False, f"no manifest is bound to {identity} (S6)",
                            clause="/permissions")

        operation = request.get("op")

        if operation == "entity.publish":
            entity_id = request.get("entity") or ""
            owner = platform.owners.get(entity_id)
            if owner is None or owner == identity:
                platform.owners[entity_id] = identity
                platform.states[entity_id] = (str(request.get("state")),
                                              dict(request.get("attributes") or {}))
                return Decision(True, "its own entity", clause="(ambient: §5.10.2)")
            # Someone else's entity. Now it is a permission, and §5.10.3 names which one.
            decision = manifest.decide({"op": "entity.write", "entity": entity_id})
            if decision.allowed:
                platform.states[entity_id] = (str(request.get("state")),
                                              dict(request.get("attributes") or {}))
            return Decision(decision.allowed,
                            decision.reason if decision.allowed
                            else f"{entity_id} belongs to {owner}; {decision.reason}",
                            clause=decision.clause)

        decision = manifest.decide(request)
        if not decision.allowed:
            return decision

        # Step 5. Only now, and only with the mediator's own view of the platform.
        if operation == "entity.read":
            entity_id = request.get("entity") or ""
            state, attributes = platform.states.get(entity_id, (None, {}))
            return Decision(True, decision.reason, decision.clause,
                            data={"state": state, "attributes": attributes})
        if operation == "service.call":
            service = request.get("service") or ""
            service_domain, _, service_name = service.partition(".")
            platform.calls.append((service_domain, service_name,
                                   dict(request.get("data") or {})))
            return Decision(True, decision.reason, decision.clause)
        return decision

    return policy
