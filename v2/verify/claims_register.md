# Claim register

The claim inventory the verification plan rests on (`notes/verification_plan_20261005.md` §3).
**Started 2026-10-05.** Nothing in this file has been tested yet: every status is *pending* until
the campaign runs on the frozen tag.

## How to read it

**Tiers.** The extractor (`verify/extract_claims.py`) found **1,980 candidate sentences and table
rows** in the front matter and Chapters 5–8, about four times the plan's estimate. Many restate the
same result or record dated history. So the register works in three tiers:

- **Tier A — curated one claim per row:** the abstract, the 20 requirements, the 19 internal and 11
  external threat verdicts, the central claim's three assertions and the three contributions. These
  are the claims an examiner checks first. *(This file, below.)*
- **Tier B — one row per measurement:** each Chapter 7 results table or figure set, tied to its
  evidence directory and its criterion. *(Next.)*
- **Tier C — triage of the remaining candidates:** each is linked to the Tier A or B row that covers
  it, or marked as dated history. *(After B.)*

**Columns.**
- **Type:** *M* measured · *T* self-test · *A* argued · *C* cited · *D* design.
- **Measured on:** the date of the run the claim currently rests on.
- **Test:** the plan's methods. *R* regression (L1–L3) · *RM* re-measure (Phase 3) · *RD* re-derive
  from raw data · *X* mutant (with its number) · *CT* negative control · *FI* fault injection · *CI*
  citation check · *DC* document consistency · *H* the human path.
- **Status:** *pending* until run, then *Verified*, *Qualified*, *Withdrawn* or *Argued*.
- **Flag:** a problem found while building the register, before any test. Each flag is also in the
  plan's findings log.

## A1 — The abstract

| ID | Claim | Type | Evidence | Measured on | Test | Status | Flag |
|---|---|---|---|---|---|---|---|
| A1.01 | Home Assistant reports 669,743 active installations | C | [1], retrieved 2026-08-21 | — | CI | pending | |
| A1.02 | No permission model, no scoping rule, no caller check | C | [2] | — | CI | pending | |
| A1.03 | A sensor integration may call `lock.unlock`, read every stored credential, reach the home network | A/M | §2.4, §7.13, §7.15 unconfined arms | 09-02, 10-03 | RM (unconfined arms), CI | pending | |
| A1.04 | Garbage-collector walk reaches another integration's secrets [9] | C/M | [9]; §7.15.3 reproduced it | 10-03 | RM, CI | pending | |
| A1.05 | The 2021 disclosures show it is not hypothetical [4][6] | C | [4], [6] | — | CI | pending | |
| A1.06 | Integrations confined **without modifying them** | M | C1, §7.29: zero source changes | 10-03 | RM (C1 integrity), X14 | pending | |
| A1.07 | The declaration already exists in every manifest, spent on a log line and a discovery heuristic | A/C | §5.9 | — | CI (HA source) | pending | |
| A1.08 | Garbage-collector result eliminates every in-process design | A | §5.3 | — | — (argued; wording must say so) | pending | |
| A1.09 | Runs inside namespaces, seccomp, cgroup v2, against a real stripped HA, reaching platform and network only through the mediator, which holds a credential the integration never sees | D/M | §6, §7.13, §7.15.3 | 10-03 | R, X2, X13, X15 | pending | |
| A1.10 | Import-level cost of confinement is **zero**, against an unconfined baseline, same host and release | M | §7.12, §7.23, §7.31 | 10-03 | RM, RD | pending | |
| A1.11 | 77 integrations, two corpora sharing 5%, 37 by install count and 40 uniform | M | §7.23 | 10-03 | RD | pending | |
| A1.12 | Same failures for the same reasons; 84% and 92% clean in both arms | M | §7.12, §7.23 | 10-03 | RM, RD | pending | |
| A1.13 | **Ten** integrations executed end to end, a named set; 26 of 37 need a credential | M | §7.17, §7.31, §7.17.1 | 10-03 | R (L3), RD | pending | **F01: stale — thirteen since §7.40–§7.42** |
| A1.14 | **All ten** load confined | M | §7.31 | 10-03 | R (L3) | pending | F01 |
| A1.15 | Five that poll an API match unconfined output: three exactly, two within a live value's movement | M | §7.31 | 10-03 | RM, RD | pending | |
| A1.16 | Through mediated connections logged to a named host and port, over three network stacks | M | §7.31 | 10-03 | RM, RD | pending | |
| A1.17 | One with a valid account credential that never reached the mediator | M | §7.34 | 10-03 | RM, RD (scan of records) | pending | |
| A1.18 | Mediation costs 31.5 µs on the Pi 5 | M | §7.19 | **08-24** | RM ×3 | pending | stale code |
| A1.19 | Audit record durable before its action, 3.67 ms | M | §7.20.1, §7.36.1 | 10-03 | RM on disk ×3, X7 | pending | |
| A1.20 | 63× clear of realistic demand | M | §7.20.1, §7.18 | 09-02 | RD | pending | |
| A1.21 | Entities in (A) are registry entities with unconfined names and survive a restart | M | §7.37 | 10-04 | R (L2, `--restart`) | pending | |
| A1.22 | Real changes reach it **within a millisecond** | M | §7.37 | 10-04 | RM ×3 | pending | **F02: median 0.71 ms, worst 1.57 ms** |
| A1.23 | A user's command reaches the integration's own code in 16 ms | M | §7.38 | 10-04 | RM ×3 | pending | |
| A1.24 | A flood is stopped after 100 refusals, within a second; the household is told in Repairs and can restart without widening permissions | M | §7.44 | 10-05 | R, RM, X11, X12, H | pending | |
| A1.25 | Twenty-six self-test suites pass | T | suite logs | 10-05 | R (L1 ×2) | pending | |
| A1.26 | Nineteen threats, fifteen demonstrated, five paired | M/A | §7.26.3, §7.30.5, §7.44.4 | mixed | see A3 | pending | |
| A1.27 | Eight of the closest published model's eleven threats are mapped | A | §7.26.4 | 09-03 | see A4 | pending | |
| A1.28 | `async_get_clientsession` built Zeroconf, and a fresh netns's `lo` has no multicast flag | M | §7.27.2 | 09 | RM (a regression case exists) | pending | |
| A1.29 | Egress unusable for the 41% of the corpus it serves, behind eighteen passing suites | M/A | §7.27, §5.6 | 09 | RD | pending | |
| A1.30 | Three further defects behind twenty passing suites, two of which had produced wrong attributions | M | §7.31 | 10-03 | RD (history) | pending | |
| A1.31 | Record-after-act for every acting operation, 2026-08-25 to 2026-10-04 | M | §7.36.1 | 10-04 | X7, RD (git history) | pending | |
| A1.32 | Six of eight predictions registered before measurement were wrong; none revised | M | §8.4.1, §7.6 | — | RD (git timestamps of predictions) | pending | |
| A1.33 | Corrections were to sentences, not measurements, except named artifact defects (1 + 4 + 3) | A | §8.4.2 | — | RD (recount) | pending | |
| A1.34 | On a corrected instance the end-to-end cost is none; import-level figures did not move | M | §7.31.6, §7.31.12 | 10-03 | RM | pending | |

## A2 — The 20 requirements (§7.5)

| ID | Requirement, as tested | Verdict now | Evidence | Measured on | Test | Status | Flag |
|---|---|---|---|---|---|---|---|
| C1 | Zero changed source lines, counted | Counted | §7.29 | 10-03 | RM, X14 | pending | |
| C2 | Every arm on unmodified HA 2026.8.3, recorded in each result | Met | §7.12 | 10-03 | RD (every result file) | pending | |
| C3 | Absent, over-broad, mismatched manifests handled per §5.9 | Met | `selftest_c3` | 10-05 | R | pending | |
| C4 | Every performance figure on the Pi 5, memory and latency | Met | §7.19–§7.22 | mixed | RM | pending | |
| F1 | Entities present and behave as native | Met | §7.17.3, §7.37 | 10-04 | R (L2, L3) | pending | |
| F2 | A declared API polled successfully while confined | Met | §7.25, §7.27, §7.31 | 10-03 | R (L3) | pending | |
| F3 | Every decision names its clause; a clause-less decision is unconstructible | Met | §7.4.2, §7.16.1 | 10-05 | RD (every record in every committed log), X3 | pending | **F03: refusals are built with `clause=None` (default deny, a command with no sandbox, the cut-off record)** |
| F4 | Manifest renders, denials at the same weight as grants | Met | `selftest_describe` | 10-05 | R | pending | |
| S1 | GC technique reaches nothing confined; mediator and credential unreachable | Met, paired | §7.15.3 | 10-03 | RM, CT (unconfined), X2 | pending | |
| S2 | No credential recoverable from env, filesystem, process table or memory | Met, paired | §7.13, §7.15.3 | 09-02 | RM, CT, X15 | pending | |
| S3 | Read and subscription to undeclared entities denied, paired | Met | §7.14, §7.36 | 10-04 | RM, CT, X10 | pending | |
| S4 | A host declared only by another integration is denied | Met | §7.25 | 09-03 | R, X3 | pending | |
| S5 | `lock.lock` does not permit `lock.unlock`; structural | Met | §7.16.1 | 10-05 | R, X17 | pending | |
| S6 | No manifest and unparseable manifest each denied everything, naming the rule | Met | `selftest_policy` | 10-05 | R, X1 | pending | |
| S7 | Three-part identity; modification, deletion, reordering each detected, chains independent | Met | `selftest_audit`, §7.32 | 10-05 | R, X8, FI (disk full) | pending | |
| S8 | 2021 file theft succeeds unconfined, blocked confined, same host and release | Met, paired | §7.13.2 | **09-02** | RM, CT, X13, X14 | pending | stale code |
| S9 | CPU, memory, disk exhaustion does not hang the gateway, unprivileged | Met, narrowed | §7.22 | 09 | RM | pending | |
| N1 | Latency, memory, concurrency reported against a baseline | Met as specified | §7.19–§7.20 | **08-24** / 10-03 | RM ×3 | pending | |
| N2 | Imports-clean and end-to-end reported separately, never conflated | Met | §7.12, §7.17 | — | DC | pending | |
| N3 | Mediator unavailability specified and tested; refuses rather than degrades | Met | `preflight`, §7.16.2 | 10-05 | FI | pending | |

## A3 — Chapter 4's 19 threats (§7.26.3, restated by §7.30.5 and §7.44.4)

| ID | Verdict now | Evidence | Test | Status | Flag |
|---|---|---|---|---|---|
| T01 | Demonstrated, paired | §7.15.3 | RM, CT, X2 | pending | |
| T02 | Demonstrated | §7.16.1, `selftest_channel` | R, X2 | pending | |
| T03 | Demonstrated, unpairable | §7.15.3, §7.13.3 | RM | pending | |
| T04 | Demonstrated, paired | §7.15.3 | RM, CT | pending | |
| T05 | Demonstrated | §7.16.1 | R, X17 | pending | |
| T06 | Partial → closed at the stand-in and (A) | §7.14, §7.36 | RM, X10 | pending | wording to settle |
| T07 | Demonstrated | §7.16.1 | R | pending | |
| T08 | Demonstrated | §7.25.2 | R, X3 | pending | |
| T09 | Retained (R5), measured | §7.24.5 | RD | pending | |
| T10 | Demonstrated at the decision layer | §7.26.2, §7.43 | R, X4, X5 | pending | |
| T11 | Demonstrated at the decision layer | §7.26.2 | R, X6 | pending | |
| T12 | Demonstrated at the decision layer | §7.30 | R (`selftest_t12`), X9 | pending | |
| T13 | Retained, ceiling measured | §7.16.1 | R | pending | |
| T14 | Demonstrated, paired | §7.13.2 | RM, CT, X14 | pending | stale code (09-02) |
| T15 | Demonstrated, paired | §7.13 | RM, CT, X15 | pending | stale code (09-02) |
| T16 | Partial (space yes, I/O not delegated) | §7.22 | RM | pending | |
| T17 | Demonstrated, paired | §7.15.3 | RM, CT | pending | |
| T18 | Demonstrated, bounded by R4 | §7.16.2, §7.32 | R, X7, X8 | pending | |
| T19 | Demonstrated, unpairable | §7.44 | R, X11, X12, H | pending | |

## A4 — Corno and Mannella's 11 (§7.26.4)

| ID | Verdict | Maps from | Test | Status | Flag |
|---|---|---|---|---|---|
| CM-T1 | Demonstrated, four of five paired | T04, T06, T14, T15, T17 | via A3 | pending | |
| CM-T2 | Split: T08 demonstrated, T09 retained | T08, T09 | via A3 | pending | |
| CM-T3 | Demonstrated | T05, T10 | via A3 | pending | |
| CM-T4 | Demonstrated | T07, T17 | via A3 | pending | |
| CM-T5 | Unmapped | — | DC | pending | |
| CM-T6 | Unmapped | — | DC | pending | |
| CM-T7 | Partial | T16 | via A3 | pending | **F04: T19 now also maps here (§4.8); the row predates it** |
| CM-T8 | Out of reach, retained | — | DC | pending | |
| CM-T9 | Demonstrated | T02, T11 | via A3 | pending | |
| CM-T10 | Demonstrated except T13 (retained) | T01, T03, T05, T13 | via A3 | pending | |
| CM-T11 | Demonstrated, bounded by R4 | T18 | via A3 | pending | |

## A5 — The central claim and the contributions (§8.2, §8.3)

| ID | Claim | Type | Evidence | Test | Status | Flag |
|---|---|---|---|---|---|---|
| A5.A | Confinement is effective, against the falsifier fixed in §7.7 | M/A | §8.2.1, A3 | via A3, X1–X17 | pending | |
| A5.B | Confinement is compatible | M | §8.2.2, A1.10–A1.16 | via A1 | pending | |
| A5.C | Confinement is affordable | M | §8.2.3, A1.18–A1.20 | via A1 | pending | |
| A5.D | The fourth falsifier, about the evaluation, fired | A | §8.2.4 | DC | pending | |
| A5.1 | Contribution 1: API surface of 1,458 core and 144 community integrations, parsed with `ast`, zero parse failures, figures lower bounds | M | §8.3, `notes/ch5_evidence_api_surface.md`, §7.33 | RM, RD | pending | |
| A5.2 | Contribution 2: a confinement architecture for an unchangeable extension model, delivered and evaluated; suites pass on the target; C2 holds; C1 counted (75 comparisons, zero changes) | M | §8.3, §7.29 | R (L1), RM (C1) | pending | **F06: the suite tally in this paragraph stops at twenty-four** |
| A5.3 | Contribution 3: a quantified trade-off; compatibility half 77 integrations, cost 0, against prior work's three; security half per-threat over two registers, five paired | M/C | §8.3 | via A1, A3; CI for the prior-work comparison | pending | |

## Flags found while building the register

These are findings before any test has run. They also go into the findings log in
`notes/verification_plan_20261005.md` §11.

| ID | Where | What | Severity |
|---|---|---|---|
| F01 | Abstract | "Ten integrations … all ten" is stale: thirteen have run end to end since §7.40–§7.42 (`midea_ac_lan`, `localtuya`, `trakt_tv`) | Minor |
| F02 | Abstract | "Within a millisecond" is true of the median (0.71 ms) and not of the worst case measured (1.57 ms) | Minor, wording |
| F03 | §7.5 F3 | Claims every decision names a clause and that a clause-less decision is unconstructible; the mediator builds refusals with `clause=None` (`deny_everything`; `command` with no sandbox, a non-owner, a full queue). **Checked 2026-10-05 against every committed record: 0 of 467 durable decisions lack a clause**, so no run on file exercised those paths durably. To test: exercise each path with a durable log and read the records; then judge whether F3's wording holds, needs narrowing to the manifest decision path, or the code needs a rule name in `clause` | Potentially Major, open |
| F04 | §7.26.4 CM-T7 | T19 maps to CM-T7, so the "partial" row predates it | Minor |
| F06 | §8.3, contribution 2 | The running tally of suites stops at twenty-four; the count is twenty-six | Minor |
| F05 | Experiments | The adversary pair (§7.13) and mediation latency (§7.19) were last run before the mediator's October changes | Re-measure (plan Phase 3) |
