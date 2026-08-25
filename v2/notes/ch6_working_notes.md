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
| 6.6 | The manifest and the permit path — validation, S5, clause pointers, what a decision costs | ✅ drafted; `manifest.py` + `selftest_policy.py` pass |
| 6.7 | Where the user meets the declaration — **T13's unplaced half discharged** | ✅ drafted; `describe.py` + `selftest_describe.py`, 14 assertions over four states |
| 6.8 | Identity and the audit record — three components, two chains, the durable ordering | ✅ drafted; `audit.py` + `selftest_audit.py`, 14 assertions |
| 6.9 | The adversarial cases — one canary, three outcomes, 37 attempts | ✅ drafted; `selftest_adversary.py`, 21 blocked / 9 empty / 6 denied / 1 permitted |
| 6.10 | **The bridge** — an unmodified integration running inside a sandbox | ✅ drafted; `sandbox_runtime.py`, `platform.py`, `selftest_bridge.py` |
| 6.11 | What is not built; §5.8.2's scope items scored; the G3 report | ✅ drafted |

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

## §6.6 — the manifest

**Two rules the module is written to**, both worth being able to state as decisions rather than
as style: reject at parse time so the decision path has no error branches in it, and treat an
unknown key as a rejection rather than ignoring it, because ignoring under-enforces silently.
The second matches what `hassfest` already does (`PREVENT_EXTRA`), which is a useful thing to be
able to point at.

**S5 is a property of the comparison, not a rule applied to it.** Validation rejects wildcards in
`services.call` outright, so the decision path is exact string equality. There is no code that
could be written slightly wrong and let `lock.*` through, because `lock.*` never gets past
parsing. That is the strongest form of the argument and it is worth putting that way round.

**Still owed for S5:** §5.8.2 requires a `lock`-domain service path through the *running* system.
§6.6.2 establishes the manifest layer cannot express the defeating grant; it is not the end-to-end
verification and says so.

**Cost of a decision: ~2.4 µs** (median 35.6 → 38.0 µs against the deny-everything placeholder),
tail unchanged. Confirms §6.5.3's decomposition: the work per request is small, the queueing is
not.

### The test that passed for the wrong reason

Three `files` rejections were green and proved nothing: `files` was missing from the known-members
table, so those manifests were refused as *"unknown member 'read'"* and never reached §5.10.5's
path check. Caught only by reading the rejection *reasons* rather than the verdicts.

**Why this keeps happening, and the generalisation to carry into Chapter 7:** a default-deny
system is one in which almost every mistake produces the safe answer. §6.4.5's version was a bug
producing an absence, where absence means denied; this is a bug producing a rejection, where
rejection is what the test wanted. **Safe answers are exactly what tests do not investigate.**
Chapter 7's negative cases must assert on *why* something was refused, never that it was.

## §6.6.6 — the third correction to Chapter 5, and the pattern in all three

§5.14.4 states "Nothing about the filesystem is declared (§5.10.2)" while §5.10.3 lists `files`
among the eight declarable capabilities and §5.10.5 spends two paragraphs constraining it. The
misreading is specific: §5.10.2 makes the integration's *own directory* ambient, and §5.14.4
read that as the filesystem being ambient.

It had a consequence beyond a sentence — it placed an obligation on Chapter 7 never to repeat
§4.10's phrase "filesystem isolation to declared resources". That obligation is **withdrawn**;
the phrase is accurate.

**What settles it is a result, not a re-reading.** §6.4.5's self-test shows a declared file
present and read-only inside a running sandbox next to an absent `secrets.yaml`. Nothing about
the filesystem being undeclared could produce that row.

**The pattern across all three corrections is the thing to be able to say at a viva.** §6.3.2
(the budget would double), §6.4.1 (the sandbox must be placed at creation), §6.6.6 (nothing about
the filesystem is declared): every one was an **inference stated in the register of a result**.
The measurements have all replicated — §5.6.3's 136.5 MB came back at 136.6 a day later from a
different script. It is the sentences *next to* the measurements that need auditing, and §6.1's
three strengths of "built" exist precisely to keep them apart. Worth volunteering rather than
being caught by.

Uncomfortable but honest addition: §5.14 was the traceability check, the section whose entire
purpose was catching this class of error. It caught three others correctly, including the T13
gap §6.7 discharges. On T14 it produced a confident finding, with an obligation attached, from a
misreading of the section it cited.

## §6.7 — the F4 surface

**Discharges the oldest outstanding obligation** (§5.14.4, T13's unplaced half).

**The design idea worth defending:** the denials are printed at the same weight as the grants,
because §5.10.7's worked example denies nine of ten capabilities by absence. Showing only grants
would show the smaller half of what enforcement does. Two grants, nine denials, from a four-line
`permissions` block.

**Four states, four renderings**, and the unreadable one is the one to argue for: rendering
nothing when a manifest fails to parse reproduces §1.8 exactly, except the framework knows and
did not say — and it is the state the user is most likely to be looking at, because something is
wrong.

**Three things declined, each because including it would over-claim:** risk labels (an
unvalidated ranking presented as authoritative is a claim about how users decide — §3.7 declines
it, and §5.10.4's no-wildcard rule already makes `lock.unlock` visible as a line of text without
anything flagging it); the content hash (§5.12.5: no for the digest, yes for the change); and a
consent flow (§3.7, and what was owed is a surface).

**What this is not:** evidence anyone understands it. R6 stays open at Medium, and §6.7.3 says
so in the section rather than in a footnote.

## §6.8 — the audit record

**Two things worth volunteering rather than being caught on.**

1. **The third identity component is currently vestigial.** Home Assistant declares requirements
   inside `manifest.json`, so a declared-dependency change moves the manifest hash anyway.
   §5.12.1 asks for *resolved* versions, which is where the separation earns its place — a
   dependency shipping a new release under an unchanged declaration moves nothing else — and the
   install step that would resolve them does not exist. The self-test asserts the dependent
   behaviour (`["manifest", "requirements"]`) rather than the promised independent one, so the
   gap cannot be read as the feature.

2. **`fsync` per decision is not in §6.5.3's latency figures.** The ordering §5.11.3 requires is
   only real if the record is durable before the action is attempted, and that costs far more
   than the 2.4 µs of the decision itself. Whether S7's durability is worth it per-decision, or
   whether a bounded window of loss is the right trade, is Chapter 7's to measure. Stating it
   here is better than being asked why the numbers do not add up.

**The bug the strong assertion caught.** `verify()` first carried the *stored* hash forward
between records instead of the recomputed one. An attacker who edited a record and repaired that
record's own hash then broke exactly one downstream link, and §5.12.4's "breaks every link after
it" was quietly false. One-line fix; the generalisation is that **a stored hash is a convenience
for a reader and must never be an input to verification.**

Note what would have hidden it: asserting that tampering is "detected". It was — at one record
instead of four. The test asserted the strong form of the claim, which is why it failed. This is
the same lesson as §6.6.5 from the other direction: there, a green test proved nothing because
the safe answer arrived by the wrong route; here, a weak assertion would have accepted a
materially weaker property.

**Why two chains cost nothing.** Both are computed over the same canonical bytes in the same
pass. The payoff is `01_PLAN.md` §5's "two controls that fail independently": an attacker who can
write the file but not read the mediator's memory recomputes every sha256 link cleanly and cannot
recompute one HMAC.

**The key's cost, which §5.12.4 does not draw:** it does not outlive the mediator. Records from
an earlier run stay hash-verifiable and stop being MAC-verifiable — including by the mediator
that wrote them. Persisting the key would hand it to exactly the adversary it exists to stop.

## §6.9 — the adversary

**The single strongest result in the chapter, and it is a success rather than a block.**
§2.4.1's garbage-collector attack — the published finding §5.3 used to eliminate every
in-process design — runs perfectly inside the sandbox. 11,473 objects enumerated, no error, and
nothing found, because every object in that heap belongs to the integration running it. An
in-process defence would have to *catch* the sweep, which means being an object in the heap the
sweep enumerates. Here there is nothing to catch.

**Three outcomes, not two, and the report says why.** `BLOCKED` (it raised), `EMPTY` (it
succeeded and found nothing), `LEAKED`. §5.6.2's claim is that denial is structural rather than
procedural, so a design producing only `BLOCKED` would be the procedural one. All twelve 2021
traversal paths return `FileNotFoundError`, not `PermissionError`.

**Honesty items to volunteer:**
- `setuid(0)` succeeds. It is meaningless — the sandbox is already uid 0 inside its own user
  namespace, mapped to an unprivileged uid outside — and omitting it would look like hiding it.
- The adversary is synthetic and written by the same person as the framework. It shows the
  attacks §5.8.2 names do not succeed, not that no attack does.
- There is no baseline arm here. Chapter 7's comparison against an unconfined Home Assistant is
  what turns this from a demonstration into a measurement.

### S9 fired at something it was not built for

Both bulk-search attacks were OOM-killed: `oom_kill=1`, peak exactly `memory.max`. **cgroup v2
charges page cache to whichever cgroup faulted it in**, so a sandbox reading enough file data
hits its memory limit without holding anything.

S9 exists for T16. Nothing in Chapters 4 or 5 predicted it would also bound how much of a
filesystem an integration can search. §5.13 argues layer independence; this is an instance
observed rather than argued, and it is the best defence-in-depth evidence the project has.

**But it is not free, and both costs go in the report:**
1. **The kill destroys the evidence.** The adversary died before reporting. §6.4.6 chose EPERM
   over KILL for seccomp precisely to keep refusals legible — the cgroup has no EPERM. The
   audit trail is weakest exactly where the control is strongest. Chapter 8 limitation.
2. **A legitimate integration hits the same wall.** `resources.memory_mb` now bounds file
   reading, which no reader of §5.10.6 would expect. Chapter 7 must measure it.

**Process note worth keeping:** the first two versions of this suite reported *nothing at all*,
because they built one report and printed it at the end — and the framework killed them
part-way. The fix was to emit each attempt as it completes. That is §6.8.3's rule in a third
place: write the record before the thing that might not survive. It took two failures to apply
a lesson already written down twice in this chapter.

## §6.10 — the honest score, and what G3 has to decide

**§5.8.2's four scope items:** item 4 measured, items 2 and 3 half, item 1 not started. Nothing
redefined to make the score look better — item 1's criterion is "zero source lines changed" and
no community integration has run against this framework. §5.6.3 and §6.3.2 ran a *synthetic*
one, which establishes the sandbox's interior works and is not C1.

**The sentence the chapter turns on:**

> §5.15.6 said the design's central claim is empirical and Chapter 6 is where it stops being an
> argument. **The security half has. The compatibility half has not**, because no unmodified
> integration has run, and C1 is what makes the problem hard.

Say that before anyone else does. It is the honest score and it is also the argument for what to
build next.

**The G3 report: none of §5.6.5's three triggers has fired, and none has been tested.** The
useful contribution is converting that into a cheap test plan rather than leaving it as a gap:

1. *Footprint with mediator and bridge* — direction favourable, because the mediator is one
   process for all sandboxes and does not scale with them. The bridge is per-sandbox and
   unmeasured. Re-run `experiments/base_component`'s scale arm with the bridge: an afternoon.
2. *Real integrations fail against a minimal instance* — **the one that matters**, untested,
   and blocked on the bridge.
3. *Version coupling* — cheapest; build against two HA releases and record what breaks.

**The coincidence worth exploiting:** the bridge discharges scope items 1 and 3 *and* tests the
trigger most likely to fire. One piece of work, three obligations.

**What this does to §5.8.5's cut-order conflict** — and it cuts against the recommendation
Chapter 5 left. The actuator path is now much cheaper than when §5.8.5 was written, because the
manifest layer that makes S5 true is built and tested; what remains is a service call through
the *same* bridge item 1 needs. So the G3 question is no longer "actuator or coverage" but
"**bridge, or neither**". Still Younes's call, but a narrower one.

## §6.10 — the bridge

**The result to lead with:** an integration whose source was never touched ran inside a sandbox,
published its entity through the mediator, read the one entity it declared, and **could not reach
a refusal** for `lock.unlock` — the service is not in its registry, so Home Assistant's own
dispatch fails before this framework is consulted. That is S5 end to end and it is stronger than
§6.6.2's schema result, where the manifest *refused* the call.

**The bridge is not an enforcement point, and say so before being asked.** It registers handlers
for declared services and mirrors declared entities so the sandbox has a local shape; every
forwarded request is checked again by the mediator. A bridge trusting its own copy of the manifest
would be in-process enforcement, which §5.3 eliminated on Corno & Mannella's evidence.

**What the spike gave, and what it did not.** §6.2.2's sorting held up under test: the R1 shim and
`runner.py`'s path-shadow trick are superseded — under R2 the import must resolve to the *real*
homeassistant, so the trick is wrong and not merely unnecessary. `sandbox_bridge` and
`registry_gap.py`'s finding are orthogonal to the divergence and carry over, because step 5 is the
same problem under R1 and R2. The registry finding is **cited with its date, not relied on**
(00_METHOD §2) — and it is independently plausible from §5.6.1's own numbers, since 83% publish
through `async_add_entities` and the registry row is what that path produces.

**The ownership rule (§6.10.3)** is authority the design grants ambiently that Chapter 5 never
states: first publisher of an entity id owns it; anyone else writing to it needs `entities.write`.
Without it an integration publishes `lock.front_door` and impersonates a lock. Chapter 4 does not
enumerate that path because it modelled a platform where entity publication is unmediated.

**Three failures, all exit 126 with no output** — resolve() following the venv symlink; the venv's
target being a symlink whose own target was unbound; the component not being where HA looks. Each
diagnosed by asking the sandbox what it could see. **Chapter 7 consequence: a compatibility
failure inside a sandbox is silent by default**, because the thing that would report it is the
thing that failed to start.

## §6.11.3 — the corpus, and the trigger firing

**The headline: 46% of the 37 most-installed community integrations import clean, with all their
entity platforms, inside a sandbox, unmodified.** 57% once their declared components are supplied.
First compatibility evidence in the project.

**The classification decision is the part to defend.** A missing Python module is *not*
automatically a packaging gap — HA installs a component's requirements when that component is set
up, so `dependencies: ["mqtt"]` is why `paho-mqtt` exists. In a minimal instance the module is
missing *because the component is*. The first version of this measurement classified it as
packaging, reported 17%, and could not test the trigger at all. Every dependency install
succeeded across all 37, so nothing in the result is packaging.

**`http` is the finding.** It blocks 10 of the 16 component failures; then mqtt (6), lovelace (4),
frontend and websocket_api (3 each). §5.6.3 built the instance with "no HTTP server" and 27% of
the corpus declares a dependency on it. So the open question is not "is R2 compatible" but **"can
a sandbox run `http`, and what does it cost"** — a far narrower thing to answer.

**The three undeclared-dependency cases are the sharpest illustration in the chapter.**
`battery_notes` imports `async_timeout`, `dreame_vacuum` `turbojpeg`, `dwd_weather` `numpy` —
none declared, none shipped by HA. They work in the wild only because *another* integration
installed the package into the shared environment. That class breaks under R2 however complete
the instance is: it is a cost of **isolation**, not of stripping, and worth separating for that
reason.

**§6.11.4 — the fourth correction to Chapter 5, and the first found by *running* rather than
building.** §5.6.5 lists footprint and compatibility as independent G3 triggers. They are
coupled: every component added to fix trigger 2 costs footprint, which is trigger 1. Arm B's peak
went 151 → 209 MB for four recovered integrations.

**Do not overstate the memory numbers.** `memory.peak` includes page cache; §6.3.2's 90 MB is PSS
at rest. Not comparable. They indicate direction. Say so before being asked.

**What G3 actually has to decide now** (Younes's call, and the measurement exists to make it
concrete): un-strip toward `http` and pay the footprint; or accept a 46–57% import-level ceiling
and report it honestly; or revert to R1 — which would get these components free by proxying, and
pay §5.6's original price of emulating a helper layer that **100%** of this corpus imports.

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

**"46% sounds low. Is your framework simply incompatible with Home Assistant?"** — 46% is
imports-clean against a *minimal* instance, and 43% of the corpus fails for one identifiable
reason: components the instance strips, `http` above all. Supplying declared components recovers
a quarter of those immediately. What the number cannot yet do is separate "confinement broke it"
from "it was broken anyway on this release", because there is no baseline arm — the same 37
against a full Home Assistant. That is Chapter 7's first task and I would not defend the figure
as a property of the design until it exists.

**"You ran one integration and you wrote it yourself. How is that a compatibility result?"** —
It is not, and §6.11.1 scores it as half. What it establishes is that the *mechanism* works on an
integration written in the idiom §5.6.1 measured as dominant, with its source untouched. What is
unevidenced is the population. The distinction matters because the two halves need different
work: the mechanism needed a component, and the population needs a corpus that
`figures/fetch_hacs_corpus.py` already fetches. That is Chapter 7's first task and it is now
unblocked.

**"You have built a security framework and never run a real integration through it. Isn't the
compatibility claim unevidenced?"** — Yes, and §6.10.2 says so in those words rather than
waiting to be asked. The security half is measured and the compatibility half is still an
argument; C1 is the constraint that makes the problem hard and it is exactly the one not yet
demonstrated. What the chapter does instead of hedging is name the single component that blocks
it, show that the same component tests the G3 trigger most likely to fire, and put both in the
plan. The alternative — reporting a percentage of "the framework" as complete — would have hidden
which half was missing.

**"Your adversary was written by you. What does it actually prove?"** — That the attacks
§5.8.2 names do not succeed, and nothing more; §6.9.5 says so. The one result that does not
depend on my imagination is the garbage-collector sweep, because it is *published* — Corno &
Mannella's attack, run unmodified, working exactly as they describe and finding nothing. The
rest is a demonstration until Chapter 7 adds the baseline arm, which is what makes the 2021
comparison a measurement.

**"Your audit log is described as tamper-evident. Evident to whom, and for how long?"** —
Within a run, to anyone with the mediator's key, against every attack in §6.8.2's table including
a full consistent rewrite. Across restarts, the MAC key is gone, so old records are
hash-verifiable only and a complete rewrite by someone with filesystem write access is no longer
detectable. Against the confined integration it is stronger than either, and for a reason that
has nothing to do with cryptography: §5.12.4's structural argument is that the sandbox has no
path to the log at all. The claim the architecture supports is "authoritative against the
confined integration, evidentiary against everything else", and §6.8.4 keeps it there.

**"Chapter 6 has now corrected Chapter 5 three times. Should I trust Chapter 5?"** — Trust its
measurements and audit its inferences, and the report now makes that separation visible rather
than asking for it. All three corrections (§6.3.2, §6.4.1, §6.6.6) were inferences written in the
register of results; no measurement has failed to replicate, and §5.6.3's marginal figure came
back to within 0.1 MB a day later from a different script. The corrections are in the report
with the wrong sentences left standing and pointers added, because a chain that shows where it
was wrong is worth more than one that was quietly tidied.

**"How do you know your negative tests are testing anything?"** — Because one of them was not,
and it is in the report (§6.6.5). Three path-rejection cases were passing through the wrong rule
entirely. The structural answer is that a default-deny system produces the safe answer for almost
any mistake, so a passing negative test is weak evidence by construction; the practice that
follows is asserting on the reason rather than the verdict, and Chapter 7's adversarial cases are
written that way.

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
