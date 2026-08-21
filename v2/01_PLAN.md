# Rebuild plan

**Written:** 2026-08-21 · **Status:** working note · **Covers:** 2026-08-21 → end of November 2026

Companion to `00_METHOD.md`, which fixes the ground rules. This plan says what gets
built, in what order, why that order, and where the plan is allowed to change.

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

| Deliverable | Method | Done when |
|---|---|---|
| **Ch. 1 — Problem & context** | HA's own security documentation, the 2021 disclosure, HACS's distribution model, install-base figures from HA analytics | An informed reader agrees there is a current, real exposure, having been shown it rather than told |
| **Ch. 2 — Literature & the gap** | Systematic search: browser-extension permission models, mobile capability systems, IoT platform security (SmartThings/IFTTT literature), plugin sandboxing, prior HA-specific work, the 2026 "Remote Integration Execution" RFC | The gap is stated as one sentence that a hostile reader cannot answer with "but X already did that" |
| **Proposal email** (Track C) | Built from Ch. 1–2 + the spike's demo, measurement, and self-audit | Sent |

> **This stage's real deadline is the email, not the chapters.** If Ch. 2 runs long, the
> email goes out on Ch. 1 plus a provisional gap statement, and the literature chapter
> follows. Advisors invest in projects they helped shape; that value decays every week.

### Stage 1 — September weeks 1–2 · *requirements and threats, in that order*

| Deliverable | Notes |
|---|---|
| **Ch. 3 — Requirements** | Derived from ch. 1–2. Functional, security, and the compatibility constraint that makes the problem hard. Each requirement traceable to something in ch. 1–2, or it does not belong |
| **Ch. 4 — Threat model** | ISO 31000 for process, STRIDE for identification (both from coursework, so defensible from teaching rather than citation). Assets, actors, trust boundaries, then threats **before any architecture** |
| Programme deadlines resolved | Removes the ⚠️ in §3 |

The ordering rule that matters: **the threat model is written before the architecture is
chosen.** In the first pass it came after, which is why its controls read as
justifications. Here it constrains the design instead.

### Stage 2 — September weeks 3–4 · *architecture earned, not assumed*

**Ch. 5 — Architecture & design rationale.** Options with genuine trade-offs, evaluated
against ch. 3's requirements and ch. 4's threats. This is where the four re-openable
decisions get settled *in this pass*: platform, compatibility strategy, isolation
primitive, target scope. Rejected alternatives are written up in `notes/`, because a viva
probes exactly there.

Also in this stage: the manifest schema, promoted from strawman to specified.

### Stage 3 — October weeks 1–3 · *the artifact meets the design*

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
