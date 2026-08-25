# Chapter 6 — working notes

**Started:** 2026-08-25 · Not part of the report. Reasoning, rejected alternatives, and the
questions a viva will probe.

---

## Section plan

| § | Content | State |
|---|---|---|
| 6.1 | What the chapter must deliver; the three strengths of "built" | ✅ drafted |
| 6.2 | The prior artifact — what survives R2, what is superseded, what may be cited | ✅ drafted |
| 6.3 | The sandbox — constructed not booted; the base component; the defect that found | ✅ drafted |
| 6.4 | The supervisor — where it must run (§6.4.1), the preflight (§6.4.2), the ordering bug (§6.4.3), the sandbox's filesystem (§6.4.4–§6.4.5) and the seccomp filter (§6.4.6) | ✅ **§6.4 complete.** All three of §5.7.3's primitives built and measured on the Pi; preflight 8/8, self-test passes |
| 6.5 | The channel — framing, identity by construction, and what it costs when real | ✅ drafted; `channel.py`, `mediator.py`, `selftest_channel.py` pass on the Pi |
| 6.6 | The mediator — manifest evaluation, resolve-then-pin | ⬜ |
| 6.7 | The manifest as the user meets it — **T13's unplaced half**, owed by §5.14.4 | ⬜ |
| 6.8 | The audit record — three-part identity, the hash chain | ⬜ |
| 6.9 | The adversarial cases, as built — §5.8.2's fourth scope item | ⬜ |
| 6.10 | What is not built; the report against §5.6.5's G3 triggers | ⬜ |

## Obligations this chapter inherits

| From | What | State |
|---|---|---|
| §5.6.5 | Measure whether the sandbox needs the base `homeassistant` component | ✅ **done 2026-08-25** — `experiments/base_component/`. It can go; **1.53×**, not the predicted 2× |
| §5.7.4 | The sandbox is placed in its cgroup **at creation**, not migrated afterwards | ✅ **discharged by correction, 2026-08-25** — §6.4.1. The rule was wrong; the supervisor's *position* is what binds |
| §5.14.4 | A surface where the user encounters the declaration (T13's unplaced half), bounded by §3.7 | ⬜ §6.7 |
| §5.8.2 | The four scope items, read out of Chapter 3's verification column | ⬜ §6.5–§6.9 |
| §5.6.5 | Report against the three R1 re-decision triggers at G3 | ⬜ §6.10 |

## §6.3 — the base-component measurement

**What was asked, and what came back.** §5.6.5 predicted the budget would "roughly double".
It improves by **1.53×** — 17 to 26 sandboxes. The prediction was arrived at by subtracting a
single-process figure, which is precisely the arithmetic §5.6.3 warns against two sections
earlier in the same chapter.

**Why this is worth keeping rather than quietly correcting.** It is the cleanest available
demonstration that the measurement discipline is doing work rather than decorating the report.
The warning was written, published, and then not applied by its own author — and the thing
that caught it was running the measurement instead of quoting the consequence.

**The design decision is unaffected by the correction.** R2 survives either way; only the
size of §5.8.1's third qualification changes. If the answer had gone the other way — if the
base component had been unremovable — the budget would have stayed at 17 and §5.8.1's
four-fold headroom would have stood unrevised. So this was never a decision-changing
measurement, and it should not be presented as one.

### The accidental finding, which is the more valuable one

`build_minimal_hass` reaches the running state with `set_state(CoreState.running)`, which
never fires `EVENT_HOMEASSISTANT_START`. Reading `helpers/start.py` rather than inferring from
the symptom: `async_at_start` branches on `hass.is_running`, so the omission **splits**
deferred callbacks rather than dropping them all.

- Registered **before** the flag — the helper layer's own, wired during construction — they
  wait for an event that never arrives and are lost. `RestoreStateData` is here, so state
  restoration is silently dead.
- Registered **after** — integrations, set up later — they fire *immediately*, part-way
  through assembly, where Home Assistant would run them once every component is up.

The fix is therefore not "call `async_start()`" but "start where Home Assistant starts": last.
Starting before the integrations are loaded also repairs restoration and was the first fix
tried; it leaves every integration in the second case, so it is the wrong fix.

**Process point worth defending aloud.** The probe failed in *both* arms. A result identical
on both sides of the variable is a broken test, not a finding about the variable, and treating
it as one is what turned a wasted afternoon into the most useful thing in the experiment. This
is the second time this pass that a failing test has been worth more than a passing one — the
first was the cgroup migration failure of 2026-08-25 that produced the placement-at-creation
rule.

## §6.4.1 — the correction to §5.7.4

**What happened.** §5.7.4 saw a migration refused with `EACCES` and concluded that the sandbox
must be placed in its cgroup at creation. That conclusion has an untested premise: that
creation is permitted where migration is not. `clone3(CLONE_INTO_CGROUP)` — the only mechanism
that would do it — was never tried, because Python has no `clone3` and trying it meant writing
C. So the cheapest available inference was written down as a design rule.

Measured: `clone3` fails with the identical `EACCES` from the identical position. The kernel
checks the common ancestor either way. **The rule was not merely unproven, it was false.**

**Why this one is more embarrassing than §6.3.2's**, and worth saying so in the viva rather
than being caught: §6.3.2's error was an arithmetic shortcut on a figure explicitly labelled a
prediction, in a section titled "the re-decision point". This one was stated as a finding, in
bold, and generalised in the same paragraph into "three separate mechanisms have now landed on
the same rule". A pleasing generalisation is exactly what should have triggered the check, and
instead it discouraged one — the pattern felt like confirmation.

**What survives.** The observed failure was real, and so is the instinct behind the rule: the
window between fork and placement is a window in which the sandbox runs uncapped. Self-migration
by the child immediately before `exec` closes it, works from the right position, and needs no C.
So the design lands where §5.7.4 wanted it, by a route §5.7.4 had wrong.

**The trap to keep.** `mkdir` succeeds from the wrong position. Everything the supervisor
inspects looks right and only the placement fails. This is the third distinction in the same
area — controller *present* (probe, 2026-08-24), limit *enforced* (probe re-run, 2026-08-25),
and now *permission to enforce* — and all three were discovered by testing rather than reading.

## §6.4.2–§6.4.3 — the first code

**What exists:** `framework/confine/` — `cgroup.py` (delegation discovery, sandbox cgroup,
self-placement), `namespaces.py` (the seven flags, identity maps, availability probe),
`preflight.py` (seven checks and the N3 refusal). Standard library only, plus `ctypes` for the
two syscalls Python does not wrap. Seven of seven pass on the Pi inside a systemd user scope;
from an ssh session the run stops at `supervisor inside it` and says what to do.

**The design point worth defending:** every check exercises the operation it checks. That is
not thoroughness for its own sake — it is the third correction in a row in the same area, and
each was invisible to the check that preceded it (controller listed → limit enforced →
permitted to enforce). A framework that checked what it could *see* would have declared itself
ready in a position where it could confine nothing.

**No override flag, deliberately.** Asked at a viva "what if an operator needs to run without
it", the answer is that such an operator is running unconfined and the framework's whole claim
is that the user cannot tell — §1.6. A `--i-know-what-im-doing` flag reproduces the status quo
with a nicer name.

### The bug in the namespace check, and why it is in the report

The check failed with `Operation not permitted` on a host where `host_isolation_probe` had
already shown all seven namespaces available. Two candidate explanations: the host changed, or
the code is wrong. Testing each flag separately took a minute and settled it — `unshare`
succeeded for all seven; the failure was the next call.

`write_identity_maps` read the uid to map with `os.getuid()` *after* the `unshare`, when the
answer is already `nobody`. It wrote `0 65534 1` and the kernel refused, because an
unprivileged process may write only a single-line map whose outer id is the one it already had.

**Why this is in the report rather than just fixed.** It is the third instance of the ordering
§6.3.4 tabulates, arriving from a fourth mechanism, and it is the one that shows the rule is
not about sandboxes: *the supervisor's own credentials must be captured before the namespace
that hides them exists.* The signature now takes them as arguments so the mistake cannot recur
silently.

**The transferable habit:** a check that contradicts an earlier measurement is usually the
check being wrong. Believing it would have put a false limitation about Raspberry Pi OS
namespaces into Chapter 7.

## §6.4.4–§6.4.5 — the mount namespace, and the finding that came out of building it

**The result.** A sandbox built around a configuration directory holding `secrets.yaml`,
`.storage/` and a second integration: uid 0 inside mapped to 1000 outside, one visible process,
`lo` only, its own directory read-only, its data directory writable, the one declared file
present, and everything else absent. Passes on the Pi.

**The finding worth carrying into the viva, and into Chapter 7.** Three separate defects came up
while getting there, and all three presented identically — as an *absence*:

1. the status descriptor was hard-coded while the supervisor passed the real number in the
   environment, and the failed write was swallowed → "the sandbox never reported a pid";
2. the private `/tmp` was mounted after the declared paths and covered one of them → the file
   was simply not there;
3. the self-test expected the configuration root to be absent, and it is legitimately present
   as a skeleton → a failing check against correct code.

That is not a coincidence, it is the shape of the design. **§5.6.2's structural denial uses
absence to mean "not granted", so any bug producing an absence is indistinguishable from the
framework working.** Chapter 5 argued that structural denial beats a procedural check because
there is no code path to forget; the other half of that trade is that a check which is missing
raises nothing and a check which is wrong denies silently. Worth saying aloud: it is a cost of
the design's best idea, found by building it, and it is the sort of thing a viva rewards
volunteering.

**Two things the self-test is not.** It uses a synthetic integration, and it tests the
filesystem view rather than an adversary trying to break out of it — that is Chapter 7's
adversarial evaluation. It establishes that the construction does what §5.6.2 says, not that
nothing defeats it.

**Design points to be able to defend aloud:**

- `pivot_root`, not `chroot`: a process in a user namespace holds `CAP_SYS_CHROOT` over it, so
  a chroot there is a boundary only from a distance.
- The second fork: `unshare(CLONE_NEWPID)` puts *children* in the new namespace, not the
  caller. Without it there is no PID 1, no honest `/proc`, and no PID isolation at all.
- The parent exits instead of waiting: an idle interpreter per sandbox would eat §6.3.2's
  budget. `PR_SET_CHILD_SUBREAPER` keeps the sandbox waitable without it.
- Spec on stdin, not `argv`: `/proc/<pid>/cmdline` is readable by anything running as the same
  user, and a sandbox's declared paths are not something to publish.

## §6.4.6 — the seccomp narrowing, stated rather than glossed

§5.7.3 specifies an allow-list ("denies syscalls outside the set an integration needs"). What
is built is a **deny-list of 29 calls**. That is a real narrowing and the report says so in the
section rather than in a footnote.

**The argument that it is sufficient here does not generalise**, and that is the point to make
first if challenged: by the time the filter is installed the other six namespaces have removed
most of what a syscall could reach, so what is left for seccomp is calls dangerous in
themselves. In a design where seccomp was the boundary rather than one of three layers, the
same choice would be indefensible.

**Residual risk, stated as a number rather than a gesture:** anything not among the 29 is
allowed, so a kernel vulnerability elsewhere is unmitigated by this layer. §5.13 already counts
seccomp as one of three layers and §5.7.5's kernel-surface residual stands; what is new is that
it is now countable.

**Why EPERM and not KILL_PROCESS.** A killed sandbox is indistinguishable from a crashed one —
§6.4.5's absence problem in another costume. An errno keeps the sandbox alive to be observed,
keeps the failure attributable, and gives the §5.12 audit record something to say. If Chapter 7
finds an integration probing denied calls in a loop, that is data; a corpse is not.

**Why the numbers are verified rather than trusted.** Hard-coded per architecture, no portable
way to ask Python, and a wrong number denies the wrong call *silently*. So a throwaway child
installs the filter and makes the calls. `chroot` and `unshare` are the probes worth having
because both **succeed** inside a user namespace — refusal is then evidence of seccomp, not of
the namespace surrounding it.

## §6.5 — the channel

**The demonstration is the section.** Two sandboxes both send
`{"integration": "demo_a", ...}`; the audit shows `demo_a` and `demo_b`, each with the claim
recorded *beside* the identity that came from the socket. §5.11.2 argued that a protocol in
which the sandbox names itself "asks the adversary to self-report the one fact the decision
turns on"; this is that argument with the adversary actually doing it.

**Default-deny was built before the permit path**, deliberately. S6 is the behaviour every later
addition has to preserve, and a default-deny added after the permit path is one that has already
been forgotten once. It also means the first working version of the mediator is trivially
correct in the only respect that matters, and everything after it is a controlled relaxation.

**The latency result is the more interesting half.** Against §5.11.4's stated floor:

| | floor (§5.11.4) | real channel, 2 sandboxes |
|---|---|---|
| median | 30.0 µs | 35.6 µs (+19%) |
| p99 | 33.9 µs | 62.7 µs (**+85%**) |

A cost that lands almost entirely in the tail is **queueing, not work**. The added per-request
work — one policy call and one audit append — moved the median 19%; the contention between two
clients on a single-threaded mediator nearly doubled p99. That decomposition is worth being able
to state aloud, because it says which fix would help: not a faster protocol, a mediator that
does not serialise.

**Owed to Chapter 7, and it is new:** latency at realistic sandbox counts. Two clients say
nothing about twenty-six (§6.3.2's budget), and the shape of the curve between them is what a
single-threaded mediator deserves to be judged on.

## Anticipated viva questions

**"Your Chapter 5 predicted the budget would double and Chapter 6 says 1.53×. Which of your
other numbers are wrong?"** — The prediction was labelled as one, in a section explicitly
titled "the re-decision point", and it was the first thing Chapter 6 tested. The distinction
the report maintains is between figures that were *measured* and consequences that were
*inferred from* them; §5.6.3's 136.5 MB was measured and replicated to 0.1 MB a day later by a
different script, and the doubling was inferred, wrongly. That is the class to audit, and
§6.1's three strengths of "built" exist to keep the two apart.

**"Why not just keep the base component? 46 MB is not much."** — It is 34% of a sandbox, and
it buys thirteen services that reach nothing inside a sandbox whose state machine holds only
that integration's own entities. The compatibility cost is bounded at 5.6% of the measured
community corpus by literal service call, and those calls belong at the mediator anyway,
because they are cross-integration effects by construction.

**"You dropped a component and 5.6% of integrations call into it. Isn't that a compatibility
regression you chose?"** — Yes, and it is stated as one. It is not a regression relative to
*confinement*, though: those calls are `homeassistant.turn_on` and friends against arbitrary
entities, which the design mediates whether the local copy exists or not. Keeping the
component would have made them silently no-op instead of visibly fail, which is worse.

**"Chapter 5 states a rule in bold and Chapter 6 says it is false. How much of Chapter 5 is
inference dressed as measurement?"** — The report distinguishes the two and this is where the
distinction is tested rather than claimed. §5.7.4's *finding* — the `EACCES` on migration — was
measured and stands. The *rule* was an inference from it, made in the same paragraph without a
marker, and that is the defect: not that an inference was wrong, but that it read like a
result. The audit that follows is §6.1's three strengths of "built", applied backwards to
Chapter 5's claims, and the two corrections found so far (§6.3.2, §6.4.1) are both inferences
sitting next to measurements. The measurements have all replicated.

**"Your mediator is single-threaded and your own numbers show the tail doubling with two
clients. Isn't that a design flaw you have measured and shrugged at?"** — It is a design flaw
that has been measured and *scheduled*. The decomposition matters: the median moved 19% and p99
moved 85%, which locates the cost in queueing rather than in the work per request, so the fix is
concurrency in the mediator and not a change to the protocol or to the boundary. §6.5.3 states
the obligation and Chapter 7 measures the curve to twenty-six sandboxes. What would be
indefensible is reporting the median and not the tail, which is why both are in the report.

**"Chapter 5 specifies an allow-list and you built a deny-list. Why should I accept that?"** —
Because of where it sits, and the report argues it from position rather than from convenience.
An allow-list for CPython plus Home Assistant is several hundred entries that move with the
interpreter version; more to the point, it would be doing work the other six namespaces have
already done. The 29 calls denied are the ones that are dangerous whatever namespace they are
made from. The residual — anything else is allowed — is stated in §6.4.6 and is consistent with
§5.13 already counting seccomp as one layer of three rather than as the boundary.

**"You said the sandbox sees only its own directory. Your own listing shows `/usr`, `/bin`,
`/lib`. Which is it?"** — The second. R2 runs a real interpreter against a real Home Assistant
and neither executes out of nothing, so the sandbox holds a read-only copy of the runtime.
§5.10.2's "its own directory and nothing else" is about *declared* resources; the runtime is
ambient in the same way the sandbox's own data dictionary is. §6.4.4 says so explicitly and
prints the root listing rather than describing it, because the alternative is letting a reader
infer an emptier sandbox than exists.

**"The configuration root is visible inside your sandbox. Isn't that exactly what §5.10.5
forbids?"** — §5.10.5 forbids *granting* it, and it is not granted: it holds the one declared
path and nothing else, with `secrets.yaml` and `.storage/` absent. What is disclosed is the
host path's name, because declared paths appear at their host locations so an integration's own
absolute paths keep working. That is a design choice with a stated cost, recorded in §6.4.5
rather than in Chapter 7's limitations, because the design caused it rather than inherited it.

**"Your preflight allocates 192 MB every time the framework starts. Is that reasonable?"** —
It is the only way to distinguish a limit that is set from a limit that bites, and §5.7.4's
re-probe exists because those came apart on this exact host. It takes about a second on the C4
device and there is a `--shallow` flag for when the caller has other reasons to trust it. If
start-up cost becomes a real objection the right answer is to cache the result against the boot
id, not to stop checking.

**"Why is the supervisor single-threaded? That sounds like a limitation you backed into."** —
It is a consequence of self-placement. The sandbox has to enter its cgroup between `fork` and
`exec`, which in Python means `preexec_fn`, which is unsafe with threads. The alternative is to
migrate the sandbox from the parent afterwards, which reopens a window in which it runs
uncapped — and T16 is a sandbox consuming memory. So the constraint was accepted rather than
worked around, and it is recorded in §6.4.2 as a constraint rather than as a design feature.

**"How do you know PSS is the right figure and not `MemAvailable`?"** — Both were recorded,
and the arms were run in both orders. PSS was identical to 0.1 MB across four arm-runs;
`MemAvailable` moved 4–5 MB, always downward for whichever arm ran second, because the second
arm reads files the first left in the page cache. §5.6.3 called `MemAvailable` ground truth,
which is right for one measurement on a quiet machine and wrong for a comparison of two arms.

**"Your prior artifact's biggest component is now dead code. Was the rebuild worth it?"** —
§6.2.2 puts the invoice in the report rather than in a footnote. The shim was ~40% of the prior
framework and it is superseded by a divergence reached from measurements taken in this pass.
`00_METHOD.md` §3 accepted that cost in advance: a rebuild that could only ever confirm would
have been theatre. What the discarded work still buys is an option — R1 and R2 built against
the same integrations would be a stronger compatibility comparison than R2 alone, and the
literature has neither. It is recorded as an option for G3, not a commitment, and on current
schedule evidence it is unlikely to be affordable.

## Open, and deliberately not decided here

- **The R1-vs-R2 comparison** (§6.2.2). Competes with coverage-widening, which §5.8.5 already
  nominates as the first cut. Both are G3 calls, and they are Younes's.
- **How many *community* integrations defer work to start-up.** The 28-component figure is
  over shipped integrations. `figures/fetch_hacs_corpus.py` rebuilds the corpus that would
  answer it; this belongs with the uniform-sample re-run already owed before Chapter 7 reports
  coverage.
