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

> **Discharged in §7.26 (2026-09-03), and not by §7.12–§7.25.** The results half is organised by
> §7.5's requirements and never scored either register; §7.26.1 records that as a reporting failure
> of the chapter's own, found by reading it as one document. Both scorings are now performed —
> §7.26.3 for Chapter 4's eighteen, §7.26.4 for the eleven — and the prediction in the paragraph
> above holds: the sweep is not clean in either register, and the divergence is wider than §4.14
> states.

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

> **This sentence was not true until 2026-09-04, and the repair is recorded at §7.5 rather than
> here.** The table carried a *verdict source* for seventeen of the twenty and a verdict for three.
> The verdicts existed in the chapter throughout; what was missing was the column that collects
> them.

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

> **Run — §7.23.** Seed 20260902, 40 of 40 fetched, both arms: **92% confined, 92% unconfined,
> identical failure sets**, sharing 2 of 40 members with the head corpus. The row above is left at
> its frozen wording per §7.21.2; it had been edited in place and was reverted on 2026-09-03
> (§7.26.6, finding 3).

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

> **This paragraph is wrong, it is the sharpest thing Stage 5's second pass found, and it is left
> as written (2026-09-04).** **No such diff exists.** Nothing in `framework/`, `figures/` or
> `experiments/` hashes or compares an integration's tree against a fetched original; no result
> file carries such a field; no results section reports the count. The sentence describes a check
> that was designed and never built, in a *methodology* section — which is the exact failure
> §7.21.3 corrected for five other obligations and did not catch here, because this one names no
> section to be discharged in.
>
> **Two things are true instead, and the second is why this matters.** The confined arm is safe by
> construction and more strongly than a diff would show: `compat.py` copies each integration with
> `shutil.copytree` and `sandbox.py:218` bind-mounts that copy **read-only**, so the confined
> process cannot write its own source at all. **The baseline arm has neither protection** — it
> passes the fetched path straight into a full, unconfined, in-process Home Assistant. So the one
> arm in which an integration *could* rewrite itself is the one with no copy, no read-only mount
> and no diff, and it is the arm the compatibility claim is measured against.
>
> **The check as described would also not have tested what it claims.** The confined run operates
> on a copy, so diffing the *original* after it proves nothing about what ran; the meaningful
> comparison is copy-against-original, taken before the run. §7.28 states the position, and §8.7
> prices the fix, which is small: hash each tree at fetch, re-hash after each arm, report
> mismatches. **C1 is not withdrawn — no modification has ever been observed — but it is downgraded
> from *counted* to *argued*, and §7.5's row says so.**
>
> **Counted 2026-09-06 (§7.29): 75 tree comparisons across both arms, zero source changes, zero
> diff lines. The paragraph this note corrects is now true — and it was not true for the two months
> it stood, which is the part worth keeping visible.**

### 7.4.2 Security — C3, S1–S9

**The question.** For each threat in Chapter 4's register, is the control claimed in §4.10
demonstrated, and does the demonstration establish what it claims?

**The method is per-threat, not aggregate, and it runs over both registers (§7.2).** A single "attacks blocked" figure is the security
equivalent of an unqualified compatibility percentage: §6.9 records 37 attempts of which 21 were
blocked, 9 succeeded and found nothing, 6 were denied and 1 was permitted, and *that
decomposition is the result*. An attempt that "succeeded and found nothing" is a stronger outcome
than one that was denied — it means the capability was not merely refused but structurally absent
(§5.6.2) — and an aggregate would erase the distinction.

> **The 21/9 split quoted above is §6.9's as it stood on 2026-09-02 and is superseded; the
> sentence is left as written and gains this pointer (2026-09-06).** §7.13.4 recounts the same
> thirty-seven as **20 blocked / 10 empty** — the filesystem sweep completed rather than being
> stopped — and adds a thirty-eighth attack, so the current suite is 21/6/10/1 over 38 (§7.22.1).
> **The argument this paragraph makes is unaffected**, because it is about why a decomposition
> beats an aggregate, and the recount is itself an instance of that: the attack that moved moved
> *to the stronger column*, which is exactly the information an "attacks blocked" figure destroys.

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

| Req | Criterion — the requirement passes if… | Verdict source (fixed 2026-09-02) | **Verdict** |
|---|---|---|---|
| **C1** | Every integration in the compatibility runs shows a **zero-line** diff against its fetched original, counted mechanically after the run | Compatibility | ✅ **Met, and counted — §7.29** (was ◐ from 2026-09-04 to 2026-09-06; §7.28) | **Counted 2026-09-06**: 37 trees in the baseline arm and 38 in the confined arm hashed before and after, **zero source changes and zero diff lines**, on a corpus directory confirmed writable by the run user. The baseline arm is the one that carries it — the fetched tree goes by path into a full unconfined in-process Home Assistant, with no copy and no read-only mount. The confined arm is additionally safe by construction: `compat.py` copies each integration and `sandbox.py:218` bind-mounts the copy **read-only**, so a change there would be a containment failure rather than a compatibility one. **Bound on the claim (§7.29.2): the corpus manifest pins `HEAD` and stores no content hash, so this counts a run and not the project's history.** Between 2026-09-04 and this run the row read *met in substance, not by the stated criterion*, and §7.28 records why. |
| **C2** | Every arm runs against an unmodified official Home Assistant release, version recorded in the result file | All arms | ✅ **Met** — §7.12 — every arm ran against unmodified Home Assistant 2026.8.3 (`759e465`), the release recorded in each result file |
| **C3** | The adversarial run includes an absent manifest, an over-broad manifest, and one deliberately mismatched to behaviour — and all three are handled per §5.9's precedence rules | Security | ✅ **Met** — §7.16.1 — `selftest_c3`: absent, over-broad and mismatched manifests. Over-broad **is honoured** (R1) and the section says so; the ceiling it cannot raise holds what §4.9 rated Critical |
| **C4** | Every performance figure is produced on the Raspberry Pi 5, reporting per-integration memory *and* added latency | Performance | ✅ **Met** — §7.19–§7.22 — every performance figure produced on the Pi 5, per-integration memory *and* added latency both reported |
| **F1** | A confined integration's entities are present in Home Assistant and behave as native entities under the measures used in this chapter | Compatibility, level 2 | ✅ **Met** — §7.17.3 — `thermal_comfort`: two declared entities mirrored in, fifteen derived sensors published out, dew point physically correct. **Bounded by §8.6.3 #2**: the mediator acts on a stand-in, not a live instance |
| **F2** | An integration polling a **declared** remote API completes successfully while confined | *(updated in place 2026-09-03 — see the note below)* | ✅ **Met — §7.25, and by a *real* integration in §7.27.** Two purpose-built integrations polled declared hosts concurrently in real namespaces (§7.25); `nordpool` — unmodified community source — then polled its own Nord Pool API confined and published **the same price as the unconfined arm**, with the mediator's durable record naming `dataportal-api.nordpoolgroup.com:443` (§7.27) |
| **F3** | Every enforcement decision in the evaluation names the manifest clause that produced it; a decision with no attributable clause is shown to be unconstructible | Security | ✅ **Met** — §7.4.2, §7.16.1 — every decision record carries a clause pointer; seven mismatched behaviours produced seven denials naming **seven distinct clauses** |
| **F4** | The manifest of each evaluated integration renders in human-readable form, with denials shown at the same weight as grants | §6.7, re-run over the evaluated set | ✅ **Met** — §7.16.2 — `selftest_describe`, four states, denials rendered at the same weight as grants. Bounded to *availability* by §3.4; comprehension is excluded by §3.7 |
| **S1** | The published garbage-collector technique (§2.4.1) is attempted from inside the sandbox and reaches no platform object; the mediator and its credential are not locatable from within | Security | ✅ **Met, paired** — §7.15.3 — the published `gc` technique reaches a live credential **7 ways** unconfined and **0** confined across 8,942 objects, while the same token is confirmed live in the mediator |
| **S2** | No platform credential is recoverable from the sandbox's environment, filesystem, process table or memory | Security | ✅ **Met, paired** — §7.13, §7.15.3 — another process’s environment `LEAKED` unconfined and `EMPTY` confined; no platform credential recoverable from the sandbox |
| **S3** | A confined integration is denied both a **read** and a **subscription** to undeclared entities, each refusal naming its clause, **against a paired unconfined baseline** quantifying what is readable without the framework | Security | ◐ **Partial** — §7.14.2 — the read half is met and paired: **36/36 → 1/36**, and **20/20 → 0/20** presence entities. **The subscription half is verified at the decision layer only**; no push loop exists to deliver a stream (§6.11.2, §8.6.3 #1) |
| **S4** | An integration is denied a host declared only by a *different* integration | *(updated in place 2026-09-03 — see the note below)* | ✅ **Met — §7.25.** Two confined integrations, running at once, each denied the host declared only by the other — evidenced by the mediator's own audit record |
| **S5** | A manifest permitting `lock.lock` is shown not to permit `lock.unlock`, and the refusal is structural rather than a check | §6.10.1 — re-verified in the evaluation run | ✅ **Met** — §7.16.1 — a manifest declaring `lock.lock` does not permit `lock.unlock`, and `lock.*` is rejected at **parse** time rather than at the point of use |
| **S6** | An integration with **no** manifest and one with an **unparseable** manifest are each denied all mediated capability, each refusal naming its rule | Security | ✅ **Met** — §7.16.2 — `selftest_policy`: absent and unparseable manifests each denied all mediated capability, each refusal naming the rule |
| **S7** | Decisions appear in the log bearing the integration's three-part identity, and modification, deletion **and reordering** are each independently detectable by both the hash chain and the keyed MAC chain | §6.8 — re-verified | ✅ **Met** — §7.16.2 — `selftest_audit`: modification, deletion and reordering each detected, and the hash chain and keyed MAC chain fail **independently**. §8.6.3 #7 states the key’s lifetime |
| **S8** | The 2021 file-theft pattern **succeeds against an unconfined baseline installation** and is blocked under the framework, on the same host and release | Security — **requires the baseline arm** | ✅ **Met, paired** — §7.13.2 — the 2021 file-theft pattern recovers **2 of 2** canaries unconfined and **0 of 2** confined on the same host and release; `open("../../secrets.yaml")` raises `FileNotFoundError`, not `PermissionError` |
| **S9** | An integration deliberately exhausting CPU, memory and disk in turn does not render the gateway unresponsive, demonstrated unprivileged, with the boot-time precondition stated | *(updated in place 2026-09-03 — see the note below)* | ✅ **Met, against narrowed wording — §7.22.** All four bounds now come from the manifest and each is verified by a sandbox exceeding it: memory OOM-killed, forks refused at the cap, a 25% CPU cap holding at 25.1%, `ENOSPC` at `disk_mb`. **Disk means space, not I/O bandwidth** — the `io` controller is not delegated to a user manager (§7.22.2), so S9's text is narrowed on evidence and the residual is stated |
| **N1** | Added latency, per-integration memory and maximum concurrent integrations are all reported against an unconfined baseline on the target hardware. **No threshold** — §3.6 fixed this position in advance | Performance | ✅ **Met as specified** — §7.19–§7.20 — latency to 26 sandboxes, per-sandbox memory and maximum concurrency all reported against an unconfined baseline on the C4 device. **No threshold, by §3.6’s position fixed in advance**; the figures are reported and discussed, and P4 was falsified doing it |
| **N2** | This chapter reports "imports clean" and "executed end-to-end" as two separate numbers, never conflated, with the first labelled an upper bound wherever it appears | **This chapter** | ✅ **Met by reporting** — §7.12 (imports-clean, 77 integrations) and §7.17 (**executed end-to-end, a named set of five**) are reported separately and never conflated; §7.17.1 states the ceiling of 11 of 37 rather than computing a rate |
| **N3** | Behaviour on mediator unavailability is specified in advance and tested; the framework refuses rather than degrades silently, including the wrong-cgroup-position case | Security | ✅ **Met** — §7.16.2 — carried by `preflight` rather than a self-test: the framework refuses to start when the memory controller is absent (§5.7.4) or the supervisor is in the wrong cgroup position (§6.4.1). Both are stated failure modes |

> **The Verdict column was added by Stage 5's read-through, 2026-09-04, and the criteria were
> not touched.** §7.4 claimed that every requirement "appears in §7.5 with a verdict"; it did not.
> Seventeen of twenty rows carried a *verdict source* — the section that would decide them — and
> only F2, S4 and S9 carried a verdict, because only those three had been updated in place. Every
> verdict was recoverable from the chapter and none is new, but **the register an auditor
> reconciles against the artifact should not require reconstructing from seventeen sections.** The
> Criterion column is verbatim as frozen on 2026-09-02, the Verdict source column is what it
> always said, and the fourth column is the reconstruction. Found by reading the report as one
> document, which is the fifth consecutive pass over this project's prose to find a sentence
> rather than a number.

> **Both blocked rows are now closed — §7.25 (2026-09-03), and the paragraph below is left as
> written.** The verdicts in the F2, S4 and S9 rows above are updated in place, which is this
> table's one deliberate exception to §7.1's freeze: §7.5 is the register an auditor reconciles
> against the artifact, and a criteria table carrying stale verdicts fails that reconciliation in
> the way §7.5's own closing sentence says silence would. The *criteria* are untouched. The
> paragraph that follows recorded the position on 2026-09-02 and is the evidence that the rows
> were named in advance rather than discovered late, so it keeps its text.

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

> **The right-hand column points at a methodology section for ten of these eleven rows, and
> §7.21.3 is the correction — this table keeps its text.** (This note said *five* until
> 2026-09-06; §7.21.3 corrects the count and separates the seven that were genuinely
> mis-pointed from the three for which §7.4 is the discharge.) §7.4.1 and §7.4.3 are *methodology* sections: an obligation is not discharged by a
> section that promises to discharge it. §7.21.3 names the results section that actually discharged
> each, and the uniform-corpus row was still owed when it was written (closed the next day by
> §7.23). **The pointer is added 2026-09-04 by Stage 5**, because a reader consulting this table
> without it is sent to the wrong place five times.
>
> **What this table does not contain is the more useful observation.** C1's verification was never
> entered here as an obligation, because §7.4.1 stated it as an accomplished fact rather than as
> something owed — and §7.28 records that the fact was not true. **A promise can be swept for; a
> false statement of completion cannot**, which is why the sweep that corrected these five rows
> could not see C1.

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

> **Discharged in §7.23.** The uniform sample was drawn (seed 20260902) and both arms run: **92%
> confined, 92% unconfined, identical failure sets.** The two corpora share 2 of 40 members, so
> this is close to an independent sample. The clause about HACS stands unchanged.

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
   number inside it carries its own qualification. *(The uniform draw came in at 40 of 40 rather
   than 37 — §7.23.1. The sentence is left at its planning figure.)*

**A fifth, added by §7.26 rather than foreseen here.** This list names what the chapter cannot
demonstrate. It should also have named what it would not *attempt*, and it missed one: **T12, a
malicious update through the authorised path, is the only threat in either register whose control
this chapter neither demonstrates nor declares unevaluable** (§7.26.5). Naming it here in advance
was the whole point of §7.1's third consequence, and the omission is recorded rather than repaired
in place.

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
**median of 2**, and for **twelve of the 37 it sets up none at all** (§6.13; the *declared* figure
is 18 of 37 with a median of 1 — §7.26.6, finding 5). The two reach identical import-level
compatibility.

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

*(The unconfined column is thirty-two rows against the confined column's thirty-eight, and both are
as measured. The confined arm's **seven mediated attacks have no unconfined counterpart** — §7.13.3
below — and collapse into the single `UNMEDIATED` row: 31 non-mediated attacks plus 7 mediated is
38, and 31 plus 1 is 32. Noted so the column can be added up; §7.26.6 records why it was not.)*

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

All eight self-tests, on the C4 device, 2026-09-02 — a count this section carries at its date;
**the 2026-09-03 run passes eighteen**, tabulated in §7.26.7:

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

> **Superseded by §7.25 (2026-09-03) for F2 and S4.** This section is a snapshot of 2026-09-02
> and is left as written; the egress proxy was built between then and now, and both rows are
> now ✅ Met. What follows in this section is otherwise unchanged.

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
integration is fine, and only setting it up reaches the socket. It bears directly on `01_PLAN.md` §9.5's open
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
> is still true as a statement about mechanisms; the first is not evidenced.** `01_PLAN.md` §9.5's decision
> must not be taken on it.
>
> **Re-established on the evidence this paragraph specified — §7.27.4 (2026-09-03).** The bar set
> below is *"an integration is needed which works unconfined and fails confined on discovery, and
> this corpus has not produced one."* It has now: `nordpool` loads unconfined and failed confined
> on the identical `IP_ADD_MEMBERSHIP` call in the identical library. The restored finding is
> **sharper than the withdrawn one and points elsewhere** — the cost fell on an integration that
> does no discovery at all, because the platform's own HTTP helper joins a multicast group as a
> side effect of building a DNS resolver. This section's withdrawal was correct on the evidence it
> had, and correct about what would restore it.

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

**Run 2026-09-02**, `experiments/egress_demand/`. `01_PLAN.md` §9.5 leaves one decision open — whether to
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
twenty-three and pointed `01_PLAN.md` §9.5 at a number the integrations had no part in producing.

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

### 7.18.3 What this means for the egress decision (`01_PLAN.md` §9.5)

The decision is better informed than it was and it has not been taken here. What the evidence
now supports:

- **The need is real and large.** 81% declare a network reach. An artifact that cannot serve any
  of it leaves F2 unverified and most of the corpus non-functional beyond import.
- **The proxy as scoped closes about half of it.** 41% cloud-facing, served directly; 41%
  local-facing, served only through the non-public flag, which is a further design decision
  §5.10.3 provides for but which §5.8.2's scope item does not mention.
- **No measured evidence yet that confinement's *current* network position costs compatibility.**
  §7.17.5 withdrew the one candidate. The argument for building the proxy remains the one `01_PLAN.md` §9.3
  ranks first — a requirements register that does not match the artifact — not a measured
  compatibility loss.

> **Extended, not corrected, by §7.24 (2026-09-03).** This section closes by saying no
> observational method can answer questions about egress, because demand appears at setup and 26
> of 37 need a credential first. That holds for **how much** egress is wanted and it does not
> bind **what shape** it has: a config flow validates a credential *by making the call*, so the
> resolution, the connection and the handshake all complete before the 401. §7.24 measures the
> repertoire on that basis and finds three of §5.10.3's assumptions wrong. The claim above about
> *demand* is unchanged.

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
(§6.13: twelve have no components set up at all, and the median set up is two — §7.26.6, finding
5). Three points, three sandboxes each:

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
sentence. **Closed in §7.22**: `cpu_percent` is enforced, so the sentence is now true when it is
produced, and the latent defect cannot be reached.

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

> **Done the same day, and §7.22 reports it — including the half this paragraph got wrong.**
> The clause now reaches enforcement and each bound is verified by a sandbox exceeding it. But
> `io.max` was not a choice between two options: the `io` controller is **not delegated to a
> user manager**, so an unprivileged supervisor cannot implement it at any effort. The
> alternative this paragraph offered as the weaker one was the only one available, and taking it
> produced a better result than the fix would have — §6.4.1's *present-but-not-permitted*
> distinction, found a second time in a place §6.4.1 did not reach. S9's row in §7.5 is ✅
> against narrowed wording.

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

§7.8 listed eleven inherited obligations, and **ten point at a §7.4.x section** — which are
*methodology* sections. An obligation is not discharged by a section that promises to discharge
it. Seven of the ten are corrected below; the other three are a different kind, and the
note beneath the table says why.

| Owed from | Obligation | Now discharged in |
|---|---|---|
| §6.14.6 | Run the baseline arm | **§7.12** |
| §6.5.3 | Latency at realistic sandbox counts | **§7.19** |
| §6.8.3 | Decide whether `fsync` per decision is affordable | **§7.20.1** — yes, at 3.6 ms and 63× headroom |
| §6.9.4 | What `resources.memory_mb` costs a legitimate integration | **§7.20.2** — *withdrawn*, P5 falsified |
| §3.6 (N2) | Report both numbers separately | **§7.12 and §7.17** |
| §6.3.3 | Check failures against the harness before charging them to the design | **§7.17.4**, where three of five were harness faults |
| §5.14 | Uniform-corpus re-run | **Still owed** — §7.10's item 7, not run |

**The three that stay where they are, and the distinction that decides it.**

> **Added by Stage 5's third pass (2026-09-06), which found the count above wrong.** This section
> and §7.8's note both said *five* rows were mis-pointed. Ten of §7.8's eleven rows point at a
> §7.4.x section, and the table above corrects seven. The number is corrected in place — a
> miscount has no reasoning to protect (§7.21.7) — but the more useful repair is the rule the
> exception list was standing in for.

**An obligation owed a *measurement* is not discharged by a section that plans the measurement.
An obligation owed a *practice* is discharged by the section that adopts the practice.** Every
row in the table above is the first kind: run the baseline arm, measure the latency, decide
whether `fsync` is affordable. The three not in it are the second:

| Owed from | Obligation | Discharged by adoption in | And exercised at |
|---|---|---|---|
| §5.7.4, §6.4.1 | State S9's boot-time precondition whenever S9 is evaluated | §7.4.3 | §7.5's S9 row, §7.22.2 |
| §6.6.5 | Negative cases assert on **why** something was refused, never that it was | §7.4.2 | §7.16.1 — seven behaviours, seven denials, **seven distinct clauses** |
| §6.4.5 | An absence is not evidence of confinement working until the grant is shown to have arrived | §7.4.2 | §7.17.4, where three of five failures were harness faults |

For these, §7.4 **is** the discharge: the obligation asks that the chapter behave a certain way
throughout, and the methodology section is where that behaviour is committed to. The right-hand
column is the check that it was honoured, not a second discharge. With the two kinds separated,
all ten rows resolve and no exception list is needed — which is what the miscount was concealing.
The distinction is worth stating because **it is the same one §7.28 turns on**: C1 was written as
a completed *measurement*, so it needed a result and had none, and no sweep of promises could
see it.

### 7.21.4 The schedule, closed out

§7.10's eight items: **1–6 are complete** (§7.12, §7.13–§7.14, §7.19, §7.20.3, §7.20.1, §7.20.2).
**Item 7, the uniform-sample corpus, was not run** and is the only scheduled measurement this
chapter did not attempt; §7.9's external-validity limit therefore stands undischarged and
Chapter 8 carries it. **Item 8 is conditional on a decision not yet taken.**

> **Item 7 was run the same day — §7.23, and this paragraph is left as written.** All eight
> scheduled items are now complete or conditional, and §7.9's external-validity limit is
> discharged rather than carried: 92% confined and 92% unconfined on a uniform draw sharing 2 of
> 40 members with the head corpus. §7.21.5's scorecard below is superseded by §7.23.7, which
> scores eight predictions rather than five.
>
> **And item 8 is no longer conditional — §7.24 and §7.25 (2026-09-03).** `01_PLAN.md` §9.5's decision was
> taken, the proxy was measured for before it was built, and F2 and S4 are both ✅ Met. All eight
> scheduled items are complete. The sentence above is left as written because it was true on
> 2026-09-02 and the date is the evidence.

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


## 7.22 S9, wired to the manifest — the one finding this chapter acted on

**Run 2026-09-02**, `framework/confine/selftest_resources.py`, on the C4 device inside a
systemd user scope. §7.21.1 found that S9 was reported against a criterion two thirds of which
nothing enforced, and said the fix was small. It was, and running it produced a measurement that
changes what S9 can honestly claim — so the fix is reported here rather than deferred to
Chapter 8's future work.

### 7.22.1 What the clause now reaches

`ResourceLimits` (in `cgroup.py`) is the single type both the manifest and the enforcement path
speak. `SandboxCgroup.create` takes one and applies every field; **there is no longer a
signature that accepts a limit and drops it**, which is what the previous `memory_max=` /
`pids_max=` keywords permitted and what every harness in the repository was doing. `Manifest`
grew a `resources` property, values are validated at parse time against stated bounds, and the
two paths that run real integrations — `compat.py` and `endtoend.py` — take their bound from the
integration's own clause instead of from a literal.

Each bound is verified by a sandbox **trying to exceed it**, per §6.4.2's rule that a check
exercising a different mechanism from the one the supervisor uses is not a check:

| Bound | How it was checked | Result |
|---|---|---|
| `memory_mb` | 512 MB asked against a 64 MB cap | Killed, `oom_kill=1` |
| `max_processes` | 200 forks attempted against a cap of 16 | **15 succeeded**, then the kernel refused |
| **`cpu_percent`** | a busy loop capped at 25% of one processor | **25.1% consumed over 2.12 s, 1.55 s throttled** |
| **`disk_mb`** | 64 MB written into an 8 MB private `/tmp` | **8 MB written, then `ENOSPC`** |
| An unenforceable declared limit | `create` pointed at a cgroup the kernel refuses | **`PlacementUnavailable`**, naming the clause |

Seven parse-time cases run alongside them, including the one §6.6.5 demands: a **well-formed**
clause that must be *accepted* and arrive intact, so the suite is not passing by rejecting
everything. **13 of 13.** All twelve pre-existing suites still pass, including the adversary
suite at 21 blocked / 6 denied / 10 empty / 1 permitted with neither canary reached.

> **That split is over thirty-eight attacks, not §6.9's thirty-seven, and Stage 5's third pass
> found that the report never says so (2026-09-06).** §7.13.4 does two things to the adversary
> suite and states only the first as a number: it moves one attack from `BLOCKED` to `EMPTY`
> over §6.9's original thirty-seven — *21 blocked / 9 empty* becoming **20 / 10** — and it
> **adds** a thirty-eighth, the direct memory allocation that demonstrates S9 independently of
> what the sandbox happens to contain. The new attack is OOM-killed, so it is `BLOCKED`, and
> **20 + 1 = 21**. Every figure in §6.9, §7.13.4 and this paragraph is correct at its own date;
> what was missing is the one line that reconciles them, and a reader meeting *20 blocked* in
> §7.13.4 and *21 blocked* here had no way to recover it. Confirmed against the artifact: the
> suite prints `BLOCKED 21  DENY 6  EMPTY 10  PERMIT 1`.

### 7.22.2 Disk is narrower than §4.10.1 wrote it, and the reason is measured

§4.10.1 wrote S9 as bounding *"CPU, memory and disk"*. Disk turns out to be two resources and
this framework can bound only one of them.

| | Mechanism | Available unprivileged? |
|---|---|---|
| **Disk space** a sandbox consumes in its own scratch | tmpfs `size=` on the private `/tmp` | ✅ **Yes** — and now from `resources.disk_mb` |
| **Disk I/O bandwidth** | cgroup v2 `io.max` | ❌ **No** |

The `io` controller is **present on the host and not delegated to a user manager**. Writing
`+io` to the delegated subtree's `cgroup.subtree_control` fails with `ENOENT`, and `io.max`
never appears in a child cgroup, while `cpu`, `memory` and `pids` all arrive:

```
host root delegates ['cpu', 'cpuset', 'io', 'memory', 'pids']
this user's subtree has ['cpu', 'memory', 'pids']
```

**That is §6.4.1's distinction one layer down.** §6.4.1 found that a controller being present is
not this supervisor being permitted to use it, and drew the rule about where the supervisor must
run. Here the same gap appears within a supervisor that *is* correctly placed: `cpu` and `memory`
are delegated and `io` is not, and no position on the host changes it. The only route to
bounding I/O bandwidth is privilege or a systemd unit override on the user manager, and §5.7.4
chose an unprivileged design.

**So S9's disk clause is narrowed on evidence, and the narrowing is stated rather than absorbed.**
S9 now reads: *the framework bounds CPU, memory, process count and the disk space a sandbox
writes into its own scratch. Disk I/O bandwidth is not bounded.* §7.21.1 named this as the
legitimate alternative to implementing `io.max` — *"a requirement narrowed on evidence is
legitimate, a requirement quietly unmet is not"* — and this is that alternative taken.

**Two things stay uncovered and neither should be read out of the table above.**

- **`/sandbox/data` is not bounded.** The disk cap is the private `/tmp`'s tmpfs. An
  integration's own writable directory is a bind mount of a host directory, and bounding it
  needs filesystem quotas, which are a privileged operation. An integration can still fill the
  user's disk through its own data directory.
- **I/O bandwidth is a live T16 vector.** A sandbox cannot exhaust *space* outside its scratch
  but it can saturate the device, and nothing here stops it. **This is a residual risk the
  evaluation generated, and §4.11 could not have carried it**: the `io` controller's
  non-delegation is a property of the host measured here, not of the design modelled there. It is
  entered as **R7** against §4.11 (2026-09-04) rather than left as an unnumbered note, on the
  symmetry §4.10.1 already established — Chapter 4 generated a requirement Chapter 3 could not
  have written, and Chapter 7 generates a residual risk Chapter 4 could not have written.

### 7.22.3 The one place absence is not denial

Every other capability in this design denies by absence — S6, and §6.9.1's whole argument.
`resources` cannot, and the asymmetry is worth stating because it looks like an inconsistency
and is the opposite of one.

If an absent `resources` clause meant "no limit", then **the integration that declares nothing
would run unbounded** — inverting default-deny for the single requirement whose threat, T16, is
an integration consuming everything. Absence therefore means *the framework's* bound rather than
*the integration's*: 640 MB, 64 processes, 64 MB of scratch, CPU unset. A declaration can only
be read as a request to be bound **more** tightly than the default, never less.

That is the general rule the clause obeys, and it explains why `resources` sits in a permissions
manifest at all despite granting nothing: **it is the one capability whose declaration is a
constraint on its declarer.** Chapter 8 should say so, because a reader who has absorbed §6.9.1
will otherwise read `resources` as a hole in default-deny.

### 7.22.4 What this changes in the chapter

- **§7.5's S9 row moves from ⚠ to ✅**, with the narrowed wording of §7.22.2 rather than
  §4.10.1's. Two rows still fail — **F2 and S4, both egress** — and they are the only two.
  *(Both closed the next day: §7.25. All twenty rows now carry a verdict, and this sentence is
  left at its date per §7.26.6, finding 4.)*
- **§7.21.1's F4 half is closed.** `describe.py` renders a `cpu_percent` clause that is now
  true, and a `disk_mb` clause that is also true. The latent false sentence §7.21.7 recorded
  can no longer be produced.
- **Every memory figure in §6.11–§6.14 was measured against the harness's 640 MB literal, not
  against a declaration**, and none of the corpus integrations declares a `resources` clause, so
  no number moves. That is worth checking rather than assuming, and it was: `compat.py` now
  takes `max(declared, 640)`, so the profile measurements reproduce exactly.



## 7.23 The uniform-sample corpus — the last scheduled measurement

**Run 2026-09-02**, predictions registered in `notes/ch7_uniform_prediction.md` and committed
before the corpus was drawn. §7.10's item 7 was the only scheduled measurement this chapter had
not attempted, and §7.9 names the threat it answers: every compatibility figure so far — 46%,
57%, 70%, 84%, and §7.12's zero — was measured on the **most-installed** integrations, and so
answers *what most installations run* rather than *what most integrations do*.

`fetch_hacs_corpus.py` gained `--uniform SEED`, which draws from the whole HACS index with equal
probability. Seed **20260902**, 40 requested, recorded in the manifest so the draw can be
repeated. Everything else is held constant: same release, host, interpreter, profile
(`declared` + core package set), harness and `inspect()` function.

### 7.23.1 The two corpora are barely the same population

| | Head-weighted (§6.14) | **Uniform (seed 20260902)** |
|---|---|---|
| Requested | 40 repositories | 40 repositories |
| Fetched | 39 | **40** |
| **Distinct integrations measured** | **37** | **40** |
| Install count, median | **16,294** | **48** |
| Install count, range | 7,816 – 379,326 | 0 – 26,109 |
| Installs represented, total | **998,478** | 46,979 |
| Python files, median | 19 (max 1,015) | **11 (max 143)** |
| Declares no components at all | 18 of 37 | **26 of 40** |
| Declared components, median | 1 | **0** |
| Declared packages, median | 1 | **0** |
| Overlap between the two | — | **2** (`bermuda`, `browser_mod`) |

**Two of forty is the number that justifies having run this at all.** The corpora share 5% of
their members, so this is close to an independent sample of the same ecosystem rather than a
re-slicing of the same integrations. The install columns show why: the head corpus represents
**twenty-one times** the deployed reach of the uniform one, from the same number of repositories
requested. Neither figure is wrong; they are answers to different questions, which is what §7.4.1
said when it scheduled this.

> **The three rows above that separate *repositories* from *integrations* were added by Stage 5's
> third pass (2026-09-06), and the install figures are restated over the smaller population.**
> The head corpus requests forty repositories and measures **thirty-seven integrations**, and the
> gap is not the one fetch failure alone. **Three domains are claimed by two different repositories
> each** — `scheduler` (`nielsfaber/scheduler-component` and `Smiley73/ha-scheduler`), `govee`
> (`LaggAt/hacs-govee` and `lasswellt/govee-homeassistant`) and `solarman` (`davidrapan/ha-solarman`
> and `StephanJoubert/home_assistant_solarman`). An integration is stored as
> `custom_components/<domain>/`, so a domain is a single slot and the later fetch takes it.
>
> The figures previously given — 39 fetched, median 14,793, total 1,018,398 — were computed over
> the thirty-nine fetched **repository entries**, while the component and package rows beneath them,
> and every compatibility figure in this report, are over the thirty-seven **integrations**. One
> column was therefore describing two populations. Restated over the thirty-seven measured, the
> median rises to 16,294 and the total falls to 998,478; the range, the Python-file figures and the
> overlap are unchanged, and **the reach ratio moves from 21.7 to 21.3, which is why the sentence
> above now reads twenty-one rather than twenty-two.** No result in this chapter depends on it.
>
> **The reproducibility consequence is the part worth carrying forward.** Which repository won each
> collision is not recoverable from the manifest: for `govee` and `solarman` both candidates are
> recorded `ok`. It is recoverable only by inspecting the corpus on disk, where the winners are
> `lasswellt/govee-homeassistant` (46 Python files, against the loser's 5) and
> `StephanJoubert/home_assistant_solarman` (8, against 36). **Those are materially different
> integrations, so "`govee` imports clean" names a different artifact depending on which was
> fetched.** This is the same weakness §7.29.2 records from the other side — the corpus manifest
> pins `HEAD` and stores no content hash, so it is a weaker record of what was measured than the
> chapter has been treating it as. The uniform corpus has no collisions, so its forty entries and
> forty integrations coincide and its column needs no such distinction.

### 7.23.2 P6 is wrong, and wrong in the direction the prediction named

**P6 predicted the uniform sample would import clean 10–30 points *below* the head sample's 84%.**

| | Imports clean, all platforms | Peak memory, median |
|---|---|---|
| Head-weighted, `declared` + core | 31/37 — **84%** | 119.7 MB |
| **Uniform, `declared` + core** | **37/40 — 92%** | **96.9 MB** |

**The tail does better, and it is cheaper.** +8 points and −22.8 MB per sandbox. The prediction
was not merely wrong in magnitude but in sign, and it is reported as registered rather than
adjusted — the fifth prediction this chapter has scored wrong out of eight.

The reasoning behind P6 was that tail integrations are less maintained and so more likely to have
rotted against a release that moved. That effect is real and visible — `lightwave2` fails on a
constant Home Assistant deleted, exactly as `eufy_security` does in the head corpus — but it is
**smaller than the effect the prediction's own counter-argument named**, which the last three rows
of §7.23.1 measure directly:

> A tail integration declares a median of **zero** components and **zero** packages, against the
> head's one and one, and 26 of 40 declare no components at all. It is usually a single sensor
> file talking to one HTTP endpoint. **The head corpus's failures were overwhelmingly missing
> packages and missing components — and an integration that asks for nothing cannot fail to
> receive it.**

That is the more useful form of the result. Compatibility here is not a property of confinement
and not really a property of maintenance either; **it tracks how much of the platform an
integration reaches for**, and the popular integrations reach for more because they do more.

### 7.23.3 P8 is wrong in both halves

**P8 predicted more corpus artefacts in the tail** — non-standard repository layouts, failed
fetches, integrations unloadable for reasons that are nobody's design decision.

| | Head | Uniform |
|---|---|---|
| Fetch failures | 1 of 40 | **0 of 40** |
| Non-standard layout | 0 | **0** — all 40 use `custom_components/<domain>/` |
| Corpus artefacts among failures | **2** (`hacs`, `spook`) | **0** |

Every one of the forty followed the standard layout and every one downloaded. The head corpus's
two artefacts are both consequences of *popularity* rather than obscurity: `hacs` bundles its
frontend at release-build time because it ships releases, and `spook` uses a non-standard layout
because it is large enough to have opinions. **A small integration has nothing to package
unusually.**

> **A third class of corpus artefact was found by Stage 5's third pass and it points the same way
> (2026-09-06).** The row above counts artefacts *among failures*, which is the right thing for
> P8's purposes and misses one that causes no failure: **the head corpus contains three domain
> collisions and the uniform corpus none** (§7.23.1). Two repositories claiming `govee` is a
> consequence of popularity in exactly the sense this paragraph describes — a domain worth
> reimplementing is a domain someone already implemented. It makes P8 wrong in a third way rather
> than a second, and it is recorded here because a reader who finds the collisions in §7.23.1 will
> otherwise reasonably ask why the artefact row does not mention them.

### 7.23.4 P7 holds — the design's compatibility cost is zero on a second corpus

**P7 predicted the confined and unconfined arms would fail on the same set, or within one of it,
and named what it would mean if they did not**: that §7.12's zero was an artefact of measuring
only well-maintained code.

| | Imports clean, all platforms | Failures |
|---|---|---|
| Uniform, **confined** | 37/40 — **92%** | `bermuda`, `lightwave2`, `next_rocket_launch` |
| Uniform, **unconfined baseline** | 37/40 — **92%** | `bermuda`, `lightwave2`, `next_rocket_launch` |
| **Broken only by confinement** | — | **none** |
| **Broken only unconfined** | — | **none** |

**Identical sets, identical error strings, `failures(design) = 0` for the second time on a corpus
that shares 5% of its members with the first.** §7.12 established this on the head-weighted
corpus and could not say whether the result was a property of the design or of measuring popular,
actively maintained code. It is the design.

The asymmetry underneath it is sharper here than in §7.12. The unconfined arm has **53 components
available** to every integration; the sandbox sets up a **median of zero** and a maximum of seven.
§7.12 measured 52 against 2 and called that the finding; on a corpus of simpler integrations the
gap widens to 53 against 0 and the compatibility outcome still does not move. **Whatever those
components are for, importing a community integration and bringing up its entity platforms is not
it.**

### 7.23.5 The three failures, composed rather than counted

A percentage would hide what §6.14.3 established is the interesting part:

| Integration | Why it failed | Whose problem | Fails unconfined too? |
|---|---|---|---|
| `bermuda` | `ModuleNotFoundError: aiofiles` | **The design's** — an undeclared package | ✅ Yes |
| `lightwave2` | `cannot import name 'COLOR_MODE_BRIGHTNESS' from homeassistant.components.light` | Home Assistant 2026.8.3 — the constant is gone | ✅ Yes |
| `next_rocket_launch` | `ImportError` importing its own `sensor` module | Its own, and the baseline is what settles it | ✅ Yes |

**`bermuda` is the same integration failing on the same package as in §6.14.4**, and it is one of
the two members the corpora share — so this is determinism rather than replication, and it is
worth saying which. What *is* new is the rate: the head corpus had **three of 37 (8%)** failing on
an undeclared package, this one has **one of 40 (2.5%)**. §6.13.3's bound on how far "the
declaration always already exists" can be relied on is therefore **looser in the tail than in the
head**, in the same direction and for the same reason as §7.23.2 — a simple integration declares
less because it needs less.

**`next_rocket_launch` is the case that shows why the baseline is not optional.** Its error is
opaque — `ImportError: Exception importing custom_components.next_rocket_launch.sensor`, with no
missing name and no missing module. Read from the confined arm alone it is exactly what a
confinement failure would look like: something the sandbox did not provide, unnamed. The
unconfined arm produces the identical string, so it is the integration's own defect and not this
framework's. **That is the third time in this chapter that a baseline has stopped a
misattribution** — after §7.13's three attacks blocked in both arms and §7.17.5's withdrawn
multicast finding.

### 7.23.6 What this does and does not settle

**Settled.** §7.9's external-validity threat on corpus selection is discharged, not merely
restated. Both questions now have an answer measured the same way:

| Question | Corpus | Confined | Unconfined | Design's cost |
|---|---|---|---|---|
| What do most *installations* run? | Head, 37 | 84% | 84% | **0** |
| What do most *integrations* do? | Uniform, 40 | **92%** | **92%** | **0** |

**Not settled, and Chapter 8 owes both.**

- **Neither corpus generalises beyond HACS.** §7.9 says so and this does not change it.
- **Both are import-level.** §7.17's executed end-to-end arm ran on five head integrations and
  has no uniform counterpart; the ceiling there was credentials, and a tail integration needs
  them just as much.
- **One draw, one seed.** A single uniform sample of 40 has real sampling error and no confidence
  interval is claimed. The seed is recorded so the draw can be repeated or extended.

### 7.23.7 The prediction scorecard, now at eight

| | Registered, as written in §7.6 and `notes/ch7_uniform_prediction.md` | Outcome |
|---|---|---|
| P1 | Baseline **34/37** | ❌ **Wrong** — 31/37 (§7.12.3) |
| P2 | The baseline **passes** the three `aiofiles` integrations | ❌ **Wrong** — it fails all three (§7.12.3) |
| **P3** | **Confinement's compatibility cost is 0–3 integrations of 37, 0–8 points** | ✅ **Right**, at the floor — **0** (§7.12.2) |
| P4 | Median ≤2×, p99 ~10× worse at 26 sandboxes | ❌ **Wrong** — both 16–20×; saturation, not tail queueing (§7.19.2) |
| P5 | S9 kills a legitimate large-file reader | ❌ **Falsified** — never killed; page cache is reclaimable (§7.20.2) |
| P6 | The uniform sample is 10–30 points *below* 84% | ❌ **Wrong in sign** — 92% (§7.23.2) |
| **P7** | **The design's cost stays zero, or within one, on a uniform sample** | ✅ **Right** — zero (§7.23.4) |
| P8 | More corpus artefacts in the tail | ❌ **Wrong in both halves** (§7.23.3) |

**Six of eight wrong, none revised.** The two that held are the two that were predictions *about
the design* rather than about the world — and they are the same prediction measured twice: P3 that
confinement's compatibility cost would be at or near zero, and P7 that a zero measured once would
hold on a near-independent sample. Every wrong one was a prediction about what the ecosystem or
the kernel would do. Chapter 8 should make that distinction rather than reporting a bare 6-of-8,
because it is the more defensible claim: **the design behaved as designed; the world did not behave
as assumed.**

> **The rows above were corrected in place on 2026-09-03 — §7.26.6, finding 1.** The first version
> of this table paraphrased P1 and P2 into claims §7.6 does not make, and replaced P3 with an
> observation from §7.13 that was never registered as a prediction. The counts and the argument are
> unchanged; the wording is now the register's own, and a scorecard that misquotes its register has
> no reasoning the leave-it-and-point convention exists to protect.

## 7.24 What egress actually looks like, measured before the proxy is built

**Run 2026-09-03**, `experiments/egress_shape/`. `01_PLAN.md` §9.5's decision is taken: build mediated egress.
This section is the measurement that decides *what to build*, and it is placed before the artifact
rather than after it because the alternative is discovering a wrong assumption inside working code.

§5.10.3 fixed the `network.egress` clause in Chapter 5, and it carries three assumptions that no
measurement had touched:

| # | Assumption | Where it lives |
|---|---|---|
| 1 | Egress is **hostnames**; the clause has no port field | §5.10.3's schema |
| 2 | A name becomes an address through `socket.getaddrinfo`, which is where a mediator interposes for T11's resolve-then-pin | §5.10.3, and §5.10.5's "checking the name is not checking the thing" |
| 3 | Egress means **outbound TCP**; the clause cannot express UDP, multicast or an inbound listener | §5.10.3's schema |

Twelve integrations from §7.12's head corpus were set up in a **full unconfined Home Assistant
with real network access** — the §7.17.5 arm, same release, host, interpreter and the same
`drive_flow` — and driven through their own config flows with a recorder watching every
resolution, connection, datagram, TLS wrap, bind and multicast join.

### 7.24.1 Why this is measurable at all, when §7.18 said it was not

§7.18 closed with a strong claim, and it needs answering rather than quietly stepping around:
*no observational method can answer this*, because egress demand appears at setup and setup needs
a credential for 26 of 37 (§7.17.1).

That is right about **how much** and it does not bind **what shape**, for one reason: *a config
flow validates a credential by making the call.* A wrong API key still produces the name
resolution, the TCP connection, the TLS handshake and the request, and only the last of those is
refused. Every mechanism a mediator would have to implement has already run by the time the 401
comes back. The credential wall stands where §7.18 put it and it is not in front of this question.

What this therefore does **not** claim, and Chapter 8 should not be allowed to borrow it as
though it did: polling frequency, sustained connection counts, or how many integrations would
use egress in service. It claims the **repertoire**.

### 7.24.2 Assumption 2 fails, and it fails uniformly

| | `getaddrinfo` | `aiodns` | share via `aiodns` |
|---|---|---|---|
| Across twelve integrations | **120** | **3,073** | **96%** |

Per integration the share is 93–97%, with no outlier. That uniformity is the finding: this is not
a property of any integration's taste in libraries but of the platform. `aiohttp_client.py:479`
gives **every** Home Assistant client session an `AsyncDualMDNSResolver` built on `aiodns`, which
resolves through `pycares` in C and never calls `getaddrinfo`.

**A mediator interposing at `getaddrinfo` would see one name in twenty-five.** The design's
enforcement point, as §5.10.3 describes it, is in the wrong place.

The correction is not to the principle but to its location, and the principle survives intact.
T11 requires that the address connected to be the address that was checked. What the measurement
adds is *where the only opportunity to do that is*: **the name exists at the resolver and nowhere
after it.** By the time `connect` is called the destination is an address — `pirateweather`'s
connect is to `108.157.98.116:443` via `aiohappyeyeballs/impl.py:210`, with no hostname anywhere
in the call. Resolution and connection happen in **different libraries**, so an enforcement point
at either one alone has either a name it cannot connect or an address it cannot judge.

This makes resolve-then-pin *more* structural than §5.10.5 argued, not less. If the sandbox's
resolver returns a placeholder that only the mediator can map back to a real destination, then
the sandbox never possesses a routable address at all, and the check cannot be raced because
there is no window between it and the use — there is no address in the sandbox to race with.
§5.10.3 is not edited; it gains a pointer here, as §6.3.2 and §6.4.1 did to Chapter 5.

### 7.24.3 Assumption 1 fails — the clause needs a port

Ports the integrations themselves reached: **443** (five integrations), **8123**, **6445**,
**20086**. `frigate` additionally attempted `ccab4aaf-frigate:5000` over plain HTTP and got no
further than a failed resolution.

A clause that declares `["api.example.invalid"]` cannot express any of the last three. Worse for
S6, it cannot express them *in either direction*: it can neither grant port 6445 nor withhold it,
so an integration granted a host is granted every port on that host. That is a grant wider than
anything the manifest says, which is the property §5.10.4 exists to prevent in `services.call`
and which nothing was enforcing here.

### 7.24.4 Assumption 3 fails in one half and holds in the other

**UDP is real.** `midea_ac_lan` sent **18 datagrams** from `config_flow.py:406`, nine to port
6445 and nine to 20086, on `SOCK_DGRAM`. An egress path that serves only TCP does not serve it.

**Inbound is not.** No integration in the sample established a listener. Every bind observed was
either `AF_NETLINK` — 79 of them from `scapy`'s route queries, which are not network operations
at all — or an ephemeral local port of the kind every UDP client binds before sending. The
absence of an inbound clause in §5.10.3 is **adequate for this sample**, which is worth recording
as a positive result about the schema rather than leaving as an untested silence.

### 7.24.5 Two findings that were not being looked for

**There are three network stacks, not one.** `aiohttp` with `aiohappyeyeballs` (`pirateweather`,
`nordpool`, `sonoff`), `urllib3`/`requests` synchronously (`localtuya`, ten connections to
`openapi.tuyaeu.com`), and a raw socket (`midea_ac_lan`). TLS follows the stack: `wrap_bio` over
a memory BIO for the async path, `wrap_socket` for the synchronous one, both appearing in the
same sample. A shim covering only aiohttp covers neither of the others — and a recorder watching
only `wrap_socket` would have reported a corpus with no TLS in it at all, which is why
`selftest_netshape` tests both paths.

Every wrap in the sample had `check_hostname` set. **The mediator therefore sees destination and
never content**, by construction rather than by policy: TLS is established end to end between the
integration and the remote host, over a descriptor the mediator supplies. §4.10 rates **T09 —
exfiltration through a declared host — as Retained, structural**, and that position is now
measured rather than assumed.

**A popular integration's ordinary operation is the T10 shape.** `alexa_media` — 29,308 installs,
the fourth largest in the corpus — connects from `config_flow.py:329` to `192.168.11.109:8123`,
which is the gateway's **own** Home Assistant. It is not an attack; it is how its login proxy
works. §5.10.3 puts non-public destinations behind a separate explicit flag for T10, and this is
the first measured evidence about what that flag costs and who needs it: not a rare case, and not
one whose declaration a user could evaluate without knowing what the address means.

### 7.24.6 The recorder's blind spot, bounded rather than caveated

The in-process recorder is paired with `strace -f -e trace=network`, which attributes nothing and
misses nothing. Counting **egress only** — `AF_INET`/`AF_INET6` connect and sendto — the recorder
saw 74–87% of what the kernel saw, and 42% for `localtuya`.

The first version of this comparison reported the recorder catching about 6%, and that figure was
an artifact of the comparison rather than of the recorder: it counted every `AF_*` mention in the
trace, including roughly 2,000 `AF_NETLINK` and `AF_UNIX` operations per run — route lookups,
interface enumeration, dbus, the log socket — none of which is egress and none of which the
recorder ever claimed to watch. **That is §7.18.2's error committed a second time and caught by
the pairing that exists to catch it**, which is the argument for running both instruments rather
than trusting either.

The residual gap is real and is what a C-level library does below Python's `socket` module. It
bounds the *recorder*, not the design: the artifact enforces at a namespace the kernel owns, not
at a patched module.

### 7.24.7 What the sample could and could not drive

Six of twelve reached the network under their own attribution. The other six did not, and the
reasons divide into three kinds that should not be reported as one number:

| Kind | Integrations | Reading |
|---|---|---|
| Reached the network | `pirateweather`, `nordpool`, `alexa_media`, `localtuya`, `midea_ac_lan`, `sonoff` | the evidence above |
| The flow stopped before its call | `dwd_weather`, `solcast_solar` (`DependencyError: recorder`), `waste_collection_schedule` (corpus layout artifact), `frigate` (its default host does not resolve), `solarman` (`InvalidData: Schema validation failed @ data['inverter_serial']` — the shared credential set cannot invent a serial number) | a limit of the driver and the corpus, not of the ecosystem |
| Broken on 2026.8.3 | `bambu_lab` — `No module named 'aiofiles'` | §6.13.3's finding, met a third time |

`aiofiles` has now blocked integrations in the compatibility run, the end-to-end run and this one.
Chapter 8 already owes it a paragraph; this is the third independent occasion.

> **`solarman` was added to this table by Stage 5's third pass (2026-09-06).** The table listed
> eleven of the twelve and the row was simply absent; both counts in the sentence above it were
> already right. Corrected in place rather than pointed at, on §7.21.7's rule for §6.11.2's
> identical miscount — the leave-it-and-point convention protects reasoning that evidence
> overturned, and an omitted row has no reasoning to protect.
>
> **What is worth more than the omission is what `solarman` was for.** It was selected as
> *"local_polling, Modbus TCP on a non-standard port — tests assumption 1"*: it is the one member
> of the sample chosen specifically to exercise the port question. Its flow never completed, so
> **the sample's designated probe for assumption 1 returned no evidence.** §7.24.3 falsifies that
> assumption regardless, on ports 6445 and 20086 from `midea_ac_lan` and 8123 from `alexa_media`,
> so no conclusion rests on the gap — but a selection defended integration by integration (§7.4.1)
> owes the reader the cases where the defence did not pay off, and this one did not.

### 7.24.8 Two corrections the experiment made to itself

Both are recorded in the code rather than tidied out of it, because each is a mistake the
artifact's own design is meant to prevent and is therefore evidence for it.

**A global answer collided.** To get `nordpool` past its form, `region: "SE1"` was added to the
shared credential set. It worked, and it took `localtuya` from ten connections to **zero** —
Tuya's regions are `eu`/`us`/`cn`. One integration's input had silently changed another's result.
Answers are now per-integration. The parallel is not decorative: it is the same failure §2.4.2
identifies in the closest prior work, where consolidating every plug-in's declarations into one
profile makes the effective policy the union of all of them.

**A heuristic overturned direct evidence.** The platform fetches `alerts.home-assistant.io` during
the integration's phase from `aiohttp/connector.py` — the identical frame a genuine integration
request comes from — so it can only be excluded by destination, and a connect carries an address
rather than a name. Walking back from each TLS wrap to the preceding connect fixed that, and in
doing so removed `alexa_media`'s connection to the gateway, which had been attributed directly to
`alexa_media/config_flow.py:329`. The walk-back no longer applies to connects the integration's
own code made.

That second one is the more instructive. **Attribution by stack walk fails under an event loop**,
because the frame that makes the call identifies the library and never the requester. The
framework proper does not attribute this way and cannot acquire this bug: identity is the socket
the request arrived on (§5.11.2), established before the request exists. The measurement had to
reach for a heuristic precisely because it lacked the property the artifact is built around.

### 7.24.9 What this changes

| | Before | After |
|---|---|---|
| Enforcement point | `socket.getaddrinfo` | **both** resolution seams — `getaddrinfo` and `aiodns` — because the name exists only there |
| `network.egress` clause | hostnames | hostnames **with ports**; a host grant is otherwise a grant of every port on it |
| Transport | outbound TCP | TCP **and** UDP, or UDP refused with a clause pointer rather than by silence |
| Inbound | not expressible | not needed by this sample — recorded as tested, not as overlooked |
| T09 | asserted structural | **measured** structural: every wrap verified, content never visible to the mediator |
| `network.allow_private` | provided for | needed by a 29k-install integration in its ordinary operation |

None of this was reachable by reading Chapter 5 again. Four of the six rows change the artifact
about to be written, and the two that do not are now tested rather than assumed.

## 7.25 F2 and S4, closed — the egress proxy, evaluated rather than merely built

**Run 2026-09-03**, `framework/confine/selftest_egress_sandboxed.py`. §7.24 measured what the
proxy had to be; §5.10.3's schema and §7.24.9's corrections gave it a design
(`notes/decision_network_capability.md`); this section is the artifact built to that design and
evaluated against the two rows §7.5 named as blocked on 2026-09-02.

Everything else built for the egress path is tested piece by piece against a substitute for the
rest of it — `channel.py`'s descriptor passing (`selftest_fdpass`), the mediator's decision path
called as a plain function (`selftest_egress`), real HTTP clients against that same function call
(`selftest_egress_shim`), real datagrams through the relay (`selftest_udp`). That is the right way
to build a mechanism and it is not the claim F2 makes. F2's criterion, fixed in §7.5 before any of
this existed, is *"an integration polling a declared remote API completes successfully while
confined"* — and confined is a namespace with no route to anywhere, not a function call.

### 7.25.1 What ran

One integration, shaped the way §5.6.1 measured the corpus actually looks — a config entry, a
`DataUpdateCoordinator`, a `SensorEntity` — spawned into real namespaces, seccomp and a
memory-limited cgroup, exactly as `selftest_bridge.py` spawns its own subject for F1 and C1. It
declares `example.com:80` and polls it with its own `aiohttp.ClientSession()`, unmodified from
how a community integration would write it.

> **The second half of that sentence is withdrawn — §7.27.2 (2026-09-03), and the text is left as
> written.** A community integration calls `async_get_clientsession(hass)`, and the bare
> `aiohttp.ClientSession()` constructor is the one call that skips the platform's own resolver —
> which in 2026.8.3 instantiates Zeroconf and joins the mDNS group, an operation that **failed in
> this sandbox** until §7.27.3 corrected the namespace. What this section measured is accurate;
> what it could not have known is that the subject it wrote avoided the platform helper that
> broke the sandbox. Only a real integration could show that, and §7.27 is the one that did.

A second, identically-shaped integration runs **at the same time**, in its own sandbox, declaring
`example.net:80`. Each coordinator does two things: fetches its own declared host, then attempts
the *sibling's* declared host. That second request is what turns the run into an S4 test rather
than two unrelated successes — a host that is a valid grant for one identity is attempted, from
inside a genuinely separate confined process, by the identity it was never granted to.

Both sandboxes are registered with the mediator before either is served, and `mediator.serve()`
answers both over one selector loop — which is what makes "concurrent" a fact about two processes
running at once rather than a claim about the order two function calls happened to execute in.

### 7.25.2 Result

| | |
|---|---|
| A's own poll | HTTP 200, published as the entity's state, `found_marker` true |
| B's own poll | HTTP 200, published the same way |
| A's probe of B's host | denied |
| B's probe of A's host | denied |
| Memory | `oom_kill=0` for both, 384 MB cap |

The evidence for the denial is the mediator's own audit record rather than a status code the
sandbox reported about itself, because a confined process is exactly the party whose self-report
should not be trusted for this. Each identity made exactly two `network.egress` decisions, in the
order it made them: `[True, False]`. The second names `/permissions/network/egress` — denied by
absence, S6 — because the sibling's host matches no clause this identity holds.

**Stable across three consecutive runs**, real internet each time. 17 checks, 17 passing, and the
suite fails informatively rather than silently if the target hosts are unreachable at all — a
result it cannot produce is distinguished from one it disproves.

### 7.25.3 Two structural bugs the driver itself caught

Neither is a finding about the egress design; both are about writing a test that spawns two
concurrent confined processes correctly, and both are recorded because getting them wrong would
have produced a false pass.

**`Mediator.policy` is one function shared by every registered channel.** A first draft set it
separately for each sandbox as it was spawned, which silently replaced the first sandbox's
manifest in the policy closure with the second's — sandbox A would have been evaluated against
only B's manifest by the time it made its first request. Both manifests now exist and are combined
into one `acting_policy` before either sandbox is spawned (`prepare()`'s docstring in the file
carries the explanation).

**A cgroup opened with `with` inside a function that returns before the sandbox exits tears the
cgroup down while the sandbox is still running.** `SandboxCgroup.create()` is a plain object —
`__enter__` returns `self`, `__exit__` calls `.remove()` — so nothing requires the `with` form.
The cgroup's lifetime now spans `spawn()` (which starts it) to `finish()` (which reads its stats
and removes it), matching the sandbox's own lifetime rather than the function call that launched
it.

### 7.25.4 Where §7.5 now stands

> **F2 — ✅ Met (§7.25).** An unmodified-shaped integration, confined in real namespaces with no
> route to anywhere, polled a declared remote API and published the result.
>
> **S4 — ✅ Met (§7.25).** Two such integrations, confined and running concurrently, each denied
> precisely the host declared only by the other — evidenced by the mediator's own audit record,
> not by either sandbox's self-report.

§7.16.3's reconciliation, written 2026-09-02, correctly recorded both as blocked at that date and
is not edited — it gains this pointer. All twenty requirements in §7.5 now carry a verdict.

### 7.25.5 What this does not establish

- **UDP is not exercised here.** F2's criterion names an API, and every integration in this
  suite polls over TCP — the transport the corpus's cloud-facing half overwhelmingly uses
  (§7.24.3). §7.24.4's UDP finding and `udp_relay.py`'s build are evaluated by `selftest_udp`
  against the same decision path, not inside a spawned sandbox; a confined UDP round trip
  through real namespaces is not built and is owed to Chapter 8 alongside the unserved
  asyncio-datagram quarter.
- **Two sandboxes, not the corpus.** This is a targeted demonstration of F2 and S4's own stated
  criteria, with a selection defended the way §7.4.1 requires — not a coverage claim across the
  37- or 40-integration corpora. Whether the egress path holds up against a real community
  integration's actual API (rather than a synthetic coordinator polling a stable IANA host) is a
  different, larger measurement that §7.10's schedule did not include and this section does not
  substitute for.
  > **Run the same day — §7.27, and it did not merely confirm this one.** `nordpool` against the
  > real Nord Pool API, three arms, and the first run **failed**: the platform's own
  > `async_get_clientsession(hass)` could not be constructed inside the sandbox at all. The
  > paragraph above was right that this was a different measurement; it was not anticipated that
  > it would find the design unusable for the 41% it was built for until a two-step namespace
  > correction.
- **The DNS-library coupling named in §7.24.6 is unchanged by this result.** A working run today
  says nothing about a future Home Assistant release that replaces `aiodns`.

## 7.26 The read-through — the two registers scored, and what one voice found

**2026-09-03.** §7.21 read the methodology half against the results half and Chapter 6 against
Chapter 7. Neither pass read this chapter *as one document*: §7.12–§7.25 were written one result
at a time, over two days, each section correct where it stood. §7.7's fourth falsifier makes
reading them together a requirement rather than tidiness — *an evaluation that reports a
requirement as passed when it cannot demonstrate it has failed on its own terms* — and the same
standard applies to a commitment made in the frozen half and then not kept.

Two findings are substantive. Both are about **things the chapter promised or possessed and did
not report**, which is the failure mode a section-at-a-time chapter has and a read-through is the
only instrument for.

### 7.26.1 §7.2 promised a scoring the chapter never performed

§7.2 is not vague about it:

> The security axis is therefore scored **twice** — once against Chapter 4's own register of
> eighteen threats, and once against Corno and Mannella's eleven (their T1–T11), using the mapping
> column §4.8 supplies. The second scoring is the one an external reader can check without
> accepting any of this project's own threat-identification work.

**Neither scoring exists in §7.12–§7.25.** The results half is organised by *requirement* — §7.5's
twenty rows, which are what §7.3 calls the chapter's spine — and every security section discharges
a requirement rather than a threat. Across seventeen hundred lines of results a T-number appears
sixteen times, every one of them in passing, and no section enumerates either register.

This is not a missing measurement. Every threat in both registers is either demonstrated by
evidence already in this chapter or retained by a decision already recorded in §4.11; nothing new
had to be run to produce what follows. It is a **reporting** failure of exactly the kind N2 was
written to catch one level up, and it went unnoticed for the same reason N2 exists: the chapter was
scored against the table it was organised by, and the table it was *also* answerable to was in a
section nobody re-read after the results started landing. §7.10's schedule lists measurements, so
closing the schedule out (§7.21.4) gave no signal that a reporting obligation was outstanding.

The rest of this section is that scoring, performed rather than promised.

### 7.26.2 T08, T10 and T11 — evidence the artifact holds and the chapter never reported

§7.5's note on its two blocked rows made a prediction about what building the proxy would do, and
it named threats rather than requirements:

> If the egress proxy is built, both rows become verifiable and **T08, T10 and T11 acquire
> demonstrated controls**.

§7.25 closed F2 and S4 and **scored none of the three.** The proxy was built, the evidence was
produced, and the sentence that anticipated it was never returned to. Recovering it needs no new
run: `selftest_egress` is one of the eighteen suites the 2026-09-03 run passed on the C4 device,
and its cases are the demonstrations §7.5 anticipated.

**T11 — a declared name that resolves inward — is demonstrated exactly as §4.10 specifies the
control.** `case_t10_t11` grants an integration the name `innocent.invalid:<port>`, arranges for
that name to resolve to `127.0.0.1`, and then makes the two decisions separately:

```
    policy("demo_rebind", …)  →  allowed      the manifest permits the name, because a
                                              manifest can only speak of names
    broker.open(…)            →  refused      "not a public address"  — on the address the
                                              resolution actually returned
```

That split is the whole of T11. §5.10.5's *"checking the name is not checking the thing"* is here as
two lines of measured behaviour: the clause is satisfied and the connection is still refused, because
what the broker judges is what resolution returned rather than what the manifest said. §7.24.2
argued that resolve-then-pin is *more* structural than §5.10.5 claimed, since a sandbox holding only
a placeholder address has nothing to race the check with; this is the same property observed from
the enforcement side.

**T10 — reach into the LAN and onto the gateway — is demonstrated on the classification and once
adversarially.** `is_public` refuses loopback, RFC 1918 [28], link-local, `0.0.0.0`, IPv6 loopback,
link-local IPv6 **and IPv4-mapped IPv6** — the last because `::ffff:192.168.11.109` is a form the
§7.24 run actually produced, twenty-four times, so it is a case drawn from measurement rather than
from the RFC index.
The adversarial half is `case_allow_private_is_not_request_controlled`, and it is worth stating in
the chapter rather than only in the code, because the bug it regression-tests was this design's own:

> `EgressBroker.open`'s first version read `allow_private` from the **request** — a field the
> sandbox composes. A hostile integration could have granted itself the whole of T10's reach by
> writing one key into a message it already controlled, while its manifest declared nothing but a
> public hostname.

The fix makes it a parameter of the caller, and `acting_policy` never passes it. The case sets the
key in the request anyway and asserts the refusal still comes. **This is the one place in the
evaluation where a control failed against an attack the design itself invented, was fixed, and is
now tested under the same attempt** — and §4.11 has no residual risk covering it, because it was
never a residual risk. It was a defect, and the reason it is in the chapter is that a defect found
by building the adversary case is evidence about the method (§7.4.2's rule that negative cases
assert on the reason) rather than an embarrassment to be resolved in a commit message.

**T08 — exfiltration to an undeclared host — is §7.25's own result** and was reported there as S4.
The two are the same measurement scored against different registers, which is precisely what §7.2
asked the chapter to do and what it stopped doing.

### 7.26.3 Chapter 4's register, scored per threat

All eighteen. **The verdict column is not aggregated**, on §7.4.2's rule that a single "threats
controlled" figure is the security equivalent of an unlabelled compatibility percentage. *Paired*
means the threat was also demonstrated against an unconfined arm on the same host and release —
the standard §3.5 imposed on S8 and S3, and the only standard under which a block is evidence.

| ID | Control (Ch. 3) | Evidence in this chapter | Verdict |
|---|---|---|---|
| T01 | S1 — execute outside the platform's process | §7.15.3: unconfined the victim's token is reached **7 ways**; confined 8,942 objects, all its own | ✅ **Paired** |
| T02 | S1, S7 — identity per request | §7.16.1: *"claim to be another integration"* → `/permissions/entities/read`; `selftest_channel`, identity is the socket (§5.11.2) | ✅ Demonstrated |
| T03 | S1 — mediator unreachable from the address space | §7.15.3, §7.13.3 | ✅ Demonstrated, **unpairable by construction** — unconfined there is no mediator to tamper with, and the suite reports `UNMEDIATED` rather than a comparison |
| T04 | S2 — credential only in the mediator | §7.15.3: token **live in the mediator, 7 references**, at the moment the sandbox's sweep finds nothing | ✅ **Paired** |
| T05 | F3, S5, S6 — manifest-checked calls | §7.16.1: unlock refused to a manifest declaring only `lock.lock`; `lock.*` rejected at parse | ✅ Demonstrated |
| T06 | S3 — mediate reads *and* subscriptions | §7.14.2: **36/36 → 1/36**, and **20/20 → 0/20** presence entities | ⚠ **Partial.** Reads paired; the subscription half is a refusal without a delivered stream (§7.14.4) |
| T07 | F3, S6 — writes to declared entities only | §7.16.1: `/permissions/entities/write` | ✅ Demonstrated |
| T08 | S4 — per-integration egress allow-list | §7.25.2: two concurrent sandboxes, each denied the other's host, audit `[True, False]` | ✅ Demonstrated |
| T09 | **Retain** (R5) | §7.24.5: every TLS wrap had `check_hostname`; the mediator supplies a descriptor and sees destination, never content | ⊘ **Retained — and now measured rather than asserted** |
| T10 | S4 — deny non-public destinations | §7.26.2, and §7.24.5's measurement that a 29k-install integration needs the flag in ordinary operation | ✅ Demonstrated at the decision layer |
| T11 | S4 — check the address, not the name | §7.26.2: clause satisfied, connection refused on the resolved address | ✅ Demonstrated at the decision layer |
| T12 | F3, S6 — declaration re-checked per version | **none** | ✗ **Not evaluated** — §7.26.5 |
| T13 | **Retain** partially (R1, R2) | §7.16.1: the over-broad grant **is honoured**; what is measured is the ceiling it cannot raise | ⊘ Retained, with the ceiling measured |
| T14 | S8 — filesystem isolation | §7.13.2: canaries **2/2 → 0/2**, five 2021 traversals → zero, `FileNotFoundError` not `PermissionError` | ✅ **Paired** |
| T15 | S8 — process-table isolation | §7.13: *"read another process's environ"* → `LEAKED` unconfined, `EMPTY` confined | ✅ **Paired** |
| T16 | S9 — resource limits | §7.22.1: four bounds, each checked by a sandbox exceeding it | ⚠ **Partial against §4.10.1's wording** — space yes, I/O bandwidth not delegated (§7.22.2); `/sandbox/data` unbounded |
| T17 | S1 — separate process removes the shared heap | §7.15.3 — this is the threat §2.4.1 demonstrated and the one that forced the architecture | ✅ **Paired** |
| T18 | S7 — attributed, tamper-evident log | §7.16.2 `selftest_audit`, hash and MAC chains failing independently; §7.25.2's per-identity record | ✅ Demonstrated, bounded by **R4** — §7.11 and §7.13.2: an OOM kill leaves no record, and unconfined the attacker found a real audit log on the host |

**Thirteen demonstrated, five of them against an unconfined arm; two partial; two retained by a
decision Chapter 4 already recorded; one not evaluated.** The five paired ones are T01, T04, T14,
T15 and T17 — and it is worth noticing which: they are the confidentiality threats, and they are
the ones where §3.5 required a baseline. Where the evaluation is strongest it is strongest because
Chapter 3 made pairing a requirement before anything existed to pair.

**The four Critical inherent risks (§4.9) are T01, T03, T04 and T05.** All four are demonstrated,
two of them paired, and none is among the partial or unevaluated rows. §4.9's observation that the
Critical risks *"share a single cause: integration and platform occupy one process with no boundary
between them"* is answered by a single control, and §7.15 is the measurement of it.

### 7.26.4 The external register, scored — and §4.14 records one divergence where there are three

This is the scoring §7.2 said an external reader could check without accepting any of this
project's threat-identification work. Mapping from §4.8's `CM` column, unaltered.

| CM | Their threat | Maps from | Verdict |
|---|---|---|---|
| **T1** | Confidentiality — use of data outside scope | T04, T06, T14, T15, T17 | ✅ Demonstrated, **four of five paired**; T06's subscription half partial |
| **T2** | Spread of data outside scope | T08, T09 | ⚠ **Split, and the split is the design's honest boundary.** T08 demonstrated (§7.25); T09 retained (R5) — destination is controlled, content is not |
| **T3** | Integrity — alter device state | T05, T10 | ✅ Demonstrated |
| **T4** | Integrity — alter private data | T07, T17 | ✅ Demonstrated |
| **T5** | Availability — delay | **nothing** | — **Unmapped** |
| **T6** | Availability — partial loss | **nothing** | — **Unmapped** |
| **T7** | Availability — complete loss, incl. *"resource saturation up to a frozen state"* | T16 | ⚠ Partial — space bounded, I/O bandwidth not (§7.22.2) |
| **T8** | Availability — physical damage | **nothing**, and §4.14 says so | ⊘ Out of reach; retained immediately |
| **T9** | Authentication — impersonation | T02, T11 | ✅ Demonstrated |
| **T10** | Authorisation — escalation | T01, T03, T05, T13 | ✅ Demonstrated except T13, which is retained (R1, R2) |
| **T11** | Non-repudiation — anonymous action | T18 | ✅ Demonstrated, bounded by R4 |

**Eight of their eleven are mapped; five of the eight score cleanly and three carry a stated
qualification. Three of the eleven are not mapped at all, and §4.14 accounts for only one of them.**
§4.14 states the divergence as *"their model is broader in consequence; this one is broader in
mechanism"* and gives physical damage (their T8) as the example. It is not the only case: **their
T5 (delay) and T6 (partial loss) have no counterpart in §4.8's eighteen either.**

The defensible reading is that this is an under-mapping rather than an omission. T16 is *"exhausts
CPU, memory or disk, rendering the gateway unresponsive"*, and a gateway being exhausted delays
and partially loses before it completely loses — so T16's control plausibly reaches their T5 and T6
as well, and §4.8's column maps it only to their T7. Either way the statement in §4.14 is one
example presented as the whole difference, and **§4.14 is not edited — it gains a pointer here**, on
the convention §6.4.1 established for Chapter 5 and §7.21.6 applies to Chapter 6.

**What the external scoring adds that the internal one cannot.** §7.2 predicted that *"a clean sweep
of Chapter 4's register is not a clean sweep of theirs"*, and that is now measured rather than
anticipated. The two registers disagree in both directions: theirs reaches consequences this design
cannot touch (T8, and arguably T5 and T6), while §4.8's eighteen separate the supply path (TB4) and
the host OS (TB5) into boundaries their gateway-level framing folds together — which is why T12 and
T15 have thin or no CM counterparts. **Neither register is a superset, and reporting only the one
this project wrote would have been the more flattering of the two.**

### 7.26.5 T12 is the one threat with no evidence, and it was never declared unevaluable

§7.11 names four things this chapter cannot do, and T12 is not among them. §4.10 treats it —
*"confinement applies to whatever version runs; declaration re-checked per version"* — and the first
clause is structural and true: a sandbox confines whatever code is inside it, so a malicious update
inherits the previous version's boundary rather than escaping it. The **second** clause is the one
with content, and nothing in this chapter exercises it. No section spawns the same integration
twice across a version change, and no section spawns one whose manifest changed between runs.

Stating it plainly: **T12's control is asserted, not demonstrated, and this is the only threat in
either register of which that is true.** It is a small measurement — set an integration up, change
its manifest, spawn it again, and show the second run is bounded by the second declaration and
that the change is visible through `describe.py` before it takes effect — and it is a small
measurement that was never scheduled, which is why §7.10's close-out in §7.21.4 did not catch it.
Chapter 8 owes it as future work, and this section owes the admission that §7.11 should have
carried it in advance if it was not going to be run.

### 7.26.6 Four corrections the read-through made, and how each was handled

The chapter's convention is that a section is left as written and gains a pointer when later
evidence overturned its *reasoning*, and is corrected in place when there is no reasoning to
protect — §7.21.7 drew that line for a miscount and a damaged sentence. Both cases arose again.

**1. §7.23.7's scorecard misquotes the register it claims to score, and drops the prediction that
was right.** §7.6 registered P1 as *"Predicted baseline: 34/37"* and P3 as *"the compatibility cost
attributable to confinement is 0 to 3 integrations of 37"*; §7.21.5 scored P3 ✓. §7.23.7's table
paraphrases P1 as *"confinement costs compatibility on the corpus"*, P2 as *"the baseline will fail
on fewer than the confined arm"*, and replaces P3 entirely with *"structural denial produces
`EMPTY`, not `BLOCKED`"* — which is a true observation from §7.13 and **was never registered as a
prediction anywhere**. The arithmetic survives: two of eight held, six did not. The argument
survives and improves — §7.23.7 says the two that held were *"predictions about the design rather
than about the world"*, and P3-as-registered (the design's compatibility cost) and P7 (the same
cost on an independent corpus) are the same prediction measured twice, which is a tighter statement
than the one the section makes. **Corrected in place**, to the registered wording, because a
scorecard that quotes its register wrongly has no reasoning to protect.

**2. §7.13.2's unconfined column sums to 32 where the section states thirty-eight attacks.**
`BLOCKED 14 · EMPTY 4 · LEAKED 11 · NOT RUN 2 · UNMEDIATED 1` is thirty-two rows; the confined
column's `21 · 10 · 6 · 1` is thirty-eight. Both are as measured. The difference is that the
confined arm's **seven mediated attacks have no unconfined counterpart** — §7.13.3 says so in prose
(*"an unconfined integration is not denied `lock.unlock`; there is nobody to ask"*) — and collapse
into the single `UNMEDIATED` row. 31 non-mediated rows plus 7 mediated is 38; 31 plus 1 is 32. **A
clause is added** to §7.13.2 so the column can be added up, because a reader who checks the
arithmetic and finds it short has been given a reason to distrust every other table in the chapter.

**3. §7.4.1's corpus table was edited in place, against §7.21.2's own rule.** §7.21.2 holds that the
methodology half is *"evidence of what was planned before the results, and editing it into agreement
destroys the only thing that makes §7.1's claim checkable"*, and names two stale sentences left
standing for that reason. The uniform corpus's row was nonetheless changed from *"Owed;
`figures/fetch_hacs_corpus.py` takes it, only the selection changes"* to *"**Run — §7.23.** Seed
20260902…"* when §7.23 landed. **Reverted to the frozen text, with the pointer moved below the
table**, which is the form §7.9 already uses for the same result. The inconsistency is worth the
paragraph: the convention is only load-bearing if it is applied where it is inconvenient, and this
is the one place in two chapters where it was not.

**4. Three sections state a chapter-wide count that a later section moved, and none carries a
pointer.** §7.21.4 closes with *"Item 8 is conditional on a decision not yet taken"* — §7.24 opens by
taking it. §7.22.4 states *"Two rows still fail — F2 and S4, both egress — and they are the only
two"* — §7.25 closes both. §7.16.2 reports *"all eight self-tests"* where the 2026-09-03 run passes
**eighteen**, a total this chapter states nowhere. **Each gains a pointer and keeps its text**, because
each was true on the date it carries and the dates are the evidence; and §7.26.7 records the suite
total, since a chapter that reports individual suite counts in four places and never the sum is
inviting the reader to add them up wrongly.

**5. Two sections say "declare" of a figure that counts what was *set up*, and it reads as a
conflict between measurements when it is not.** §7.23.1's table reports **18 of 37** head
integrations declaring no components, against §7.12.5's and §7.20.3's **twelve of the 37 declare
none at all**. Recomputed from `compat_declared_core.json` and `uniform_confined.json`, both are
right and they count different fields:

| | Head, 37 | Uniform, 40 |
|---|---|---|
| **Declares** no components (`dependencies` in the manifest) | **18** — median 1 | **26** — median 0 |
| Has none **set up** (the declared set plus its transitive closure) | **12** — median 2 | 23 — median 0 |

§7.23.1's row is the declared figure and is precisely labelled. §7.12.5, §7.20.3 and §6.13's
*"the median declaration is two components, and the twelve of the 37 that declare none at all are
charged nothing"* use the set-up figure under the word *declare*. **The numbers are load-bearing
and correct** — §6.13's argument is about cost, and cost follows what is set up rather than what is
named — so the two Chapter 7 sentences are corrected in place and §6.13 gains a pointer, keeping
its text.

This one is worth the space it takes because of what it is **not**. Read quickly it looks like the
first case in this report of two measurements disagreeing; it is instead the fifth case of a
sentence being imprecise about a measurement that is fine, which is the pattern §7.21.7 identified
and §7.26.8 restates. It was found by recomputing both figures from the recorded results rather
than by reading either sentence again.

### 7.26.7 The suite, as it stands at the end of the chapter

| | On 2026-09-02 (§7.16.2) | On 2026-09-03 |
|---|---|---|
| Self-test suites passing on the C4 device | 8 | **18** — re-run 2026-09-03 after §7.27's namespace and audit changes, 18/18 |
| Added by §7.22 | `selftest_resources` — 13 checks | |
| Added by §7.25 | `selftest_fdpass` 12, `selftest_socket_pinning` 6, `selftest_egress` 23, `selftest_egress_shim` 9, `selftest_udp` 12, `selftest_egress_sandboxed` 17, `selftest_netshape` 13 | |
| Added by §7.29 (2026-09-06) | `selftest_integrity` — 15 checks, carrying **C1**. The suite count is **19** from that date | |

The two counts are not a compatibility figure and no rate is computed from them; they are recorded
because §7.16.2's table is the chapter's only statement of what the artifact's own tests cover, and
it stopped being current the moment §7.22 ran.

### 7.26.8 What this pass did not find, which is the more useful half

**No result in this chapter contradicts another.** Every figure quoted twice is quoted the same way:
84% and the zero cost in §7.12 against §7.23's 92% and zero; 31.5 µs in §7.19 against §7.20.1's
correction to 272 decisions per second, which §7.19.3 carries in place; 36-to-1 entities in §7.14;
2-of-2 canaries in §7.13; 96% of resolutions via `aiodns` in §7.24. The four corrections in §7.26.6
are **one misquotation of a register, one uncheckable sum, one convention lapse, three stale counts
and one field named wrongly** — and, as in §7.21.7, every one of them is a sentence next to a
measurement rather than a measurement. Finding 5 is the sharpest instance: two figures that look
like a contradiction are both correct, and recomputing them from the recorded results is what
established that rather than re-reading the prose.

That asymmetry now holds across four chapters and two read-throughs, and §7.21.7 was right to say
it belongs in Chapter 8 as a methodological result rather than as a run of luck. It has a plain
explanation and the explanation is the argument for the discipline: **a number in this project is
produced by a harness that is itself tested, and a sentence about a number is produced by an author
writing at the end of a long day.** The measurements have a mechanism that catches their errors.
The prose has only a read-through, which is why there have now been two.

**What the pass could not check.** It read the chapter against itself, against Chapter 4's two
registers and against §7.6's frozen predictions. It did not re-run anything — every figure above is
quoted from the recorded result files, and a transcription error common to a results file and this
chapter would survive it. §7.24.6's argument applies here too: two instruments catch what one
misses, and for the prose there is currently one.


## 7.27 F2 against a real integration's real API — and what only a real one could find

**Run 2026-09-03**, `framework/confine/endtoend_egress.py`,
`experiments/end_to_end/results/pi5_nordpool_egress.json`. §7.25 closed F2 with two
purpose-built coordinators polling `example.com` and `example.net`, and stated its own limit in
the same section:

> Whether the egress path holds up against a real community integration's actual API (rather
> than a synthetic coordinator polling a stable IANA host) is a different, larger measurement
> that §7.10's schedule did not include and this section does not substitute for.

This is that measurement. It was not scheduled, it is not a re-run of anything, and **it found a
defect that made the design unusable for the population it was built for** — which is the
argument for having run it.

### 7.27.1 Why `nordpool`, and why the choice is forced rather than convenient

§7.17.1 measured the ceiling on any end-to-end arm: **26 of 37 integrations need an API key,
token, password, username, host or email** before their own config flow can complete, and an
unconfined baseline meets the identical wall. The eleven that need none are overwhelmingly the
ones that need no *network* either — three of §7.17's five declare `iot_class: calculated`, which
is exactly why that section could not see egress at all (§7.18).

`nordpool` is the intersection, and as far as this corpus goes it is the only member of it:
**`cloud_polling`, configurable from a price region alone.** §7.24 recorded it completing its own
flow unconfined, reaching `dataportal-api.nordpoolgroup.com:443` over TLS with `check_hostname`
set, and creating a LOADED config entry — on `region` and `currency` and nothing else. It has
exactly one endpoint, written once in its own `aio_price.py`, so the manifest clause
`dataportal-api.nordpoolgroup.com:443` is a fact about the integration rather than a guess about
it.

**Three arms, because two would not settle the question.**

| | Arm | What it answers |
|---|---|---|
| **A** | unconfined baseline | Does it work at all today, on this release and this host? |
| **B** | confined, host declared | Does it work through the mediator's egress path? |
| **C** | confined, **clause absent** | Does removing the grant remove the capability? |

**Arm C is what makes arm B evidence.** §6.4.5's rule is that an absence is not proof
confinement worked until the grant is shown to have arrived; the converse binds just as hard —
*a success is not proof the mediator supplied the connection unless withdrawing the declaration
withdraws it*. A sandbox whose network namespace had silently leaked would produce arm B's result
exactly. With C, the difference between the two is the mediated path and nothing else: same
integration, same flow input, same profile, same host, same minute.

### 7.27.2 The first run failed, and the reason is the finding

Arms B and C both reached `create_entry` and then failed setup, with an **empty egress audit** —
the integration never got as far as asking the mediator for anything:

```
homeassistant.setup: Error during setup of component nordpool: [Errno 19] No such device
  File "zeroconf/_utils/net.py", line 350, in add_multicast_member
    listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, _value)
OSError: [Errno 19] No such device
```

`nordpool` neither declares nor imports `zeroconf`. It does one ordinary thing, on line 63 of its
own `__init__.py`, which is what the platform's documentation tells an integration author to do:

```python
from homeassistant.helpers.aiohttp_client import async_get_clientsession
client = async_get_clientsession(hass)
```

And in 2026.8.3 that reaches, four calls down:

```python
def _async_make_resolver(hass) -> HassAsyncDNSResolver:
    return HassAsyncDNSResolver(async_zeroconf=zeroconf.async_get_async_zeroconf(hass))
```

**Every Home Assistant client session builds a resolver that instantiates Zeroconf, and Zeroconf
joins the mDNS multicast group when it is created.** A fresh network namespace's `lo` carries no
`IFF_MULTICAST` flag, so the join fails with `ENODEV` and the session cannot be constructed.

**So a real integration could not make an HTTP request at all, and the failure was nowhere near
the egress path.** It happened before any name was resolved and before any connection was
attempted — which is why the mediator's audit was empty rather than full of denials, and why no
amount of testing the egress path would have found it.

**This is the same seam §7.24.2 measured from the other side.** That section found that 96% of
resolutions go through `aiodns` because `aiohttp_client.py` gives every session an
`AsyncDualMDNSResolver`, and drew the conclusion that the *enforcement point* was in the wrong
place. The same line has a second consequence it did not draw: the resolver is not merely a
different code path, it is one with a **hard dependency on multicast being available**. §7.24
corrected where to interpose. This corrects whether the sandbox can get that far.

**And it explains why §7.25 did not see it.** §7.25.1 describes its subject as polling "with its
own `aiohttp.ClientSession()`, unmodified from how a community integration would write it." The
first half is accurate and the second is not: a community integration uses
`async_get_clientsession(hass)`, and the bare constructor is precisely the one call that skips
the platform's resolver. **A synthetic integration written by the author of the sandbox avoided
the platform helper that breaks the sandbox** — not deliberately, which is the point. §7.25's
result stands as written for what it measured; the sentence claiming it was written the way a
community integration would is withdrawn here, and this section is the evidence for withdrawing
it.

### 7.27.3 The correction, in two steps, and why it grants nothing

`namespaces.bring_loopback_up` already existed for a structurally identical reason recorded in
its own docstring: §5.7.3 described the namespace as giving "no route to anywhere", which "is
accurate and incomplete: it also gives no working loopback, and that is a different thing." The
same sentence now covers multicast.

**Step 1 — `IFF_MULTICAST` on `lo`.** Not sufficient, and the measurement says why:

```
lo flags 0x1049 (UP | LOOPBACK | RUNNING | MULTICAST)
    join via 127.0.0.1 : OK
    join via 0.0.0.0   : [Errno 19] No such device
```

**Step 2 — route `224.0.0.0/4` to `lo`.** `zeroconf` joins through `INADDR_ANY`, and for an
unbound join the kernel picks the interface *from the routing table*. A fresh namespace has no
route for the multicast range at all, so there is nothing to pick. With the route added by
`SIOCADDRT` — the syscall rather than `ip route add`, on §6.4.6's rule that the supervisor should
not need a tool inside the sandbox's mount namespace — the `0.0.0.0` join succeeds.

**The grant is vacuous by construction, and the arithmetic is the whole argument.** The route's
device is `lo`. Every multicast datagram the sandbox sends is delivered to the sandbox; there is
no second interface in the namespace for the kernel to choose, and none can be added without
`CAP_NET_ADMIN` over a namespace the sandbox does not own. **This is §5.6.2's structural denial
in a routing table** — the capability is present and empty rather than absent and fatal — and it
is the same shape as the loopback grant beside it, which lets the sandbox talk to itself and to
nobody else. Discovery that is *meant* to reach the real network stays mediated behind the
`discover` clause of `notes/decision_network_capability.md`.

**The cost is stated rather than absorbed.** An integration that genuinely depends on mDNS to find
a device finds none here. That is a real compatibility limit and it is a far smaller one than
being unable to construct an HTTP client, which is what the alternative was.

### 7.27.4 §7.17.5's withdrawn finding, re-established on better evidence

§7.17.5 withdrew `scheduler` as evidence that confinement costs compatibility, because the
baseline showed it broken on this release either way, and set the bar for re-establishing it:

> To establish that, an integration is needed which **works unconfined and fails confined on
> discovery**, and this corpus has not produced one.

**`nordpool` is that integration.** It loads unconfined and — before the correction above — failed
confined on `IP_ADD_MEMBERSHIP`, the identical call in the identical library. §7.17.5 was right to
withdraw the claim on the evidence it had and right about what would restore it, and the arm that
restores it is one it did not run.

The restored finding is **sharper than the withdrawn one and points elsewhere**. The withdrawn
version said network isolation costs compatibility because integrations use discovery. The
measured version says something narrower and worse: **the cost fell on an integration that does
no discovery at all**, because the platform's own HTTP helper joins a multicast group as a side
effect of building a DNS resolver. It was not a discovery problem. It was every cloud-facing
integration in the corpus, and the 41% §7.18.1 identified as the population the proxy exists to
serve.

### 7.27.5 The result

| | A — unconfined | B — confined, declared | C — confined, no clause |
|---|---|---|---|
| Config entry | **LOADED** | **LOADED** | LOADED |
| `sensor.nordpool_kwh_se1_eur_3_10_025` | **0.026** | **0.026** | **`unavailable`** |
| `network.egress` decisions | — (no mediator) | **3 granted** | **3 denied** |
| Destination in each record | — | `dataportal-api.nordpoolgroup.com:443` | `dataportal-api.nordpoolgroup.com:443` |
| Clause | — | `/permissions/network/egress/0` | `/permissions/network/egress` |
| Name resolved inside the sandbox | — | once | once |
| Connections completed | — | **3** | **0** |
| `oom_kill` | — | 0 | 0 |

**The confined value is not merely present, it is the same number.** F2's criterion is *"an
integration polling a declared remote API completes successfully while confined"*, and what
satisfies it here is a real electricity price, fetched by unmodified community source from the
real Nord Pool API, arriving through the mediated path with the identical value the unconfined
arm produced in the same minute.

**Arm C degrades rather than crashes**, which was not predicted and is worth recording: the entry
still reaches LOADED and the sensor is still created, and its state is `unavailable` because the
fetch behind it was refused. An integration denied its network does not fail to install; it
installs and reports no data, which is the behaviour a user would be able to diagnose.

**The evidence for both is the mediator's own durable audit record**, not either sandbox's report
of itself, on §7.25.2's reasoning. Each record names the destination and the clause, and the log's
**hash and MAC chains both verify** over the run, so S7's property is exercised by this
measurement rather than only by `selftest_audit`.

**One column needs its qualification stated, or the table misreads.** The unconfined arm shows ten
entities against the confined arm's one. **Exactly one of the ten is `nordpool`'s**; the other
nine are `sun`, `zone` and `conversation`, which belong to `default_config` — set up by the
generous baseline of §7.12.1 and not by the sandbox, whose profile is `declared` + the core
package set. It is a profile difference, not nine lost entities, and both arms produce the one
entity that is the integration's.

### 7.27.6 A defect in the audit record, and two harness faults

**The audit log recorded a host where the clause now names a host and a port.** §7.24.3 measured
that a hostname-only clause can neither grant nor withhold a port, and §7.25's schema added one —
but `audit.py`'s `decision()` still extracted `request.get("host")` alone, so the durable record
could not distinguish a grant of `:443` from a grant of `:6445` on the same host. F3 requires
every decision be attributable to the clause that produced it, and the clause *pointer* does
disambiguate by index; the human-readable target should not be the weaker of the two. Corrected
here, and the table above is the first record to carry the port. **This is a defect introduced by
§7.25's schema change and invisible to every test that existed**, because none of them logged an
egress decision to a real log.

Two harness faults are recorded per §6.3.3's rule, both caught before any number was reported:

- **The audit log was created inside the directory the harness removes.** `records()` then found
  an empty directory and the run reported *no decisions at all* — which presents exactly as "the
  mediator logged nothing" and is §6.4.5's warning in its most literal form. The log now lives
  outside that tree.
- **The first version read `request` out of `mediator.audit`.** That structure carries `op`,
  `allowed` and `clause` at the top level and does not carry the request, so every destination
  read as `None`. The fix moved the destination evidence to the durable log, which is the record
  §5.12 commits to and the stronger source.

Neither was a finding about the design. Both would have produced a wrong report.

### 7.27.7 What this does and does not establish

**Established.** F2's criterion is met by a **real, unmodified community integration** rather than
by a coordinator written for the test: it polls its own declared remote API, over the mediated
path, and publishes the correct value. S4's shape is demonstrated a second time and by
subtraction rather than by two identities — the same integration, with and without the clause,
granted and refused the same destination. `notes/decision_network_capability.md`'s design survives
contact with a real HTTP stack, a real TLS handshake and a real API.

**Not established, and the first is the one most likely to be over-read.**

- **One integration.** This is a named set of one, chosen because the corpus offers no second
  member, and no rate is computed from it. §7.17.1's credential wall is the reason and it binds
  any confinement scheme equally.
- **The correction was found, not predicted, and there may be more of its kind.** The failure was
  in a platform helper nothing had exercised because no real integration had been run confined
  against a network. That is one seam; §7.24.5's finding that there are three network stacks
  suggests others exist. **What this measurement licenses is that the egress path works for the
  `aiohttp` + `async_get_clientsession` shape, which is the platform's own**, and not that it
  works for `urllib3`/`requests` or a raw socket confined, neither of which has been spawned.
- **mDNS discovery does not work in the sandbox and now fails silently rather than loudly.**
  Before the correction an integration needing discovery crashed at setup; now it finds nothing.
  The second is better behaviour and it is still a compatibility limit, and §7.24.4's measurement
  that no integration in that sample established a listener does not bound it, because that
  sample was recorded unconfined where discovery worked.
- **Arm C's denial is a refusal to connect, not a refusal to resolve.** The name resolved inside
  the sandbox in both arms — to a placeholder that only the mediator can map (§7.24.2) — so what
  C demonstrates is the pin, not a DNS block. That is the design as specified and it is worth
  stating, because "the name resolved" in a denial record looks wrong until the placeholder is
  understood.

## 7.28 The whole-report read-through, and the requirement it found unverified

§7.26 read this chapter as one document and found two reporting obligations it had not met.
Stage 5 then read **all eight chapters** as one document, in two passes on 2026-09-04, and this
section records the one finding that belongs to Chapter 7 rather than to the prose. The rest —
citations still on a superseded numbering, a correction spliced through the paragraph it corrected,
a schema table broken in half by a blockquote, eight references to a chapter that does not exist —
were repairs to sentences and are not reported here, on §7.4.2's rule that what is worth a section
is what changes a verdict.

**One did.** §7.4.1 states that *"C1 is verified mechanically, not asserted"* and §8.3 repeats it.
**The mechanism does not exist.** Nothing in the artifact hashes or diffs an integration's tree
against its fetched original; no result file carries the field; no results section reports the
count. The claim was designed in a methodology section and never built, and it survived §7.21.3's
sweep of five mis-discharged obligations because, unlike those five, it named no section in which
it would be discharged.

### 7.28.1 What is actually true, and why it is not simply weaker

| | Confined arm | Baseline arm |
|---|---|---|
| Source that runs | A copy — `shutil.copytree` (`compat.py`) | **The fetched tree itself**, passed by path |
| Can the integration write it? | **No.** `sandbox.py:218` bind-mounts the copy read-only | **Yes.** Full authority, in-process, no mount |
| Is a diff taken? | No | No |

For the confined arm the real guarantee is **structural and stronger than the criterion asked
for**: the integration cannot modify its source, rather than being observed not to have. That is
§5.6.2's principle — deny by absence, not by check — arriving in a place no section claimed it.

**For the baseline arm there is no guarantee at all**, and that is the half that matters. The
unconfined arm exists to establish what the corpus does *without* this framework, and it runs each
integration's real fetched source in a full Home Assistant with nothing preventing a write. The one
arm where an integration could rewrite itself is the one with no copy, no read-only mount and no
count — and it is the arm every compatibility figure in this chapter is measured against.

### 7.28.2 The stated check would not have tested what it claims

Worth separating from the fact that it is missing, because implementing it as written would not
repair it. The confined run operates on a *copy*; diffing the **original** after that run compares
a tree nothing touched and passes trivially. The comparison that carries the claim is
**copy-against-original, taken before the run** — plus a re-hash of the baseline tree after it,
which is the only place a modification could occur.

### 7.28.3 The verdict, downgraded rather than withdrawn

C1 moves from **counted** to **argued**, and §7.5's row states it. No modification has ever been
observed, `copytree` performs no transformation, and every compatibility figure in this report
would be unaffected if the check were run and passed — which is the expected outcome. But §7.7's
fourth falsifier is *"if the evaluation cannot demonstrate a requirement and reports it as passed
anyway… the evaluation has failed on its own terms"*, and §8.2.4 answered it with *"nothing was
reported as passed that was not demonstrated."* **That answer was wrong about C1**, and §8.2.4 now
carries the correction rather than this section carrying it alone.

The fix is small and §8.7 prices it: hash each integration tree at fetch, re-hash the copy before
the confined run and the tree after the baseline run, and report mismatches. It is an hour, and
until it is run C1 rests on reading two lines of the harness rather than on a count.

> **Run 2026-09-06, and this section is left as written. §7.29 reports it: 75 tree comparisons
> across both arms, zero source changes, zero diff lines. C1 is counted.** One thing in the
> paragraph above did not survive contact — *"hash each integration tree at fetch"* is not
> achievable for a corpus whose manifest pins `HEAD` and records no content hash, so the count
> covers a run rather than the project's history. §7.29.2 states the bound.

**The general lesson is §7.21.3's, one level up.** That section found five obligations discharged
"in" a methodology section and corrected them by naming the results section that actually
discharged each. This one had no such pointer to check, because it was phrased as a statement of
fact rather than as an obligation — so the sweep that caught the other five could not see it. **A
claim that something *is* verified is harder to audit than a promise that it *will be*.**

## 7.29 C1, counted — the check §7.28 said did not exist

**Run 2026-09-06.** §7.28 downgraded C1 from *counted* to *argued* and §8.7 #4 priced the repair
at an hour. This section reports it. `confine/integrity.py` hashes an integration's tree before
and after a run, classifies what moved, and both arms of the compatibility measurement were
re-run with it wired in.

### 7.29.1 The result

| | Baseline arm | Confined arm |
|---|---|---|
| Trees hashed before and after | **37** | **38** (37 + one arm-B retry) |
| With changed source | **0** | **0** |
| Total diff lines | **0** | **0** |
| Files whose lines could not be counted | 0 | 0 |

**Seventy-five tree comparisons, zero source changes, zero diff lines.** §7.5's C1 criterion — *a
zero-line diff against the fetched original, counted mechanically after the run* — is met and
counted rather than argued. Evidence is `experiments/compat/results/c1_baseline.json` and
`c1_declared_core.json`, both carrying a per-integration `integrity` record as well as the totals.

**The baseline arm is the one that carries the claim**, for §7.28.1's reason: it passes the fetched
tree by path into a full, unconfined, in-process Home Assistant, with no copy and no read-only
mount. **The corpus directory was confirmed writable by the user running that arm before the run**,
so the zero is a result about what the integrations did and not about what the filesystem refused
them.

**The compatibility figures were unchanged by the re-run**, which is worth stating because a
re-measurement that moved them would have raised a question this section is not equipped to answer.
Both arms returned **31/37 — 84%** with the same six failures §6.14 names: `aiofiles` in
`bambu_lab`, `bermuda` and `tapo_control`; `eufy_security`, broken on 2026.8.3 itself; `hacs` and
`spook`, corpus artifacts. Requirements were installed fresh and drift changed nothing.

### 7.29.2 What was implemented differently from what §8.7 priced, and why

§8.7 #4 describes hashing *"each integration tree at fetch"*. **That is not achievable for this
corpus and the difference bounds the claim**, so it is stated here rather than left for a reader to
infer from the file dates.

`figures/hacs_corpus_manifest.json` pins each repository at `"ref": "HEAD"` and records no commit
identifier and no content hash. The fetched state is therefore unreconstructible after the fact:
re-fetching today yields whatever upstream now holds, which is not what was fetched on 2026-08-25.
Corroboration that the trees have been written to since fetch is direct — **91 `__pycache__`
directories** were already present in the corpus from earlier baseline runs.

So the count establishes:

- **What it does establish.** Across a complete run of both arms, no integration modified its own
  source, counted mechanically per file and per line, on trees an integration could have written.
- **What it does not.** That no run between 2026-08-25 and 2026-09-06 modified a tree. The
  fetch-time hashes to compare against were never recorded, and no later measurement can create
  them.
- **What changes from here.** The check is wired into `compat.py` itself rather than kept as a
  separate script, so every future compatibility run counts C1 as a side effect of running at all.

This is a smaller claim than §8.7 #4 implied, and the gap is of exactly the kind §7.28 was written
about: a sentence promising more verification than the artifact performs. It is recorded on the
same rule.

### 7.29.3 Two decisions inside the instrument that the number depends on

**Bytecode is counted separately, not ignored.** The baseline arm imports each integration from a
tree it can write to, so CPython drops `.pyc` files beside the source; a check that treated those as
modifications would report C1 as failing everywhere for a reason having nothing to do with an
integration's source. `audit.Identity` already excluded `__pycache__` from the source hash — a
§5.12.1 decision taken for T12, not one taken here to obtain a convenient answer — and
`integrity.py` reuses that identity rather than defining a second one, so the report has one
mechanism answering *did this code change* in both places. Bytecode additions are still counted and
reported, because a tree that gained forty `.pyc` files is unmodified in C1's sense and is not
untouched, and a run should be able to say both. In these two runs the count was zero in both arms:
the corpus already held current bytecode from earlier runs, and the confined arm sets
`PYTHONDONTWRITEBYTECODE` (`enter.py`).

**A line count that cannot be established is reported as unknown, never as zero.** The first version
of `compare()` read the pre-run bytes off disk. For the confined arm that is correct — copy and
original are distinct directories, both still present. For the baseline arm, where the tree is
compared against *itself* after being written to, it is not: both reads return the post-run file and
the count comes back **0**, which is indistinguishable from a clean result. **That is §6.4.5's
failure mode**, which this project has now recorded four times — an absence produced by a defect
reading exactly like the mechanism working. It was caught by a self-test case written for it, and
the instrument now retains pre-run bytes where it needs them and reports `lines_unknown` where it
cannot. `selftest_integrity` is 15/15 and includes that case.

**The confined arm's zero means something different from the baseline arm's**, and §7.28.1 said so
before the check existed: a source change there would not be a compatibility finding but a
containment failure, because the copy is bind-mounted read-only. Both are reported, and the
summary distinguishes them in those words.

---

*§7.1–§7.11 written 2026-09-02, before any measurement specified here had been run. Criteria in
§7.5 and predictions in §7.6 are frozen at that date and were not revised in light of results —
§7.12.3 scores two of them as wrong rather than adjusting them. §7.12 is the first results
section; the remaining measurements are scheduled in §7.10.*
