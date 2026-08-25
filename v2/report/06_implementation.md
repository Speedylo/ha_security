# Chapter 6 — Implementation

## 6.1 What this chapter must deliver

Chapter 5 closes by observing that the design's central claim — that unmodified, pre-existing
integrations can be confined at a cost worth paying — is an empirical claim, and that Chapter 6
is where it stops being an argument (§5.15.6). This chapter is answerable for four things.

1. **The four scope items §5.8.2 derived.** They were not chosen for being achievable. They
   were read out of Chapter 3's verification column, which was written before any design
   existed precisely so that the artifact could not be sized to whatever was easiest to build.
2. **Reconciliation with the artifact that already exists.** A working framework preceded this
   design, and Gate G2 diverged from it twice. The larger of those divergences puts the prior
   work's single biggest component on the wrong side of a decision. §6.2 states what survives,
   what does not, and — the harder discipline — what may be *cited* and what may not.
3. **The obligations Chapter 5 handed forward**: the base-component measurement (§5.6.5), the
   requirement that a sandbox be placed in its cgroup at creation rather than migrated into it
   (§5.7.4), and a surface at which the user encounters the declaration (§5.14.4, T13).
4. **A report against §5.6.5's three re-decision triggers**, so that Gate G3 is decided on
   evidence rather than on how much has been written by then.

**The standard applied.** A chapter can claim something is built on three different strengths
of evidence, and they are not interchangeable:

| Strength | What it means |
|---|---|
| It exists | The code is in the repository and does what it was written to do when read |
| It runs | It has been executed end to end, at least once, and observed to work |
| It was measured | Its behaviour was recorded against a criterion fixed before the run |

This chapter says which of the three applies, every time it claims something. Chapter 7 is
where the third becomes systematic; anything standing only at the first level is named as such
rather than allowed to read as the third.

**A second standard, about what an implementation chapter is for.** Written as a tour of the
code it is a manual, and a manual is not graded. What is graded, and what a viva probes, is the
decisions that implementation forced and design could not have anticipated. §6.3 opens with
one: a measurement Chapter 5 asked for, which corrected Chapter 5.

## 6.2 The prior artifact, and what it is allowed to prove

A working artifact preceded this design: roughly 3,700 lines of framework code, three
unmodified HACS integrations that set up, poll and publish their entities through a
permission-checked channel, a ten-check adversarial probe blocking ten of ten on two
architectures, and an API-surface measurement over 3,105 repositories. It is a two-week
feasibility spike, and it is described here as one.

### 6.2.1 Why this is stated before anything is built

Because the plan rests on it. `01_PLAN.md` §2 argues that rebuilding the chain of reasoning
costs no schedule, on the ground that implementation is largely gap-closing rather than
green-field work. If that is not true, the argument fails and the schedule with it. So the
honest accounting of what survives Chapter 5's decisions belongs at the start of the
implementation chapter, not in its conclusions.

### 6.2.2 What Gate G2's divergences cost

| Prior component | Status under the Chapter 5 design | Why |
|---|---|---|
| **Compatibility shim** — an R1 proxy `hass` | **Superseded** | §5.6 chose R2 on evidence gathered in this pass |
| Shim generator, shim coverage scorer | Superseded with it | They generate and score a surface R2 does not have |
| Isolation by namespaces | **Carried** | §5.7 confirmed the primitive, and probed it on the target |
| seccomp-BPF filter | **Carried** | As above |
| Egress broker | Carried, **re-scoped** | §5.8's F2 and S4 require per-integration attribution across two concurrent integrations |
| Audit chain | Carried, **extended** | §5.12's identity is a three-part tuple the prior chain does not record |
| Supervisor | Carried in role, **rewritten in fact** | §5.7.4's placement-at-creation and §5.11.2's socket-before-sandbox both change its construction order |
| Adversarial probe | **Carried** | It is §5.8.2's fourth scope item, already in the right shape |

The shim was the largest single component of the prior framework, and it is on the wrong side
of §5.6's divergence. **This is a real cost and it is stated as one rather than absorbed.**
`00_METHOD.md` §3 accepted it in advance: a rebuild that could only ever have confirmed its
predecessor would have been theatre, and a rebuild that can diverge has to pay when it does.

One thing the superseded work still buys, and it is worth claiming rather than mourning: R1 and
R2 built against the same integrations would be a stronger compatibility comparison than R2
alone, and neither the prior work nor the literature has it. That is recorded as an **option**
for Gate G3 and not as a commitment — it competes for the same time as coverage-widening, which
§5.8.5 already nominates as the first thing to cut.

### 6.2.3 What may be cited from it, and what may not

`00_METHOD.md` §2 fixes the rule: everything the prior pass learned is private knowledge, and
it is not evidence in this pass's chain until it has been re-derived here with a stated method.
Five things have been:

| Re-derived in this pass | Where |
|---|---|
| What integrations are actually written against | §5.6.1, and `notes/ch5_evidence_api_surface.md` |
| Whether a minimal Home Assistant can host one, and at what cost | §5.6.3, `experiments/r2_footprint/` |
| Whether the isolation primitives exist on the target | §5.7.4, `experiments/host_isolation_probe/` |
| What a mediated request costs | §5.11.4, `experiments/mediation_latency/` |
| Whether the sandbox needs the platform's base component | §6.3.2, `experiments/base_component/` |

Each was run in this pass, on stated hardware, with its method recorded, and each would stand
had the prior pass never happened. That is the test the evidence rule sets.

What the prior artifact is allowed to do in this report is therefore exactly one thing:
establish that a working artifact preceded the design, which is why the schedule in
`01_PLAN.md` holds. Where one of its results appears, it appears as a prior result with its
date attached, and never as support for a claim in the chain.

## 6.3 The sandbox

§5.6 chose R2 — a real, stripped Home Assistant inside the sandbox — and §5.6.3 established
that one fits on the C4 device. This section builds it, and reports what building it changed.

### 6.3.1 The instance is constructed, not booted

Home Assistant's own entry point cannot be used. `homeassistant/bootstrap.py` imports
`.components` at module level, pulling in the frontend and the recorder's sensor support, which
is precisely the weight a sandbox exists to avoid. §5.6.3 recorded this as a property of the
design rather than a detail of its implementation, and it holds: the sandbox constructs a
`HomeAssistant` object directly and wires the registries the helper layer reaches for.

*Strength of claim: measured.* An ordinary integration — a config entry, a
`DataUpdateCoordinator`, a `SensorEntity`, `async_add_entities` — reaches `LOADED` and
publishes its entity against such an instance, on the Pi 5, with no HTTP server, no recorder,
no frontend and no authentication.

### 6.3.2 The first measurement Chapter 5 asked for

§5.6.5 identified one optimisation and deferred it here: **60 MB of a sandbox's 176 MB is the
platform's own `homeassistant` base component**, and §5.8.1's third qualification says that if
it can be dropped, the sandbox budget roughly doubles. Neither section knew whether it can be.

**The method is not a subtraction, and that is the whole of it.** The obvious experiment builds
one sandbox each way and subtracts the two resident-memory figures. §5.6.3 established why that
is wrong for the *cost* of a sandbox — most of one is interpreter and library pages the kernel
maps into every sandbox from the same physical memory — and the identical arithmetic invalidates
it for a *saving*. A megabyte removed from one process's resident set is a megabyte removed from
the budget only if it was private to that process. So the saving was measured the way §5.6.3
measured the cost: across six live sandboxes per arm, by proportional set size.

| | RSS, one sandbox | **PSS per sandbox, six live** | Sandboxes in 60% of 4 GB |
|---|---|---|---|
| With the base component | 161.3 MB | **136.6 MB** | **17** |
| Without it | 109.4 MB | **90.0 MB** | **26** |
| Difference | 51.9 MB | **46.6 MB** | **+9 — a factor of 1.53** |

*Full write-up, both controls and raw output: `experiments/base_component/`.*

**§5.6.5's prediction was wrong, in an instructive way.** "Roughly doubles" was obtained by
taking 60 MB off the single-sandbox figure — the exact arithmetic §5.6.3 spends a paragraph
warning against, performed two sections later in the same chapter. Measured marginally the
saving is 46.6 MB, and the budget improves by half rather than doubling. The correction is
recorded here rather than applied silently to Chapter 5, because it is the clearest available
demonstration that the measurement discipline is doing work: the warning was written, published,
and then not applied by its own author, and what caught it was running the measurement instead
of quoting its consequence.

Two controls support the figures rather than being asserted alongside them:

- **Order.** Both arms were run in both orders. PSS per sandbox was identical to 0.1 MB across
  four arm-runs; the whole-machine `MemAvailable` figure moved 4–5 MB, always downward for
  whichever arm ran second, because that arm reads files the first left in the page cache.
  §5.6.3 treated `MemAvailable` as ground truth, which it is for one measurement on a quiet
  machine and is not for a comparison of two arms. PSS is therefore what is quoted.
- **Replication.** The with-base arm's PSS per sandbox is 136.6 MB against §5.6.3's 136.5 MB,
  taken a day earlier by a different script. Agreement to 0.1 MB is the strongest available
  evidence that the two experiments measure the same system, and therefore that the difference
  between the arms is the only difference.

**What is lost.** Exactly one component, and its thirteen services: `check_config`,
`reload_all`, `reload_config_entry`, `reload_core_config`, `reload_custom_templates`,
`restart`, `save_persistent_states`, `set_location`, `stop`, `toggle`, `turn_off`, `turn_on`
and `update_entity`. Nothing else differs — the same entities are published and both config
entries reach `LOADED`. Without the base component the sandbox's service registry is **empty**,
which makes §5.6.2's claim that it "starts empty" literally true rather than approximately so.

Three observations follow, and the first decides:

1. **These services are cross-integration by nature, and the design already routes such effects
   through the mediator** (§5.11.3). `homeassistant.turn_on` takes an arbitrary entity as its
   target; inside a sandbox whose state machine holds only that integration's own declared
   entities, a local copy of it can reach nothing the integration does not already have. It is
   a dead end rather than a capability, and removing it converts a silent no-op into an explicit
   `ServiceNotFound` — the more honest failure of the two.
2. **The security gain is small and should not be inflated.** Nothing crosses a trust boundary
   either way, because the registry is local to the sandbox. What changes is that a claim in
   §5.6.2 becomes checkable.
3. **The compatibility cost is bounded but not zero.** From the corpus measured in
   `notes/ch5_evidence_api_surface.md`: **8 of 144** community integrations (5.6%) call a
   `homeassistant.*` service with a literal domain, and **13 of 144** (9.0%) import the
   component. Both are static lower bounds. Those calls do not vanish — they become requests
   the mediator sees, which is where a cross-integration effect belongs.

**Decision: the sandbox does not set up the base component.** The consequence for §5.8.1 is a
budget of **26** sandboxes rather than 17, against a mean of 4.02 community integrations per
HACS-using installation — headroom of roughly six-fold rather than four. §5.8.1's third
qualification is discharged, though not in the terms it anticipated: it expected to "largely
dissolve", and instead it has merely shrunk. The other two qualifications are untouched. The
mean is still not the distribution, and the budget is still an idle-state figure taken without
a mediator attached.

### 6.3.3 A defect the measurement found, which is not what it was looking for

The experiment carried a second probe whose only purpose was to fail: a `RestoreSensor`
publishing a generation counter, which increments across a restart only if the platform's state
restoration actually ran. It was written on the suspicion that the base component might be
carrying restoration, since it is the base component that registers
`homeassistant.save_persistent_states`.

It failed — **in both arms**, including the one that keeps the base component. A result
identical on both sides of the variable is not a finding about the variable; it is a broken
test, and treating it as one is what made it useful.

The cause is in §5.6.3's own recipe. The minimal instance reaches the running state by setting
the flag directly:

```python
hass.set_state(CoreState.running)
```

That is not the same thing as starting: it never fires `EVENT_HOMEASSISTANT_START`. Reading
`homeassistant/helpers/start.py` rather than inferring from the symptom, `async_at_start` —
the platform's standard way of deferring work until the instance is up — branches on
`hass.is_running`, so the omission does not drop every deferred callback. It **splits** them:

| Registered | What happens | Where Home Assistant runs it |
|---|---|---|
| **Before** the flag is set | Waits for an event that never arrives — **lost permanently** | At start |
| **After** the flag is set | Runs **immediately**, part-way through assembling the instance | At start, after every component is set up |

The helper layer wires itself during construction and so lands in the first row.
`RestoreStateData` registers there, which is why **no state is ever dumped and every
`RestoreEntity` in the sandbox silently restores nothing**. Integrations, set up later, land in
the second row: not lost, but run in the wrong place. In Home Assistant 2026.8.3 the helper is
used by one helper module and **28 shipped components** — `mqtt`, `template`, `group`, `filter`,
`utility_meter`, `history_stats` and `zwave_js` among them — so a callback written on the
assumption that its peers already exist is a plausible way for the second row to matter too.

**The fix is to start the instance rather than to declare it started, and to start it where
Home Assistant does — last, after every component is set up.** Adding the start *before* the
integrations are loaded also repairs restoration and was the first fix tried; it is the wrong
one, because it leaves every integration in the second row. The order is part of the fix.

*Strength of claim: measured.* With the corrected order the round trip passes in both arms —
generation 1 restored, 2 published — and the arms remain identical in every other respect.

**Why this matters more than restoration does.** The defect produced no exception, no warning
and no log line. It produced a sensor that quietly reported the wrong number. Had it survived
into Chapter 7, the compatibility evaluation would have measured the resulting breakage and
attributed it to confinement — reporting the recipe's cost as the design's. Two consequences
are therefore carried forward:

- **The supervisor calls `hass.async_start()` last**, and the sandbox is not ready until it
  returns. Nothing is set up afterwards.
- **Any compatibility failure is checked against the minimal instance before it is charged to
  the design.** This is now a procedure in Chapter 7, not a good intention.

It is also the first concrete instance of the hazard §5.15.4 names in the abstract. The
supervisor is the component nothing checks; here the part of it that constructs the sandbox
produced a silently wrong instance, and no layer of the design noticed, because no layer of the
design is looking at it.

### 6.3.4 The sandbox's construction order, as it now stands

Four ordering constraints have accumulated, from four unrelated mechanisms:

| Constraint | Source | Reason |
|---|---|---|
| The socket pair exists **before the sandbox does** | §5.11.2 | Identity is the socket, so it cannot be established afterwards |
| Identity is computed **before any integration code runs** | §5.12.2 | A hash taken after execution is a hash of whatever execution left behind |
| `async_start()` is called **last**, after every component is set up | §6.3.3 | Deferred work is lost before the flag and misplaced after it |
| The supervisor runs **inside its user's delegated cgroup subtree** | §6.4.1 | Otherwise no placement mechanism is permitted at all — including placement at creation |

The first two are one rule — **construction precedes execution, or the property is not
available at all** — which §5.7.4 named. The third is the same rule turned inward: the sandbox
must be fully assembled before it is started. Both halves are violated by the obvious
implementation, which is why the rule is worth stating rather than merely following.

The fourth row is a different kind of constraint, and §6.4.1 is where it displaces one that
§5.7.4 put here. §5.7.4 required the sandbox to join its cgroup *at creation*, on the reasoning
that migration was refused and creation would not be. Measured, creation is refused too, and
the constraint that actually binds is on the supervisor's own position rather than on the order
of its operations.

## 6.4 The supervisor

The supervisor is the process that builds a sandbox: it creates the cgroup and the namespaces,
installs the seccomp filter, creates the socket that carries the sandbox's identity, computes
that identity, and starts the confined process. §5.15.4 named it the component nothing checks,
and §6.3.3 has already produced one instance of what that means in practice.

This section is answerable for four things: where the supervisor must run, how it confines,
what it does in what order, and what it refuses to do. The first is settled below, and it
settles it by correcting Chapter 5.

### 6.4.1 Where the supervisor must run, which is not where Chapter 5 thought

§5.7.4 recorded a real finding — an unprivileged process could not create a cgroup and then
move a running process into it, because migration requires write access to the **common
ancestor** of source and destination, and that ancestor was root-owned — and drew a design rule
from it: *the sandbox must be placed in its cgroup at creation, not confined after the fact*.

The rule contains an assumption the failed command could not test. It presumes that placement
at creation is permitted where migration is not, and the mechanism that would do it —
`clone3(CLONE_INTO_CGROUP)` — was never tried. §6.4 has to implement whichever is true, and
the two lead to very different supervisors: one needs `clone3` and therefore a C component, the
other needs only to be started in the right place. So it was measured
(`experiments/cgroup_placement/`), from two positions, as an ordinary user.

| Operation | From an ssh session | From inside the delegated subtree |
|---|---|---|
| Common ancestor with the destination | `user-1000.slice` — **root-owned** | `…/app.slice` — **user-owned** |
| `mkdir` the sandbox's cgroup | **OK** | **OK** |
| Migrate a running child into it | `EACCES` | **OK** |
| Have the child migrate itself | `EACCES` | **OK** |
| `clone3(CLONE_INTO_CGROUP)` | `EACCES` | **OK** |
| 192 MB against a 64 MB cap | not testable | **killed — enforced** |

**Placement at creation is governed by the same rule as migration.** `clone3` fails with the
same `EACCES`, in the same position, because the kernel checks the common ancestor either way;
creating the process there is not a way around a rule about moving it there, since it is not a
rule about moving. §5.7.4's finding stands and the rule drawn from it does not.

What binds is the supervisor's own position:

> **The supervisor must run inside the cgroup subtree that its user's manager delegates to it.**
> On a systemd host that means being started as a systemd *user unit*. An interactive login or
> an ssh session lands in `user-<uid>.slice/session-N.scope`, outside that subtree, and from
> there no placement mechanism works at all.

**The trap worth naming, because it is what made the original reading plausible.** `mkdir`
succeeds from the wrong position. The supervisor can create the cgroup, write `memory.max` into
it, read every file it expects to find, and fail only at the one step that matters. A framework
that checked for the cgroup's existence and concluded it was enforcing would be reporting a
control it does not have — §1.6's complaint about the status quo, wearing a security label.
§5.7.4 already distinguished the controller being *present* from the limit being *enforced*;
this adds a third distinction, between enforcement and **permission to enforce**.

Four consequences for the rest of §6.4:

1. **The supervisor ships as a systemd user unit**, and that is a security property rather than
   packaging convenience. The unprivileged design §5.7.4 chose depends on it, and the only
   alternative is privilege.
2. **`clone3` is not needed, so the supervisor stays in Python.** From the right position,
   migration works and `clone3` buys nothing that migration does not already give. A C
   component would have been a real cost against maintainability by one person, and it is worth
   recording that the measurement removed it rather than the preference removing the
   measurement.
3. **The child places itself, immediately before `exec`.** Ordinary migration leaves a window
   between fork and the parent's write in which the sandbox runs uncapped. Having the child
   write its own pid closes that window without `clone3`, and self-migration was measured to
   work from the right position. This keeps what was *right* about §5.7.4's rule — nothing
   substantial executes before the limit applies — while dropping the premise that was wrong.
4. **The supervisor tests placement at startup and refuses to start if it fails**, with the
   position it is in named in the message. This is N3 applied to the same case §5.7.4 applied
   it to, and the same argument holds a second time: a framework that ran anyway would leave
   T16 uncontrolled while implying protection.

*Strength of claim: measured.* All four operations, both positions, on the C4 device, as
uid 1000. What has not been built is the supervisor itself; this establishes which of two
designs is available to it.

### 6.4.2 What the supervisor checks before it confines anything

§5.7.4 required the framework to refuse to start, with a stated reason, when the memory
controller is unavailable — N3 applied to one case, on the ground that starting anyway would
leave T16 uncontrolled while implying protection. §6.4.1 found a second case with the same
shape. The supervisor therefore runs a preflight, and the interesting property of it is not the
list of checks but that **every check exercises the operation it is checking.**

That is a reaction to three findings in sequence, each invisible to the check before it:

| Found | What the previous check could not see |
|---|---|
| The `memory` controller is absent by default on Raspberry Pi OS (§5.7.4) | Listing the design's primitives says nothing about this host |
| A controller being *listed* is not a limit being *enforced* (§5.7.4, re-probed) | Reading `cgroup.controllers` says nothing about behaviour |
| A limit being enforceable is not this supervisor being *permitted* to enforce it (§6.4.1) | `mkdir`, `memory.max` and every file read succeed from the position where placement does not |

The third is what makes the pattern worth stating rather than merely following. A framework
that checked what it could see would have reported itself ready in a position where it could
confine nothing whatever — and it would have been reporting a control it did not have, which is
§1.6's complaint about the status quo under a security label.

The seven checks, and what each does rather than reads:

| Check | What it actually does |
|---|---|
| cgroup v2 hierarchy | Requires a `0::` line in `/proc/self/cgroup`; v1 and hybrid hosts are refused |
| cgroup subtree delegated | Locates the delegated root by **ownership of `cgroup.subtree_control`**, not by assuming a path |
| supervisor inside it | Compares the supervisor's own cgroup against that root (§6.4.1) |
| memory controller | Requires `memory` in the *parent* cgroup's controllers, where a sandbox would be created |
| placement permitted | Creates a cgroup, starts a child that places itself, and **reads back the cgroup the child reports from inside itself** |
| memory limit enforced | Caps a child at 64 MB, asks it for 192 MB, and requires both a non-zero exit **and** `oom_kill` on the cgroup's own counter |
| unprivileged namespaces | Forks, unshares all seven, and writes the identity maps — the same calls the supervisor will make, not `unshare(1)` |

*Strength of claim: measured.* On the C4 device, as uid 1000: seven of seven pass inside a
systemd user scope, and from an ssh session the run stops at `supervisor inside it` and prints
the position it is in together with what to do about it. The refusal is the check working.

**The last row is not a formality.** The earlier probe used `unshare(1)`, and a check that
exercises a different mechanism from the one the supervisor uses is not a check — it was this
row that caught the implementation bug in §6.4.3.

Three constraints on the supervisor came out of writing this, none of them visible from the
design:

1. **The supervisor must be single-threaded.** The sandbox places itself between `fork` and
   `exec`, which in Python means `preexec_fn`, which is unsafe in a process that has threads.
   The alternative — migrating the sandbox from the parent afterwards — reopens the window in
   which the sandbox runs uncapped, so the constraint is accepted rather than worked around.
2. **Swap must be capped along with memory.** `memory.max` alone bounds *resident* memory; a
   sandbox that exceeds it is slowly swapped rather than stopped, which satisfies the file and
   not S9.
3. **`oom_kill` is read from the cgroup, not inferred from the exit status.** A process can die
   for many reasons and only one of them is the one under test.

### 6.4.3 An ordering constraint found by the check that was meant to be a formality

The namespace check failed on its first run, reporting `Operation not permitted` — on a host
where `experiments/host_isolation_probe/` had already shown all seven namespaces available to
an ordinary user. Two explanations were available: the host had changed, or the code was wrong.

Testing each flag separately settled it in a minute. `unshare` succeeded for all seven,
individually and together; the failure was in the next call, writing the user namespace's
identity map, and it was a defect in this framework's own code.

The kernel lets an unprivileged process write only a single-line map, and only one whose outer
id is the id the process already had — it compares the value written against the credentials
the `/proc` file was opened with. The function read that id itself, with `os.getuid()`, *after*
the `unshare`. By then the correct answer is `nobody`, so it faithfully wrote `0 65534 1` and
was refused.

**The identity has to be captured before the namespace that hides it exists.** That is the
third instance of the ordering §6.3.4 tabulates, arriving from a fourth mechanism: the socket
pair before the sandbox, the identity hash before any integration code, and now the supervisor's
own credentials before the namespace. The function's signature now requires them as arguments,
so that the mistake cannot be made silently a second time.

Two smaller points are worth keeping, because both are about diagnosis rather than about
namespaces:

- **The probe now reports which stage failed.** `Operation not permitted` from a check that
  does four things is not a diagnosis, and it cost twenty minutes to find out which of the four
  it was.
- **The disagreement was the signal.** A check that contradicts an earlier measurement is
  usually the check being wrong, and treating it as a host finding would have produced a
  limitation in Chapter 7 about namespaces on Raspberry Pi OS that is simply untrue. This is
  the same discipline that turned §6.3.3's failure in both arms into a finding rather than a
  wasted afternoon.

### 6.4.4 The sandbox's filesystem

§5.6.2's central claim is that under R2 default denial is *structural* rather than procedural:
an integration reading `secrets.yaml` is not refused by a check, because the file is not in its
mount namespace and there is nothing there to refuse. §5.10.2 says the same of everything the
manifest does not declare. This is where those sentences become a filesystem.

The construction is conventional — private mount propagation, a fresh tmpfs root, bind mounts
for what is allowed, then `pivot_root` — and four decisions in it are not.

**`pivot_root`, not `chroot`.** A process inside a user namespace holds `CAP_SYS_CHROOT` over
that namespace, and a `chroot` is escapable by anything holding it. Using `chroot` here would
produce a boundary indistinguishable from the inside and not one in fact — which is precisely
the failure §6.4.2's preflight exists to catch in a different form.

**The sandbox is not "its own directory and nothing else", and the report should not imply it
is.** R2 runs a real Python against a real Home Assistant, and neither can execute out of
nothing, so the sandbox also holds a read-only copy of the interpreter and the libraries
beneath it. §5.10.2's phrasing is about *declared* resources; the runtime is ambient in the
same sense the sandbox's own data dictionary is. Stating this is better than letting a reader
infer an emptier sandbox than exists, and it is what the self-test's `/` listing shows:
`bin dev lib proc sandbox sbin tmp usr`.

**The integration's own two directories are at fixed paths inside**, `/sandbox/component` and
`/sandbox/data`, whatever they were called outside. The sandbox runner then needs no
configuration, and an integration cannot learn where on the host it was installed.

**The `pivot_root` syscall number is per-architecture**, and glibc does not export the call
everywhere, so it is issued directly with a small table of numbers. This is a portability
limit rather than an incidental detail: isolation code of this kind couples to the machine, and
a framework claiming to run "on Linux" should say which Linux it was run on. Chapter 7 reports
the architectures tested rather than generalising from one.

Two consequences fell out of the process structure rather than the filesystem:

- **`unshare(CLONE_NEWPID)` does not move the caller into the new PID namespace**; it arranges
  for its *children* to be born there. So the process that unshares can never be PID 1, can
  never mount a `/proc` showing only the sandbox, and keeps an ordinary view of every process
  on the machine. A second fork is what makes the PID namespace real, and the process that
  unshared then exits immediately rather than idling — an idle Python interpreter per sandbox
  would be a measurable share of §6.3.2's budget, spent on waiting.
- **The supervisor declares itself a child subreaper**, so that the sandbox stays waitable once
  its parent has gone. The alternative is keeping that parent alive, which is the cost just
  avoided.

The sandbox's specification travels on stdin rather than on `argv`, because a sandbox's
declared paths are readable in `/proc/<pid>/cmdline` by anything running as the same user.

### 6.4.5 What the sandbox can see, and the failure mode this design has

The claims above are testable, so `confine/selftest.py` tests them. It builds a configuration
directory containing exactly what an attacker would want — a secrets file, the config-entry
store, and a second integration's source — grants one integration one unrelated file, and asks
it to report what it can see.

| | |
|---|---|
| uid inside / outside | **0** / 1000 |
| processes visible | **1** — itself |
| network interfaces | **`lo`** only |
| its own directory | present, **read-only** |
| its own data directory | present, writable |
| the one declared file | present, read-only |
| `secrets.yaml` | **absent** |
| the `.storage` directory | **absent** |
| the other integration | **absent** |
| the user's home directory | **absent** |
| the configuration root | present — and holding only the granted path |

*Strength of claim: measured.* On the C4 device, as uid 1000, from inside a systemd user scope.

**The configuration root is present, and that row is worth reading carefully.** A bind mount
creates the directories above its target, so granting one path inside the configuration
directory necessarily makes that directory exist. It is a skeleton: it holds the granted path
and nothing else, and §5.10.5's claim — that the configuration root is not *grantable* — is
untouched. What does leak is the host path itself, which the sandbox would not otherwise learn.
That is a small and real disclosure, and it is recorded here rather than in Chapter 7's
limitations because the design chose the behaviour that causes it: declared paths appear at
their host locations so that an integration's own absolute paths keep working.

**Three defects were found writing this, and all three are the same defect.**

| What happened | How it presented |
|---|---|
| The child wrote its status to a hard-coded descriptor number, while the supervisor passed the real one in the environment — and the failed write was swallowed | "the sandbox never reported a pid", with no other information |
| The private `/tmp` was mounted *after* the declared paths, so a declared path under `/tmp` was covered by it | The file was simply not there |
| The self-test expected the configuration root to be absent | A failing check, against correct code |

Each produced an **absence** where something should have been, and that is the property worth
extracting, because it is a cost of §5.6.2's argument that Chapter 5 did not identify:

> **This design uses absence to mean "not granted". Any bug that makes something absent is
> therefore indistinguishable, from inside the sandbox, from the framework working correctly.**
> Structural denial is stronger than a check against an adversary — there is no code path to
> forget — and weaker against implementer error, because a check that is missing raises nothing
> and a check that is wrong denies silently.

Two responses, both in the code rather than in the prose:

1. **Declared paths are bound last**, so that a later mount cannot cover a grant.
2. **Ordering is not trusted to be enough.** Before the sandbox is allowed to run, every
   declared path is verified to exist in the new root, and construction fails loudly if one
   does not. This is §6.4.2's preflight argument at the scale of a single sandbox, and it is
   what turns a silently unhonoured grant into a refusal that names the path.

This also settles how Chapter 7 must read a compatibility failure. An integration that cannot
find a file it declared is not evidence that confinement broke it until the grant has been
shown to have arrived — the same procedure §6.3.3 established for the minimal instance, now
with a second reason to follow it.

### 6.4.6 The seccomp filter, and a narrowing that should not be glossed

§5.7.3 gives seccomp one job: it "denies syscalls outside the set an integration needs". Read
literally that is an allow-list, and an allow-list for a real CPython running a real Home
Assistant is several hundred entries that change with the interpreter's version and would have
to be re-derived at every upgrade. **What is implemented is a deny-list, and that is a genuine
narrowing of what Chapter 5 specified rather than a different way of achieving it.**

The argument for it being sufficient *here* is specific, and it does not generalise:

> By the time the filter is installed, the other six namespaces have already removed most of
> what a syscall could reach. There is no network to open, no other process to signal, no host
> filesystem to name. What is left for seccomp is the set of calls dangerous **in themselves**,
> whatever namespace they are made from — the ones that attack the kernel, or that rearrange or
> leave the boundary the other six mechanisms have just built.

That set is small and enumerable, which is why the deny-list is defensible in this position and
would not be in a design where seccomp was the only boundary. Twenty-nine calls, in four
groups: leaving or rearranging the sandbox (`mount`, `pivot_root`, `chroot`, `unshare`, `setns`
and the newer mount API); reaching into another process (`ptrace`, `process_vm_readv/writev`);
attacking or reconfiguring the kernel (`bpf`, `perf_event_open`, the module calls, `kexec_load`,
`reboot`, `swapon/swapoff`, `acct`, `syslog`); and the kernel keyring together with the two
calls that bypass path resolution entirely (`name_to_handle_at`, `open_by_handle_at`).

**The residual risk this accepts** is the one a deny-list always carries: a syscall that is not
on the list is allowed, so a kernel vulnerability in anything else is unmitigated by this layer.
§5.13 already counts seccomp as one layer of three rather than as a boundary, and §5.7.5's
residual risk on kernel surface stands unchanged. What has changed is that the residual is now
concrete enough to state as a number, and Chapter 7 reports it that way.

Three implementation decisions are worth recording.

**The architecture is checked before the syscall number is.** A filter that compares numbers
without first confirming the calling ABI is the classic way a seccomp filter is bypassed: the
same number means different things in different tables. A call from an unexpected architecture
is killed rather than filtered.

**Denial is `EPERM`, not death.** A killed sandbox is indistinguishable from a crashed one, and
§6.4.5 has already established what this design pays for making its failures look like
absences. An errno leaves the sandbox alive to be observed, keeps the failure attributable to
the call that caused it, and leaves something for the audit record of §5.12 to say.

**The syscall numbers are hard-coded per architecture, so they are not trusted.** There is no
portable way to ask Python for them, and a wrong number denies the wrong call silently — the
§6.4.5 failure mode again. So the filter is verified by behaviour: a throwaway child installs it
and *makes* the calls. `chroot` and `unshare` are the useful probes, because both **succeed**
inside a user namespace; seeing them refused is evidence of the filter rather than of the
namespace around it.

*Strength of claim: measured.* On aarch64 (the C4 device) and on x86_64. The preflight's eighth
check reports `chroot denied, keyctl denied, ptrace denied, unshare denied`, and the self-test
makes the same three calls **from inside a real sandbox**, after the filter was installed
immediately before that interpreter was executed:

```
  ok    chroot(2)                  Operation not permitted
  ok    ptrace(2)                  Operation not permitted
  ok    unshare(2)                 Operation not permitted
```

Ordering, one more time: the filter is installed **last**, after the mounts and immediately
before `exec`. Installed any earlier it would confine the construction of the sandbox rather
than the sandbox — `mount` and `pivot_root` are both on its own deny-list.

## 6.5 The channel

§5.11.2 makes the design's sharpest claim about identity: it is *a property of the channel, not
a claim in the message*. The supervisor creates one connected Unix domain socket before the
sandbox exists, keeps one end for the mediator and passes the other into the child; the mediator
knows who is speaking because it created that socket for that sandbox. There is no field to
forge and no authentication step to bypass.

That is a testable claim, and §6.5.2 tests it the only way worth testing it — by having both
sandboxes lie.

### 6.5.1 What is built, and what a hostile far end forces

The wire format is §5.11.3's: a four-byte big-endian length followed by a JSON object. The
sandbox's side of it is implemented in the self-test *without importing anything from this
framework*, which is not a stylistic choice — `confine` is not in the sandbox's mount namespace
and cannot be. That the far end needs no library is what keeps the sandbox's half of the
protocol auditable.

**The sandbox is the untrusted end of this socket**, and two decisions follow that would be
unnecessary between cooperating processes:

- **A frame's declared length is checked against a cap before anything is allocated for it.**
  The number came from the sandbox. Reading it and then allocating is how a one-line change to
  an integration becomes a denial of service against the mediator.
- **A malformed frame costs that sandbox its channel and nothing else.** One sandbox must not
  be able to stop the mediator by sending rubbish, and §5.15.4 has already named the supervisor
  as the component nothing checks.

The mediator implements steps 1, 3 and 4 of §5.11.3's five, and its **default is the whole of
S6**: a mediator holding no manifest denies everything. That was built before any permit path
rather than after it, because default-deny that arrives second is default-deny that has already
been forgotten once.

### 6.5.2 Both sandboxes claim to be the same integration

Two sandboxes are started, `demo_a` and `demo_b`. Both send
`{"integration": "demo_a", …}`. One of them is lying — and the integration it claims to be is
one that **holds a grant**, so the lie has something to win. `demo_a`'s manifest permits reading
one sensor; `demo_b` declares nothing. The mediator's audit record:

| True identity | Claimed | Request | Verdict | Clause |
|---|---|---|---|---|
| `demo_a` | `demo_a` | `entity.read` | **permit** | `/permissions/entities/read/0` |
| `demo_a` | `demo_a` | `service.call` | deny | `/permissions/services/call` |
| `demo_b` | **`demo_a`** | `entity.read` | **deny** | `/permissions/entities/read` |
| `demo_b` | **`demo_a`** | `service.call` | deny | `/permissions/services/call` |

*Strength of claim: measured.* On the C4 device, two concurrent sandboxes, 4,004 requests.

The third row is the one that matters. `demo_b` asked for exactly what `demo_a` was permitted,
while claiming to be `demo_a`, and was refused — because the claim is recorded as a *claim*, in
its own field, beside an identity that came from the socket. There was nothing in the protocol
to check and therefore nothing to get wrong.

This is the demonstration §5.11.2's argument needs, and it is the S4 mechanism in miniature:
attribution is a property of the topology rather than a deduction from it, which is precisely
what §2.4.2's prior work cannot do. A demonstration in which everything is denied would not have
shown it; the permit path has to exist for the refusal to mean anything.

### 6.5.3 What the channel costs when it is real

§5.11.4 measured a **floor** of 30.0 µs median, p99 33.9 µs, and said so — it excluded the
manifest check and the audit write, and it did not cross a sandbox boundary. This measurement
does all three, with two sandboxes contending for one single-threaded mediator:

| | §5.11.4 floor | Measured here | Change |
|---|---|---|---|
| median | 30.0 µs | **35.6 µs** | +19% |
| p99 | 33.9 µs | **62.7 µs** | **+85%** |

**The median held and the tail did not, and the asymmetry is the finding.** A cost that lands
almost entirely in the tail is the signature of queueing, not of work: two sandboxes share one
single-threaded mediator, so a request can wait behind another sandbox's rather than behind
anything of its own. That the median moved only 19% while p99 nearly doubled says the added
per-request work — the policy call and the audit append — is small, and that the contention is
not.

N1 is unaffected either way. A polling integration reading ten entities every thirty seconds
now spends 0.36 ms per cycle in mediation rather than 0.30 ms, against a thirty-second period.

**It is a real obligation for Chapter 7, though, and a new one.** This was two sandboxes;
§6.3.2 puts the device's budget at twenty-six. A tail that doubles at two clients is not
evidence about twenty-six, and the shape of the curve between them is exactly what a
single-threaded mediator's design deserves to be judged on. Chapter 7 measures latency at
realistic sandbox counts.

**How much concurrency could help is bounded, and the bound is in Chapter 5.** §5.12.4 makes
the audit log a hash chain, in which "modifying, deleting **or reordering** any record breaks
every link after it" — and a chain requires a total order. Step 4 of §5.11.3's five must
therefore serialise however concurrent the rest becomes. Steps 1, 2, 3 and 5 can proceed in
parallel; the record cannot.

That reframes the measurement above rather than excusing it. **The mediator does not yet
implement step 5**, so these figures are almost entirely the part that has to stay serial, and
adding the platform call will make the tail worse before any concurrency makes it better. The
fix, when it is needed, is an asynchronous mediator rather than a threaded one — the work at
step 5 is I/O to the platform, so the constraint that the supervisor be single-threaded at the
moment it forks (§6.4.2) need not be given up to get it.

## 6.6 The manifest, and the permit path

§5.10 specifies what a manifest can say and §5.9.4 specifies where one comes from. Both are
security properties rather than presentational ones, so the implementation is written to two
rules that are worth stating before anything else.

**Reject at parse time, not at use time.** §5.10.5 already required this of one thing — a
declared path enclosing the configuration root "is rejected when the manifest is parsed, not
when it is first used" — and the same discipline is applied to every constraint: a wildcard in
`services.call`, a pattern without a domain, an unknown capability, a wrong schema version. A
manifest that reaches the mediator has already been found well-formed, so **the decision path
contains no error cases at all**. That matters more than it sounds: the decision path runs
thousands of times a second and an error branch there is a branch that can be got wrong under
load.

**An unknown key is a rejection, not something to ignore.** Ignoring an unrecognised capability
means a manifest written against a later schema is silently under-enforced — the exact failure
this design exists to remove, and §6.4.5's absence problem in yet another costume. It is also
what the platform's own tooling does: `hassfest`'s voluptuous schemas default to `PREVENT_EXTRA`
(§5.10.1).

### 6.6.1 What is refused when a manifest is read

| Refused | The rule |
|---|---|
| `lock.*` in `services.call` | §5.10.4. **Every entry names one `domain.service`** — the rule S5 exists to produce |
| `*` as an entity pattern | §5.10.4. A domain is always required, so `*` alone is never a grant |
| `*.temperature` | The same rule, wildcarding the domain rather than the object |
| `*` in `events.subscribe` | §5.10.3. The bus carries every state change in the home |
| An unknown capability, or an unknown member of a known one | §5.10.1 |
| `schema_version` other than 1 | §5.10.1 |
| A `files` grant naming the configuration root, `.storage/`, or `secrets.yaml` **reached through `..`** | §5.10.5, resolve-then-pin |

The last row is the resolve-then-pin principle doing visible work: `…/shared/../secrets.yaml` is
resolved before it is compared, so the traversal cannot name what the declaration could not.

### 6.6.2 S5, which is the one rule the schema exists for

A manifest permitting `lock.lock`:

```json
{"schema_version": 1, "services": {"call": ["lock.lock"]}}
```

permits `lock.lock` at `/permissions/services/call/0`, and refuses `lock.unlock` with
*"'lock.unlock' matches no clause at /permissions/services/call"*.

*Strength of claim: measured*, though of the schema and not yet of the artifact end to end.
§5.8.2 requires a `lock`-domain service path through the running system to verify S5 against its
own stated criterion, and that is still owed — this establishes that the manifest layer cannot
express the grant that would defeat it. Because validation rejects wildcards outright, the
comparison in the decision path is exact string equality: **S5 is a property of the comparison
itself rather than of a rule applied to it.**

### 6.6.3 Every decision names a clause

F3 requires every enforcement decision to be attributable to a manifest clause, and §5.10.8
makes that mechanical by giving each clause a JSON pointer. All three of its rows are
implemented, and the pointer is constructed *by the branch that decided* rather than looked up
afterwards — so a decision that cannot name a clause is not merely a bug that Chapter 7 could
detect, it is a state this module cannot reach.

| Decision | Pointer recorded |
|---|---|
| Permitted | the clause that permitted it — `/permissions/entities/read/0` |
| Denied by absence | the capability that held no matching clause — `/permissions/services/call` |
| Denied by rule | the constraint that rejected it, at parse time, with the path that triggered it |

### 6.6.4 What the decision costs

The channel measurement of §6.5.3 was repeated with the real manifest evaluation in place of
the placeholder that denied everything:

| | deny-everything (§6.5.3) | real manifest evaluation |
|---|---|---|
| median | 35.6 µs | **38.0 µs** |
| p99 | 62.7 µs | 64.6 µs |

**Step 3 costs about 2.4 µs**, and the tail is unchanged within noise. That is the useful shape:
the decision itself is nearly free, and §6.5.3's conclusion that the cost lives in queueing
rather than in per-request work survives contact with a real policy.

### 6.6.5 A test that passed for the wrong reason

The three `files` rejections above initially passed — and proved nothing. `files` had been
omitted from the table of known capability members, so those manifests were being refused as
*"unknown member 'read'"* and never reached §5.10.5's path check at all. The suite was green,
the rule was untested, and the output said `rejected` in both cases.

It was caught by reading the rejection *reasons* rather than the verdicts, which is the only
reason it was caught at all. Two things follow, and the second is the one worth keeping:

- The self-test prints the rejection *reason* beside every verdict, not just the verdict. That
  is what made the defect visible, and it is why the practice is worth keeping rather than
  trimming as noise.
- **This is the same failure as §6.4.5's, one level up.** There, a bug produced an absence and
  absence is what the design uses to mean "denied". Here, a bug produced a rejection and
  rejection is what the test was looking for. A default-deny system is one in which almost every
  mistake produces the safe answer, and safe answers are exactly what tests do not investigate.
  Chapter 7's negative cases have to assert on *why* something was refused, not that it was.

### 6.6.6 A contradiction inside Chapter 5, found by implementing it

Building the validator meant implementing §5.10.5's constraints on the `files` clause. That
clause turns out to be one Chapter 5 both specifies and denies the existence of.

| Section | Says |
|---|---|
| §5.10.3 | `files` is one of the eight declarable capabilities — "Paths outside its own directory", used by 33.3% of community integrations, "individual paths with `read`/`write`" |
| §5.10.5 | Two full paragraphs constraining it: the configuration root and `.storage/` are not grantable, and paths are resolved before comparison |
| **§5.14.4** | "**Nothing about the filesystem is declared** (§5.10.2)" |

**§5.14.4 is the one that is wrong**, and the mistake is a specific misreading rather than a
slip. §5.10.2 makes the integration's *own* directory ambient — it is in the sandbox by
construction, so no clause is needed for it. §5.14.4 read that as the filesystem being ambient,
which is a different and much larger claim.

The consequence was not confined to a sentence. §5.14.4 placed an obligation on Chapter 7 —
never to repeat §4.10's phrase "filesystem isolation *to declared resources*", on the ground
that the phrase misdescribed the artifact. It does not: filesystem access *is* bounded to
declared resources, §4.10's wording is accurate, and **the obligation is withdrawn.**

What settles it is not a re-reading but a result. §6.4.5's self-test shows a declared file
present and read-only inside a running sandbox, alongside a `secrets.yaml` that is absent.
Nothing about the filesystem being undeclared could have produced that row.

**Why this is worth a subsection.** §5.14 was the traceability check — the section whose whole
purpose was to catch exactly this class of error, and which did catch three others. It found the
T13 gap that §6.7 discharges, correctly. On T14 it produced a *confident* finding, complete with
an obligation for a later chapter, from a misreading of the section it cited. That is the third
correction Chapter 6 has made to Chapter 5 (§6.3.2, §6.4.1, and this), and all three share a
shape worth naming: **each was an inference stated in the register of a result.** The
measurements have all replicated; it is the sentences next to them that need auditing.

## 6.7 Where the user meets the declaration

§5.14.4's traceability check found T13's control split in two, with one half unplaced.
"Enforcement bounded to the declaration" is thorough — §5.9 says who may author one and §5.10
says what it can express. "Declaration made visible" was specified by F4 and placed nowhere.
This section places it, and it is the oldest outstanding obligation in the chapter.

**What is owed is bounded, and the bound is worth stating first.** §3.7 excludes user
*comprehension* as a human-factors question with its own literature, and F4 says explicitly that
it "concerns *availability* of the information, not user comprehension". So what Chapter 6 owes
is a surface, not evidence that anyone reads it — and R6 already retains, as a Medium residual,
the risk that the user is not equipped to evaluate a declaration. Nothing here reduces R6.

### 6.7.1 The denials are most of what there is to show

§5.10.7 makes the observation this rendering is built around: in its worked example, **nine of
the ten capabilities are denied by their absence**. The manifest never mentions them. A
rendering that shows only what was granted therefore shows the smaller half of what enforcement
does, so what an integration *cannot* do is printed at the same weight as what it can:

```
Example Weather  1.4.2
====================

These permissions were declared by whoever wrote this integration.

If you install this, it will be allowed to:
  - read the state of:
    sensor.outdoor_temperature
  - contact these addresses on the internet:
    api.example-weather.invalid

It will NOT be allowed to:
  - control anything — it cannot ask any other integration to do anything
  - change the state of any of your devices
  - be told when anything in your home changes
  - read any file outside its own folder
  - change any file outside its own folder
  - announce anything to the rest of Home Assistant
  - listen to what other parts of Home Assistant are doing
  - see any other integration's settings or saved passwords
  - add anything to Home Assistant's web interface

It is limited to 192 MB of memory, 8 processes.
```

Two grants, nine denials, from a manifest whose `permissions` block is four lines long. That
ratio is not a presentation trick; it is what default-deny means, made visible.

### 6.7.2 Four states, four renderings

An integration is in one of four states with respect to its declaration, and the third is the
one that would otherwise reproduce §1.8 exactly.

| State | Rendering |
|---|---|
| Author-declared | As above, with "declared by whoever wrote this integration" |
| Derived (§5.9.4 precedence 2) | "worked out for you, **not declared by the author** — check them before continuing", which is where §5.9.4's requirement for explicit user confirmation attaches |
| **Unreadable** | "could not be read, so it will be given no permissions at all", **with the reason** |
| Absent | "declares nothing… no permissions at all… nothing it asks for will be granted, because it has asked for nothing" |

**The unreadable case is the one worth arguing for.** A framework that rendered nothing when a
manifest failed to parse would leave the user unable to see what the integration intends —
§1.8's complaint precisely, except that this time the framework knows and did not say. It is
also the state in which the user is *most* likely to be looking, because something is wrong.

### 6.7.3 Three things this deliberately does not do

Each was considered and left out because including it would claim more than the project can
support:

- **Risk labels.** Marking `lock.unlock` as dangerous and a sensor read as harmless is an
  unvalidated ranking presented as authoritative — a claim about how users decide, which is
  exactly what §3.7 declines to make. The schema already does the legibility work structurally:
  §5.10.4's no-wildcard rule means a lock grant must name each operation, so a weather
  integration asking for `lock.unlock` is visible as a line of text without anything having to
  flag it.
- **The content hash.** §5.12.5 settled this — *no for the digest, yes for the change*. A hex
  string means nothing to the reader F4 exists to serve. A change in it is a sentence a
  non-programmer can act on, and the rendering carries that instead: *this integration's code
  has changed since you approved these permissions. What it is allowed to do has not changed.*
- **A consent flow.** Buttons, prompts, a wizard. §3.7 puts the interaction out of scope, and
  what §5.14.4 recorded as owed is a surface.

*Strength of claim: it runs, and its output is checked.* Fourteen assertions over the four
states — that the grants and denials are both named, that the provenance is stated, that no
digest appears, and that an unreadable declaration reports why. **This is not evidence that a
user understands any of it**, which is R6 and stays open.

**T13 is now placed in both halves**, and §5.14.4's oldest obligation is discharged.

## 6.8 Identity, and the record that makes a decision attributable

§5.12 defines identity as the domain name plus a content hash of what was loaded, hashed as a
tuple of three components — source, manifest, declared requirements — "each hashed separately
and then together". The separation is the design decision it asks to be judged on: a single
composite says *something changed*, three components say *what* changed.

### 6.8.1 The three components, and the one that does not yet earn its place

| Change made | Components that moved |
|---|---|
| A line of code | `source` |
| A `permissions` clause, code untouched | `manifest` |
| A declared dependency | `manifest` **and** `requirements` |

The first two are what §5.12.1 promises, and the second is the one that matters most: a manifest
swapped without a source change is an authority change, and an identity blind to it would miss
the most direct attack on this design.

**The third row is not what §5.12.1 promises, and the reason is structural.** Home Assistant
declares an integration's dependencies *inside* `manifest.json`, so a declared-dependency change
necessarily moves the manifest hash too. As implemented, `requirements` is therefore not an
independent component — it tells the log nothing the manifest hash has not already said.

It becomes independent exactly where §5.12.1 says it matters. That section asks for declared
requirements **with resolved versions**, and resolution happens when dependencies are installed
into the sandbox. A dependency that ships a new release under an unchanged declaration is
precisely the supply-chain case, and it moves the resolved versions while leaving both the source
and the manifest identical. **That install step is not built**, so the component is presently
vestigial, and the self-test asserts the dependent behaviour rather than the promised one so that
the gap cannot be mistaken for the feature.

### 6.8.2 Two chains, failing independently

§5.12.4 describes an escalation: the chain is evident against tampering, and "a keyed MAC over
each link, with the key held only in the mediator's memory, raises the bar — an attacker who can
write the file but not read that memory can no longer forge a consistent chain". Both are
implemented, and each record carries both links.

| Attack | `hash` chain | `mac` chain |
|---|---|---|
| Flip a denial into a permit | **breaks** at that record and every one after | **breaks** |
| ...and repair that record's own stored hash | **breaks** — see below | **breaks** |
| Delete a record | **breaks**, with a sequence gap | **breaks** |
| Reorder two records | **breaks** | **breaks** |
| Rewrite the whole file, recomputing every `sha256` link | **verifies cleanly** | **breaks at every record from the edit onward** |

*Strength of claim: measured.* Fourteen assertions, on both machines.

**The last row is the point of having two.** An attacker who can write the log but cannot read
the mediator's memory can recompute every `sha256` link, because `sha256` needs no secret — and
cannot recompute one HMAC. That is `01_PLAN.md` §5's "makes two controls fail independently",
and it is what the row above it costs: nothing, because both chains are computed over the same
canonical bytes in the same pass.

**A bug this found, which is the reason the second row is in the table.** The first version of
the verifier carried the *stored* hash forward from record to record rather than the one it had
just recomputed. An attacker who edited a record and repaired that record's own hash then broke
exactly one downstream link instead of all of them, and §5.12.4's "breaks every link after it"
was quietly false. The fix is one line — carry the computed value forward, never the one in the
file — and the principle behind it generalises: **a stored hash is a convenience for a reader
and must never be an input to verification.**

It was caught only because the self-test asserted the *strong* form of §5.12.4's claim rather
than that tampering is "detected". Under the weak form the bug passes: the tamper was still
detected, just at one record instead of four.

### 6.8.3 The order §5.11.3 requires, made durable

§5.11.3 puts the record before the action, "so an action that succeeds and then crashes the
mediator is still attributable", and says the ordering "is not an implementation detail". Two
things were needed to make it true rather than nominal:

- **The record is written and `fsync`ed before the action is attempted.** An ordering that
  leaves the record in a buffer is an ordering in the source code only; the crash it exists to
  survive takes the buffer with it.
- **The self-test crashes on purpose.** An action that raises immediately after the record is
  written leaves the record on disk, saying what was permitted. That is a two-line test and it
  is the only thing standing between this ordering and a comment claiming it.

The cost is real and belongs in Chapter 7's performance axis rather than hidden here: an
`fsync` per decision is far more expensive than the 2.4 µs §6.6.4 measured for the decision
itself, and §6.5.3's latency figures do **not** include it. Whether S7's durability is worth
that per-decision, or whether decisions should be batched with a bounded window of loss, is a
question with a real trade-off and Chapter 7 is where it gets measured rather than assumed.

### 6.8.4 What the key costs

The MAC key is generated at mediator start and held only in memory, which is what §5.12.4
specifies and what makes the last row of §6.8.2's table possible. It has a consequence that
section does not draw: **the key does not outlive the mediator.** Records written by an earlier
run remain hash-verifiable by anyone and are no longer MAC-verifiable by anyone, including the
mediator that wrote them.

So the strong property holds within a run and decays to the weak one across restarts. Persisting
the key would trade that away for exactly the adversary the key exists to stop — anyone who can
write the log file can then also read the key beside it. This is not a defect to be fixed but a
position on a trade-off, and it is stated here so that Chapter 7 evaluates the log it has rather
than the one the phrase "tamper-evident" suggests.

## 6.9 The adversarial cases

§5.8.2's fourth scope item is a hostile integration: "the garbage-collector technique,
credential recovery attempts, absent and malformed manifests, and the 2021 file-theft pattern".
This builds one and runs it inside a sandbox.

**The manifest it ships is ordinary**, and deliberately: the 2021 disclosures were not
integrations that asked for everything, they were widely-installed ones with a flaw. This one
legitimately declares a single sensor read. Everything beyond that is the attack.

### 6.9.1 One criterion, and three outcomes rather than two

The configuration directory holds a canary string in `secrets.yaml` and another in
`.storage/core.config_entries`. **The suite fails if either string appears anywhere in the
adversary's report** — whatever attack produced it, and whatever that attack's own verdict said.
A single unambiguous criterion is worth more than thirty individual assertions that could each
be written slightly wrong, which §6.6.5 is the standing reminder of.

Each attempt is recorded as one of three outcomes, and the third distinction is the design's
whole argument:

| Outcome | Meaning |
|---|---|
| `BLOCKED` | The attempt raised. Something refused it |
| `EMPTY` | The attempt **succeeded** and found nothing, because there was nothing there |
| `LEAKED` | It returned something it should not have |

§5.6.2 claims denial under R2 is structural rather than procedural — reading `secrets.yaml` "is
not refused by a check, there is nothing there to read". **A design producing only `BLOCKED`
would be the procedural one.** Collapsing the two into "pass" would hide exactly the property
the architecture was chosen for.

### 6.9.2 Results

*Strength of claim: measured.* On the C4 device, 37 attempts: **21 blocked, 9 empty, 6 denied by
the mediator, 1 permitted — the one its manifest declared.** Neither canary appeared.

| Family | Attempts | Result |
|---|---|---|
| **The 2021 traversal pattern** | 12 paths — `../../secrets.yaml`, `/config/secrets.yaml`, absolute paths to the real configuration root, `/sandbox/../secrets.yaml` | All `FileNotFoundError`. **Not "permission denied" — "no such file".** |
| Bulk filesystem search | Walk everything reachable, reading every file | Both variants killed by the cgroup — see §6.9.4 |
| **The garbage-collector technique** | `gc.get_objects()`, sweeping the heap for another integration's live objects | **Runs perfectly. 11,473 objects, all its own.** |
| Credential recovery | Other processes' `/proc/*/environ`, `/etc/shadow`, the user's home directory | Empty, empty, absent |
| Escaping | `chroot`, `unshare`, `ptrace`, `mount` over its own directory | `EPERM` from the seccomp filter |
| Reaching another integration | TCP to the host, DNS, open Unix sockets | Network unreachable; name resolution fails; no sockets |
| The audit log | Find any `.jsonl` anywhere | Nothing |
| Mediated requests | Undeclared entity, `lock.unlock`, claiming to be another integration, enumerating everyone's config entries, an undeclared host, an operation that does not exist | Six denials, each naming a clause |

### 6.9.3 The garbage-collector result is the one that matters

§2.4.1's published attack — walking `gc.get_objects()` to reach another integration's live
objects and read its secrets — is what §5.3 used to eliminate every in-process design, and §5.2
calls it the finding that settles the architecture. Here it is, run against this framework:

**it works.** It is not blocked, not filtered, not detected. It enumerates 11,473 objects
without error, exactly as published, and finds nothing — because every object in that heap
belongs to the integration running it. The other integrations are in other processes.

That is the difference between a design that answers this attack and one that survives it. An
in-process defence would have to *catch* the sweep, which means being an object in the heap the
sweep enumerates (§5.13.3). Here there is nothing to catch, and the attack's own success is the
evidence.

The same shape appears twice more in the table above. `/proc` lists one process, so reading
another process's environment returns an empty list rather than a refusal — T15, which Chapter 4
rated as requiring no attacker skill, has nothing left to read. And `setuid(0)` **succeeds**,
which is worth stating rather than quietly omitting: the sandbox is already uid 0 inside its own
user namespace, and that uid maps to an unprivileged user outside. The call does exactly what it
says and means nothing, which is what a user namespace is for.

### 6.9.4 A control fired that was not built for this

Both bulk-search attacks were killed by signal 9, with the cgroup's `oom_kill` counter at 1 and
peak memory at exactly `memory.max`. **S9 stopped a disclosure attempt.** S9 exists for T16,
resource exhaustion, and §4.10.1 generated it because T16 was the one threat with no control at
all; nothing in Chapter 4 or 5 predicted it would also bound how much of a filesystem an
integration can search. §5.13 argues defence in depth from the layers' independence; this is an
instance of it observed rather than argued.

The mechanism is worth naming because it is not obvious: **cgroup v2 charges page cache to
whichever cgroup faulted it in.** A sandbox reading enough file data reaches `memory.max` without
holding anything at all.

Two consequences, and neither is comfortable:

- **The kill destroyed the evidence.** The adversary died before it could report what it had
  attempted. §6.4.6 chose `EPERM` over `KILL_PROCESS` for the seccomp filter precisely so that a
  refusal stays legible and attributable — and the cgroup has no `EPERM` to offer. A framework
  whose strongest control produces a corpse and no record is one where the audit trail is weakest
  exactly when it is most needed. This is real, and it belongs in Chapter 8's limitations rather
  than being resolved here.
- **A legitimate integration can hit the same wall.** §5.10.6's `resources.memory_mb` now bounds
  file reading as well as memory, which no reader of that section would expect. An integration
  processing a large local dataset is indistinguishable, to this control, from one searching for
  secrets. Chapter 7 must measure that rather than discover it.

The suite itself was rebuilt around the finding: each attempt is written to the report the moment
it completes rather than at the end, so that a run stopped part-way still says what it managed.
That is §6.8.3's ordering argument in a third place — **write the record before the thing that
might not survive** — and the first two versions of this suite reported nothing at all, twice,
for exactly the reason §6.4.5 warned about.

### 6.9.5 What this is not

- **It is not Chapter 7's security evaluation.** That reproduces the 2021 pattern against a
  *baseline* Home Assistant as well, and the comparison is what makes the result a measurement
  rather than a demonstration. Here there is no baseline arm.
- **The adversary is synthetic.** It was written by the same person as the framework, which
  bounds what it proves: it establishes that the attacks named in §5.8.2 do not succeed, not that
  no attack does.
- **One host, one kernel, one configuration.** Everything in §6.4's limitations applies unchanged.
- **The permitted row is flagged, not hidden.** One request was granted, and the suite prints it
  with a marker that draws the eye rather than a tick, because a permit in an adversarial run is
  the thing a reader should check.

## 6.10 The bridge

§6.11.2 names the bridge as the single component everything remaining depends on. This is it, and
it is smaller than its position suggests — about 290 lines, all of it inside the sandbox.

Its shape follows from §5.6.2 rather than from convenience. Three mechanisms, and each is the
structural form of something a procedural design would have to check:

| Mechanism | What it does | What makes denial structural |
|---|---|---|
| **Declared services are registered** | One local handler per `services.call` clause, each forwarding to the mediator | The registry starts empty — §6.3.2 measured that it is *literally* empty. An undeclared service raises `ServiceNotFound` from Home Assistant's own registry: nothing refused it, there was nothing to call |
| **Declared entities are mirrored in** | The bridge asks the mediator for each declared entity at construction and sets it locally | An undeclared entity is **absent**. The integration reads `None`, not an error |
| **Local publications are forwarded out** | A state change for an entity the integration created becomes an `entity.publish` request | — |

**The bridge imports nothing from the framework.** The framing is reimplemented in thirty lines,
which §6.5.1 argued is a property worth having: the sandbox's half of the protocol needs no
library, so the trusted code inside a sandbox is exactly one reviewable file.

**And it is not an enforcement point.** The declared clauses arrive in the spec so the bridge can
construct local handlers, never so it can decide anything — every forwarded request is checked
again by the mediator. A bridge that trusted its own copy of the manifest would be in-process
enforcement, which §5.3 eliminated on published evidence.

### 6.10.1 An unmodified integration, running

*Strength of claim: measured.* On the C4 device, an integration written in the ordinary idiom —
config entry, `DataUpdateCoordinator`, `SensorEntity`, `async_add_entities`, the shape §5.6.1
measured at 83% of community integrations — placed in a sandbox with its source untouched.

| Claim | Result |
|---|---|
| **C1** — runs with zero source lines changed | Config entry reaches `LOADED` |
| **F1** — its entity is published | `sensor.ticks` appears locally, reaches the platform through the mediator, and is attributed to `demo_weather` at publish time |
| **§5.6.2** — a declared entity is readable | `sensor.outdoor_temperature` reads `11.5` from the integration's *own* state machine, mirrored in at construction rather than fetched per read |
| **§5.6.2** — an undeclared entity is absent | `sensor.bedroom_occupancy` reads `None` |
| **S5** — the declared service call goes through | `lock.lock` → called, and the platform saw exactly one call |
| **S5** — its counterpart does not | `lock.unlock` → **`ServiceNotFound`** |

**The `lock.unlock` row is S5 end to end**, and it is stronger than the schema result of §6.6.2.
There, a manifest granting `lock.lock` *refused* `lock.unlock`. Here the integration cannot reach
a refusal: the service is not in its registry, so Home Assistant's own dispatch fails before
anything of this framework is consulted. The permission that would have been checked does not
need to be — and §5.10.4's no-wildcard rule is what makes the registration set exact enough for
that to hold.

### 6.10.2 What the prior feasibility work contributed, and what it did not

`00_METHOD.md` §5 permits reusing the spike's working code rather than retyping it, and §6.2.2
sorted its components by whether they survive Gate G2's divergences. Building the bridge tested
that sorting.

| From the spike | Verdict |
|---|---|
| The R1 shim, its generator, its coverage scorer | **Superseded, and confirmed so.** R2's sandbox imports the genuine `homeassistant`; there is no proxy surface to generate |
| `runner.py`'s "path shadow" — making `import homeassistant` resolve to the fake package | **Superseded with it.** Under R2 the import must resolve to the *real* package, so the trick is not merely unnecessary but wrong |
| `bridge_integration/sandbox_bridge/` — the trusted component inside real Home Assistant | **Carried, and orthogonal to the divergence.** It answers step 5, which R1 and R2 face identically |
| `registry_gap.py`'s finding | **Cited as prior work, not relied on** — see below |

The finding is worth stating because it constrains work not yet done. The spike measured that
publishing an entity over Home Assistant's states API produces *states without identity*: no
entity-registry row, no `unique_id`, no config entry, no device, and nothing surviving a restart.
Its `sandbox_bridge` exists to close that — it owns a config entry and creates registry-backed
entities on a sandboxed integration's behalf, in about 250 lines that load and execute nothing
from any integration.

Under `00_METHOD.md` §2 that is private knowledge and **is not evidence in this chapter**; it is
cited with its date (2026-08) as prior work. What it does is tell Chapter 7 where to look, and
the shape of the claim is independently plausible from §5.6.1's own measurement: 83% of community
integrations publish through `async_add_entities` rather than through the state machine, and the
registry row is what that path produces and the state machine does not.

### 6.10.3 One rule Chapter 5 implies and does not state

Implementing `entity.publish` forced a decision. §5.10.2 makes an integration's own things ambient
— its own config entry, its own storage, registering *its own* services, on the ground that "the
risk is in *calling* others', not in offering one's own". §5.10.3 makes `entities.write` —
"setting state on entities it does not own" — declarable at 6.9%.

Publishing therefore splits on **ownership**, and ownership has to be recorded somewhere. The rule
adopted is the smallest one that works:

> **The first integration to publish an entity id owns it. Any other integration writing to that
> id needs an `entities.write` clause.**

Without it, an integration could publish `lock.front_door` and impersonate a lock — a spoofing
path Chapter 4 does not enumerate, because Chapter 4 modelled a platform in which entity
publication is not mediated at all. It is recorded here rather than folded in silently, because it
is authority the design grants ambiently and Chapter 5 never says so.

### 6.10.4 Three failures, all the same failure

Getting an interpreter to start inside a sandbox took three attempts, and all three produced
**exit code 126 with no output at all** — `execve` failing, which by construction happens before
anything can report.

1. `Path.resolve()` on the interpreter followed the symlink, so the *base* interpreter was bound
   and the virtual environment was not. Python found no `homeassistant`, because a virtual
   environment is located from the path it was *invoked* as.
2. Following the chain unresolved fixed that and exposed the next link: the directory the
   environment points at is itself a symlink — uv names one directory by minor version and
   another by patch — and `build_root` recreates a symlinked runtime path as a symlink rather
   than binding it. That is correct, and it leaves the link dangling unless the target is bound
   too.
3. The integration then loaded but its config entry stayed `NOT_LOADED`, because Home Assistant
   looks for a custom integration under `<config_dir>/custom_components/<domain>` and
   `/sandbox/component` is not that path.

Each was diagnosed by asking the sandbox what it could see rather than reasoning about what it
should have been able to see — the move that also settled §6.4.1 and §6.4.3. The general point is
worth keeping for Chapter 7: **a compatibility failure inside a sandbox is silent by default**,
because the thing that would report it is the thing that failed to start. Every one of these would
have been indistinguishable from "this integration is incompatible" had the harness not been made
to report the exit status and the cgroup's own counters.

### 6.10.5 What the bridge does not yet do

- **No push loop.** Declared entities are mirrored once, at construction. §5.11.3's push shape —
  the mediator sending a declared entity's changes as they happen — is not implemented, so an
  integration sees the value that existed when its sandbox was built.
- **No egress.** Scope item 2's second half is untouched: no proxy, no resolve-then-pin at
  connection time.
- **The platform is a stand-in.** Step 5 acts on an in-memory object, not a running Home
  Assistant. §5.8.2 makes the same concession about the lock and the reason is the same: what is
  under test is the mediator's decision. What a real instance would add is §6.10.2's registry
  identity, which is not nothing.
- **The integration is written for this test.** It is written in the idiom §5.6.1 measured as
  dominant and its source is never touched, which is what C1 asks — but it is not a community
  integration off HACS, and §6.11.1 scores it accordingly.

## 6.11 What is not built, and what Gate G3 has to decide

§6.1 fixed three strengths of evidence — it exists, it runs, it was measured — and said the
chapter would name which applied every time. This section applies that to the chapter as a whole,
and then reports against §5.6.5's re-decision triggers so Gate G3 is decided on evidence rather
than on the calendar.

### 6.11.1 §5.8.2's four scope items, honestly scored

| # | Scope item | Status |
|---|---|---|
| 4 | **Adversarial cases** — S1, S2, S6, S8 | ✅ **Measured** (§6.9). 37 attempts, the published garbage-collector attack among them, no canary reached |
| 3 | **One `lock`-domain service path** — S5, T05 | ✅ **Measured end to end** (§6.10.1). `lock.lock` travels to the platform; `lock.unlock` is not in the sandbox's registry to be called |
| 1 | **Sensor publication on unmodified integrations** — F1, C1 | ◐ **Half, and the half has moved.** One integration ran end to end and published through the mediator (§6.10.1); **37 real community integrations were then run, of which 46% import clean with all their entity platforms, unmodified** (§6.11.3). What is unmeasured is what happens past import |
| 2 | **Mediated egress with per-integration attribution** — F2, S4 | ◐ **Half.** Attribution is measured (§6.5.2). **Egress does not exist**: no proxy, no resolve-then-pin at connection time, no traffic |

**The remaining halves are different in kind.** Item 2's is a component nobody has written. Item
1's is no longer a population — it is a *depth*: the corpus has been run, and what is unmeasured
is what happens after an integration imports. N2 requires those two numbers be reported
separately for exactly this reason, and this chapter has the first.

### 6.11.2 What is still missing

The bridge of §6.10 removed the largest gap. Four remain, in descending order of what they block:

| Missing | What it blocks |
|---|---|
| **A baseline arm** | Whether 46% is the design's doing or the corpus's. Running the same 37 against a *full* Home Assistant is what decomposes it, and without it the number describes both |
| **Executed end-to-end** | N2's second number. Needs configuration data that only each integration's own config flow produces |
| **The egress proxy** | Scope item 2's second half, and F2 |
| **The push loop** | §5.11.3's push shape. Declared entities are mirrored once at construction, so an integration sees the value that existed when its sandbox was built |
| **The real Home Assistant component** | Step 5 currently acts on a stand-in. §6.10.2 records what a real instance would add, and why it is more than realism |
| **Dependency installation** | §6.8.1's third identity component, which stays vestigial until resolved versions exist |

So the honest summary of where Chapter 6 leaves the work has moved, and it is worth stating
precisely because it moved:

> **§5.15.6 said the design's central claim is empirical and Chapter 6 is where it stops being an
> argument.** The security half is measured. The compatibility half is now **demonstrated but not
> evidenced**: an unmodified integration runs, publishes and is confined, and the population it
> was drawn from is one.

### 6.11.3 Real integrations, and the trigger that fires

§5.6.5's second re-decision trigger was untestable until the bridge existed. It is now tested,
on 37 community integrations taken by install count, each in its own sandbox with its source
untouched (`experiments/compat/`).

| | Arm A — the minimal instance | Arm B — with declared components |
|---|---|---|
| **Imports clean, all entity platforms** | **17/37 — 46%** | +4 → **21/37 — 57%** |
| Failed for want of a declared component | 16 | 12 |
| Failed on a dependency they never declared | 3 | 3 |
| Peak memory, median / max | 100.6 / 151.0 MB | 110.8 / **209.4** MB |

*Strength of claim: measured.* On the C4 device. **Every dependency install succeeded**, across
all 37, so nothing here is attributable to packaging.

**The trigger fires, and the qualification matters more than the verdict.** §5.6.5 asked whether
integrations fail "for reasons a *fuller* instance would fix". Sixteen fail for want of a
component they declare — and making the instance fuller fixes only **four**. The other twelve
fail because the components they declare *do not themselves set up* in a stripped instance.

**One component accounts for most of it.** `http` blocks ten of the sixteen; then `mqtt` (6),
`lovelace` (4), `frontend` and `websocket_api` (3 each). §5.6.3 built the minimal instance with
"no HTTP server, no recorder, no frontend and no authentication", and 27% of this corpus declares
a dependency on the first of those. The encouraging half is that `ffmpeg`,
`persistent_notification`, `device_automation`, `dhcp`, `template`, `group`, `light`,
`utility_meter` and `onvif` all set up inside a minimal instance without complaint.

So the question R2 turns on is now much narrower than "is R2 compatible": **can a sandbox run
`http`, and what does it cost?**

**A classification decision worth defending**, because getting it wrong would have hidden the
finding. A missing Python module is not automatically a packaging gap: Home Assistant installs a
component's `requirements` when that component is set up, so an integration declaring
`dependencies: ["mqtt"]` receives `paho-mqtt` *because mqtt was set up*. In a minimal instance
the module is missing because the component is. The first version of this measurement did call
it packaging, reported 17% imports-clean, and could not test the trigger at all.

**Three integrations fail for a different reason, and it is a cost of isolation rather than of
stripping.** `battery_notes` imports `async_timeout`, `dreame_vacuum` imports `turbojpeg`,
`dwd_weather` imports `numpy` — none declared, none shipped by the platform. In a real
installation they work because *another* integration installed the package into the shared
environment. R2 gives each sandbox its own declared dependencies and nothing else, so this class
breaks under confinement, and it is the sharpest illustration available of what a shared
interpreter has been providing invisibly.

> **Refined by §6.12, and the correction is mine rather than Chapter 5's.** Two of the three —
> `dreame_vacuum` and `dwd_weather` — turn out to be reachable after all: `turbojpeg` and `numpy`
> arrive with the requirements of components the platform ships, so an instance that sets those
> up has them. Only `battery_notes` is a genuine shared-environment dependency, and
> `async_timeout` is a package Home Assistant's own `pyproject.toml` **bans** ("use
> `asyncio.timeout` instead"). The class is real and it is a third the size this paragraph
> claims.

### 6.11.4 The two triggers are coupled, which Chapter 5 did not anticipate

§5.6.5 lists footprint and compatibility as independent conditions. This measurement shows they
are not, and the coupling runs in the unhelpful direction:

> **Every component added to fix trigger 2 costs footprint, which is trigger 1.** Arm B's peak
> memory rose from a 151 MB maximum to 209 MB for four recovered integrations. Un-stripping far
> enough to run `http` for a quarter of the corpus would move it further.

*A caution on those figures.* `memory.peak` is the cgroup's high-water mark and includes page
cache; §6.3.2's 90 MB is proportional set size at rest. They are not comparable, and the numbers
above indicate direction rather than a revised budget. Chapter 7 must re-measure PSS at scale
with real integrations loaded — which is now a different measurement from the one §6.3.2 ran,
because the subject has changed from a synthetic probe to a corpus.

### 6.11.5 The Gate G3 report §5.6.5 asked for

| Trigger | Status |
|---|---|
| Footprint with the mediator and bridge attached | **Not fired, and now entangled with the second.** The mediator is one process for all sandboxes; the bridge is per-sandbox and cheap. What is not cheap is the components trigger 2 wants added |
| Real integrations fail for reasons a fuller instance would fix | **FIRES, qualified.** 16/37 fail for want of a component; 4 are recovered by supplying them. The residue needs `http` and its relatives, which a stripped instance cannot currently set up |
| Version coupling between sandbox and host | **Still untested.** Cheapest of the three: build sandboxes against two Home Assistant releases and record what breaks |

**What this does not say is that R2 should be abandoned.** §5.6.5's own wording is that a firing
trigger "would mean the stripping, not the architecture, is what breaks compatibility, and R1
would then be no worse". The measurement supports the first half and not the second: the failures
are at *import* of packages that arrive with components, and the fix is to supply those
components rather than to change how the integration is hosted. R1 would get them free by
proxying to the real instance — that advantage is real — and it would pay §5.6's original price,
which was emulating a helper layer that 100% of this corpus imports.

**The decision G3 now faces is therefore concrete rather than architectural**, and it is Younes's:

1. Un-strip toward `http` and measure the footprint cost, keeping R2.
2. Accept 46–57% import-level compatibility and report the ceiling honestly.
3. Revert to R1 on the strength of this result, and re-run §5.6.1's argument against it.

The first is the smallest step with the largest expected return, and it is the one this
measurement was run to make available.

### 6.11.6 Where the chapter leaves the work

Eight self-tests run on the C4 device, each naming the claim it checks. Together they establish that the mechanisms Chapter 5 specified exist, work unprivileged
on the target, behave as specified under attack, host an unmodified integration, and are
compatible with **46% of the most-installed community integrations at import level, without
modification**.

What they do not establish is what happens past import. N2 requires "executed end-to-end" to be
reported separately from "imports-clean" precisely because the first flatters the second, and
this chapter has only the first number. Nor is there a baseline arm: without running the same 37
against a *full* Home Assistant, 46% does not decompose into "confinement broke it" and "it was
broken anyway on this release". **That comparison is Chapter 7's first task**, and it is what
turns this into a measurement of the design rather than of the corpus.

Three corrections to Chapter 5 were found by building it — §6.3.2, §6.4.1 and §6.6.6 — and a
fourth by running it: §6.11.4's coupling of two triggers Chapter 5 treated as independent. Each
of the first three was an inference written in the register of a result. No measurement failed to
replicate. That asymmetry is the most useful thing this chapter hands to the next one.

## 6.12 Un-stripping toward `http`, and what it costs

§6.11.5 offered Gate G3 three options and called the first the smallest step with the largest
expected return: un-strip toward `http`, and pay the footprint. §6.11.3 makes it the obvious one
to try — `http` alone blocks ten of the sixteen component failures. This section pays.

### 6.12.1 Two changes, and one of them is free

**`http` will not set up without an authentication manager.** On a minimal instance
`async_setup_component(hass, "http", {})` returns `False` with no exception and no explanation.
Capturing Home Assistant's own log — which §6.11.3's arm B did not, and which is why it reported
eleven bare `False`s and said nothing about any of them — gives the reason at once:

```
AttributeError: 'HomeAssistant' object has no attribute 'auth'
    homeassistant/components/http/auth.py:113   hass.auth.async_create_system_user(...)
```

§5.6.3 built the instance with "no HTTP server, no recorder, no frontend and **no
authentication**", and the third turns out to gate the first. One line —
`auth_manager_from_config(hass, [], [])` — takes the cascade from **0 of 11 components to 10**,
and costs **0.1 MB**. Everything else was failing because `http` had.

**This collides with §5.10.3 and the collision is worth arguing rather than stepping around.**
That section says `hass.auth` "has no clause and cannot be declared. Users and tokens are the
platform's authentication state; a design whose whole purpose is to keep credentials away from
third-party code should not offer a permission that hands them over."

The manager built here has **no providers**, so its store holds no users, no credentials and no
tokens belonging to anyone. The system user `http` creates belongs to the sandbox's own store and
authenticates against the sandbox's own server, bound to the sandbox's own loopback in its own
network namespace, reaching nothing. It is the same pattern as the empty state machine (§5.6.2)
and the empty service registry (§6.3.2): **a real object whose contents are nothing.** §5.10.3's
refusal is about any route to the *installation's* auth manager, and this is not one. What would
violate it is mirroring real users in, and nothing does.

**A new network namespace's loopback is down.** With auth wired, `http` set up on the host and
still failed inside a sandbox, leaving only `homeassistant.components.network: Because the system
does not have any enabled IPv4 addresses`. §5.7.3 describes the network namespace as giving "no
route to anywhere" — accurate, and incomplete. It also gives no *working loopback*, which is a
different thing, and anything that binds a socket fails until it is raised. One `SIOCSIFFLAGS`
ioctl in the supervisor fixes it, and the grant is narrow by construction: the interface exists
only inside that namespace, so the sandbox gains the ability to talk to itself and nothing else.

### 6.12.2 What it buys

*Strength of claim: measured.* Same 37 integrations, same harness, one sandbox each.

| | Minimal | Un-stripped |
|---|---|---|
| **Imports clean, all entity platforms** | 17/37 — **46%** | 26/37 — **70%** |
| ...plus each integration's own declared components | 21/37 — 57% | 28/37 — **76%** |
| Failing for want of a component | 16 | 8 |
| Failing on a package nobody provides | 3 | 2 |

Nine integrations move from failing to clean and **none regresses**: `alarmo`, `browser_mod`,
`dreame_vacuum`, `dwd_weather`, `homematicip_local`, `llmvision`, `meross_lan`, `powercalc`,
`webrtc`. Every one of the ten components sets up in every sandbox.

### 6.12.3 What it costs, and peak memory is not the answer

Per-component cost, measured in-process, in the order Home Assistant resolves them:

| Component | Cost | Running total | Integrations unblocked |
|---|---|---|---|
| auth manager | **0.1 MB** | 73.5 MB | all of the below |
| **`http`** | **37.8 MB** | 111.3 MB | **10** |
| `frontend` | 26.1 MB | 137.4 MB | 3 |
| `mqtt` | 12.2 MB | 150.4 MB | 6 |
| `stream` | 28.3 MB | 178.8 MB | 2 |
| `websocket_api`, `lovelace`, `panel_custom`, `repairs`, `media_source`, `notify` | 0.6 MB total | — | 3, 4, 2, 1, 1, 1 |

But the budget is proportional set size across live sandboxes, not peak resident memory, and the
two tell different stories. Measured the way §6.3.2 measured it — six sandboxes, same probe in
both arms:

| | PSS per sandbox | Sandboxes in 60% of 4 GB |
|---|---|---|
| Minimal | 54.5 MB | 44 |
| Un-stripped | **130.4 MB** | **18** |

**+75.9 MB per sandbox, and the budget more than halves.** The per-sandbox *peak* moved only from
a median of 100 MB to 133 MB, which would have suggested a third; PSS at scale says 139%. This is
the same distinction §6.3.2 was built around and it matters again in the opposite direction —
there, a peak-based reading would have overstated a *saving*; here it understates a *cost*.

> **Translating to §6.3.2's published figure.** That harness used a probe with a sensor platform
> and a coordinator and measured 90.0 MB; this one uses a trivial probe. Applying the same
> +75.9 MB delta puts a realistic integration in an un-stripped sandbox at roughly **166 MB PSS,
> about 14 sandboxes** — an estimate from a measured delta rather than a measurement, and
> Chapter 7 should take it directly.

Against §5.8.1's mean of **4.02** community integrations per HACS-using installation, fourteen is
still three and a half times what a typical installation needs. The 449 MB of packages these
components require sit on disk rather than in each sandbox: they are the platform's own, bound
read-only and shared exactly as the `homeassistant` library already is.

### 6.12.4 The answer Gate G3 now has, and the option none of this measured

| Option | Compatibility | Budget |
|---|---|---|
| Keep the minimal instance | 46% | ~26 sandboxes |
| **Un-strip to the ten-component profile** | **70%** | **~14 sandboxes** |
| Un-strip, plus each integration's declared components | 76% | lower still, unmeasured |

**+24 points of import-level compatibility for roughly half the sandbox budget, and the budget
that remains is still 3.5× a typical installation.** On those numbers the trade is worth taking,
and §6.11.5's third option — reverting to R1 — is not indicated: the failures were never about
how the integration is hosted.

**The measured profile is not the one to build, though, and the data says why.** It pays for
`stream` (28 MB, two integrations) and `frontend` (26 MB, three) in every sandbox including those
that need neither, while the change that actually unblocks the cascade costs 0.1 MB. The
indicated design is therefore: **wire the auth manager always, and set up components per
integration from its own manifest.**

That was not measured. The per-integration arm ran with auth unwired — which is precisely why it
reached only 57% — and re-running it now that auth is free is the obvious next measurement. It
should approach 70–76% at well under 130 MB for integrations that declare little, and it is what
Chapter 7 should evaluate rather than the blanket profile.

**One correction of my own to record.** §6.11.3 reported three integrations failing on packages
nobody provides. Two of them — `dreame_vacuum` and `dwd_weather` — turn out to be reachable:
`turbojpeg` and `numpy` arrive with the requirements of components the platform ships. Only
`battery_notes` is a genuine shared-environment dependency, and the package it wants,
`async_timeout`, is one Home Assistant's own `pyproject.toml` bans. The class is real and a third
the size §6.11.3 claimed, and the classifier that produced the larger number credited components
that were never attempted — a bug fixed here rather than left to flatter the earlier result.

---

*Chapter 6 drafted 2026-08-25, §6.1–§6.12. Eight self-tests and three corpus measurements
passing on the C4 device, including an unmodified integration running inside a sandbox and **70%
of the most-installed community integrations importing clean** against an un-stripped one. Gate
G3 has its numbers. The section plan, the obligations this chapter inherits, and the questions a
viva will probe are in `notes/ch6_working_notes.md`.*