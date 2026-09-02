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
| **S9** | An integration deliberately exhausting CPU, memory and disk in turn does not render the gateway unresponsive, demonstrated unprivileged, with the boot-time precondition stated | Performance |
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

---

*§7.1–§7.11 written 2026-09-02, before any measurement specified here had been run. Criteria in
§7.5 and predictions in §7.6 are frozen at that date and were not revised in light of results —
§7.12.3 scores two of them as wrong rather than adjusting them. §7.12 is the first results
section; the remaining measurements are scheduled in §7.10.*
