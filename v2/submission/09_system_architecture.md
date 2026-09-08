# 9. System Architecture and Technology Integration

Four decisions determine the architecture. Each was taken against named candidates, and two of the
four **diverged** from the project's first pass when re-examined against evidence.

## 9.1 Decision 1 — where enforcement lives

**The design problem, stated precisely:** the untrusted code, the platform's authority and any
proposed permission check currently occupy the same address space.

Three locations are available. **L1 — in-process** (wrap the API the integration calls). **L2 —
inside the platform's own loader** (a capability check in Home Assistant itself). **L3 — outside
the process** (run the integration elsewhere and mediate).

**L1 is eliminated by evidence, not by preference.** The garbage-collector result [9] shows an
integration enumerating the heap and reaching another integration's live objects. A permission
layer implemented in-process is an object in that heap, and so is any credential it holds. It is
reachable and defeatable by the code it purports to constrain.

**L2 is the better design on every axis except one.** It is where enforcement belongs, it costs
nothing per request, and it is what the platform should eventually do. It is unavailable to this
project because it requires modifying Home Assistant, which C2 forbids — not because it is wrong.
§15.3 states that this project's most durable contribution to L2 may be the evidence such a
proposal would need.

**The decision is L3**, and the report is explicit that it is chosen for deployability rather than
elegance.

## 9.2 Decision 2 — what runs inside the sandbox

Two candidates. **R1 — the proxy object:** run the integration against a stand-in for `hass` that
forwards every attribute access to the mediator, making mediation total by construction. **R2 — a
real, minimal platform:** run a *stripped* Home Assistant inside the sandbox, so the integration
imports the genuine helper layer and receives a genuine `hass` object — but a **local** one whose
state machine, service registry and event bus are private to the sandbox and **start empty**.

**The decision is R2, and the first argument for it is a measurement.** R1's premise is that
`hass` is the compatibility surface. It is not; it is the entrance to it.

**Table 9.1 — What integrations are actually written against**

| What the integration touches | Shipped (n=1,482) | Community (n=144) |
|---|---|---|
| `homeassistant.helpers` — the helper layer | 91% | **100%** |
| `async_add_entities` — helper-layer entity registration | 63% | **83%** |
| `DataUpdateCoordinator` — helper-layer polling | 38% | 58% |
| `hass.states.async_set` — setting state directly on `hass` | **0.1%** | 6.9% |

**Every community integration measured imports the helper layer.** Substituting `hass` therefore
substitutes the thing almost nothing uses directly, and leaves the 91–100% case resting on how
faithfully that layer's expectations are reproduced — a surface that is large, undocumented
because it was never intended as a public contract, and free to change every release. **R1 does
not remove the compatibility problem; it relocates it to the least documented place available.**

**The second argument is that R2 makes default denial structural rather than procedural.** Under
R1, every read is a request that must be checked, and S6 holds exactly as long as no path is left
unchecked. Under R2, **the sandbox's state machine starts empty**. An integration reading an
undeclared entity is not refused by a check — there is nothing there to read. Only what the
manifest declares is mirrored in, and a registry holding nothing offers `lock.unlock` to no one.

> A design whose safe behaviour is its *default state* is stronger than one whose safe behaviour is
> a check that must never be forgotten.

## 9.3 Decision 3 — the isolation primitive

Six candidates were considered. **Language-level confinement** and **WebAssembly** are eliminated
before cost: the first puts the restriction in the same interpreter as the code it restricts;
the second cannot run CPython integrations with native extensions unmodified, so it fails C1 at
the first compiled dependency. **gVisor** and **microVMs** are eliminated on cost — each adds a
per-sandbox kernel to a device where the marginal sandbox already costs 136 MB against 4 GB total,
and C4 is a constraint rather than a preference. **OCI containers** are not a competitor: Docker
and Podman are management layers over precisely the primitives chosen, and Home Assistant is
itself frequently deployed in a container, which makes nesting an operational problem.

**The decision is Linux namespaces + seccomp-BPF + cgroup v2, driven by an unprivileged
supervisor.**

**Table 9.2 — What each primitive does**

| Mechanism | Requirement | Effect |
|---|---|---|
| **user** namespace | S2, S8 | The sandbox's root is an unprivileged uid outside it |
| **mount** namespace | S8, T14 | A private filesystem view. `secrets.yaml` is not merely unreadable — **it is absent** |
| **pid** namespace | S8, T15 | The sandbox sees only its own processes, closing the `/proc/<pid>/environ` read |
| **network** namespace | **S4**, T10 | Its own network stack with no route anywhere. All egress leaves through the mediator |
| **ipc**, **uts** | S8 | Removes shared memory and hostname as side channels |
| **seccomp-BPF** | S8 | **29 syscalls denied**, returning `EPERM` rather than killing, so a refusal stays legible |
| **cgroup v2** | **S9** | Bounds memory, CPU, process count and disk space |

**The network namespace is the part that matters most.** Per-integration egress attribution is not
achieved by inspecting traffic and inferring its source — which is what a gateway-level firewall
must do, and why the closest prior work [18] cannot attribute. It is achieved by giving each
integration a network stack whose only exit is the mediator. **Attribution becomes a property of
the topology rather than a deduction from it.**

**The primitives were verified on the target rather than assumed**, and the probe found two things
a specification would not have: cgroup v2's `memory` controller is **absent** on a stock Raspberry
Pi OS installation and must be enabled at boot, and the `io` controller is present but **not
delegated** to a user manager — which is R7.

> **Figure 9.1 — [TO DRAW]** One sandbox: the six namespaces, the seccomp filter, the cgroup slice,
> the single inherited socket, and what is on each side of the boundary.

## 9.4 The manifest

**The declaration goes in the `manifest.json` the integration already ships**, under a
`permissions` key. This is the design's central economy: **the ecosystem already declares
something authority-shaped** — `iot_class`, `dependencies`, `requirements` — and that declaration
is currently spent on a log line and a discovery heuristic.

**Table 9.3 — The declarable capabilities**, with the measured community use of each

| Clause | Grants | Community use | Granularity |
|---|---|---|---|
| `entities.read` | Reading other entities' state | 38.9% | Entity-ID patterns, **domain required** |
| `entities.subscribe` | State-change subscription | — | Same patterns; polling and watching are the same disclosure |
| `entities.write` | Setting state on entities it does not own | 6.9% | Patterns, domain required |
| `services.call` | Calling a service belonging to something else | 22.2% | **`domain.service`, exact, no wildcards** |
| `events.subscribe` / `events.fire` | Event bus access | 48.6% touch the bus | Explicit event types; `*` is not accepted |
| `network.egress` | Outbound network | — | **`host:port`**, resolved and pinned by the mediator. Non-public destinations require a separate flag |
| `files` | Paths outside its own directory | 33.3% | Individual paths with `read`/`write` |
| `config_entries.read_all` | Enumerating *everyone's* config entries | 41.0% | Separate from the ambient own-entry lifecycle |
| `http.register` | Registering routes on the running server | 19.4% | Explicit path prefixes |

**`hass.auth` — 5.6% of integrations — has no clause and cannot be declared.** Users and tokens
are the platform's authentication state, and a design whose whole purpose is to keep credentials
away from third-party code should not offer a permission that hands them over. Those integrations
are unsupported under this framework, and §12 reports them as such rather than quietly permitting
it.

### 9.4.1 The asymmetry rule

**No wildcard is accepted in `services.call`. Every entry names one `domain.service`.** This is
the single rule S5 exists to produce, and it comes from Tyche [17]: `lock.unlock` is not the
inverse of `lock.lock` in risk terms, and a `lock.*` grant hands over the unlock with the lock.
T05 — an integration calling `lock.unlock` — is the register's joint-highest risk.

**The same rule is not applied to entity patterns**, and the asymmetry is deliberate: an
integration usually cannot know the entity IDs it will need at authoring time, because they depend
on the user's devices, whereas **it always knows which services it calls**, because those are
written into its code. Requiring exactness where it is knowable and permitting patterns where it
is not is what keeps the manifest writable.

### 9.4.2 What no grant may reach

**The configuration root is not grantable, and neither is `.storage/`.** A grant of the
configuration directory would include `secrets.yaml` and the config-entry store — precisely the
capability exercised in the 2021 disclosures. A declared path enclosing either location is
**rejected when the manifest is parsed**, not when it is first used.

**Path grants are checked after resolution**, so `..` traversal and symbolic links cannot escape a
grant. This is the same principle as the network's resolve-then-pin, applied to the filesystem:
**a name is not the thing it names, and checking the name is not checking the thing.**

### 9.4.3 A worked example

```json
{
  "domain": "example_weather",
  "name": "Example Weather",
  "iot_class": "cloud_polling",
  "permissions": {
    "schema_version": 1,
    "network": { "egress": ["api.example-weather.invalid:443"] },
    "entities": { "read": ["sensor.outdoor_temperature"] },
    "resources": { "memory_mb": 192, "max_processes": 8 }
  }
}
```

What this integration **cannot** do, without any of it being written down: call any service, write
any entity, subscribe to any event, read any file outside its own directory, enumerate anyone's
config entries, register an HTTP route, or reach any host but the one named. **Eight of the ten
declarable clauses are denied by their absence**, which is S6.

Note what the declaration *reveals*. This manifest is legible to a user who cannot read Python —
one host, one sensor — and a weather integration requesting `lock.unlock` would be equally
legible. **F4 does its work through the schema's shape rather than through a presentation layer.**

### 9.4.4 One capability that inverts the rule, and why

Every capability in this design denies by absence. **`resources` cannot.** If an absent `resources`
clause meant "no limit", the integration that declares nothing would run unbounded — inverting
default-deny for the single requirement whose threat is an integration consuming everything.
Absence therefore means *the framework's* bound, and a declaration can only be read as a request to
be bound **more** tightly than the default, never less. `resources` sits in a permissions manifest
despite granting nothing because **it is the one capability whose declaration is a constraint on
its declarer.**

## 9.5 The mediator and the channel

### 9.5.1 Not everything is mediated, and that is the performance argument

| Mechanism | Enforced by | Capabilities | Per-request cost |
|---|---|---|---|
| **Structural** | The kernel, at sandbox creation | Filesystem, process visibility, resource limits, everything scoped to "its own" | **None** — the sandbox cannot express the request |
| **Mediated** | The mediator, per request | Entity reads, writes, subscriptions; service calls; events; config-entry enumeration | One round trip |
| **Proxied** | The mediator, per connection | Network egress | One connection setup |

**Structural enforcement is the majority of the manifest.** An integration cannot ask to read
`secrets.yaml` and be refused; the file is not in its mount namespace, so there is nothing to ask.

### 9.5.2 Identity is a property of the channel, not a field in the message

Each sandbox is created with **one connected Unix domain socket, inherited as a file descriptor**.
The supervisor creates the socket pair before the sandbox exists, keeps one end for the mediator,
and passes the other into the child. Nothing else crosses the boundary.

**The mediator knows which integration is speaking because it created that socket for that
sandbox.** There is no identity field to forge, no token to steal, and no authentication step that
could be bypassed: the question "who is asking?" is answered by *which file descriptor the request
arrived on*. The alternative is worth stating in order to reject it — a protocol in which the
sandbox names itself asks the adversary to self-report the one fact the decision turns on, and
would be defeated by a one-line change to the integration.

### 9.5.3 The protocol, and the order of the five steps

Length-prefixed JSON over the socket, carrying request/response in one direction and push in the
other. **Every response carries the clause that decided it**, so attribution is a property of the
protocol rather than something reconstructed from logs afterwards.

The mediator's handling of one request is five steps, in this order:

1. **Identity** — from the socket the request arrived on.
2. **Manifest** — the manifest bound to that integration's content hash.
3. **Decision** — match against the clauses; absent a match, **deny**.
4. **Record** — write the decision, its clause and the identity to the audit log.
5. **Act** — only now, and only using the mediator's own platform credential.

**The order matters and is not an implementation detail: the record is written *before* the
action**, so an action that succeeds and then crashes the mediator is still attributable.

> **Figure 9.2 — [TO DRAW]** The mediated request path, five steps, showing the credential on the
> mediator's side of the boundary and never crossing it.

## 9.6 Mediated egress

The egress broker is the one capability that cannot be enforced structurally, because the
integration must genuinely reach the internet for 41% of the corpus to work at all.

**The broker resolves the declared hostname itself and pins the connection to the resolved
address**, then passes the connected socket into the sandbox by `SCM_RIGHTS`. The sandbox never
holds a route and never performs the resolution, so a hostname that resolves to an internal
address at request time — DNS rebinding, T11 — is refused by the broker on the address rather than
permitted on the name. **Resolve-then-pin is structural by construction**, not a check that could
be skipped.

Two implementation findings are recorded because they changed the design:

- **The name does not survive to the connection.** Measured against twelve running integrations,
  **96% of resolutions go through `aiodns`** rather than `getaddrinfo`, because the platform gives
  every client session an async resolver. Resolution and connection happen in different libraries,
  so the shim must patch **both seams**.
- **A grant of a host is a grant of every port on it.** The clause therefore carries a port. The
  measured sample reached 8123, 6445 and 20086 as well as 443.

A **UDP relay** serves the datagram integrations the measurement found; the quarter of them using
asyncio `DatagramProtocol` transports is named as unserved rather than assumed handled.

## 9.7 Identity and the audit record

**An integration's identity is its domain name plus a content hash of what was loaded.** A name
alone cannot support attribution, because the name is stable across every version an integration
ever ships — and a malicious update through the authorised path is exactly threat T12.

What is hashed is a **tuple of three components, hashed separately and then together**: the source
tree (the code that ran), the manifest including the permissions block (**the manifest *is* the
grant** — a manifest swapped without a source change is an authority change), and the declared
requirements with resolved versions (where supply-chain change actually lands).

**Keeping the three separate is the decision worth defending.** A single composite hash says
*something changed*. Three component hashes say *what* changed — and a source change, a permission
change and a dependency change are different events warranting different responses.

Identity is computed **once per sandbox construction**, which makes "re-check the declaration per
version" automatic rather than a rule someone must remember: a changed integration is a changed
identity before it has run a line.

**Two chains, failing independently.** Each record carries the hash of the record before it, so
modification, deletion or reordering breaks every subsequent link; a keyed MAC over the same
records detects an adversary who rebuilds the chain wholesale. **Decisions are recorded; their
consequences are not** — a subscription is one decision, and logging every state update it then
delivers would bury the record that matters under traffic.

> **Figure 9.3 — [TO DRAW]** The audit record: the three-component identity, the run record, the
> decision records, and the two chains — what each detects and what neither does.

## 9.8 What the design does not do

Stated here rather than conceded later. The **push loop is not built**: declared entities are
mirrored once at sandbox construction, so an integration sees the value that existed when it was
built. This is why S3's subscription half is partial. The **mediator acts on an in-memory stand-in
rather than a live Home Assistant**, so what crossed the boundary is real and carries its clause,
but what a live instance would do with it is untested. **Dependency installation is unresolved**,
so the third component of the identity stays vestigial. Each is priced in §14.
