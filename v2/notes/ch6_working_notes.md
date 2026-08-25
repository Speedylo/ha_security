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
| 6.4 | The supervisor — where it must run (§6.4.1 ✅), namespaces, seccomp, distinct uid | 🔵 §6.4.1 drafted |
| 6.5 | The bridge and the channel | ⬜ |
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
