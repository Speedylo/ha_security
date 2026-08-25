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

---

*Chapter 6 in progress: §6.1–§6.3 and §6.4.1–§6.4.6 drafted 2026-08-25. All three of §5.7.3's
isolation primitives are now built and measured on the C4 device, in `framework/confine/`.
Next: §6.5, the bridge and the channel. The section plan and the obligations this chapter
inherits are in `notes/ch6_working_notes.md`.*
