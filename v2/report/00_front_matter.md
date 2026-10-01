# Confining Unmodified Third-Party Integrations in Home Assistant

## A Declared-Authority Architecture and Its Measured Cost

**Younes Rahati**

<!-- HANDBOOK: the four fields below are placeholders. They are the only content in this report
     that cannot be derived from the work itself, and they are blocked on the same unresolved
     input as every date in 01_PLAN.md §9.6 — see "Outstanding" at the foot of this page. -->

| | |
|---|---|
| Degree and programme | *[to be supplied — see note below]* |
| Institution | *[to be supplied]* |
| Supervisor | *[to be supplied]* |
| Submitted | *[to be supplied]* |

Report prepared 21 August – 8 September 2026. Artifact, measurements and chapter sources:
`git@github.com:Speedylo/ha_security.git` (private), directory `v2/`.

---

## Abstract

Home Assistant reports 669,743 active installations [1], and a third-party integration installed
into one of them executes inside the platform's own process with the platform's own authority.
There is no permission model, no scoping rule and no caller check [2]: an integration that declares
itself a temperature sensor may call `lock.unlock`, read every stored credential, reach the home
network, and — as Corno and Mannella demonstrate [9] — walk the Python garbage collector to another
integration's live object and read its secrets. The 2021 disclosures show this is not hypothetical
for this ecosystem [4][6]. **This work designs, builds and evaluates confinement for these
integrations without modifying them**, on the ground that the declaration such a scheme needs
already exists in every integration's manifest and is currently spent on a log line and a discovery
heuristic. Enforcement is placed outside the integration's process, because the garbage-collector
result eliminates every in-process design; the integration runs unmodified inside Linux namespaces,
seccomp and cgroup v2, against a real stripped Home Assistant, and reaches the platform and the
network only through a mediator that holds the credential it never sees.

**The cost of confinement, measured against an unconfined baseline on the same host and release,
is zero at the import level.** Across 77 community integrations on two corpora sharing 5% of their
members — 37 by install count and 40 drawn uniformly — the confined and unconfined arms fail on the
*same* integrations for the *same* reasons: 84% and 92% clean in both arms, so the failures
attributable to the design number none, twice. Five integrations were executed end to end, the
ceiling being that 26 of 37 need a credential before any configuration flow completes; one of them,
`nordpool`, published the same electricity price confined as unconfined, in the same minute,
through a mediated connection logged to a named host and port. On the Raspberry Pi 5 the
requirements name, mediation costs 31.5 µs and the audit record is durable before the action it
records at 3.67 ms, 63× clear of realistic demand. Nineteen self-test suites pass; against the
project's own eighteen-threat register thirteen threats are demonstrated, five of them paired
against an unconfined arm, and against the closest published model eight of eleven are mapped.

**The most useful result was a failure, and it arrived last.** Running a single real community
integration confined against its own real API found that the platform's own HTTP helper could not
be constructed inside the sandbox at all — `async_get_clientsession` builds its resolver by
instantiating Zeroconf, which joins the multicast group, and a fresh network namespace's loopback
carries no multicast flag. The egress design had therefore been unusable for the 41% of the corpus
it exists to serve, for as long as it had existed, **behind eighteen suites that all passed**, because
every earlier subject had been written by the author of the sandbox. Two measured steps fixed it.
Four other mechanisms in this project each caught a class of error — a paired baseline stopped three
misattributions, two instruments bounded each other, a self-test passed when the surprising thing
was true, a figure was recomputed from its source — and none of the four could have found this one,
because all four are written out of the same assumptions as the thing they test. Six of eight
predictions registered before measurement were wrong and none was revised. Every correction across
eight chapters has been to a sentence next to a measurement and none to a measurement; the two
exceptions were defects in the artifact rather than in the report, and both were found this way.

**Keywords:** Home Assistant; smart-home gateway; extension security; permission manifest;
sandboxing; Linux namespaces; seccomp; cgroup v2; least privilege; threat modelling; STRIDE;
ISO 31000; empirical evaluation.

---

## Declaration

<!-- HANDBOOK: most programmes prescribe exact wording for this and for an AI-use statement, and
     substituting invented wording for a prescribed form is worse than leaving the form visible.
     The factual content each will need is stated here so only the phrasing has to change. -->

*[Wording to be supplied from the programme handbook.]* The factual content it will need:

- The design, implementation, measurements and text of this report are the author's own work.
  Sources are cited at every use and consolidated in `09_references.md`.
- **A prior two-week feasibility spike by the same author exists** and is *not* part of this
  submission. `00_METHOD.md` §2 states the rule this report is written under: everything learned in
  that spike is private knowledge that is **not citable until re-derived in this pass**. Where the
  spike's finding is mentioned it is labelled as prior work with its date and explicitly not relied
  on — §6.10.2 is the worked example.
- **Generative AI was used as a working tool throughout**, for drafting prose, writing code and
  reviewing arguments. Every measurement reported here was executed by the author on the hardware
  named in §3.3 and every figure in the report is reproducible from the scripts and result files in
  the repository. The exact disclosure form the programme requires should replace this bullet.

## Acknowledgements

*[To be supplied.]*

---

## Contents

Chapter and section level. Third-level headings — 248 of them — are omitted; the chapters carry
their own internal signposting. **Generated by `report/toc.py`, not maintained by hand**, for the
same reason the threat-model figure is generated from the model file: a contents page edited
separately from the thing it describes is wrong within a session and nothing says so. Run
`python3 report/toc.py --check` to fail loudly if it has gone stale.

<!-- toc:start -->

| | Section | |
|---|---|---|
| | **Chapter 1 — Problem and Context** | `01_problem_and_context.md` |
| 1.1 | Introduction | |
| 1.2 | How Home Assistant is extended | |
| 1.3 | The distribution channel and the scale of exposure | |
| 1.4 | What HACS verifies before listing an integration | |
| 1.5 | The exposure is documented, not hypothetical | |
| 1.6 | The review that does happen, and what it covers | |
| 1.7 | What is at stake | |
| 1.8 | The stated positions of the platform and the channel | |
| 1.9 | The problem is recognised, but framed as a reliability problem | |
| 1.10 | Problem statement | |
| | **Chapter 2 — Literature and the Gap** | `02_literature_and_gap.md` |
| 2.1 | Scope and method of this review | |
| 2.2 | The precedent: least privilege for extensions is a solved problem elsewhere | |
| 2.3 | Smart-home application platforms: a decade of work on a different platform model | |
| 2.4 | Extensible hubs, and the closest prior work | |
| 2.5 | The distribution channel: supply-chain attacks | |
| 2.6 | Measurement as a method for justifying a privilege model | |
| 2.7 | The gap | |
| 2.8 | Contribution claim | |
| 2.9 | Threats to the validity of this review | |
| | **Chapter 3 — Requirements** | `03_requirements.md` |
| 3.1 | How these requirements were derived | |
| 3.2 | Stakeholders | |
| 3.3 | Constraints | |
| 3.4 | Functional requirements | |
| 3.5 | Security requirements | |
| 3.6 | Non-functional requirements | |
| 3.7 | Non-goals | |
| 3.8 | Traceability | |
| 3.9 | What this chapter fixes, and what it leaves open | |
| | **Chapter 4 — Threat Model** | `04_threat_model.md` |
| 4.1 | Framework, and why two of them | |
| 4.2 | Scope of the assessment (ISO 31000 §6.3.2) | |
| 4.3 | Context (ISO 31000 §6.3.3) | |
| 4.4 | Assets (ISO 31000 §6.3.2) | |
| 4.5 | Actors | |
| 4.6 | Trust boundaries | |
| 4.7 | Risk criteria (ISO 31000 §6.3.4) | |
| 4.8 | Risk identification: STRIDE per boundary (ISO 31000 §6.4.2) | |
| 4.9 | Risk analysis and evaluation (ISO 31000 §6.4.3–6.4.4) | |
| 4.10 | Risk treatment (ISO 31000 §6.5) | |
| 4.11 | Residual risk statement (ISO 31000 §6.5.3) | |
| 4.12 | Monitoring and review (ISO 31000 §6.6) | |
| 4.13 | Limits of this threat model | |
| 4.14 | Relationship to the closest published model | |
| | **Chapter 5 — Architecture and design rationale** | `05_architecture.md` |
| 5.1 | What this chapter must settle | |
| 5.2 | The design problem, restated precisely | |
| 5.3 | Where enforcement can live | |
| 5.4 | Decision 1 — the platform | |
| 5.5 | The relocation problem | |
| 5.6 | Decision 2 — how the integration runs, and what it finds | |
| 5.7 | Decision 3 — the isolation primitive | |
| 5.8 | Decision 4 — scope | |
| 5.9 | Who authors the manifest | |
| 5.10 | The manifest | |
| 5.11 | The mediator and the channel | |
| 5.12 | Identity and the audit record | |
| 5.13 | Defence in depth | |
| 5.14 | The design drawn, and the controls checked | |
| 5.15 | What this design does not do | |
| | **Chapter 6 — Implementation** | `06_implementation.md` |
| 6.1 | What this chapter must deliver | |
| 6.2 | The prior artifact, and what it is allowed to prove | |
| 6.3 | The sandbox | |
| 6.4 | The supervisor | |
| 6.5 | The channel | |
| 6.6 | The manifest, and the permit path | |
| 6.7 | Where the user meets the declaration | |
| 6.8 | Identity, and the record that makes a decision attributable | |
| 6.9 | The adversarial cases | |
| 6.10 | The bridge | |
| 6.11 | What is not built, and what Gate G3 has to decide | |
| 6.12 | Un-stripping toward `http`, and what it costs | |
| 6.13 | The declared profile, and a prediction that did not survive | |
| 6.14 | The core package set, and the profile that dominates every other | |
| | **Chapter 7 — Evaluation** | `07_evaluation.md` |
| 7.1 | The rule this chapter is written under | |
| 7.2 | What is being evaluated, and the claim under test | |
| 7.3 | The spine: Chapter 3's verification column | |
| 7.4 | The four axes | |
| 7.5 | Pass/fail criteria, fixed in advance | |
| 7.6 | Predictions recorded before the measurements run | |
| 7.7 | What would falsify the central claim | |
| 7.8 | Obligations this chapter inherits | |
| 7.9 | Threats to the validity of this evaluation | |
| 7.10 | The measurement schedule | |
| 7.11 | What this chapter cannot do | |
| 7.12 | The baseline arm, and what 84% actually was | |
| 7.13 | S8's paired baseline — the 2021 pattern, with and without the framework | |
| 7.14 | S3's paired baseline — the surveillance the framework removes | |
| 7.15 | S1's baseline — the attack that forced the architecture, made real | |
| 7.16 | C3, and the remaining security criteria re-verified | |
| 7.17 | N2's second number — integrations executed end-to-end | |
| 7.18 | How much egress is actually needed, and of what kind | |
| 7.19 | Mediation latency at the budget, and why the number that matters is the other one | |
| 7.20 | What durability costs, what S9 costs, and one measurement that would not resolve | |
| 7.21 | A reconciliation pass, and what reading the chapter against Chapter 6 found | |
| 7.22 | S9, wired to the manifest — the one finding this chapter acted on | |
| 7.23 | The uniform-sample corpus — the last scheduled measurement | |
| 7.24 | What egress actually looks like, measured before the proxy is built | |
| 7.25 | F2 and S4, closed — the egress proxy, evaluated rather than merely built | |
| 7.26 | The read-through — the two registers scored, and what one voice found | |
| 7.27 | F2 against a real integration's real API — and what only a real one could find | |
| 7.28 | The whole-report read-through, and the requirement it found unverified | |
| 7.29 | C1, counted — the check §7.28 said did not exist | |
| 7.30 | T12, measured — the declaration re-checked per version | |
| | **Chapter 8 — Conclusions, Limitations and Future Work** | `08_conclusions.md` |
| 8.1 | What this chapter is for, and what it will not repeat | |
| 8.2 | The central claim, answered against the falsifiers fixed in advance | |
| 8.3 | The three contributions, closed against §2.8 | |
| 8.4 | What this project got wrong, and why the record of it is a result | |
| 8.5 | The finding nobody was looking for | |
| 8.6 | Limitations | |
| 8.7 | Future work, priced and ordered | |
| 8.8 | The single ask of the platform | |
| 8.9 | What a reader should take from this | |
| | **References** | `09_references.md` |

<!-- toc:end -->

---

## Figures

<!-- figures:start -->

| Figure | Subject | In | Generated by |
|---|---|---|---|
| **4.1** | Home Assistant as it stands today, with the six trust boundaries of §4.6 overlaid; four of the six do not exist | `04_threat_model.md` | `figures/fig_4_1_current_state.py` |
| **5.1** | The same system with the design of Chapter 5 applied, drawn on Figure 4.1's canvas | `05_architecture.md` | `figures/fig_5_1_confined.py` |

<!-- figures:end -->

## Tables

Three tables are numbered, and they are the three the report navigates *to*. They are listed here;
the other 154 are not.

| Table | Subject | In | Referred to from |
|---|---|---|---|
| **1.1** | Scale of the custom-integration ecosystem | `01_problem_and_context.md` | §1.3, §1.6 |
| **1.2** | Authority held by any custom integration | `01_problem_and_context.md` | §1.7, §2.4.1, §2.4.2, §2.7, §3.4, §3.5, §4.2, §4.4, §4.6, §5.2 |
| **2.1** | Platform assumptions in prior work versus Home Assistant | `02_literature_and_gap.md` | §2.3, §2.7, §3.3, §3.8 |

**The other 154 tables are deliberately unnumbered**, and the split is the point rather than an
inconsistency. Table 1.2 is an exhibit: five later chapters derive requirements, assets and
boundaries from it by name. The rest are two- to six-row registers embedded in the argument they
belong to — a requirement and its derivation, a threat and its rating, a prediction and its outcome
— which no section refers to from elsewhere. Numbering those would create 150 cross-reference
targets nothing uses. **If the handbook requires every table numbered, this is the decision to
revisit**, and the work is mechanical.

---

## Abbreviations and conventions

| | |
|---|---|
| **HA** | Home Assistant. Version pinned throughout: **2026.8.3** (`759e465`, 21 August 2026) |
| **HACS** | Home Assistant Community Store — the distribution channel for third-party integrations |
| **Integration** | Third-party code that connects a device or service to Home Assistant's entity model. The subject of this report. Distinct from an **add-on**, which is a separate container and already isolated [3] |
| **Mediator** | The out-of-process component that holds the platform credential and decides every request a confined integration makes |
| **Manifest** | An integration's declaration. Its `manifest.json` already exists; this work adds a permissions clause and makes it load-bearing |
| **Sandbox** | One confined integration: its own user, mount, PID, network and IPC namespaces, a seccomp filter and a cgroup |
| **F*n* / S*n* / C*n* / N*n*** | Functional, security, constraint and non-functional requirements (Chapter 3). Twenty in the §7.5 verdict table |
| **T*nn*** | Threats in Chapter 4's register (eighteen). **R*n*** are its residual risks (seven) |
| **P*n*** | Predictions registered in Chapter 7 *before* the corresponding measurement (eight; six were wrong) |
| **G1–G4** | Gates at which the plan was allowed to change (`01_PLAN.md` §6) |
| **netns** | Linux network namespace |
| **cgroup v2** | Linux control-group hierarchy, used here for memory, CPU, PID and disk bounds |
| **seccomp** | Linux system-call filter. This work denies 29 calls, returning `EPERM` rather than killing, so a refusal stays legible |
| **PSS** | Proportional set size — the memory accounting used for per-sandbox cost, because shared pages must not be counted once per sandbox |
| **MAC** | Message authentication code (the audit chain's keyed half). Never *media access control* in this report |
| **mDNS** | Multicast DNS, the local discovery protocol whose multicast join broke egress (§7.27.2) |
| **STRIDE** | Spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege [26] — the risk-identification technique of Chapter 4 |
| **ISO 31000** | The risk-management process Chapter 4 follows clause by clause [25] |
| **§x.y** | A section of this report. **§x.y of `01_PLAN.md` or `00_METHOD.md`** is always named explicitly |

**Two conventions the reader should know before Chapter 5.**

1. **Superseded text is not edited to be right.** Where a later chapter corrects an earlier one, the
   earlier text stands as written and gains a forward pointer. §5.6.5 predicted the base component
   would roughly double the budget and §6.3.2 measured 1.53×; §5.6.5 still says "roughly doubles"
   and points at §6.3.2. This is deliberate, so a reader can check what was believed before the
   number arrived rather than only what is believed after.
2. **Every number is attributed to the run that produced it**, and results files live beside the
   chapters in `experiments/`. Where a claim is reasoned rather than measured, the chapter says so
   in the same sentence.

---

## The artifact

| | |
|---|---|
| Framework | `v2/framework/confine/` — standard library plus `ctypes`, no dependencies, no override flag |
| Self-tests | **20 suites**, all passing on the test hardware. `selftest_*.py` in the same directory — the pattern is exact, and `selftest.py`, the framework's own base self-test, is counted separately in `01_PLAN.md` rather than among the suites |
| Experiments | `v2/experiments/` — each with its script, its raw result file and a readable write-up |
| Figures | `v2/figures/` — each figure and its threat model generated from one source |
| Method and plan | `v2/00_METHOD.md` (ground rules and the evidence rule), `v2/01_PLAN.md` (stages and gates) |
| Working notes | `v2/notes/` — the decision records, evidence write-ups and pre-registered predictions the chapters cite by name. Reasoning that supports the report without belonging in it |
| Test hardware | Raspberry Pi 5, 4 GB, Pi OS. Every measurement in Chapters 6 and 7 was taken on it |

---

## Outstanding

Recorded here rather than left for a reader to discover.

- **The four fields on the title page and the two prescribed statements above are unsupplied**,
  and they are the same unresolved input as `01_PLAN.md` §9.7's top-ranked risk: programme
  deadlines and requirements for proposal, mid-report, final and defence are not known. Nothing
  else in this report is blocked on it.
- **Three bibliographic details in `09_references.md` are unverified against the source itself**
  and are listed at the foot of that file.
- ~~**This front matter has not been through the Stage 5 read-through**~~ — **done 2026-09-08, and
  it found five things.** Three were in the abstract, the newest prose in the report: mediation
  latency was given as §5.11.4's **30 µs** floor in a sentence whose other two figures are
  §7.20.1's, where the corrected figure §8.2.3 quotes is **31.5 µs**; *"two lines fixed it"* described
  a fix that is a flag bit and a route added by `SIOCADDRT`, which §7.27.3 calls two measured
  *steps*; and the closing sentence claimed every correction was to a sentence next to a measurement
  in the paragraph immediately after describing a correction to the artifact — the two exceptions now
  travel with the claim. The other two: the Tables section stated **149** unnumbered in one sentence
  and **152** in the next (155 tables, 3 numbered — `report/toc.py` checked the second sentence and
  not the first, and now checks both), and the abbreviations table still said **six** residual risks
  where §4.11 gained **R7** on 2026-09-04. **No measured figure was wrong**, which is the seventh
  consecutive pass over this project's prose where that has held.
