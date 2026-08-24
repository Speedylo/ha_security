# Chapter 5 — Architecture and design rationale

## 5.1 What this chapter must settle

Chapters 3 and 4 constrain this design tightly enough that most of it is determined. Chapter
3 fixed nineteen requirements and four constraints; Chapter 4 enumerated eighteen threats
against a system that has none of them, found four Critical risks, and observed that those
four share a single cause. This chapter converts that into an architecture, and it is
answerable for five things:

1. **The two questions Chapter 3 deliberately left open** (§3.9): how an unmodified
   integration can execute outside the process it was written to run inside, and who authors
   the manifest given that C3 forbids assuming the author is honest.
2. **The four decisions this rebuild re-opened.** The first pass settled a platform, a
   compatibility strategy, an isolation primitive and an implemented scope. None is assumed
   here. Each must be reached by argument from evidence gathered in this pass, and where the
   argument arrives somewhere different, the divergence is followed and reported rather than
   suppressed.
3. **The manifest**, promoted from the strawman of §1.10 to a specified schema with a stated
   granularity, since S5 constrains granularity without fixing it.
4. **Two arguments promised earlier and not yet discharged**: the defence-in-depth framing of
   §1.6, and §1.9's claim that relocation without scoping does not constrain authority. §1.9
   has now been made twice; this chapter must *discharge* it, not repeat it.
5. **Traceability in the other direction.** Chapter 4 mapped each threat to a control and a
   requirement. This chapter must show where each of those controls actually lives, and
   §5.14 is where that is checked rather than asserted.

**The standard being applied.** A design chapter can be written two ways: as a description of
what was built, or as a record of what was chosen and why. The second is what is graded, and
it is also the only one that survives a viva, because a viva probes the alternatives. Options
that were considered and rejected are therefore recorded in `notes/`, and the ones that were
close are recorded in this chapter.

## 5.2 The design problem, restated precisely

Chapter 1 established that an integration can reach the assets of Table 1.2. Chapter 4
established that the four Critical risks share one cause. Neither states the mechanism at the
level of precision a design needs, so this section does.

**Home Assistant loads an integration with Python's ordinary import machinery.** The whole of
the coupling is one line of `homeassistant/loader.py`:

```python
cache[domain] = cast(ComponentProtocol, importlib.import_module(self.pkg_path))
```

The platform's own comment above it describes the function as "mostly a thin wrapper around
importlib.import_module with a dict cache". Because importing a Python module *executes* it,
the integration's code runs inside the platform's process, in the same interpreter and the
same address space, from the moment it is loaded. Two call sites then hand that code the root
object of the running system: `setup.py` passes `hass` to `async_setup`, and
`config_entries.py` passes both `hass` and the configuration entry — the object holding that
integration's stored credentials — to `async_setup_entry`.

From `hass`, the following are reachable by ordinary attribute access: the shared data
dictionary holding every integration's runtime state, the event bus, the service registry,
the state machine, the configuration directory path, the authentication manager, the HTTP
server, every integration's stored configuration, and the event loop itself. A weather
integration needs approximately one of these. It is handed all nine.

**The decisive property is that none of this is conferred by a grant that could be withheld.**
Two facts establish it. First, the root object is ambient rather than disclosed: Home
Assistant stores it in module-level state and publishes `async_get_hass()`, whose documented
purpose is to supply it to code that was not passed it. Withholding the argument would
withhold nothing. Second, and more fundamentally, code sharing an interpreter can enumerate
the objects that interpreter holds — which is the technique Corno and Mannella demonstrate to
reach another integration's live object and read and modify its private state (§2.4.1).

An integration's authority is therefore **positional**: it is a consequence of where the code
runs, not of anything handed to it. This is the single most important sentence in the
chapter, and three consequences follow immediately.

**First, no in-process control can be sound.** A permission layer living in the same
interpreter as the code it constrains is an object in that interpreter's heap, reachable by
the same technique. This is S1, and it is why S1 was called the highest-leverage requirement
in §3.8.

**Second, relocation alone changes nothing — the §1.9 discharge.** §1.9 examined the *Remote
Integration Execution* proposal, which would allow integrations to run on separate machines,
and observed that its motivation is principally reliability. The precise reason relocation is
insufficient can now be stated. Moving the code changes its position, and position is exactly
what conferred its authority — so unless the *new* position confers less, nothing has been
gained. An integration relocated to another machine must still read and write platform state
to be useful, which means it must hold a credential that Home Assistant honours. If that
credential is unscoped, the relocated integration has the same authority it had before,
exercised over a socket rather than a pointer. Relocation without scoping relocates authority
rather than reducing it. This is why S2 requires that the confined code hold no such
credential, and it is why this project is complementary to that proposal rather than
competing with it: the proposal supplies a mechanism for moving code, and what is missing
from it is the scoping.

**Third, the design target is now expressible in one sentence.** The confined integration must
be somewhere that confers no authority, while still being able to obtain — by request, subject
to a decision — exactly the authority its manifest declares. Everything remaining in this
chapter is a consequence of trying to build that while satisfying C1 and C2.

> **On the evidence for this section.** The coupling above was re-derived for this pass by
> reading Home Assistant 2026.8.3 (commit `759e465`) directly, and the method, the full
> attribute table and the line references are in `notes/ch5_evidence_ha_coupling.md`. The
> first pass had reached the same conclusion; under the evidence rule (`00_METHOD.md` §2)
> that was private knowledge and not usable here until re-derived.

## 5.3 Where enforcement can live

Given a design target, the first question is architectural rather than technical: at what
point in the system does a decision get made? Four locations are available, and three are
eliminated by requirements already fixed.

| Location | What it would mean | Verdict |
|---|---|---|
| **L1 — Inside the integration** | A wrapper, decorator or import hook in the integration's own process rejecting disallowed calls | **Eliminated by S1.** In the integration's own address space, therefore reachable by the demonstrated technique. Also fails C3: an author who does not call the wrapper is not constrained by it |
| **L2 — Inside Home Assistant core** | The platform checks a manifest before honouring a call | **Eliminated by C2.** Requires modifying core. Would be the *right* answer for the platform project to adopt, and §5.15 returns to this — but it is a proposal, not a deployable control |
| **L3 — In a separate process on the same host** | The integration runs confined; a mediator in another process holds the credential and decides | **Available** |
| **L4 — In a separate host** | As L3, across a network | **Available, and strictly weaker on C4** — it requires a second machine, which §1.1's deployment does not have |

**L1 deserves more than a table row**, because it is the design most people propose first and
because a variant of it is genuinely useful later. Python offers real interception machinery:
import hooks, audit hooks, module-level shadowing. All of it executes in the interpreter it
is trying to police. Against a buggy integration it works; against a hostile one it is an
object in a heap the adversary can enumerate. This distinction — effective against accident,
void against intent — is precisely the likelihood/impact split of §1.6, and it is why L1
reappears in §5.12 as a defence-in-depth layer and never as the boundary.

**L3 is therefore the architecture**, and the choice is forced rather than preferred: S1
requires enforcement outside the integration's execution context, C2 forbids putting it in
core, and C4 makes a second machine unavailable in the general case. The remaining design
space is *how* to build L3, not whether.

This yields the shape the rest of the chapter fills in:

- a **confined execution context** the integration runs in, conferring no ambient authority;
- a **mediator** in a separate process, holding the platform credential (S2), deciding each
  request against the manifest (F3, S6), and recording the decision (S7);
- a **channel** between them carrying per-integration identity (T02);
- a **manifest** the decisions are made against (F3, S5).

Each is settled below, in the order in which the evidence forces them.

## 5.4 Decision 1 — the platform

The first of the four re-opened decisions is which platform this work targets. It is recorded
here for completeness and because Gate G2 requires all four to be revisited, but it is settled
with less argument than the others, for a reason worth stating plainly: **this decision was
made by Chapters 1 and 2, on evidence, and re-litigating it here would be theatre.**

The evidence that made it is: an ecosystem of 4,220 community integrations installed on 56.6%
of reporting installations (§1.3); a documented incident class in this specific ecosystem, the
2021 disclosures affecting eight integrations (§1.5); a platform whose own security
documentation places third-party integration behaviour outside its security programme (§1.8);
a published threat model of this exact platform to evaluate against (§2.4.1); and a systematic
review naming a Home Assistant proof-of-concept as future work (§2.4.3). No comparable
combination of scale, documented harm, platform-acknowledged gap and published evaluation
baseline was found for any other platform during the Chapter 2 search.

**Divergence from the first pass: none.** The first pass chose Home Assistant, and this pass
re-derives it. Per `01_PLAN.md` §6, re-reaching a decision through an independent chain is
reported as confirmation rather than passed over in silence — but it is also weak
confirmation here, since Chapters 1 and 2 were written about this platform and a chain that
begins with a platform will tend to end with it. The honest statement is that the platform
choice is **not contested by this work and not independently re-tested by it**.

## 5.5 The relocation problem

This is the hardest engineering question in the project, deferred from §3.9 on purpose so
that Chapter 4 could constrain the answer before it was attempted.

**The problem.** C1 requires that integrations run unmodified — no change to their source,
counted mechanically. §5.2 established that an integration's code says `hass.states.async_set(...)`,
`hass.data[DOMAIN]`, `hass.bus.async_listen(...)`, `hass.config.path(...)`, and expects real
answers. §5.3 established that the code must run somewhere that confers no authority.

These two are in direct tension, and the tension is the whole difficulty: **the integration
must find, at the end of every one of those attribute paths, something that behaves as the
real object did — while the real object is in another process and must stay there.**

**The criteria any candidate must meet**, drawn from requirements already fixed:

| # | Criterion | Source |
|---|---|---|
| K1 | Integration source is unchanged | C1 |
| K2 | Home Assistant core is unchanged | C2 |
| K3 | The confined side holds no credential Home Assistant honours | S2 |
| K4 | Every mediated request carries the integration's identity | T02, S7 |
| K5 | Reads and subscriptions are mediated, not only writes | S3 |
| K6 | Runs within the resources of a single-board computer | C4, N1 |
| K7 | Undeclared operations fail closed | S6, N3 |

**The candidates.** Four are viable enough to be worth comparing, and a fifth is recorded
because it will be asked about.

| ID | Approach | Sketch |
|---|---|---|
| **R1** | **Proxy object** | The confined process runs the integration against a stand-in that presents the same attribute surface and forwards each access to the mediator over IPC |
| **R2** | **Minimal platform in the sandbox** | A cut-down real Home Assistant runs inside the confined process, so the integration talks to a genuine local object; only outward effects — state writes, service calls, egress — are mediated |
| **R3** | **Loader interposition** | A custom component installs an import hook so the integration is loaded with a substituted `hass`, staying inside the platform process |
| **R4** | **Wait for the RFC** | Build the scoping layer on *Remote Integration Execution*, and let the platform solve relocation |
| **R5** | **Ask authors to port** | Define an out-of-process integration API and have authors adopt it |

**R5 is eliminated by C1**, and the elimination is the finding of §2.2: Chrome could require
migration because it was a new platform with no installed base; a mechanism for 4,220 existing
volunteer-written integrations cannot. It is recorded because "why not just define a better
API?" is the most common first question, and the answer is that the entire problem is the
existing corpus.

**R3 is eliminated by S1.** Substituting `hass` inside the platform's own process leaves the
integration in the interpreter that holds everything, where the substitution is an object it
can route around — including by calling `async_get_hass()`, which returns the real one. R3 is
a *compatibility* technique that answers nothing about *authority*, and mistaking one for the
other is precisely the error §1.9 warns about.

**R4 is eliminated as a dependency, and retained as a relationship.** The proposal was
examined for this pass against Home Assistant 2026.8.3: it is not implemented — no remote
execution machinery exists in the release, and the RFC remains an open community discussion.
A capstone cannot depend on an unshipped proposal. The relationship §1.9 identified stands
unchanged: if it ships, it supplies relocation and this work supplies the scoping that §5.2
showed relocation does not provide by itself.

**That leaves R1 and R2, and they are genuinely different designs** rather than variants. The
comparison is the substance of the decision, and it is taken up in §5.6.

## 5.6 Decision 2 — how the integration runs, and what it finds

**R1 — the proxy object.** The confined process runs the integration against a stand-in for
`hass` that presents the same attribute surface and forwards each access to the mediator.
Mediation is then total by construction, because every access is already a message.

**R2 — a real, minimal platform in the sandbox.** The confined process runs a stripped Home
Assistant. The integration imports the genuine helper layer and receives a genuine `hass`
object — but a *local* one, whose state machine, service registry and event bus are private
to the sandbox and start empty. A single bridge component forwards permitted effects to the
mediator, which holds the credential and applies them to the real platform.

**The decision is R2.** Three arguments, and they are ordered by weight rather than by how
obvious they are.

### 5.6.1 What integrations are actually written against

R1's premise is that `hass` is the compatibility surface. It is not; it is the entrance to
it. To establish this rather than assert it, every integration shipped with Home Assistant
2026.8.3 was examined for what it imports and calls:

| What the integration touches | Integrations | Share |
|---|---|---|
| `homeassistant.helpers` — the helper layer | 1,356 | **91%** |
| `async_add_entities` — helper-layer entity registration | 941 | 63% |
| `DataUpdateCoordinator` — helper-layer polling | 572 | 38% |
| `hass.data` — the shared dictionary directly | 279 | 18% |
| `hass.states.async_set` — setting state directly on `hass` | **2** | **0.1%** |

*n = 1,482 integrations; method and command in `notes/ch5_working_notes.md`.*

Integrations are, overwhelmingly, not written against `hass`. They are written against Home
Assistant's **helper layer** — its entity base classes, its polling coordinator, its platform
registration. Two integrations in 1,482 write state directly on `hass`.

The consequence for R1 is structural, not incidental. The helper layer is Home Assistant's
own code; under *any* confined design it runs inside the sandbox alongside the integration,
and it expects real platform internals beneath it. Substituting `hass` therefore substitutes
the thing almost nothing uses directly, and leaves the 91% case resting on how faithfully
that layer's expectations are reproduced — a surface that is large, undocumented because it
was never intended as a public contract, and free to change every release. R1 does not remove
the compatibility problem; it relocates it to the least documented place available.

> **Stated limit.** These are the integrations shipped with the platform, not the community
> integrations this work targets. The measurement establishes the *shape* of the dependency,
> which is what the argument needs; it does not establish its exact magnitude in HACS, and
> Chapter 7 re-runs it over the target population before any figure here is quoted as
> characterising it.

### 5.6.2 Default denial becomes structural rather than procedural

Under R1, every read is a request that must be checked, and S6 holds exactly as long as no
path is left unchecked. Under R2, the sandbox's state machine **starts empty**. An
integration reading an undeclared entity is not refused by a check — there is nothing there
to read. Only what the manifest declares is mirrored in.

The same is true of the service registry: a sandbox whose registry holds nothing offers
`lock.unlock` to no one. S3 and S6 are then properties of the shape of the system rather than
obligations on an implementer's diligence, and a design whose safe behaviour is its default
state is stronger than one whose safe behaviour is a check that must never be forgotten.

### 5.6.3 The premise and the cost were tested before the decision was taken

R2's advantages are worthless if a real Home Assistant cannot be built small enough, or if
the helper layer does not in fact work against a locally-constructed instance. Both were
open questions, and deciding first and discovering later is the expensive order. They were
therefore measured on the target hardware — a Raspberry Pi 5 with 4 GB, the C4 device —
before this section was written. The full write-up is `experiments/r2_footprint/`.

A threshold was fixed in advance: if one sandbox cost more than roughly a fifth of the
device's memory — 809 MB — R2 would not survive C4 and the design would fall back to R1.

| Question | Result |
|---|---|
| Can a Home Assistant instance be built without `bootstrap`? | **Yes** |
| Does an ordinary integration run against it? | **Yes** — config entry reaches `LOADED` and publishes its entity |
| First sandbox | **176 MB** resident; ready in 6.1 s |
| **Each additional sandbox** | **136 MB** |
| Capacity in 60% of the device's memory | **~17 sandboxes** |

The test integration was written in the ordinary idiom — a config entry, a
`DataUpdateCoordinator`, a `SensorEntity`, `async_add_entities` — precisely the pattern
§5.6.1 found to dominate, and it ran against an instance with no HTTP server, no recorder, no
frontend and no authentication.

The marginal figure is the one quoted, and the distinction matters: most of a sandbox is the
Python interpreter and the Home Assistant library, which the operating system maps into every
sandbox from the same physical pages. Measured at six concurrent sandboxes, the sum of
resident memory was 970.8 MB while the machine actually consumed 844.6 MB, and per-sandbox
proportional memory fell from 154.7 MB at one sandbox to 136.4 MB at six as the sharing became
visible. Reporting 176 MB per sandbox would have overstated the cost of six by 126 MB.

**One design consequence came out of the experiment rather than out of the reasoning.** The
sandbox cannot use `bootstrap`: `homeassistant/bootstrap.py` imports `.components` at module
level — the frontend and the recorder's sensor support among them — which is exactly the
weight the sandbox exists to avoid. A minimal instance is constructed directly and its
registries wired by hand. This is a property of the design, not a detail of its
implementation, and it is recorded here for that reason.

**What the experiment does not establish**, stated so that it is not later read as more than
it is: one integration was tested, and a synthetic one; the sandboxes were measured idle; and
no mediator was attached, so the bridge and the inter-process channel will add cost not
counted here. It establishes that the premise holds and the cost is affordable. It is not the
compatibility evaluation, which is Chapter 7's and is a different measurement entirely.

### 5.6.4 Divergence from the first pass — Gate G2

**The first pass built R1.** This pass reaches R2, and per `01_PLAN.md` §6 a divergence at
Gate G2 is reported prominently rather than absorbed quietly.

The divergence is genuine and it is the most substantial result of rebuilding the chain. The
first pass arrived at a proxy design by growing outward from an implementation — the shim was
built because something had to make an integration run, and the question of what integrations
are *actually written against* was never posed as a measurement. This pass posed it, and the
answer inverted the design.

**A discipline note on how this argument is allowed to be made.** The first pass's experience
of building a proxy — its size, its difficulty — is private knowledge under `00_METHOD.md` §2
and is not evidence here. It cannot appear in this chapter, and the argument above does not
rest on it: §5.6.1 is a measurement taken in this pass, and §5.6.3 is an experiment run in
this pass. Both would stand had the first pass never happened. That is the test the evidence
rule sets, and it is met.

### 5.6.5 The re-decision point, and what would trigger it

R2 is chosen on evidence that is real but partial: one integration, measured idle, without a
mediator. The honest position is that implementation can still refute it, and the fallback is
identified now rather than improvised later.

**The design reverts to R1, with a reduced scope, if any of the following holds at Gate G3
(end of October, `01_PLAN.md` §6):**

| Trigger | Why it would be decisive |
|---|---|
| Footprint with the mediator and bridge attached leaves fewer sandboxes than a realistic installation needs | C4 and N1 are not negotiable; an unadoptable control protects nobody |
| Real community integrations fail against a minimal instance for reasons a *fuller* instance would fix | Would mean the stripping, not the architecture, is what breaks compatibility — and R1 would then be no worse |
| Version coupling between sandbox and host proves unmanageable in practice | An operational cost R1 does not carry |

Reverting is not cheap, and saying so is part of the decision: the bridge would be replaced by
a proxy, and the compatibility evaluation would have to be re-run. It is cheaper than
discovering in November that the architecture does not fit, which is why the experiment was
run before the choice rather than after it.

Two considerations bound the risk. The measured margin is wide — 136 MB against a 809 MB
threshold — so the footprint trigger has room before it fires. And **60 MB of the 176 MB is
the platform's own base component**, which Chapter 6 tests first for removability; if it can
go, capacity roughly doubles.

**A consequence for §5.8.** Seventeen sandboxes is sufficient but not generous, and an
installation with more integrations than that cannot have one sandbox each. The implemented
scope decision is therefore load-bearing rather than cosmetic, and it now has a number to be
decided against rather than an intuition.

## 5.7 Decision 3 — the isolation primitive

§5.6 settled what runs in the sandbox. This section settles what the sandbox *is*: the
mechanism that makes the confined process a place conferring no authority. It is the third
of the four decisions Gate G2 re-opened.

### 5.7.1 What the primitive has to deliver

Five requirements bear on it directly, and they are not equally easy to satisfy.

| Requirement | What the primitive must provide |
|---|---|
| **S1** | An execution context the mediator is not inside |
| **S2** | No path from the sandbox to a platform credential — including the process table (T15) and the filesystem (T14) |
| **S8** | Filesystem and process isolation confined to declared resources |
| **S9** | Resource limits (T16 — the one threat Chapter 4 found with no control at all) |
| **S4** | Egress attributable *per integration* |
| **C4 / N1** | Affordable at the scale §5.6.3 measured — the budget is roughly 17 sandboxes |

**S4 deserves particular attention, because it is where this project differs from its closest
prior work.** §2.4.2's gateway MUD architecture consolidates every plug-in's declaration into
a single gateway-level profile, enforced by a firewall that sees one host — so the effective
policy for any plug-in becomes the union of all of them, and attribution is impossible in
principle rather than merely unimplemented. Any primitive chosen here must give each
integration its own network identity, or this project inherits the same limitation it
identified in the prior work.

### 5.7.2 The candidates

| ID | Primitive | Verdict |
|---|---|---|
| **I1** | Linux namespaces + seccomp-BPF + cgroup v2, driven by a supervisor | **Chosen** |
| **I2** | OCI containers (Docker, Podman) | Viable, but a packaging choice built on I1 — see below |
| **I3** | gVisor — a user-space kernel intercepting syscalls | Stronger containment, unaffordable here |
| **I4** | microVMs (Firecracker, QEMU) | Strongest containment, decisively unaffordable |
| **I5** | Language-level confinement (`RestrictedPython`, sub-interpreters) | **Eliminated by S1** |
| **I6** | WebAssembly | **Eliminated by C1** |

**I5 and I6 are eliminated before cost is considered.** Language-level confinement puts the
restriction in the same interpreter as the code it restricts, which is exactly the class §5.2
showed to be unsound — and §5.3's L1 argument applies unchanged. WebAssembly cannot run
CPython integrations with native extensions unmodified, so it fails C1 at the first
integration that imports a compiled dependency; the elimination is C1's, not a judgement
about the technology.

**I3 and I4 are eliminated on cost, and the arithmetic is the argument.** §5.6.3 measured a
marginal sandbox at 136 MB using ordinary processes, against a device with 4 GB. Namespaces
add essentially nothing to that: they are kernel bookkeeping, not a runtime. gVisor adds a
user-space kernel process per sandbox and intercepts every system call — and a Python
interpreter is syscall-heavy. A microVM adds a guest kernel per sandbox. Either would consume
the margin that makes ~17 sandboxes possible, and C4 is a constraint rather than a preference.
This is a trade the design is *losing* something on, and §5.7.5 says what.

**I2 is not really a competitor.** Docker and Podman are management layers over precisely the
primitives I1 uses. Choosing them would add a daemon or a toolchain to the deployment without
adding a boundary, and Home Assistant is itself frequently deployed inside a container, which
makes nesting an operational problem rather than a convenience. The distinction worth keeping
is that **I1 is the security boundary and containerisation is a packaging question**, which
Chapter 6 may revisit without reopening this decision.

### 5.7.3 The decision, and what each primitive does

**I1: a supervisor that places each integration in its own set of namespaces, applies a
seccomp-BPF filter, and confines it to a cgroup v2 slice.**

| Mechanism | Requirement served | Effect |
|---|---|---|
| **user** namespace | S2, S8 | The sandbox's root is an unprivileged uid outside it; no privileged operation on the host |
| **mount** namespace | S8, T14 | A private filesystem view: the integration's own directory and nothing else. `secrets.yaml` is not merely unreadable, it is absent |
| **pid** namespace | S8, T15 | The sandbox sees only its own processes, closing the `/proc/<pid>/environ` read that T15 records as requiring no attacker skill |
| **network** namespace | **S4**, T10 | Each integration gets its own network stack with no route to anywhere. All egress leaves through the mediator, so the request's origin is known by construction |
| **ipc**, **uts** namespaces | S8 | Removes shared memory and hostname as side channels |
| **seccomp-BPF** | S8 | Denies syscalls outside the set an integration needs |
| **cgroup v2** | **S9** | Bounds memory, CPU and process count — the control T16 had none of |

**The network namespace is the part that matters most**, and it is worth stating plainly why.
Per-integration egress attribution (S4) is not achieved by inspecting traffic and inferring
its source, which is what a gateway-level firewall must do and why §2.4.2's design cannot
attribute. It is achieved by giving each integration a network stack whose only exit is the
mediator. Attribution becomes a property of the topology rather than a deduction from it, and
T11's resolve-then-pin requirement becomes implementable because the mediator, not the
integration, performs the resolution.

### 5.7.4 The primitives were verified on the target, not assumed

A design that assumes kernel features is only as good as the kernel it runs on, so the C4
device was probed directly (`experiments/host_isolation_probe/`, run 2026-08-24 against
Raspberry Pi OS trixie, kernel 6.12.47, on the Pi 5):

| Primitive | Result |
|---|---|
| Unprivileged user + net + pid namespaces | **Available** — created as an ordinary user; inside, uid 0, pid 1, and a single interface |
| All seven namespace types | Present |
| seccomp-BPF | Present, including `user_notif` |
| cgroup v2 with `pids`, `cpu`, `io`, `cpuset` | Available |
| cgroup v2 `memory` | **Missing** |

Two consequences follow, and the second is a genuine constraint on deployment rather than a
detail.

**The supervisor does not need to be privileged.** Unprivileged user namespaces work on the
target, so a sandbox can be created without granting the framework root. That is worth having
for its own sake: a confinement mechanism that must run as root to confine anything enlarges
the very surface it is meant to reduce.

**S9's memory limit is not available on a default Raspberry Pi OS installation.** The probe
found `cgroup_disable=memory` on the kernel command line, which is that distribution's
default, and the memory controller is consequently absent. Bounding memory therefore requires
a boot-time configuration change and a reboot before the framework can enforce S9 at all.

This is exactly the kind of finding that is cheap now and expensive in November, and it forces
a design decision rather than merely being noted. **Under N3 the framework must refuse to
start, with a stated reason, when the memory controller is unavailable** — not start anyway
and leave T16 uncontrolled while implying protection. N3 requires a stated failure mode
precisely because §1.6's complaint about the status quo is that the user's exposure is
invisible; a framework that silently ran without the one control T16 has would reproduce that
property under a security label.

### 5.7.5 What is being given up, and the residual risk

**The kernel is the boundary.** I1's confinement is enforced by the same kernel the sandboxed
code makes system calls into, so a kernel vulnerability reachable through the syscalls seccomp
still permits defeats the sandbox. I3 and I4 exist to shrink exactly this surface, and both
were rejected on cost in §5.7.2.

Stated as a residual risk rather than argued away: this design assumes the host kernel is
sound, and it is a weaker assumption than a microVM design makes. Three things bound it
without removing it — seccomp reduces the reachable syscall surface, the user namespace means
a successful escape lands on an unprivileged uid rather than root, and the alternative that
would remove it costs more than C4 permits. **A deployment where the threat model justifies
the expense should prefer I3 or I4, and the architecture does not prevent that**: the
supervisor's interface to the sandbox is process creation, and substituting a stronger
sandbox is a change of implementation, not of design.

### 5.7.6 Divergence from the first pass — Gate G2

**None: the first pass also chose namespaces and seccomp, and this pass re-derives them.**
Per `01_PLAN.md` §6 that is reported as independent confirmation.

It is worth more than the platform confirmation of §5.4, and the reason is the route. §5.4
conceded that a chain beginning with Home Assistant will tend to end there. Here the chain
arrived through criteria the first pass did not have in this form: S4's attribution
requirement, which came out of Chapter 2's reading of the gateway MUD architecture's
consolidation limitation; S9, which Chapter 4 generated itself in §4.10.1; and a measured
memory budget from §5.6.3 that made the cost comparison arithmetic rather than intuition. The
same answer reached along a different road is the case where confirmation carries weight.

The one thing the first pass did not produce is §5.7.4's finding about the memory controller,
which came from probing the target rather than from reasoning about it.

---

*Chapter in progress. §5.8 (implemented scope) onward is next; the section plan is in
`notes/ch5_working_notes.md`.*
