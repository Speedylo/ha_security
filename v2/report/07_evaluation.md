# Chapter 7 — Evaluation

## 7.1 The rule this chapter is written under

**Sections 7.1 to 7.11 were written on 2026-09-02, before any of the measurements they specify
had been run.** No result reported later in this chapter existed when its pass/fail criterion was
fixed. This is stated first, and dated, because it is the only thing that separates an evaluation
from a results section.

The reason is not procedural fastidiousness. Chapter 6 recorded two occasions on which a
prediction made before a measurement was wrong — §6.12.4 over-predicted the `declared` profile at
70–76% against an actual 57%, and §6.13.4 under-predicted the core-package profile — and in both
cases the wrongness was the finding. That only works if the prediction is on the record before the
number is. An evaluation whose criteria are written afterwards can always be satisfied, because
the criteria can always be chosen to fit; and an artifact that has passed criteria selected after
the fact has demonstrated nothing except its author's ingenuity in selecting them.

Three consequences follow, and they bind the rest of the chapter:

1. **Criteria fixed here are not revised in light of results.** If a criterion turns out to be
   badly chosen, it is reported as failed *and* the choice is criticised, in that order. §7.5 is
   frozen at the date above.
2. **Predictions are recorded in §7.6 before the runs.** Where the prediction is wrong, the
   chapter says so in the same paragraph as the result.
3. **Requirements that cannot be verified are declared unverifiable here**, in advance, rather
   than quietly omitted from the results. §7.5 has two such rows at the time of writing, and
   naming them before running anything is the difference between a stated scope limit and a gap
   a reader discovers.

`01_PLAN.md` Stage 4 committed to exactly this — *"methodology and pass/fail criteria written
before results are collected, and dated, so it is visibly not fitted to the outcome"* — and this
section is the discharge of that commitment.

## 7.2 What is being evaluated, and the claim under test

§5.15.6 states the design's central claim and concedes that it is empirical:

> Unmodified, pre-existing integrations can be confined at a cost worth paying.

That sentence contains three separable assertions, and the evaluation fails if it tests only the
comfortable one:

| | Assertion | Where it is tested |
|---|---|---|
| **A** | Confinement is *effective* — the threats Chapter 4 identified are controlled | §7.4.2, security |
| **B** | Confinement is *compatible* — real integrations still work, unmodified | §7.4.1, compatibility |
| **C** | Confinement is *affordable* — on the hardware C4 names | §7.4.3, performance |

Assertion B is the contribution nobody else has data for (§2.8, contribution 3), and it is also
the one most easily overstated, because import success is an upper bound on compatibility and
reads like a compatibility result. N2 exists to prevent exactly that conflation and this chapter
treats it as binding on the *reporting*, not only on the artifact.

**The evaluation is framed against a published threat model, not against criteria invented here.**
Thingnes and Meland's systematic review (§2.4.3) calls in its future-work section for "a
proof-of-concept implementation for Home Assistant … evaluated based on the threat model
introduced by Corno and Mannella". This chapter adopts that framing, and §4.14 already reserved
the task for it: *"Chapter 7 evaluates against it, so the relationship is stated here."*

The security axis is therefore scored **twice** — once against Chapter 4's own register of
eighteen threats, and once against Corno and Mannella's eleven (their T1–T11), using the mapping
column §4.8 supplies. The second scoring is the one an external reader can check without
accepting any of this project's own threat-identification work, and it is what makes the security
result a measurement against an external standard rather than against a bar this project set for
itself. Where the two scorings disagree, the disagreement is reported: §4.14 records that their
model is broader in consequence (their T8, physical damage, is out of reach here and retained
immediately) while this one is broader in mechanism, so a clean sweep of Chapter 4's register is
not a clean sweep of theirs.

## 7.3 The spine: Chapter 3's verification column

Chapter 3 §3.1 committed each requirement to a stated method of verification, written before any
implementation existed, precisely so that this chapter would not have to invent one:

> "The verification column is what Chapter 7's evaluation plan is built from, and writing it now —
> before any implementation exists — is what keeps the evaluation from being fitted to whatever
> the implementation turns out to do."

That column is therefore the spine of this chapter, and §7.5 is its discharge. Twenty
requirements exist: C1–C4, F1–F4, S1–S8, S9 (added by §4.10.1), and N1–N3. Every one appears in
§7.5 with a verdict, including the ones that cannot be verified. A requirement absent from that
table would be a requirement quietly dropped.

Two requirements are met by *reporting* rather than by the artifact — N2 and, in part, F4 — and
they are scored on whether this chapter does what they require, which is an unusual but honest
construction: N2 is a requirement on the evaluation (§3.6 says so explicitly), so the evaluation
is the thing that can fail it.

## 7.4 The four axes

`01_PLAN.md` Stage 4 names four axes. They are retained, but each is now tied to the requirements
it discharges rather than left as a heading.

### 7.4.1 Compatibility — C1, F1, F2, N2

**The question.** Of real, unmodified community integrations, how many still function under
confinement — and how much of any shortfall is the design's doing rather than the corpus's?

**The corpus.** Two corpora, answering two different questions, and the chapter reports both
because they are not interchangeable:

| Corpus | Selection | Question it answers | State |
|---|---|---|---|
| **Head-weighted** | Top 37 by install count | What most *installations* run | Fetched, four arms run (§6.11.3, §6.12, §6.13, §6.14) |
| **Uniform** | Random sample from the HACS index, same size | What most *integrations* do | Owed; `figures/fetch_hacs_corpus.py` takes it, only the selection changes |

Reporting only the first would describe user-facing impact while implying ecosystem coverage.
`notes/ch5_evidence_api_surface.md` §6 records the same limitation for the API-surface
measurement, and the same correction is owed here.

**The arms.** Four profiles have been measured against the confined instance (§6.14). The
measurement this axis turns on is the one that does not yet exist:

> **The baseline arm.** The same corpus, the same release (2026.8.3), the same host, against an
> **unmodified full Home Assistant** with no confinement. Its purpose is decomposition, not
> comparison for its own sake.

Without it, the 84% of §6.14.2 is a joint property of the corpus and the design and cannot be
separated into the two things a reader needs:

```
    failures(confined)  =  failures(baseline)          ← broken on 2026.8.3 regardless
                        +  failures(design)            ← the compatibility cost of confinement
```

Only the second term is this project's result. §6.14.3 already sets aside `eufy_security` on a
removed `device_tracker` constant, `hacs` on a release-build artifact and `spook` on a corpus
layout defect, arriving at 31/34 — 91%. **Setting those three aside is exactly what the baseline
arm exists to license**, and until it runs, 91% is asserted rather than measured. §6.14.6
concedes this in terms this chapter adopts unchanged.

**Two levels, never conflated (N2).** The chapter reports, separately and always in this order:

1. **Imports clean, all entity platforms exercised** — measured across four profiles; an upper
   bound on compatibility and labelled as one everywhere it appears.
2. **Executed end-to-end** — an integration set up through its own config flow, publishing live
   state through the mediator. §6.11.1 scores the population for this as **one**.

Level 2 requires configuration data only each integration's own config flow can produce, so it
does not scale to 37 and the chapter will not pretend otherwise. What it can do is report level 2
for a stated, small, named set and say how they were chosen — which is a defensible sample, where
a single unlabelled percentage would not be.

**C1 is verified mechanically, not asserted.** Zero source lines changed, counted by diffing each
integration's tree against the fetched original after the run. A claim that source was untouched
is worth nothing if the framework could have rewritten it.

### 7.4.2 Security — C3, S1–S9

**The question.** For each threat in Chapter 4's register, is the control claimed in §4.10
demonstrated, and does the demonstration establish what it claims?

**The method is per-threat, not aggregate, and it runs over both registers (§7.2).** A single "attacks blocked" figure is the security
equivalent of an unqualified compatibility percentage: §6.9 records 37 attempts of which 21 were
blocked, 9 succeeded and found nothing, 6 were denied and 1 was permitted, and *that
decomposition is the result*. An attempt that "succeeded and found nothing" is a stronger outcome
than one that was denied — it means the capability was not merely refused but structurally absent
(§5.6.2) — and an aggregate would erase the distinction.

**Two demonstrations require a paired baseline, and the pairing is the evidence:**

- **S8, the 2021 file-theft pattern.** §3.5 requires it be "reproduced against a baseline
  installation *and* shown to be blocked under the framework". Blocking an attack that would not
  have worked anyway proves nothing, so the unconfined arm is not optional. This is the single
  strongest result available to the project (`01_PLAN.md` Stage 4) and it is only strong in pairs.
- **S3, undeclared entity reads and subscriptions.** §3.5 requires "a paired baseline measuring
  what is readable without the framework" — the point being to quantify what was reachable
  before, not merely to show it is unreachable now.

**Negative cases must assert on the reason, never the verdict (§6.6.5).** A default-deny system
produces the safe answer for almost any mistake, including mistakes in the test, so a passing
negative test is weak evidence by construction. §6.6.5 records three path-rejection cases that
passed through the wrong rule entirely. Every negative case in this chapter therefore asserts on
*which clause* refused it, and a case that cannot name the clause is reported as inconclusive
rather than as a pass.

**Absence is ambiguous and the chapter must not read it as success (§6.4.5).** §5.6.2's
structural denial uses absence to mean "not granted", so any defect producing an absence is
indistinguishable from the framework working. Three such defects arose during implementation and
all three presented as absence. Every grant is therefore verified to have *arrived* before the
sandbox is allowed to run, and a compatibility failure where an integration cannot find a
declared file is not charged to confinement until the grant is shown to have been delivered.

**C3 requires a hostile manifest, not a hostile integration.** §3.3 names three cases — a manifest
that is absent, one that is over-broad, and one deliberately mismatched to the integration's
actual behaviour — and all three must appear, because C3 is the requirement that the mechanism
does not presuppose an honest author.

### 7.4.3 Performance — C4, N1, S9

**The question.** What does confinement cost on the C4 device, and does the cost change how the
platform can be used?

`01_PLAN.md` recorded this axis as having "nothing". It now has five measurements
(`experiments/`), and what remains is scale.

| Measure | State | What is owed |
|---|---|---|
| Per-sandbox memory (PSS) | §6.3.2, §6.14 — budget 26 integrations, +19.1 MB premium | PSS as a function of what is *declared*, over the corpus's real declaration distribution (12 of 37 declare nothing; median 2) |
| Mediation latency | §5.11.4, §6.5.3 — 30.0 µs median, p99 33.9 µs | **Latency at realistic sandbox counts.** Two clients moved p99 by **85%**; the budget is 26, and two says nothing about twenty-six |
| Durability cost | Not measured | Whether `fsync` per decision is affordable (§6.8.3). §5.11.3's ordering guarantee is only real if the record is durable *before* the action, and that costs far more than the 2.4 µs decision |
| Resource limits (S9) | §6.4.1, host probe — cap verified to bite, unprivileged | What `resources.memory_mb` costs a **legitimate** integration (§6.9.4): cgroup v2 charges page cache, so the limit bounds file reading too |

**No threshold is asserted in advance for N1, and this is not a dodge.** §3.6 fixed that position
before any implementation existed: *"No threshold is asserted in advance; the figures are reported
and discussed."* A latency budget invented now would be chosen with knowledge of the measured
30 µs, which is precisely the fitting this chapter exists to avoid. What *is* fixed in advance is
the comparison — every figure is reported against an unconfined baseline on the same host — and
the discussion criterion: whether the figures change what a user can run, judged against §5.8.1's
measured mean of 4.02 integrations per installation.

**S9's boot-time precondition is stated whenever S9 is evaluated.** The Pi 5's firmware prepends
`cgroup_disable=memory` and the memory controller is absent on a stock Pi OS install; it was
enabled by appending to `/boot/firmware/cmdline.txt` on 2026-08-25 (§5.7.4, §6.4.1). Evaluating
S9 on a machine where that was quietly fixed, without saying so, is the dishonest version of this
result, and the framework's own preflight refuses to start when the controller is missing (N3).

### 7.4.4 Coverage — F3, F4, N3, and the honest table

**The question.** What is supported, what is not, and what does the evaluation itself not
establish?

This axis produces a supported/unsupported table with the measurement's own limits stated, and
three specific obligations:

- **F3 — every enforcement decision attributable to a manifest clause.** Verified by requiring
  each decision record to carry a clause pointer (`confine/manifest.py`), and by checking that a
  decision with no attributable clause is impossible rather than merely unobserved.
- **F4 — the declaration presentable before installation.** Discharged in §6.7 by
  `confine/describe.py`, which renders four states and shows denials at the same weight as grants.
  §3.4 explicitly bounds F4 to *availability* of the information; user comprehension is a
  human-factors question excluded in §3.7 and is not evaluated here.
- **N3 — a stated failure mode, not a silent one.** Behaviour on mediator unavailability is
  specified and tested. §6.4.1 supplies the case that makes this concrete: the supervisor must
  detect that it is in the wrong cgroup position at startup and refuse, because `mkdir` succeeds
  from the wrong position and everything looks right until placement silently fails.

## 7.5 Pass/fail criteria, fixed in advance

Frozen 2026-09-02. Each row states the criterion, not the expected outcome. "Blocked" means the
requirement cannot be verified with the artifact as it stands, and the reason is given.

| Req | Criterion — the requirement passes if… | Verdict source |
|---|---|---|
| **C1** | Every integration in the compatibility runs shows a **zero-line** diff against its fetched original, counted mechanically after the run | Compatibility |
| **C2** | Every arm runs against an unmodified official Home Assistant release, version recorded in the result file | All arms |
| **C3** | The adversarial run includes an absent manifest, an over-broad manifest, and one deliberately mismatched to behaviour — and all three are handled per §5.9's precedence rules | Security |
| **C4** | Every performance figure is produced on the Raspberry Pi 5, reporting per-integration memory *and* added latency | Performance |
| **F1** | A confined integration's entities are present in Home Assistant and behave as native entities under the measures used in this chapter | Compatibility, level 2 |
| **F2** | An integration polling a **declared** remote API completes successfully while confined | ⛔ **Blocked — the egress proxy does not exist** (§6.11.1 scope item 2). Reported as unverified, not omitted |
| **F3** | Every enforcement decision in the evaluation names the manifest clause that produced it; a decision with no attributable clause is shown to be unconstructible | Security |
| **F4** | The manifest of each evaluated integration renders in human-readable form, with denials shown at the same weight as grants | §6.7, re-run over the evaluated set |
| **S1** | The published garbage-collector technique (§2.4.1) is attempted from inside the sandbox and reaches no platform object; the mediator and its credential are not locatable from within | Security |
| **S2** | No platform credential is recoverable from the sandbox's environment, filesystem, process table or memory | Security |
| **S3** | A confined integration is denied both a **read** and a **subscription** to undeclared entities, each refusal naming its clause, **against a paired unconfined baseline** quantifying what is readable without the framework | Security |
| **S4** | An integration is denied a host declared only by a *different* integration | ⛔ **Blocked — no egress path exists.** Attribution alone is measured (§6.5.2); attribution without enforcement does not satisfy S4 |
| **S5** | A manifest permitting `lock.lock` is shown not to permit `lock.unlock`, and the refusal is structural rather than a check | §6.10.1 — re-verified in the evaluation run |
| **S6** | An integration with **no** manifest and one with an **unparseable** manifest are each denied all mediated capability, each refusal naming its rule | Security |
| **S7** | Decisions appear in the log bearing the integration's three-part identity, and modification, deletion **and reordering** are each independently detectable by both the hash chain and the keyed MAC chain | §6.8 — re-verified |
| **S8** | The 2021 file-theft pattern **succeeds against an unconfined baseline installation** and is blocked under the framework, on the same host and release | Security — **requires the baseline arm** |
| **S9** | An integration deliberately exhausting CPU, memory and disk in turn does not render the gateway unresponsive, demonstrated unprivileged, with the boot-time precondition stated | ⚠ **Partially met — see §7.21.1.** Memory and processes are enforced but from harness configuration, not from the manifest; `cpu_percent` is validated, shown to the user and **not enforced**; disk is absent entirely |
| **N1** | Added latency, per-integration memory and maximum concurrent integrations are all reported against an unconfined baseline on the target hardware. **No threshold** — §3.6 fixed this position in advance | Performance |
| **N2** | This chapter reports "imports clean" and "executed end-to-end" as two separate numbers, never conflated, with the first labelled an upper bound wherever it appears | **This chapter** |
| **N3** | Behaviour on mediator unavailability is specified in advance and tested; the framework refuses rather than degrades silently, including the wrong-cgroup-position case | Security |

**Two blocked rows, named on 2026-09-02 rather than discovered in November.** F2 and S4 both
depend on §5.8.2's scope item 2, which §6.11.1 scores as *"Half. Egress does not exist."* This is
the chapter's most consequential statement about its own limits, and it is deliberately placed in
the criteria table rather than in a limitations section at the end: a requirements register that
does not match the artifact is the first thing an auditor reconciles, and burying it later would
not survive that reconciliation. **If the egress proxy is built, both rows become verifiable and
T08, T10 and T11 acquire demonstrated controls; if it is not, Chapter 8 reports two of twenty
requirements as unverified and says why.** Either outcome is defensible. Silence is not.

## 7.6 Predictions recorded before the measurements run

Written 2026-09-02, before any run. Where a prediction is wrong, the chapter reports the error in
the same paragraph as the result, as §6.13 did for §6.12.4.

**P1 — The baseline arm.** A full, unconfined Home Assistant on 2026.8.3 will supply every
component the corpus declares, and `stream`'s requirements bring `numpy` and `turbojpeg`, so all
sixteen component failures and both package-spillover classes should resolve. Three failures
should persist because they are not the design's: `eufy_security` (`SOURCE_TYPE_GPS` removed from
`device_tracker` on this release), `hacs` (frontend bundled at release-build time and absent from
a source checkout), `spook` (corpus directory layout). **Predicted baseline: 34/37.**

**P2 — `aiofiles` is the discriminating case, and the prediction is uncertain on purpose.**
`homeassistant/package_constraints.txt` *constrains* `aiofiles>=24.1.0` but constraining is not
requiring, and no component in `default_config` requires it — only `matrix` and `slack` do. So a
stock full installation may or may not have it. **If the baseline also fails on `aiofiles`, the
design's compatibility cost is zero integrations out of 37** and 84% is entirely a property of
the corpus and the release. **If the baseline passes them, the cost is three**, and §6.14.4's
argument about undeclared packages is the explanation. The prediction is that it will **pass**
them, on the grounds that the constraint pin exists precisely because these packages are present
in real installations often enough to be downgraded — but this is the weakest prediction here and
is recorded as such.

**P3 — Decomposition.** Following P1 and P2, the compatibility cost attributable to confinement is
predicted at **0 to 3 integrations of 37 — 0 to 8 percentage points** — and the headline result of
this chapter is that difference, not the 84%.

**P4 — Latency at scale.** Two clients moved p99 by 85% (§6.5.3), which was queueing rather than
work. If the mediator serialises, p99 at 26 sandboxes will degrade super-linearly and N1's
discussion criterion will turn on whether the median stays flat while the tail does not.
Prediction: **median within 2× of the single-client figure, p99 an order of magnitude worse.**

**P5 — S9's cost to a legitimate integration.** Because cgroup v2 charges page cache to the
cgroup, an integration reading a file larger than its memory limit will be OOM-killed while doing
something entirely legitimate (§6.9.4). Prediction: **this is reproducible and is a genuine
usability cost of S9**, not a theoretical one, and Chapter 8 owes it as a limitation.

## 7.7 What would falsify the central claim

Stated in advance, because a claim with no falsifier is not empirical regardless of how much
measurement surrounds it.

| Assertion (§7.2) | Falsified if… |
|---|---|
| **A — effective** | The garbage-collector technique reaches a platform object, *or* a platform credential is recoverable from the sandbox, *or* the 2021 pattern succeeds under the framework. Any one is fatal to S1/S2/S8 and to the architecture, not merely to the implementation |
| **B — compatible** | The baseline arm shows that most of the confined shortfall is the design's — i.e. the baseline passes substantially all 37 while the confined arms pass 31. That would make confinement, not the corpus, the cause, and would reopen G3 |
| **C — affordable** | Per-sandbox cost puts the budget below §5.8.1's measured mean of 4.02 integrations per installation, *or* mediation latency at realistic sandbox counts changes what the platform can do. **The mean is the wrong statistic and §5.8.1 says so** — the telemetry gives per-integration install counts but not the spread across installations, so a budget comfortably above the mean may still fail the tail. The falsifier is stated against the mean because that is the only figure the data supports, and the limitation is carried with it |

**A fourth falsifier applies to the chapter rather than the artifact.** If the evaluation cannot
demonstrate a requirement and reports it as passed anyway, or reports an aggregate that conceals
a decomposition it possesses, the evaluation has failed on its own terms — and N2 makes that a
requirement failure, not a stylistic one.

## 7.8 Obligations this chapter inherits

Recorded across Chapters 5 and 6 and consolidated here so that none is discharged by being
forgotten. The right-hand column is where each is answered.

| Owed from | Obligation | Discharged in |
|---|---|---|
| §6.14.6 | Run the baseline arm before any compatibility figure is treated as a property of the design | §7.4.1 |
| §6.3.3 | Check every compatibility failure against the minimal instance **before** charging it to the design — the `async_at_start` defect was silent | §7.4.1, §7.9 |
| §6.6.5 | Negative cases assert on **why** something was refused, never that it was | §7.4.2 |
| §6.4.5 | An absence is not evidence of confinement working until the grant is shown to have arrived | §7.4.2 |
| §6.5.3 | Measure mediation latency at realistic sandbox counts | §7.4.3, P4 |
| §6.8.3 | Decide whether `fsync` per decision is affordable | §7.4.3 |
| §6.9.4 | Measure what `resources.memory_mb` costs a *legitimate* integration | §7.4.3, P5 |
| §5.7.4, §6.4.1 | State S9's boot-time precondition whenever S9 is evaluated | §7.4.3 |
| §5.14, `notes/ch5_evidence_api_surface.md` §6 | Re-run on a uniform corpus before reporting coverage | §7.4.1 |
| §3.6 (N2) | Report imports-clean and executed-end-to-end separately, always | §7.4.1, §7.5 |
| §6.6.6 | *Withdrawn.* The obligation never to repeat §4.10's "filesystem isolation to declared resources" rested on a §5.14.4 claim that contradicts §5.10.3; the phrase is accurate | — |

## 7.9 Threats to the validity of this evaluation

The evaluation is itself an artifact and has failure modes. Stated here, before results, so that
they are not read as excuses afterwards.

**Construct validity — is "imports clean" measuring compatibility?** No, and the chapter says so
wherever the number appears. It is an upper bound: an integration that imports may still fail at
setup, at first poll, or on its first device interaction. N2 exists because this specific
substitution is the easiest one to make and the hardest to notice.

**Internal validity — is the minimal instance itself sound?** Not entirely, and this is the most
dangerous known defect. §6.3.3 records that `build_minimal_hass` reached the running state via
`set_state(CoreState.running)`, which never fires `EVENT_HOMEASSISTANT_START` and silently split
deferred callbacks — losing state restoration with no exception and no log line. The fix
(`await hass.async_start()` last) is present in `framework/confine/sandbox_runtime.py` and in
`experiments/base_component/measure_base.py`, but **`experiments/r2_footprint/measure.py` still
carries the original recipe**, so §5.6.3's 176/136 MB figures were produced by the unfixed
builder. Whether that matters for a proportional-set-size measurement is plausible but unverified,
and this chapter must either re-run that measurement or state the caveat where the figure is used.

**Internal validity — the comparison arms must differ in one thing.** The baseline arm must hold
release, host, Python version and corpus fixed and vary only confinement. Any additional
difference makes the decomposition in §7.4.1 unsound.

**External validity — one release, one host, one architecture.** Home Assistant 2026.8.3, Python
3.14.7, aarch64, Raspberry Pi 5, 4 GB. §4.12's review triggers already record that the platform
changes underneath this model; `eufy_security` failing on a constant removed in this very release
is a live demonstration that a compatibility figure has a shelf life.

**External validity — corpus selection.** The head-weighted corpus describes what most
installations run. §7.4.1 owes the uniform sample for the other question, and neither number
generalises to integrations outside HACS.

**Conclusion validity — a default-deny system passes negative tests for the wrong reasons.**
§6.6.5 is the general form and §7.4.2 the response. This is the failure mode most likely to
produce a falsely favourable security result.

**Conclusion validity — n is small where it matters most.** Level-2 compatibility has a population
of one at the time of writing. Whatever it grows to, it will not be 37, and the chapter reports it
as a named set rather than a rate.

## 7.10 The measurement schedule

Order chosen so that each run's result is interpretable when it lands. Costs are engineering time,
not calendar.

| # | Measurement | Blocks | Cost |
|---|---|---|---|
| 1 | **Baseline arm** — 37 against unconfined full HA, same release and host | Every compatibility claim; S8's pairing | New profile in `confine/compat.py`, then ~30 min mostly waiting |
| 2 | **S8 and S3 paired baselines** — the 2021 pattern and undeclared reads, unconfined | The two strongest security results | Small; reuses arm 1's instance |
| 3 | **Latency at 4, 8, 16, 26 sandboxes** | N1's discussion; P4 | Extends `experiments/mediation_latency/` |
| 4 | **PSS against the declaration distribution** | The budget curve; N1 | `experiments/unstrip/scale.py` at two or three points |
| 5 | **`fsync`-per-decision cost** | §6.8.3's open question | Small |
| 6 | **S9's cost to a legitimate integration** | P5; Chapter 8's limitation | Small |
| 7 | **Uniform-sample corpus re-run** | Coverage generalisation | Selection change plus one run |
| 8 | *(conditional)* **Egress proxy, then F2 and S4** | The two blocked rows in §7.5 | Only if scope item 2 is built |

## 7.11 What this chapter cannot do

Four things, named now rather than conceded later.

1. **It cannot show the manifest is honest or minimal.** R1 and R2 are structural residual risks
   (§4.11) and §3.7 excludes the underlying question. The claim is that invisible authority
   becomes declared, bounded and audited authority — which is smaller than "confinement makes
   integrations safe", and is the claim the evaluation is scoped to.
2. **It cannot make the audit log authoritative.** R4: tamper-evidence is not tamper-proofing, and
   §6.9.4 adds a sharper point the evaluation must record — an OOM kill leaves a corpse and no
   record of what was attempted, so the audit trail is weakest exactly where the control is
   strongest.
3. **It cannot evaluate the mediator's own credential scope.** R3 is an upstream platform
   limitation: Home Assistant issues no read-only or per-domain token, so the mediator holds full
   authority in order to mediate at all. This is reported, not solved, and §4.12 names scoped
   tokens as the trigger that would change it.
4. **It cannot claim generality beyond what it measured.** One platform, one release, one host,
   two corpora of 37. Chapter 8 states the boundary; this chapter's job is to make sure every
   number inside it carries its own qualification.

---

# Results

## 7.12 The baseline arm, and what 84% actually was

**Run 2026-09-02**, after §7.1–§7.11 were written and with the criteria and predictions above
already fixed. `experiments/compat/`, `--profile baseline`.

### 7.12.1 The measurement

The same 37 community integrations, the same corpus directories, the same release (2026.8.3),
the same interpreter (Python 3.14.7) and the same host (the C4 device), against a **full,
unconfined** Home Assistant. `confine/baseline_runtime.py` is the arm; what it omits is the whole
of the confinement — no namespaces, no seccomp, no cgroup, no mount view, no mediator and no
bridge — and that omission is the only independent variable.

Two construction decisions carry the validity of the comparison and both are recorded because
either could have produced a flattering number by accident.

**The measurement function is shared, not copied.** `inspect()` is imported from
`sandbox_runtime.py` and called with the same arguments, so both arms compute *not_found →
import_failed → imports_clean → platform_import_failed → platforms_clean* with the same platform
list and the same error handling. §7.9 required the measurement be held fixed; a reimplementation
that drifted by one platform name would have satisfied that requirement in appearance only.

**The baseline's bias runs toward the baseline, deliberately.** The base `homeassistant`
component — dropped from the sandbox in §6.3.2 — is set up here; `default_config` is set up, the
same definition of "stock" from which §6.13.4's core package set is computed; the integration's
declared components are set up and their requirements installed; the core package set is present.
A generous baseline makes the design's measured cost *larger*, which is the direction an
evaluation of one's own artifact should err in.

**The first version of this arm was biased the other way, and the correction is the reason to
trust the second.** It set up `homeassistant` and `default_config` only. `default_config` does
not contain `mqtt`, so `alarmo` — which declares it — failed against the "full" instance while
passing under confinement. A baseline stingier than the arm it is compared against does not
decompose a figure; it inverts it, and it would have reported a *negative* cost for confinement.

### 7.12.2 The result

| | Baseline — full, unconfined | Confined — `declared` + core packages |
|---|---|---|
| **Imports clean, all entity platforms** | **31/37 — 84%** | **31/37 — 84%** |
| Components loaded in the instance | median **52** | median **2** |
| Peak memory | median 291 MB, max 365 MB (RSS) | median 119.7 MB (cgroup peak) |

The two arms fail on **the same six integrations**, and the failure reasons are identical — in
four of six cases byte for byte, including the truncated exception text:

| Integration | Failure, both arms |
|---|---|
| `bambu_lab`, `bermuda`, `tapo_control` | `ModuleNotFoundError: No module named 'aiofiles'` |
| `eufy_security` | `ImportError: cannot import name 'SOURCE_TYPE_GPS' from 'homeassistant.components.device_tracker'` |
| `hacs` | `ModuleNotFoundError: No module named 'custom_components.hacs.hacs_frontend'` |
| `spook` | `IntegrationNotFound: Integration 'spook' not found.` |

So the decomposition §7.4.1 was built to perform returns zero:

```
    failures(confined) = failures(baseline) + failures(design)
          6            =        6           +        0
```

**The import-level compatibility cost of confinement, on this corpus, on this release, is zero
integrations of thirty-seven.** No integration passes unconfined and fails confined, and the set
difference is empty in both directions.

**This changes what the headline number means, and the change is a demotion of the number in
favour of the finding.** 84% was never a statement about confinement. It is the fraction of the
most-installed community integrations that import cleanly on Home Assistant 2026.8.3 *at all* —
a property of the corpus and the release — and confinement moves it by nothing. The result worth
reporting is the difference, and the difference is zero.

### 7.12.3 The predictions, scored

§7.6 was fixed before the run. Two of its three compatibility predictions were wrong.

| | Prediction | Actual | |
|---|---|---|---|
| **P1** | Baseline 34/37 | **31/37** | ✗ wrong |
| **P2** | The baseline *passes* the three `aiofiles` integrations | It fails all three | ✗ wrong |
| **P3** | Confinement's cost is 0–3 integrations, 0–8 points | **0 integrations, 0 points** | ✓ correct, at the floor |

**P2 is the one that mattered and it was wrong for an interesting reason.** The prediction rested
on `homeassistant/package_constraints.txt` pinning `aiofiles>=24.1.0` with the comment *"aiofiles
keeps getting downgraded by custom components"* — reasoning that a package upstream bothers to
constrain must be present in real installations. It is not:

```
ha314/lib/python3.14/site-packages/aiofiles*   -> absent
platform-deps/aiofiles*                        -> absent
```

A stock `pip install homeassistant` on 2026.8.3 does not provide `aiofiles`, and neither does the
`default_config` closure. **A constraint is not an installation** — upstream is pinning the
version *in case* a custom component installs it, which is a defence against the ecosystem's
behaviour rather than evidence of the platform's own. The constraint carries an issue reference,
`home-assistant/core#118004`, which is a citable upstream acknowledgement of exactly the problem
§6.14.4 describes.

This strengthens §6.14.4 rather than qualifying it. That section argued that "the author would
simply declare it" is an assumption the evidence contradicts; the baseline adds that these three
integrations **do not work on an ordinary unconfined installation either**. They were already
broken. Confinement is not what breaks them, and the design is charged nothing for them.

### 7.12.4 What this licenses, and what it does not

**Licensed.** §6.14.3 set aside `eufy_security` as a release incompatibility and `hacs` and
`spook` as corpus artifacts, arriving at 31/34 — 91% — and conceded in the same paragraph that
"setting them aside is what the baseline arm exists to justify". It is now justified: all three
fail unconfined for the same reasons. The `aiofiles` three may be set aside on the same evidence,
which §6.14.3 did not claim and could not have. On what the corpus delivered in a state that
loads on this release at all, **confinement costs nothing**.

**Not licensed, and the first is the one most likely to be over-read.**

- **Both arms measure imports, not execution.** N2 requires the two numbers be reported
  separately and never conflated; the executed-end-to-end population is still one (§6.11.1).
  *Zero import-level compatibility cost* is not *zero compatibility cost*, and this chapter
  attaches the qualifier every time the figure appears.
- **One corpus, head-weighted.** §7.4.1's uniform sample is still owed and this result does not
  substitute for it.
- **One release, one host, one architecture.** `eufy_security` failing on a constant removed in
  this very release demonstrates the shelf life directly.
- **The memory columns are not comparable and are not compared.** The baseline figure is process
  RSS; the confined figure is the cgroup's `memory.peak`, which includes page cache. §6.11.3
  records the same caution. Both are reported because omitting one would be worse, and neither
  supports a per-sandbox overhead claim — that is §6.3.2's PSS measurement, not this one.

### 7.12.5 An unpredicted finding, and Chapter 8 should have it

The baseline instance loads a **median of 52 components**. The confined sandbox sets up a
**median of 2** — twelve of the 37 declare none at all (§6.13). The two reach identical
import-level compatibility.

Whatever the other fifty components do for a stock installation, the most-installed community
integrations do not need them in order to load. This is a measured statement about how much of
Home Assistant an integration actually touches, and it bears directly on §5.6's R2 decision:
stripping the platform to what an integration declares is not a compromise that costs
compatibility, on this evidence it costs none. It also sharpens §6.14.5's honesty cost — the
sandbox carries 641 MB of packages no integration declared, but it carries fifty fewer
*components*, and components are where capability lives.

### 7.12.6 What this arm does not discharge

S8's criterion in §7.5 requires the 2021 file-theft pattern to **succeed against an unconfined
baseline** and be blocked under the framework. This arm supplies the unconfined instance but not
the attack; §7.10's second item is unchanged and remains owed before the security axis can be
reported.

## 7.13 S8's paired baseline — the 2021 pattern, with and without the framework

**Run 2026-09-02**, `experiments/adversary_baseline/`. §7.5's criterion for S8 was fixed before
any of this ran, and it is not "the attack is blocked":

> The 2021 file-theft pattern **succeeds against an unconfined baseline installation** and is
> blocked under the framework, on the same host and release.

### 7.13.1 Method

A deliberately hostile integration, and a configuration directory holding two canary strings —
one in `secrets.yaml`, one in `.storage/core.config_entries`. The integration attempts
thirty-eight attacks. **The identical attack payload runs twice**: once as an ordinary process
with the invoking user's authority, which is what §5.2 establishes an integration has today, and
once inside a sandbox. `ATTACKS`, both canaries and the configuration layout are imported from
`selftest_adversary` rather than copied, on the same reasoning as §7.12.1.

**The unconfined arm's verdict is inverted, and that is the point.** It passes when the canaries
leak. An attack that cannot steal `secrets.yaml` from an ordinary process proves nothing when it
is blocked from a sandbox, so a green light there is what licenses the green light here.

### 7.13.2 Result

| | Unconfined | Confined |
|---|---|---|
| **Canaries recovered** | **2 of 2** | **0 of 2** |
| Attacks that returned data | 11 | 0 |
| 2021 traversals that worked | **5** | 0 |
| Outcome counts | BLOCKED 14 · EMPTY 4 · **LEAKED 11** · NOT RUN 2 · UNMEDIATED 1 | BLOCKED 21 · EMPTY 10 · DENY 6 · PERMIT 1 |
| Verdict | **PASS** — the pattern reproduces | **PASS** — neither canary reached it |

`open("../../secrets.yaml")` returns the credential unconfined and raises **`FileNotFoundError`**
confined. Not `PermissionError`: the file was never in the sandbox's mount namespace, so no
request was refused and nothing had to decide. §5.6.2's structural denial, in an error code.

**An incidental result, and it is S7's.** Unconfined, the audit-log search found a real audit log
on the host — `.../spike/audit/…jsonl`. An attacker that reaches the framework's own records can
rewrite what §5.12 relies on. Confined the same search returns `EMPTY`. This was not a planned
measurement and it belongs in Chapter 8's discussion of R4.

### 7.13.3 What only the pairing could show, including against the design

**Three attacks are blocked in both arms and are therefore not this framework's doing:**

| Attack | Why it fails unconfined |
|---|---|
| `read /etc/shadow` | Root-only. The operating system, not the design |
| `connect to 127.0.0.1:8123` | Nothing was listening |
| `resolve example.invalid` | The name does not exist |

Reported alone, the confined run credits the framework with three controls it does not provide.
This is exactly the substitution §3.5 wrote the paired requirement to prevent, and it is the
clearest argument in this chapter for why a baseline is not a formality.

**Two attacks succeed unconfined and are refused confined, and those are the design's:**
`unshare(CLONE_NEWUSER)` and `ptrace(PTRACE_TRACEME)` both return `True` unconfined and
`PermissionError` confined. That is seccomp (§5.7.3), and it is a measured delta rather than an
asserted one.

**And the mediated family does not exist unconfined.** It reports `UNMEDIATED` — *"no mediator
exists; this process acts directly and asks no one."* An unconfined integration is not denied
`lock.unlock`; there is nobody to ask. Confined, all six undeclared operations are denied and
each names the manifest clause that refused it (`/permissions/services/call`), which is F3
discharged by behaviour.

### 7.13.4 Two corrections to §6.9, and one withdrawn

**Correction 1 — `/dev/zero`, and it stands.** The filesystem sweep called `os.path.getsize()`
and read anything reported as small. A character device reports zero, so the attack opened
`/dev/zero`, read an infinite stream, and was killed for memory. §6.9 recorded
`BLOCKED — stopped by signal 9` and read it as the resource limit stopping a search for secrets.
The verdict was right and the reason was wrong: the process died reading a device node. Restricted
to regular files, the sweep **completes and finds nothing** — `EMPTY`, which the suite's own
vocabulary ranks above `BLOCKED` because the attack ran to completion and there was nothing there.

**Correction 2 — the counts.** For §6.9's original thirty-seven attacks, *21 blocked / 9 empty*
becomes **20 blocked / 10 empty**. One attack moved, and it moved to the stronger column.

**Withdrawn — S9's evidence was never in doubt.** An intermediate version of this work reported
that the unbounded read no longer reached the memory cap, and inferred that §6.9's S9
demonstration was invalid. **That inference was wrong, and its cause is worth recording because
it is the same failure a third time.** The harness had been hardened to kill a child that
overstayed, and in doing so it stopped distinguishing *the kernel killed this child* from *the
harness ran out of patience* — collapsing an OOM kill into a timeout. With the distinction
restored, the unbounded read is killed by the cgroup exactly as §6.9 reported. The sandbox binds
the interpreter trees and the `homeassistant` library read-only, which is ample data to exhaust
512 MB when held in memory.

**S9 nonetheless gains a second demonstration, because the first is incidental.** Whether a
file-reading attack reaches the cap depends on how much happens to be bound into the sandbox,
which is a property of the configuration rather than of the control. A new attack allocates
memory directly — an integration that wants to exhaust memory asks for memory rather than hunting
for large files — and it is OOM-killed by the cgroup as well. Both now demonstrate S9, and only
the second does so independently of what the sandbox contains.

### 7.13.5 What the harness had to learn, and why it is a result

The unconfined arm hung three times, for fifteen minutes each, reporting nothing. The cause is
worth stating because it is not a testing anecdote:

> **`PTRACE_TRACEME` succeeds unconfined.** From that moment the process is a tracee, and every
> subsequent signal — including the `SIGCHLD` from the attack's own forked children — stops it
> indefinitely for a tracer that will never answer.

The harness had always trusted a forked child to finish and to die. That assumption held for the
entire history of this suite, because **confined, seccomp refuses the call**. The harness was
fragile only where the attacks succeed, and the only arm where they succeed had never been run.
It now waits on `select`, kills what overstays, and reports `UNFINISHED` as an outcome in its own
right — because an attack that ran out of time was not refused by anything, and recording it as
`BLOCKED` is the same error as correction 1.

### 7.13.6 What this does not establish

- **One hostile integration, written here.** It exercises the *pattern* of the 2021 disclosures —
  traversal to `secrets.yaml` and the config-entry store — not the eight disclosed integrations,
  whose vulnerable versions are not in the corpus.
- **The unconfined arm is a process with the user's authority, not a running Home Assistant.**
  That is faithful to §5.2's finding about where integrations execute, and it is not the same as
  reproducing the flaw inside a live instance.
- **Two attacks were not run unconfined**, both by design and both recorded as `NOT RUN` rather
  than omitted: the unbounded read and the memory allocation. Nothing would bound either on the
  host, and T16 is not in dispute.
- **S3's paired baseline is still owed.** §7.5 requires a paired measurement of what is readable
  *without* the framework, and that needs a running instance with entities. It is next.

## 7.14 S3's paired baseline — the surveillance the framework removes

**Run 2026-09-02**, `experiments/entity_visibility/`. §7.5's criterion required a confined
integration to be denied both a **read** and a **subscription** to undeclared entities, each
naming its clause, *against a paired baseline quantifying what is readable without the framework*.

### 7.14.1 Why the pair, and why the sensitive subset is counted separately

§3.5 derives S3 from §1.7's Table 1.2, whose first row is entity states, on the grounds that
*"a design mediating only state changes would leave surveillance untouched, which is the
majority of the privacy harm."* A refusal count alone cannot speak to that. What can is the
size of what an integration otherwise holds.

`confine/home.py` furnishes both arms with the same 36-entity home, of which **20 disclose
occupancy, presence or routine** — device trackers, `person` entities, motion and occupancy
sensors, door and lock states, the alarm panel, bed presence, media state, the family calendar.
The subset is counted on its own because *"20 of 36 entities readable"* and *"every presence
sensor in the house readable"* are the same fact at very different weights, and only the second
is the one Chapter 1 is about.

The integration under test declares one entity: an outdoor temperature reading.

### 7.14.2 Result

| | Unconfined | Confined |
|---|---|---|
| **Entities present to it** | **36 / 36** | **1 / 36** |
| **Of those, occupancy or presence** | **20 / 20** | **0 / 20** |
| Changes by other integrations delivered | 4 / 4 | none — §7.14.4 |

Every undeclared probe — a phone's location, bedroom occupancy, the front door lock, the alarm
panel, the family calendar — is **absent** from the confined integration's state machine, and
every mediated read and subscription for it is refused naming `/permissions/entities/read`. The
one entity it declared is present and readable.

**The unconfined baseline is a single line, and that is the result rather than a shortcut:**

```python
hass.states.async_all()      # every state in the house, unasked, by any integration
```

No permission is consulted because none exists to consult. §1.8's "the user cannot see what an
integration intends to access" is the same fact stated from the other side.

### 7.14.3 Two mechanisms, and the report does not merge them

- **Absent, not refused.** An undeclared entity is not in the sandbox's state machine, so the
  integration reads `None` rather than being denied. Nothing decided; there was nothing to
  decide. This is §5.6.2 on the read path, and it is why §5.11.1 can put entity reads of *its
  own* mirrored state at zero marginal cost.
- **Refused, with a clause.** What the integration asks the *mediator* for is a decision, and
  every denial carries the manifest clause that produced it — F3 discharged by behaviour rather
  than by inspection, and §6.6.5's rule satisfied: each negative case names the rule that
  refused it, not merely that something did.

### 7.14.4 The limit, stated because the figure would otherwise overstate it

**The subscription half is verified at the decision layer only.** Unconfined, all four changes
to entities the integration does not own arrive through `EVENT_STATE_CHANGED`, unasked and
unfiltered. Confined, none arrive — but **that is an absent feature, not a demonstrated filter.**
§6.11.2 records that no push loop exists: declared entities are mirrored once at construction,
so there is no path by which any state change could arrive, filtered or otherwise.

What is demonstrated: `entity.subscribe` on an undeclared entity is refused with a clause.
What is not: a working subscription that delivers declared changes and withholds the rest. S3
is therefore **discharged on reads and partially on subscriptions**, and the partial half is a
gap in the artifact rather than in the measurement.

Two further limits, neither of which the number should be read past:

- **The confined arm's mediator acts on §6.10.2's stand-in, not a live instance.** What is under
  test is which entities the mediator will surrender, and that is decided before any platform is
  reached.
- **36 entities is a small home.** The proportion is the finding, not the count; a larger home
  moves the unconfined figure up and the confined figure not at all, since the confined figure
  is the size of the declaration.

## 7.15 S1's baseline — the attack that forced the architecture, made real

**Run 2026-09-02**, `experiments/gc_attack/`. §7.5's S1 criterion is that the published
garbage-collector technique (§2.4.1) is attempted from inside the sandbox and reaches no
platform object. §7.13's suite established the confined half. This establishes the half that
gives it meaning.

### 7.15.1 Why §6.9's version was not enough

§2.4.1 is the load-bearing citation of this whole project: Corno and Mannella walk
`gc.get_objects()` to reach *another* integration's live object and read its secret, and that
one result eliminates every in-process design and forces S1 and S2 (§3.5, §5.3). §6.9 ran the
sweep confined and reported `EMPTY — 11,488 objects, all its own`. That is true and it is nearly
a tautology: a process holding one integration holds one integration's objects, and §6.9's arm
had no other secret in the process for the sweep to have found. A confined block is only evidence
against §2.4.1 if the thing the attack looks for **exists, is live, and is reachable by the walk**
in a process that holds it.

### 7.15.2 The pairing

| | Credential | Adversary |
|---|---|---|
| **Unconfined** | a victim integration's live client object, same process | co-resident integration, same process |
| **Confined** | the **mediator's** process — S2's credential | a **sandbox** — S1 |

The victim (`victim_cloud`) is a real custom integration set up through the platform's own
config-entry path, so its token enters the heap through its actual `async_setup_entry`, exactly
as a real integration's does. The same sweep runs in both arms.

### 7.15.3 Result

```
UNCONFINED   victim's token reached by the heap walk : YES — 7 live objects held it
             reached as: CloudClient.attr, dict-value (hass.data), module.attr

CONFINED     adversary's heap  : 8,942 objects, all its own
             token reached     : no
             token live in the mediator process at the same time : yes, 7 references
```

**Unconfined, the published attack succeeds.** The credential is reached seven ways, including
straight off the victim's `CloudClient` instance attribute and through the nested dict in
`hass.data`. No traversal and no exploit: `gc.get_objects()` is a supported API returning live
objects, which is precisely why §2.4.1 is fatal to in-process enforcement.

**Confined, it finds nothing — and the same token is simultaneously confirmed live in the
mediator's process, seven references deep.** The third line is not decoration: it is what turns
"the adversary found nothing" from an uninformative absence into a measured result. The secret
exists, it is exactly as gc-reachable as the unconfined arm proves, and the sandbox boundary is
what the adversary cannot cross. S1 and S2 defeat the one result that forced them.

### 7.15.4 What this does and does not establish

- **The confined credential is the mediator's, which is the design's claim.** S2 places the
  platform credential in the mediator, and that is the object worth protecting. This is not a
  reproduction of two *confined* integrations failing to reach each other — each is in its own
  sandbox by construction, and mutual isolation between two sandboxes is a separate demonstration
  (§6.5's channel self-test).
- **The adversary here runs only the sweep**, where §7.13's runs the full hostile integration.
  The narrowing is deliberate: it is what lets the victim and the credential be made real, which
  is the whole contribution of this section over §6.9.
- **One published attack, faithfully.** §2.4.1 describes the `gc` reach; that is what is
  reproduced. It is not a claim about every conceivable in-process reach, only about the one the
  literature settled and this architecture is answerable to.

## 7.16 C3, and the remaining security criteria re-verified

**Run 2026-09-02.** §7.5's remaining security rows, discharged together because they are
re-verifications over the evaluated artifact rather than new rigs.

### 7.16.1 C3 — the manifest is a claim, not a description that is believed

§3.3 named three shapes before any implementation existed: a manifest **absent**, **over-broad**,
and **deliberately mismatched to behaviour**. The first two of those, plus S6's unparseable case,
were already covered by `selftest_policy`; `selftest_c3` adds the two that carry an argument.

**Over-broad is not a case the framework wins, and this section does not report it as one.**
R1 (§4.11) retains over-declaration as a **High** residual risk: confinement bounds behaviour to
the declaration, and does not make the declaration minimal. The measured result is that an
over-broad grant **is honoured** — an integration declaring `binary_sensor.*` reads bedroom
occupancy, and the clause pointer says so.

What the test establishes instead is **the shape of the ceiling that over-declaration cannot
raise**, because that is where §4.11's word "structural" is either true or empty:

| An author who wants… | Outcome |
|---|---|
| `lock.*` in `services.call` | rejected at parse: *"contains a wildcard. Every entry names one domain.service"* (S5, §5.10.4) |
| `*.temperature` | rejected: *"wildcards the domain, which grants across domains"* |
| `*` alone as an entity grant | rejected: *"must be domain.object_id"* |
| a path grant enclosing the configuration root | rejected at parse (§5.10.5) |
| a path grant reaching `secrets.yaml` or `.storage/` | rejected at parse |
| an invented capability — `process.spawn` | rejected: *"unknown capabilities ['process']"*, not ignored |

Every rejection is at **parse** time and every one names the rule that produced it, which is
§6.6.5's standard applied to a positive-looking case. So the honest statement of R1 is narrower
and more defensible than "over-declaration is a residual risk": an author may declare more than
they need **within a fixed ceiling**, and the ceiling contains exactly the authority Chapter 4
rated Critical — `lock.unlock` (T05), `secrets.yaml` (T14), and cross-domain reach.

**Mismatched is the case C3 is really about**, and it is the shortest result in the chapter. A
manifest declaring one sensor read and `lock.lock` was attached to an integration that did none
of it. Seven behaviours, seven denials, each naming a distinct clause:

| Behaviour | Denied by |
|---|---|
| read the occupancy sensor it did not declare | `/permissions/entities/read` |
| read a phone's location | `/permissions/entities/read` |
| unlock the door it declared only locking | `/permissions/services/call` |
| disarm the alarm | `/permissions/services/call` |
| subscribe to a sensor it declared only *reading* | `/permissions/entities/subscribe` |
| write to an entity it does not own | `/permissions/entities/write` |
| claim to be another integration | `/permissions/entities/read` |

…and what it *did* declare still works. The fifth row is worth pausing on: the integration
declared `sensor.outdoor_temperature` for **read** and was refused **subscribe** on the same
entity. Read and subscribe are separate members of the same capability (§5.10.3), which is S3's
requirement expressed in the schema rather than in the enforcement path.

The declaration bought its author nothing, because enforcement acts on behaviour and the
manifest was never trusted as a description of what the code would do. That is C3.

### 7.16.2 The suite, re-run against the evaluated artifact

All eight self-tests, on the C4 device, 2026-09-02:

| Self-test | Criteria it carries | |
|---|---|---|
| `selftest` | S8, filesystem and process isolation | ✅ |
| `selftest_policy` | **S5** asymmetry, **S6** default-deny, absent and unparseable manifests | ✅ |
| `selftest_c3` | **C3** over-broad and mismatched | ✅ |
| `selftest_channel` | T02, identity from the socket | ✅ |
| `selftest_audit` | **S7** — hash chain and keyed MAC chain failing independently | ✅ |
| `selftest_describe` | **F4** — four states, denials at the same weight as grants | ✅ |
| `selftest_bridge` | F1, C1 — an unmodified integration running confined | ✅ |
| `selftest_gc` | **S1**, S2 — §7.15's pairing | ✅ |

**N3** is carried by `preflight` rather than by a self-test: the framework refuses to start when
the memory controller is absent (§5.7.4) or when the supervisor is in the wrong cgroup position
(§6.4.1), and both refusals are stated failure modes rather than silent degradation. §7.4.4
records why that case matters — `mkdir` succeeds from the wrong position, so everything looks
right and only placement fails.

### 7.16.3 Where §7.5 now stands

Fifteen of twenty requirements are discharged with evidence in this chapter or in Chapter 6.
The five that are not divide into three kinds, and the distinction matters more than the count:

- **Blocked by an unbuilt component — F2, S4.** The egress proxy does not exist. Named in §7.5
  on 2026-09-02 rather than discovered later.
- **Reported, not thresholded — N1.** §3.6 fixed that position in advance; the figures are owed
  at scale (§7.10 items 3 and 5) and the discussion criterion is stated.
- **Partially discharged — S3, N2.** S3's subscription half is a decision without a delivered
  stream (§7.14.4); N2's executed-end-to-end population is one (§6.11.1). Both are gaps in the
  artifact rather than in the measurement, and both are named where the figure appears.

## 7.17 N2's second number — integrations executed end-to-end

**Run 2026-09-02**, `experiments/end_to_end/`. §3.6's N2 requires "executed end-to-end" be
reported separately from "imports-clean" and never conflated. §7.12 supplied the first number
across 37 integrations; §6.11.1 scored the population for the second as **one**. This raises it,
and states what bounds it.

### 7.17.1 The ceiling is eleven, and that is a property of the ecosystem

A config entry needs data only each integration's own flow can produce. Surveying all 37 by what
`config_flow.py` asks for: **26 of 37 require an API key, token, password, username, host or
email** before any flow can complete. Eleven require none — they are configured from other
entities, or from nothing.

**So the denominator for any end-to-end measurement of this corpus is 11, not 37**, and an
unconfined baseline meets exactly the same wall. Reporting a rate over 37 would conflate N2's two
numbers *and* imply a denominator no measurement of any confinement scheme could reach. This
chapter therefore reports a **named set of five with its selection stated**, and computes no rate.

### 7.17.2 Result

| Integration | Outcome | Own entities | Published through the mediator |
|---|---|---|---|
| `thermal_comfort` | ✅ **LOADED** | 15 | **15** |
| `watchman` | ✅ LOADED | 10 | 13 |
| `adaptive_lighting` | ✅ LOADED | 4 | 7 |
| `scheduler` | ❌ SETUP_ERROR | 0 | 0 |
| `powercalc` | ❌ NOT_LOADED | 0 | 0 |

Three of five set up through their own config flows and published entities across the boundary.
§6.11.1's population of one becomes three, which is a named set and still not a rate.

### 7.17.3 The round trip, in one integration

`thermal_comfort` is the case that discharges F1 rather than merely illustrating it:

```
mirrored in   sensor.living_room_temperature  21.4 °C   ─┐ the two entities its
              sensor.living_room_humidity       48 %    ─┘ manifest declared
                          ↓ computed inside the sandbox
published out sensor.living_room_dew_point          9.96
              sensor.living_room_absolute_humidity  9.00
              sensor.living_room_frost_point        7.06   … 15 in total
              every one accepted, clause `(ambient: §5.10.2)`, `refused: []`
```

Unmodified source, its own config flow, its own arithmetic, its own entities — in across the
mediated read path, out across the publish path. **A dew point of 9.96 °C from 21.4 °C at 48 %
relative humidity is physically correct**, so what is demonstrated is not that the integration
loads but that it *works*: the values it computed depend on the two entities the mediator handed
it, and they are right.

The published entities are accepted as **ambient** rather than checked against a clause, which is
§5.10.2's rule that an integration publishing its own entities is what being an integration is.
Nothing it did was refused.

### 7.17.4 Both failures diagnosed, and neither is the harness

§6.3.3 obliges this chapter to check a failure against the harness before charging it to the
design. Three earlier failures were harness faults and are recorded in the experiment README;
these two survive that check.

**`scheduler` — the first measured compatibility cost of network isolation.**

```
zeroconf/_utils/net.py: add_multicast_member
    listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, …)
```

The sandbox's network namespace holds loopback only, so joining a multicast group fails. It
declares `http` and `websocket_api`, and zeroconf arrives through that chain. **This is
confinement costing compatibility**, and §7.12 could not have found it: at import level the
integration is fine, and only setting it up reaches the socket. It bears directly on §9.5's open
decision — network isolation costs more than "cannot reach the internet", and an egress proxy
that mediates outbound TCP does not by itself answer multicast discovery.

**`powercalc` — an undeclared component.** Its flow completed all four steps and created the
entry; setup then failed with `KeyError: 'network'` out of
`homeassistant.components.network.async_get_loaded_network`. It declares `light`, `group`,
`template`, `select`, `utility_meter` and `integration` — **not `network`** — and does not import
it directly, so it arrives transitively. This is §6.13.2's undeclared-*package* finding in its
component form, and it extends that finding rather than repeating it: **the declaration is
incomplete for components as well as for packages.** §6.14.4's argument stands unchanged — the
answer is §5.9.3's static analysis marked *derived*, not asking the author.

> **A design refinement this measurement justifies, and Chapter 8 owes it.** §5.9.3 accepts M3,
> static analysis, as a contributor to a *derived* manifest, and §6.14.4 proposed it for the
> undeclared-package case: `import aiofiles` is a top-level import and trivially detectable.
> `powercalc` shows the same treatment is needed one level up — **the analysis must also resolve
> `homeassistant.components.*` imports and the transitive component closure**, not only
> third-party package imports. That is a strictly larger analysis and a strictly easier one: a
> component dependency is a name in the platform's own source, so the closure is computable
> exactly rather than approximated, which `core_requirements()` in `confine/compat.py` already
> does for `default_config`. Recorded here because the evidence for it arrived here; the
> recommendation belongs in Chapter 8's future work alongside §6.14.4's.

### 7.17.5 The baseline arm, which overturns half of §7.17.4

§7.17.4 was written attributing both failures from their tracebacks, and recorded that doing so
was weaker than §7.12's comparison and was the next thing owed. It was run the same day, and it
was right to distrust the attribution: **one of the two conclusions does not survive it.**

Same five integrations, same corpus, release, host, interpreter and world of entities, the same
`drive_flow` shared rather than reimplemented, against a full unconfined Home Assistant.

| Integration | Unconfined | Confined | |
|---|---|---|---|
| `thermal_comfort` | ✅ LOADED | ✅ LOADED | — |
| `watchman` | ✅ LOADED | ✅ LOADED | — |
| `adaptive_lighting` | ✅ LOADED | ✅ LOADED | — |
| **`powercalc`** | ✅ **LOADED** | ❌ NOT_LOADED | **confinement's cost** |
| **`scheduler`** | ❌ **SETUP_ERROR** | ❌ SETUP_ERROR | broken either way |

```
    loaded(unconfined) 4/5      loaded(confined) 3/5      cost of confinement: 1
```

**`scheduler` is withdrawn as a finding about confinement.** Unconfined it fails with a
`RuntimeError` out of `homeassistant/helpers/frame.py: report_usage` — the platform's own
frame-helper refusing a deprecated API pattern on 2026.8.3. It is broken on this release the way
`eufy_security` is (§6.14.3), and it never reaches the socket that stopped it in the sandbox.

The multicast observation itself stands as an **observation**: the sandbox's network namespace
holds loopback only, and `zeroconf`'s `IP_ADD_MEMBERSHIP` fails there. What does **not** stand is
the inference drawn from it in the first version of this section — that confinement was thereby
shown to cost compatibility. To establish that, an integration is needed which **works
unconfined and fails confined on discovery**, and this corpus has not produced one.

> **A conclusion that was drawn from it and is now withdrawn.** The first version of this
> section argued that network isolation costs more than "cannot reach the internet", and that an
> egress proxy mediating outbound TCP would not answer multicast discovery. **The second clause
> is still true as a statement about mechanisms; the first is not evidenced.** §9.5's decision
> must not be taken on it.

**`powercalc` is confirmed as confinement's cost, and it is the only one.** It loads unconfined —
`default_config` sets up `network`, which it needs and does not declare — and fails confined with
`KeyError: 'network'`. So the undeclared-component finding of §7.17.4 stands and is now measured
by comparison rather than inferred, which is what makes it worth the paragraph it gets.

**This is the second time in this chapter that a baseline arm has corrected a conclusion drawn
without one** — §7.12.3 scored two predictions wrong, and this scores one attribution wrong. Both
corrections went in the direction of *charging the design less*, which is the direction an
author's own attributions will tend to get wrong in the opposite way, and is the argument for the
paired discipline rather than for trusting a traceback.

### 7.17.6 What this does not establish

- **Five is a named set, not a sample**, and no rate is computed from it.
- **`published through the mediator` has no unconfined counterpart** and none is possible: there
  is no mediator unconfined, so the column is blank there rather than zero. What the comparison
  supports is `loaded`, and that is what §7.17.5 compares.
- **The mediator acts on §6.10.2's stand-in.** What crossed the boundary is real and is recorded
  with its clause; what a live Home Assistant would do with those fifteen entities is not tested.

## 7.18 How much egress is actually needed, and of what kind

**Run 2026-09-02**, `experiments/egress_demand/`. §9.5 leaves one decision open — whether to
build §5.8.2's scope item 2 — and until now nothing in this evaluation measured the thing the
decision turns on: **how many integrations need outbound network, and where they need to go.**

§7.17 looked as though it might answer it and could not. Its five subjects were selected for
being configurable without credentials, which selected almost exactly the integrations that need
no network: three of the five declare `iot_class: calculated`. A set chosen for testability was
therefore blind to the question by construction, and that is worth stating before any number.

### 7.18.1 The declared answer

Every Home Assistant integration declares an `iot_class` saying what it reaches. §5.9.1 already
established this field's value to the design — 83% of the wider corpus declare it, and it is the
third of the three findings behind "the declaration always already exists". Across the 37:

| Declared `iot_class` | Count | What it needs | Served by scope item 2? |
|---|---|---|---|
| `cloud_polling` (13) + `cloud_push` (2) | **15 — 41%** | the internet | **yes** — hostnames, resolved and pinned (T11) |
| `local_push` (12) + `local_polling` (3) | **15 — 41%** | devices on the home LAN | **only with §5.10.3's separate flag** for non-public destinations (T10) |
| `calculated` | 6 — 16% | nothing | not applicable |
| none declared | 1 — 3% | unknown | — |

**Two things follow, and the second is the one Chapter 8 owes.**

First, **the network need is real and is the majority position**: 30 of 37 — 81% — declare that
they reach something over a network. The 16% that need nothing are the class §7.17 happened to
test, which is why that section could not see this.

Second, **the need splits almost exactly in half, and the two halves are not the same
capability.** Scope item 2 as scoped in §5.8.2 is *"per-integration outbound network with T11's
resolve-then-pin at connection time"* — that serves the cloud-facing 41% directly. The
local-facing 41% need a private address, which §5.10.3 provides for but as a **separate explicit
flag**, precisely because reaching the LAN is reaching the router's admin page and every other
device in the house (T10). **So building the proxy does not by itself make 81% workable; it makes
41% workable and puts the other 41% behind a declaration the user is meant to read differently.**
Nothing in Chapters 1–7 has previously stated that the design's network position divides the
corpus this way.

### 7.18.2 The observed answer, and a measurement that had to be corrected first

`sandbox_runtime.record_egress_attempts` patches `socket` before the integration is imported and
records every resolve and connect. The namespace holds loopback only, so every attempt already
failed; what was missing was **what was attempted**.

**The first version of this measurement reported that 23 of 37 integrations attempted egress at
import, and it was entirely an artifact.** Every one of the 23 reached exactly the same three
addresses — `224.0.0.251`, `8.8.8.8` and `127.0.0.1`. Two thirds of a corpus reaching for an
identical triple is not integrations behaving alike; it is something else doing it. It was Home
Assistant itself: the `network` component probes `8.8.8.8` to find which adapter holds the
default route, and `zeroconf` joins the mDNS group, both during `async_setup_component` and
therefore **before the integration is imported at all**.

The recorder now stamps each attempt with the phase that made it, and the corrected result is
unambiguous:

| Phase | Attempts | Integrations |
|---|---|---|
| Instance construction | 0 | 0 |
| **Declared components being set up** | **71** | **23** |
| **The integration's own code** | **0** | **0** |

**Not one integration of the 37 attempts egress at import.** All seventy-one attempts belong to
components the platform set up on their behalf. §6.6.5's rule — assert on *why*, not on *that* —
has now caught a fourth case, and this one would have overstated observed demand by a factor of
twenty-three and pointed §9.5 at a number the integrations had no part in producing.

**The corrected figure is itself the finding: import-level observation cannot measure egress
demand at all.** Integrations open connections when they are *set up*, not when they are
imported, which is exactly what the zero says. Across §7.17's five, run through their own config
flows, only `scheduler` reached for anything — the same mDNS triple, and it is the one that fails
on this release regardless (§7.17.5). The other four attempted nothing, corroborating their
declarations: three are `calculated`, and `watchman` inspects local configuration files rather
than the network despite declaring `local_push`.

**So observation is doubly bounded**, and the second bound is the interesting one. Demand appears
at setup; setup needs a credential for 26 of 37 (§7.17.1); therefore **no observational method
available to this project — or to an unconfined baseline — can measure egress demand across this
corpus.** The declared figure is not merely the better estimator, it is the only one, which makes
this the sharpest instance in the evaluation of the pattern §7.2 opens with: *the declaration
already exists, and it is carrying evidence nothing else can supply.*

**Two further limits.** The recorder is in-process, so an integration issuing raw syscalls would
not be seen — acceptable here because this measures *demand from ordinary integrations*, not an
adversary, and §7.13 covers the adversary. And `iot_class` is the author's claim, subject to R1
like every other declaration, though over-declaring one's own network reach is not an attack that
buys anything.

### 7.18.3 What this means for §9.5

The decision is better informed than it was and it has not been taken here. What the evidence
now supports:

- **The need is real and large.** 81% declare a network reach. An artifact that cannot serve any
  of it leaves F2 unverified and most of the corpus non-functional beyond import.
- **The proxy as scoped closes about half of it.** 41% cloud-facing, served directly; 41%
  local-facing, served only through the non-public flag, which is a further design decision
  §5.10.3 provides for but which §5.8.2's scope item does not mention.
- **No measured evidence yet that confinement's *current* network position costs compatibility.**
  §7.17.5 withdrew the one candidate. The argument for building the proxy remains the one §9.3
  ranks first — a requirements register that does not match the artifact — not a measured
  compatibility loss.

## 7.19 Mediation latency at the budget, and why the number that matters is the other one

**Run 2026-09-02**, `experiments/mediation_latency/scale.py`. §6.5.3 measured two clients and
found p99 moving **85%** — queueing rather than work — and left the obligation explicit: the
budget is 26 sandboxes (§6.3.2) and two says nothing about twenty-six.

**This measures the real mediator, not the socket floor.** Every request goes through
`confine.Mediator` with a `Manifest` bound and `acting_policy` deciding it, so what is timed is
steps 1, 2, 3 and 5 of §5.11.3 — identity, decision, clause, reply. The audit write is not
included; §6.8.3 flags that as the open question and §7.10 schedules it separately.

### 7.19.1 Result

| Sandboxes | Median µs | p95 | p99 | Max | Aggregate req/s |
|---|---|---|---|---|---|
| 1 | 31.5 | 46.1 | 52.7 | 810 | 25,739 |
| 2 | 43.1 | 47.5 | 55.9 | 1,536 | 44,736 |
| 4 | 60.9 | 124.0 | 132.9 | 3,418 | 46,115 |
| 8 | 139.9 | 282.4 | 293.0 | 7,686 | 47,582 |
| 16 | 302.4 | 602.4 | 619.9 | 16,967 | 48,462 |
| **26** | **512.2** | 568.9 | **1,039.0** | 28,124 | 47,693 |

### 7.19.2 P4 was wrong, and its shape was wrong in an informative way

§7.6 predicted *"median within 2× of the single-client figure, p99 an order of magnitude worse"* —
the signature of queueing that spares the median and punishes the tail. What happened:

```
    median   31.5 → 512.2 µs    16.3×      predicted ≤ 2×
    p99      52.7 → 1039.0 µs   19.7×      predicted ~10×
```

**Both degraded, and by almost the same factor.** That is not tail-heavy queueing; it is a
**saturated serial server**. The aggregate throughput column is what gives it away: it reaches
~45,000 req/s at two clients and stays flat to twenty-six. The mediator is at capacity from two
clients onward, so every further client simply lengthens the queue, and latency rises close to
linearly with the queue rather than disproportionately in the tail.

The prediction assumed the tail would separate from the median. It does not, because there is no
burst behaviour to create a tail — there is a single-threaded selector loop serving a saturated
queue, which is the fairest possible scheduler and produces a *narrow* distribution at every
level. §5.11.2's "identity is the socket" and its one-loop-owns-every-socket consequence is
directly visible in this table.

*(p95 and p99 at 26 are not cleanly ordered against 16 — 568.9 against 602.4 — which is scheduling
noise at that level rather than a real inversion, and it is left in the table rather than
smoothed.)*

### 7.19.3 The number that decides N1 is the headroom, not the latency

512 µs per request at twenty-six saturated sandboxes is the wrong figure to judge N1 by, because
**no installation generates that load.** The measurement drives twenty-six clients issuing
requests back to back with no think time; a real integration polls. §5.8.1 measured a mean of
4.02 integrations per installation, and Home Assistant's ordinary polling interval is thirty
seconds.

Taking the budget rather than the mean, and being generous about how chatty an integration is:

```
    26 sandboxes × 5 mediated operations × (1 / 30 s)  =  4.33 req/s
    measured capacity                                  =  47,693 req/s
    headroom                                           =  ~11,000×   (0.009% utilised)
```

**The mediator's capacity exceeds realistic demand by about four orders of magnitude.** The
queueing that dominates §7.19.1 therefore does not occur in practice: at 0.009% utilisation the
observed latency is the one-client figure, **31.5 µs**.

> **Corrected by §7.20.1, and the correction is large.** This figure excludes the audit write,
> which §7.20.1 measures at **3.67 ms per decision** — 59× the non-durable write and a hundred
> times the mediated request itself. Capacity is therefore **272 decisions per second, not
> 47,693**, and the headroom over realistic load is **63×, not 11,000×**. The conclusion for N1
> survives and the arithmetic behind it does not, so the corrected numbers are the ones to
> quote.

§3.6 fixed in advance that no threshold would be asserted and the figures would be reported and
discussed. The discussion is this: the design's per-request cost does not change what a user can
run, and it is not close. What *would* change it is a mediated operation on a hot path — a
subscription delivering every state change rather than a poll — and §7.14.4 records that the push
loop does not exist yet, so that path is unmeasured and this conclusion is bounded to the
request/response shape §5.11.1 calls "mediated".

### 7.19.4 Limits

- **The audit write is excluded**, and §6.8.3 expects `fsync` per decision to cost far more than
  the decision. §7.10's item 5 measures it; until then the headroom above is an upper bound.
- **Saturation, not realism.** The table is a stress measurement; §7.19.3 is the one that bears
  on N1, and the two must not be quoted interchangeably.
- **Python 3.13.5**, not the 3.14.7 the sandboxes run — the harness executes under the host
  interpreter, as the supervisor does (§6.4.1). The mediator is the component measured and it is
  the supervisor's, so this is the right interpreter for it, but the version differs from every
  other figure in this chapter and is recorded rather than glossed.

## 7.20 What durability costs, what S9 costs, and one measurement that would not resolve

**Run 2026-09-02**, `experiments/durability/`. Three of Phase C's obligations, and the first is
the one that bounds §7.19.

**Both measurements were invalid on their first run, for the same reason, and it is worth
recording before either number.** They were written to `tempfile`'s default directory, which is
`/tmp`, which is **tmpfs on the C4 device** — RAM. `fsync` to RAM is a no-op, so durability
appeared to cost **−0.1 µs**; and a 512 MB "file" in RAM is not a file, so the page-cache
measurement was reading memory. A second defect compounded the second: the harness called a
`cgroup.add()` that does not exist, caught the `AttributeError`, recorded it in a field it never
printed, and reported a peak of **0.0 MB** — a process that was never in the cgroup at all. Both
now use real storage and `spawn_confined`, which places the child per §6.4.1's rule.

### 7.20.1 §6.8.3 — `fsync` per decision, answered

`audit.py` already calls `os.fsync` on every decision, so the question was never whether to pay
but what is being paid. On ext4 on the SD card:

| | Median µs | p95 | p99 | Max |
|---|---|---|---|---|
| **With `fsync`, as built** | **3,670.7** | 4,327.9 | 4,937.9 | 27,543 |
| Without `fsync` | 61.8 | 71.4 | 79.2 | 195 |

**Durability costs 3.6 ms per decision — 59× the non-durable write, and roughly a hundred times
the mediated request it accompanies (§7.19.1's 31.5 µs).** §6.8.3 predicted it would cost "far
more than the 2.4 µs decision" and that is a considerable understatement.

**It is nonetheless affordable, and §7.19.3's conclusion survives with different arithmetic:**

```
    capacity with the audit write   1 / 3.67 ms   =    272 decisions/s
    realistic demand (§7.19.3)                    =   4.33 req/s
    headroom                                      =    63×
```

63× is not 11,000×, and the difference matters for how the claim is stated: the mediator is no
longer four orders of magnitude clear of demand, it is *comfortably but finitely* clear. The
answer to §6.8.3 is therefore **yes, keep the `fsync`** — §5.11.3's ordering guarantee is real,
and it is bought at a cost the deployment can carry. The alternative §6.8.3 raised, a bounded
window of loss, is not needed and should not be taken.

**Two things this bounds.** A hot path would consume the margin quickly: at 272 decisions/s a
subscription delivering every state change in a busy home is not obviously affordable, and
§7.14.4 records that the push loop does not exist to measure. And the figure is storage-bound —
an SD card is the worst realistic case and also the most common one for this deployment (C4).

### 7.20.2 §6.9.4 and P5 — falsified, and S9 is narrower than feared

§6.9.4 raised the concern that cgroup v2 charges page cache, so `resources.memory_mb` would bound
file *reading*, making "an integration processing a large local dataset indistinguishable, to
this control, from one searching for secrets". §7.6's P5 predicted this was reproducible and a
genuine usability cost.

A process streaming a **512 MB** file, discarding each block, inside caps of 64, 128 and 256 MB:

| Cap | File | Outcome | Peak |
|---|---|---|---|
| 64 MB | 512 MB | **completed** | 6.4 MB |
| 128 MB | 512 MB | **completed** | 6.4 MB |
| 256 MB | 512 MB | **completed** | 9.0 MB |

**P5 is falsified.** Not one was killed, and the peak never approached any cap. Page cache is
*reclaimable*: under pressure the kernel drops clean cache rather than invoking the OOM killer,
so streaming a file eight times the size of the limit costs nothing measurable.

**This narrows S9's cost claim in the design's favour, and sharpens what the control does:**
**S9 bounds retention, not reading.** An integration that reads a large dataset and discards it
is unaffected; one that reads and *keeps* is killed — which is precisely §7.13's `exhaust`
attack, and precisely the behaviour the control is for. §6.9.4's obligation is therefore
discharged by being withdrawn, and Chapter 8 should carry the narrower statement rather than the
original concern.

### 7.20.3 PSS against declaration depth — not resolved, and reported as such

§7.10's item 4 asked for the per-sandbox footprint as a function of what an integration declares,
so that §6.3.2's budget of 26 could be expressed over the corpus's real declaration distribution
(§6.13: twelve declare nothing, the median is two). Three points, three sandboxes each:

| Declared components | PSS per sandbox | Capacity |
|---|---|---|
| none | 136.3 MB | 17 |
| `http`, `websocket_api` | 95.7 MB | 25 |
| `frontend`, `http`, `websocket_api`, `lovelace` | 115.8 MB | 20 |

**The series is non-monotonic and therefore does not resolve a curve.** More components ought not
to reduce the footprint, and the middle point is the lowest of the three. At three sandboxes per
point the measurement is dominated by how much of the interpreter and library happens to be
shared at that moment, and PSS is exquisitely sensitive to that — it is a *proportional*
attribution, so a page shared three ways counts a third as much as the same page mapped once.

**No trend is claimed and none should be read into these numbers.** §6.3.2's budget of 26 stands
as measured there; refining it over the declaration distribution needs more sandboxes per point
and repeated runs, and is left to future work rather than reported as a curve drawn through
noise. Recording the attempt and its failure to resolve is the alternative to quietly omitting a
scheduled measurement.

### 7.20.4 §7.9's outstanding defect

`experiments/r2_footprint/measure.py` still carries the pre-§6.3.3 recipe — the instance reaches
the running state via `set_state(CoreState.running)`, which never fires
`EVENT_HOMEASSISTANT_START`. §5.6.3's 176/136 MB figures were produced by it. That builder is
deliberately preserved so §5.6.3's published figures stay reproducible, and the defect affects
*deferred callbacks*, not the size of the process, so a proportional-set-size figure is unlikely
to move. **Unlikely is not measured**, and this chapter does not have the measurement. §5.6.3's
figures are therefore quoted in this evaluation only with that caveat attached, and re-running
the footprint experiment on the corrected builder is added to future work.

## 7.21 A reconciliation pass, and what reading the chapter against Chapter 6 found

**2026-09-02.** §7.1–§7.11 were written before the results; §7.12–§7.20 were written as each
measurement landed, one at a time, over a single day. Neither half had been read against the
other, and §7.7's fourth falsifier makes that a requirement rather than tidiness: *an evaluation
that reports a requirement as passed when it cannot demonstrate it has failed on its own terms.*
This section records what the pass found. One finding is serious and is stated first.

### 7.21.1 S9 is reported against a criterion two thirds of which nothing enforces

§4.10.1 states S9 as *"The framework shall bound an integration's consumption of **CPU, memory
and disk**"*, and §7.5's criterion follows it: *"an integration deliberately exhausting CPU,
memory and disk in turn does not render the gateway unresponsive."*

What the artifact does:

| Resource | In the manifest schema | Rendered by `describe.py` when declared | **Enforced** |
|---|---|---|---|
| Memory | `resources.memory_mb` | *"192 MB of memory"* | ✅ `memory.max`, but **not from the manifest** |
| Processes | `resources.max_processes` | *"8 processes"* | ✅ `pids.max`, **not from the manifest** |
| **CPU** | `resources.cpu_percent` | *"N% of one processor"* | ❌ **nothing** |
| **Disk** | absent from the schema | — | ❌ **nothing** |

Three separate defects, and they compound:

**1. No `resources` clause reaches an enforcement path.** `SandboxCgroup.create` is called with
`memory_max` and `pids_max` **hard-coded by each harness** — 640 MB in `compat.py` and
`endtoend.py`, 512 MB in `selftest_adversary.py`, 256 MB in `selftest_channel.py`. Grep finds no
reader of `resources.memory_mb` anywhere except `describe.py`. So the memory limit that §7.13
demonstrates is real, and it is the *test harness's* limit, not the integration's declaration.

**2. `cpu_percent` is validated, displayed, and silently ignored.** This is the sharper defect,
because it is the exact failure §5.10 legislates against one level up. §7.16.1 quotes the
manifest refusing an invented capability with *"unknown capabilities ['process']. An unrecognised
capability is rejected rather than ignored, because ignoring it under-enforces silently."* A
**recognised** capability that is ignored is worse than an unrecognised one that is rejected, and
the schema currently accepts one.

**3. It would reach the user, which makes it an F4 problem and not only an S9 one — and the
tense matters.** `describe.py:126–133` builds the limits sentence from whichever of the three
keys the manifest carries, so a manifest declaring `cpu_percent` renders *"… and N% of one
processor"* and that clause is false. **No manifest in this repository declares it**, so the
sentence has never actually been produced: §6.7.1's transcript reads *"It is limited to 192 MB of
memory, 8 processes."* because its example manifest omits the key, and `selftest_describe.py`
asserts only on the memory phrase. The defect is therefore latent rather than observed, and
saying so is the difference between this finding and the register error §6.6.6 names — *an
inference stated as a result*. It is still an F4 defect: §1.8's gap is that a user "cannot see
what an integration intends to access", F4 closes it by making authority visible, and **a visible
limit that is not enforced is worse than an invisible one** because it converts an unknown into a
wrong belief. The first author to write the key that the schema already accepts gets the false
sentence.

**How this chapter reports S9, corrected.** §7.13's memory demonstrations stand: the allocation
attack and the unbounded read are both OOM-killed by a real `memory.max`, and §6.4.1's
unprivileged cap check is independent of the manifest. What does **not** stand is any claim that
S9 as written is met. S9 is **partially discharged — memory and processes, from harness
configuration rather than from the declaration; CPU and disk not at all.** §7.5's row is scored
accordingly, and this is the third row after F2 and S4 that the artifact does not satisfy.

Chapter 8 owes the fix and it is small: read the clause, pass it to `SandboxCgroup.create`, add
`cpu.max` from `cpu_percent`, and either implement `io.max` for disk or **remove disk from S9's
text and say why** — a requirement narrowed on evidence is legitimate, a requirement quietly
unmet is not.

### 7.21.2 Where the methodology half is now out of date, and why it is not edited

§7.1 froze §7.5's criteria and §7.6's predictions. It did not freeze §7.4's *narrative*, which
was written before any result and still says so — §7.4.1 calls the baseline arm "the one that
does not yet exist", §7.4.3's table lists durability as "Not measured", and §7.4.1 records the
level-2 population as one.

**These are left as written**, on the same principle Chapter 6 applies to Chapter 5 and this
chapter applies to Chapter 6: the methodology half is evidence of what was planned before the
results, and editing it into agreement destroys the only thing that makes §7.1's claim checkable.
Each is now answered downstream — the baseline in §7.12, durability in §7.20.1, level 2 in
§7.17 — and a reader who meets a stale sentence in §7.4 finds the result under the same heading
number in the seventies.

### 7.21.3 Obligations: five pointed at a plan rather than a result

§7.8 listed eleven inherited obligations, and five were discharged "in §7.4.1" or "in §7.4.3" —
which are *methodology* sections. An obligation is not discharged by a section that promises to
discharge it. Corrected:

| Owed from | Obligation | Now discharged in |
|---|---|---|
| §6.14.6 | Run the baseline arm | **§7.12** |
| §6.5.3 | Latency at realistic sandbox counts | **§7.19** |
| §6.8.3 | Decide whether `fsync` per decision is affordable | **§7.20.1** — yes, at 3.6 ms and 63× headroom |
| §6.9.4 | What `resources.memory_mb` costs a legitimate integration | **§7.20.2** — *withdrawn*, P5 falsified |
| §3.6 (N2) | Report both numbers separately | **§7.12 and §7.17** |
| §6.3.3 | Check failures against the harness before charging them to the design | **§7.17.4**, where three of five were harness faults |
| §5.14 | Uniform-corpus re-run | **Still owed** — §7.10's item 7, not run |

### 7.21.4 The schedule, closed out

§7.10's eight items: **1–6 are complete** (§7.12, §7.13–§7.14, §7.19, §7.20.3, §7.20.1, §7.20.2).
**Item 7, the uniform-sample corpus, was not run** and is the only scheduled measurement this
chapter did not attempt; §7.9's external-validity limit therefore stands undischarged and
Chapter 8 carries it. **Item 8 is conditional on a decision not yet taken.**

### 7.21.5 Predictions, scored in one place

| | Prediction | Outcome | |
|---|---|---|---|
| P1 | Baseline 34/37 | 31/37 | ✗ |
| P2 | Baseline passes the `aiofiles` three | It fails all three | ✗ |
| P3 | Confinement costs 0–3 integrations | **0** | ✓ at the floor |
| P4 | Median ≤2×, p99 ~10× worse at 26 | Both ~16–20× — saturation, not tail queueing | ✗ |
| P5 | S9 kills a legitimate large-file reader | Never killed; page cache is reclaimable | ✗ |

**Four of five wrong, every one caught by a measurement, none revised after the fact.** §7.1
argued that a pre-registered prediction is worth having precisely because it can be wrong; this
is what that looks like when it is working, and Chapter 8 should present the scorecard rather
than bury it. The one correct prediction was correct at the extreme edge of its stated range.

### 7.21.6 Cross-chapter corrections, consolidated

Chapter 7 has corrected Chapter 6 five times. Each correction is a pointer in place and Chapter 6
keeps its original text, per the convention §6.4.1 established for Chapter 5:

| Chapter 6 | Corrected by | What changed |
|---|---|---|
| §6.9.2's counts | §7.13.4 | 21 blocked / 9 empty → **20 / 10**; the sweep was killed reading `/dev/zero`, not by the resource limit |
| §6.9.4's S9 concern | §7.20.2 | **Withdrawn.** Page cache is reclaimable; S9 bounds retention, not reading |
| §6.8.3's open question | §7.20.1 | **Answered.** 3.6 ms, 59×, and affordable at 63× headroom |
| §6.5.3's two-client figure | §7.19 | Extended to 26; the shape is saturation, not tail queueing |
| §6.13.2's undeclared packages | §7.17.4 | Extended to undeclared **components** (`powercalc`, `network`) |

Two further pointers were placed in the second pass below: §6.5.3 now carries §7.19's refinement
in the text rather than only in this table, and §6.12.3's un-measured PSS estimate now carries
§7.20.3's failure to resolve it.

### 7.21.7 A second pass, reading Chapter 6 end to end rather than by grep

§7.21.1–§7.21.6 were produced by reading Chapter 7 in full and checking Chapter 6 against it with
targeted searches. That is enough to find a disagreement between two chapters and not enough to
find a chapter disagreeing with itself, so Chapter 6 was then read straight through. Three things
came out of it, and the first is this section's own.

**1. §7.21.1 quoted a string the artifact has never produced.** It reported `describe.py` as
rendering *"192 MB of memory, 8 processes, 50% of one processor"*. The code will render that
clause — but only for a manifest declaring `cpu_percent`, and **no manifest in this repository
declares one**. §6.7.1's transcript is the two-limit form and is faithful. The S9 and F4 findings
stand unchanged; what was wrong was their register, presenting a latent defect as an observed
line. That is precisely the fault §6.6.6 names — *an inference stated as a result* — committed in
the section written to catch it, which is worth recording rather than quietly repairing. §7.21.1
now states the defect as a property of the code and says the sentence has never been produced.

**2. §6.11.2 said "Four remain" over a table of six rows.** Not a superseded claim — a miscount
contradicted by the table beneath it at the moment of writing. Corrected in place, because the
leave-it-and-point convention exists to protect reasoning that later evidence overturned, and
there is no reasoning here to protect.

**3. §6.13.1 carried a sentence damaged by a later edit**, reading *"…twelve of the 37 declare no
components at all, and the median declaration is two and are charged nothing."* The commit that
corrected sixteen to twelve left the clause it displaced in place. Corrected in place, for the
same reason.

**What the pass did not find is the more useful half.** No figure in Chapter 6 disagrees with any
figure in Chapter 7 — 46/57/70/84%, the 9.0/32.2/19.1 MB premiums, 31 of 37, the 0.7 MB noise
floor and §6.3.2's 136.6-against-136.5 MB replication all hold as printed. Every correction this
chapter has made to Chapter 6, in both passes, has been to a *sentence next to a measurement*
rather than to a measurement, which is §6.6.6's observation about Chapter 5 holding a chapter
later and about a different author's chapter — the same author's. That asymmetry is now
consistent across three chapters and belongs in Chapter 8 as a methodological result, not as a
run of luck.

---

*§7.1–§7.11 written 2026-09-02, before any measurement specified here had been run. Criteria in
§7.5 and predictions in §7.6 are frozen at that date and were not revised in light of results —
§7.12.3 scores two of them as wrong rather than adjusting them. §7.12 is the first results
section; the remaining measurements are scheduled in §7.10.*
