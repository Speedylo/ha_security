# Rebuild plan

**Written:** 2026-08-21 · **Re-fitted:** 2026-09-02 · **Status:** working note ·
**Covers:** 2026-08-21 → end of November 2026

Companion to `00_METHOD.md`, which fixes the ground rules. This plan says what gets
built, in what order, why that order, and where the plan is allowed to change.

> **§5's stage plan is overtaken and §9 replaces it.** The stages are **not** rewritten to match
> what happened — that is the same discipline Chapter 6 applied to Chapter 5, where a section
> corrected by a later measurement keeps its original text and gains a pointer. What was planned
> and what occurred are both evidence, and a plan silently edited into correctness is worth less
> than one that records where it was wrong. **Read §9 for the forward plan; read §5 for what was
> expected in August.**

---

## 1. The situation, stated plainly

A two-week feasibility spike (`~/capstone/`, outside `v2/`) established that the project
is buildable: three unmodified HACS integrations run against a stock Home Assistant behind
a permission-checked bridge, a 10-check adversarial probe blocks 10/10 on two
architectures, and there is a measured account of the HA API surface across 3,105 repos.

What does *not* exist is a defensible chain of reasoning connecting a problem in the
literature to that artifact. The spike grew outward from code; the report has to grow
downward from a problem. This plan builds the second thing.

**It is 21 August.** The semester runs September–November: roughly 13 calendar weeks,
~10 of them realistically available for engineering once the proposal, mid-report, final
report and defence are accounted for. The advisor pre-proposal is still unsent.

## 2. The central argument: this is not extra work

The obvious objection is that rebuilding costs weeks the project does not have.

It does not, because **the rebuild output *is* the report**, which has to be written
regardless. The first pass produced 250 KB of working notes in `PROJECT_STATUS.md`,
`THREAT_MODEL.md` and four findings documents — reasoning-first prose, chronologically
ordered, full of superseded positions and struck-through text. None of it is submittable
as-is. Converting it at the end, in weeks 9–10, was always the plan's weakest point.

So the real choice is not *rebuild vs. build*. It is *write the report continuously, in
the order that makes it defensible* vs. *write it in a panic in November from notes whose
own author has to reconstruct why each decision was made*. The spike also means the
implementation stage is far cheaper than a normal capstone's, which is precisely what
buys the time.

**Corollary:** the evaluation chapter gets real weight for once. Performance is currently
one of four evaluation axes with zero data.

## 3. Fixed points the plan must respect

| Fixed point | Consequence |
|---|---|
| Advisor is a lead auditor & architect by profession | Threat model and evaluation *methodology* carry the marks; a demo is not a result |
| Advisor contact is an **email carrying the proposal**, not a meeting | The proposal must state positions and invite correction — no live back-and-forth to rely on |
| Graded on Relevance · Feasibility · Innovation · Impact · Clarity | Each chapter should be able to name which criterion it serves |
| Semester is ~10 engineering weeks | Anything not sequenced is not happening |
| ⚠️ Programme deadlines for proposal / mid-report / final / defence are **unknown** | Blocking-ish. Must be resolved from the handbook or the advisor in week 1 — the plan below assumes end-of-November final submission and will need adjusting |

## 4. Three tracks, not one

Running these as one sequence is what would make the rebuild too slow.

- **Track A — the chain (chapters 1–5).** Problem, literature, requirements, threat model,
  architecture. Pure reasoning and reading. This is the rebuild proper.
- **Track B — the artifact (chapters 6–7).** Implementation and evaluation. Mostly
  *closing known gaps* and *measuring*, not writing new subsystems, because the spike
  already exists and works.
- **Track C — the proposal.** Time-critical and short. Draws on A's first two chapters,
  and must not wait for the rest.

Track B has real slack early and none late; Track A is the reverse. They interleave.

---

## 5. Stage plan

### Stage 0 — now → 31 August · *the chain's foundation, and the email out*

> **Outcome:** chapters ✅ delivered ahead of date. The email is **not sent** — parked at the user's instruction of 2026-08-21. See §7 and §9.7.

| Deliverable | Method | Done when |
|---|---|---|
| **Ch. 1 — Problem & context** | HA's own security documentation, the 2021 disclosure, HACS's distribution model, install-base figures from HA analytics | An informed reader agrees there is a current, real exposure, having been shown it rather than told |
| **Ch. 2 — Literature & the gap** | Systematic search: browser-extension permission models, mobile capability systems, IoT platform security (SmartThings/IFTTT literature), plugin sandboxing, prior HA-specific work, the 2026 "Remote Integration Execution" RFC | The gap is stated as one sentence that a hostile reader cannot answer with "but X already did that" |
| **Proposal email** (Track C) | Built from Ch. 1–2 + the spike's demo, measurement, and self-audit | Sent |

> **This stage's real deadline is the email, not the chapters.** If Ch. 2 runs long, the
> email goes out on Ch. 1 plus a provisional gap statement, and the literature chapter
> follows. Advisors invest in projects they helped shape; that value decays every week.

### Stage 1 — September weeks 1–2 · *requirements and threats, in that order*

> **Outcome:** ✅ both chapters complete by 2026-08-24, roughly three weeks early. Programme deadlines remain unresolved; see §9.7.

| Deliverable | Notes |
|---|---|
| **Ch. 3 — Requirements** | Derived from ch. 1–2. Functional, security, and the compatibility constraint that makes the problem hard. Each requirement traceable to something in ch. 1–2, or it does not belong |
| **Ch. 4 — Threat model** | ISO 31000 for process, STRIDE for identification (both from coursework, so defensible from teaching rather than citation). Assets, actors, trust boundaries, then threats **before any architecture** |
| Programme deadlines resolved | Removes the ⚠️ in §3 |

The ordering rule that matters: **the threat model is written before the architecture is
chosen.** In the first pass it came after, which is why its controls read as
justifications. Here it constrains the design instead.

### Stage 2 — September weeks 3–4 · *architecture earned, not assumed*

> **Outcome:** ✅ complete 2026-08-25, about four weeks early. G2 closed with two divergences.

**Ch. 5 — Architecture & design rationale.** Options with genuine trade-offs, evaluated
against ch. 3's requirements and ch. 4's threats. This is where the four re-openable
decisions get settled *in this pass*: platform, compatibility strategy, isolation
primitive, target scope. Rejected alternatives are written up in `notes/`, because a viva
probes exactly there.

Also in this stage: the manifest schema, promoted from strawman to specified.

### Stage 3 — October weeks 1–3 · *the artifact meets the design*

> **Outcome:** 🔵 Chapter 6 drafted §6.1–§6.14 by 2026-08-25, five weeks early. The three named controls are built; **scope item 2, mediated egress, is not** — the open decision in §9.5.

**Ch. 6 — Implementation.** The spike is cited as prior feasibility work, then reconciled
with the design ch. 5 produced. Concretely:

- Close the three known-open controls: **HMAC the audit chain** (~1 h, makes two controls
  fail independently), **cgroups** (the one threat with no control at all), **distinct
  sandbox uid**.
- Reconcile the code with the design wherever ch. 5 diverges from what exists.
- Decide the actuator proof-of-concept on evidence, not on last pass's instinct: one
  `switch` platform end-to-end as an architecture proof, if ch. 4 says the threat model
  needs it.

### Stage 4 — October week 4 → November week 2 · *evaluation, the chapter that is currently empty*

**Ch. 7 — Evaluation.** Methodology and pass/fail criteria written **before** results are

> **Outcome:** 🔵 opened 2026-09-02. §7.1–§7.11 written and dated before any result; §7.12 is the first. The commitment quoted below was kept.
collected, and dated, so it is visibly not fitted to the outcome.

| Axis | State today | Work |
|---|---|---|
| Compatibility | Partial | Widen the integration set; report imports-clean and executed-end-to-end as *separate* numbers |
| Security | Strong | Reproduce the 2021 HACS file-theft pattern: works against baseline HA, blocked by the framework — the single strongest result available |
| **Performance** | **Nothing** | Latency per state update, memory per sandboxed integration, max concurrent integrations — on the Pi 5, recording page size and interpreter version |
| Coverage | Good | Honest supported/unsupported table with the measurement's own limits stated |

### Stage 5 — November weeks 3–4 · *consolidation and defence*

Full read-through for a single voice and consistent claims; figures finalised; the
limitations and future-work chapters written honestly; defence preparation against the
questions in `THREAT_MODEL.md` Part 10.

---

## 6. Gates — where this plan is allowed to change

A plan with no branch points is a plan that will be quietly abandoned.

| Gate | When | If it fires |
|---|---|---|
| **G1 — the gap survives** | End of Ch. 2 | If the literature contains something close to this, the *contribution claim* changes, not the project. Most likely reframing: from "a novel architecture" to "the first empirical account of what confinement costs in compatibility terms" — which the spike already supports and which is arguably the stronger claim anyway |
| **G2 — the four decisions** | End of Ch. 5 | If the fresh chain reaches different decisions, follow it and document the divergence prominently. Re-deriving all four identically is independent confirmation and should be reported as such |
| **G3 — schedule** | End of October | If Stage 4 is at risk, the actuator PoC is cut first, then coverage-widening. Neither the threat model nor the performance axis is cuttable — the first is what this advisor grades, the second is a hole in the evaluation |
| **G4 — the advisor replies** | Whenever | A lead auditor's redirection outranks this plan |

**Gate outcomes as of 2026-09-02.**

- **G1 — fired.** Close prior art exists (Corno & Mannella, SpliTech 2022). The contribution claim
  was reframed from novelty to *constructive and empirical*, which §7.12 has now made good on.
- **G2 — closed.** All four decisions settled in Chapter 5; two confirmed, two diverged.
- **G3 — answered early and not on schedule grounds.** It fired on *coverage*, not time, and
  §6.14.6 recommends `declared` + core packages at 84%. **The cut list in the row above was never
  exercised and should not be**: §5.8.2 found that cutting the actuator leaves S5 unverifiable and
  T05 — the register's joint-highest risk — with no demonstrated control. §6.11.4 records the
  conflict as moot, since the actuator path is built and there is nothing left to cut that would
  save time. The row stands as written because it is what was planned.
- **G4 — cannot fire.** No email has been sent, so no reply is possible. §9.7.

## 7. Risks

| Risk | Likelihood | Response |
|---|---|---|
| Ch. 2 finds close prior art | Medium | G1. Better found in August than November |
| The email stays unsent while chapters are polished | **Medium-high** — this is the plan's real failure mode | Stage 0 deadline is the email; chapters yield to it |
| Rebuild becomes a rewrite and eats the semester | Medium | `00_METHOD.md` §5: code is not retyped. Track B is gap-closing and measurement |
| Performance work blocked on hardware | Low | Pi is verified working as of today, 10/10 on aarch64 |
| Programme deadlines differ from assumptions | Medium | Resolve in Stage 1; re-plan then, cheaply |

## 8. Immediate next actions

1. Chapter 1 — problem and context.
2. Chapter 2 — the literature search, run properly and recorded so it is reproducible.
3. The proposal email, from 1 and 2.

Everything else waits on those three.

---

# 9. Re-fit of 2026-09-02

§5's stage plan assumed the chain would take until late October and the artifact would be
reconciled against it during October. Neither held. This section replaces §5 for everything still
outstanding; §5 is left as written.

## 9.1 Where the work actually is

| | §5 expected by now | Actual |
|---|---|---|
| Ch. 1–4 | in progress, Stage 1 | ✅ complete 2026-08-24 |
| Ch. 5 | not started until late September | ✅ complete 2026-08-25 |
| Ch. 6 | October | 🔵 drafted 2026-08-25, one scope item unbuilt |
| Ch. 7 | late October | 🔵 method pre-registered, 1 of 8 measurements done |
| Ch. 8, front matter | November | ❌ not started |

Roughly five weeks ahead of the stage dates, against an end-of-November assumption that has never
been verified (§3, §9.7).

## 9.2 Three things changed the shape of the remaining work

1. **The artifact came in cheaper than §2 assumed.** §2 argued the rebuild was affordable because
   the implementation stage was mostly gap-closing. It was, and the framework reached eight
   passing self-tests and five corpus measurements in four days.
2. **G3 answered on coverage rather than on schedule**, which is not the branch §6 anticipated,
   and it answered decisively — a profile that dominates every other measured.
3. **The baseline arm returned zero (§7.12), and it moved the weakest point.** With import-level
   compatibility cost measured at zero, the obvious challenge is no longer *"what does confinement
   cost?"* but *"does a confined integration actually run?"* — and N2's level-2 population is
   **one**. That was not the biggest gap in August. It is now.

## 9.3 The ordering principle for what remains

Not the §5 stage order, and not §7.10's measurement order alone. **Order by what a lead auditor
reconciles first, tempered by cost.**

| Rank | Weakness | Cost |
|---|---|---|
| 1 | **F2 and S4 are in the requirements register and absent from the artifact** | 4–6 d |
| 2 | **N2 level 2 — executed end-to-end — has a population of one** | 2–3 d |
| 3 | **S8 is unpaired** — the strongest security claim is not yet a comparison | ~1 d |
| 4 | Mediation latency measured at 2 sandboxes against a budget of 26 | ~1 d |

Rank 1 is the requirements-to-artifact mismatch, which is the first reconciliation an auditor by
profession performs. Rank 3 is cheapest per unit of value and goes first anyway.

## 9.4 The phases

**Phase A — the security axis (~3 days, unconditional).**

| Work | Closes |
|---|---|
| S8 paired baseline: the 2021 file-theft pattern **succeeds** unconfined, blocked confined | S8, T14 |
| S3 paired baseline: what is readable *without* the framework | S3, T06 |
| C3's three hostile manifests — absent, over-broad, deliberately mismatched | C3 |
| Re-verify S5, S7, F4, N3 over the evaluated set, each refusal naming its clause (§6.6.5) | four §7.5 rows |

The unconfined instance now exists, so Phase A is the cheapest high-value work available.

**Phase B — executed end-to-end (~2–3 days).** Three to five integrations driven through their
own config flows, publishing live state through the mediator. Reported as a **named set with its
selection stated**, never as a rate — it will not scale to 37 and §7.4.1 says so. Going from one
to five with a defended selection is the difference between an anecdote and a sample.

**Phase C — performance at scale (~3 days).** Latency at 4/8/16/26 sandboxes (tests §7.6's P4);
PSS against the corpus's real declaration distribution; `fsync`-per-decision (§6.8.3); S9's cost
to a *legitimate* integration (tests P5). Plus §7.9's live defect: `experiments/r2_footprint/`
still carries the pre-§6.3.3 recipe, so either re-run it or caveat 176/136 MB where it is used.

**Phase D — coverage (~2 days).** The uniform-sample corpus re-run, and the honest
supported/unsupported table with the measurement's own limits.

## 9.5 The fork — mediated egress

**Phases A–D are unconditional. This is the one decision left, and it is Younes's.**

| | |
|---|---|
| **Build it** (~4–6 d) | F2, S4, T08, T10, T11 acquire demonstrated controls; §7.5's two ⛔ rows become verifiable; the requirements register matches the artifact |
| **Defer it** | Chapter 8 reports 2 of 20 requirements unverified and says why. Defensible — but it is the mismatch found first |

**Recommendation: decide it after Phase B, not before.** Phases A and B are cheap, they close the
strongest claims, and Phase B supplies something the decision needs — whether integrations run
end-to-end *without* network at all, which bounds what egress would actually buy.

**The standing argument against remains live** and is not a formality: the instruction of
2026-08-21 is to prefer code that can be personally owned and defended over code volume. If the
proxy would arrive undefendable, deferring it and saying so plainly in Chapter 8 is the better
thesis. The prior spike's egress broker is cited as feasibility and, under `00_METHOD.md` §5, is
not retyped.

## 9.6 Totals

| | Deferring egress | Building it |
|---|---|---|
| Phases A–D | 10–11 d | 10–11 d |
| Egress | — | 4–6 d |
| Ch. 7 write-up (~8 obligations, §7.8) | 3–4 d | 3–4 d |
| Ch. 8 — limitations, `aiofiles`, the 52-vs-2 finding, future work | 2 d | 2 d |
| ~~Front matter, abstract, bibliography (18 refs), figures~~ | ~~1 d~~ | ✅ **Done 2026-09-04.** **28 refs, not 18** — the count was never checked against the chapters |
| Stage 5 — single-voice read-through, defence prep | 3–5 d | 3–5 d |
| **Total** | **~19–23 d** | **~23–29 d** |

Engineering days at a defensible pace, **not** the four-day sprint that produced Chapters 5 and 6.
They are not convertible to a calendar while §9.7's first row stands.

## 9.7 Risks, re-rated

| Risk | August rating | 2026-09-02 |
|---|---|---|
| **Programme deadlines differ from assumptions** | Medium | **Unchanged and unresolved.** §3 marked it blocking-ish and Stage 1 was to close it from the handbook or the advisor. It is the only input that makes §9.6 mean anything, and the handbook route needs nobody's reply |
| **The email stays unsent while chapters are polished** | **Medium-high — "the plan's real failure mode"** | **Materialised.** Parked at the user's instruction of 2026-08-21; recorded here as status, not as a recommendation. Consequence: G4 cannot fire, so no advisor redirection is available at any point in §9.4 |
| Ch. 2 finds close prior art | Medium | **Occurred.** G1 fired, claim reframed, and §7.12 has now made the reframed claim good |
| Rebuild becomes a rewrite and eats the semester | Medium | **Did not occur.** Five weeks ahead |
| Performance work blocked on hardware | Low | **Did not occur**, though the Pi was unreachable on 2026-09-02 until powered on. Single point of failure |
| ~~**The repository has no remote**~~ | not listed in August | ✅ **Closed 2026-09-02.** Pushed to a private `git@github.com:Speedylo/ha_security.git`; 68 commits, 272 files. It was the highest-severity item on this list for twelve days and it cost ten minutes |

## 9.8 What this section supersedes

- **§5's Stage 3, 4 and 5 dates** — replaced by §9.4 and §9.6. Stages 0–2 are complete and their
  outcomes are annotated in place.
- **§6's G3 cut list** — G3 fired on coverage and was answered; §6.11.4 records the cut-order
  conflict as moot. The row is left as written because it is what was planned.
- **§8's immediate next actions** — all three are done except the email. §9.4's Phase A replaces
  them.

Not superseded: `00_METHOD.md` in its entirety, §2's argument for why the rebuild was not extra
work, §3's fixed points, and §4's three tracks. Track A is complete, Track B is where the work now
is, and Track C never started.
