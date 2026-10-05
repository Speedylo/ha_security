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
| A1.18 | Mediation costs 31.5 µs on the Pi 5 | M | §7.19 | **09-02** | RM ×3 | pending | stale code |
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
| N1 | Latency, memory, concurrency reported against a baseline | Met as specified | §7.19–§7.20 | **09-02** / 10-03 | RM ×3 | pending | |
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

## B — Chapter 7, one row per measurement

Each row names the result files the claim rests on, the commit and date they ran on, and the pass
criterion for the re-run. **The criteria are fixed here, on 2026-10-05, before any re-run**, and are
not re-read to fit a result. Paths are under `experiments/` unless they start with `framework/` or
`figures/`.

### Criterion kinds, declared before running

- **E — exact.** Counts, sets of integrations, verdicts and decision tuples `(op, target, allowed,
  clause)` must match exactly. Any difference is a finding.
- **T — timing.** Three runs on different boots, with logs on disk. The new median must be within
  **±20% of the reported median, or inside the run-to-run spread already recorded, whichever is
  wider**. p99 is reported and not judged. Outside that range, the report gets a dated correction;
  the figure is not averaged away.
- **M — memory.** Within **±5%** of the reported value, and the depth series monotonic.
- **L — live value.** A value fetched from a live API is compared with an unconfined fetch made in
  the same run, within the movement §7.31 already allows (one minute's change of the quantity).
- **V — verdict.** Each subject's outcome (loads, publishes, refused, reaches) is unchanged.

| § | Claim (headline) | Result files | Ran on | Kind | Criterion for the re-run |
|---|---|---|---|---|---|
| 7.12 | Head corpus, both arms: 31/37 (84%) clean confined, cost 0 on the corrected instance | `compat/results/compat_baseline.json`, `compat_declared_core.json`, `rerun_20261003/` | 54e97e4, 10-03 | E | the same 31; the same 6 failing, for the same reasons, in both arms |
| 7.13 | 2021 file theft: 2/2 canaries unconfined, 0/2 confined; another process's environ LEAKED/EMPTY; adversary split 21/6/10/1 over 38 | `adversary_baseline/results/pi5_unconfined.txt`, `pi5_confined.txt` | d6e5e7a, **09-02** | E, V | 2/2 → 0/2; LEAKED → EMPTY; every attack's outcome unchanged in both arms |
| 7.14 | Entity visibility: 36/36 → 1/36; presence 20/20 → 0/20 | `entity_visibility/results/pi5_s3.json`, `rerun_20261003/` | 7b8f4d2, 10-03 | E | exactly those four counts |
| 7.15 | GC attack: token reached 7 ways unconfined, 0 confined in 8,942 objects; 7 live references in the mediator | `gc_attack/results/pi5_s1.json`, `rerun_20261003/` | 7b8f4d2, 10-03 | E, V | 7 → 0; the token live in the mediator; the object count reported, not judged |
| 7.16 | C3, F3, F4, S5, S6, S7 by suite | suite logs: `selftest_c3`, `_policy`, `_audit`, `_describe`, `_channel` (`flood/results/pi_20261005/suites/`) | 10-05 | E | each suite's internal count equal to its last log; F03 judged separately |
| 7.17 | End to end on the stand-in: 5 subjects; the denominator is 11 of 37 | `end_to_end/results/pi5_e2e.json`, `rerun_20261003/` | e4d63e2, 10-03 | V, E | `scheduler`, `adaptive_lighting`, `thermal_comfort`, `powercalc`, `watchman`: same load and publish verdicts, same decisions |
| 7.18 | 15 integrations (41%) need egress; none at import; demand ≈ 4/s | `egress_demand/results/pi5_import_phase.json`, `pi5_endtoend_phase.json` | 87f9a65, **09-02** | E, RD | 15 and 0 exactly; the 63× headroom recomputed from 7.18 and 7.20 |
| 7.19 | Mediation latency: 31.5 µs median with one client; p99 +85% at 26 | `mediation_latency/results/pi5.json`, `pi5_scale.json` | 00dccc8, **09-02** | T | median within T of 31.5 µs on the tag (the mediator has changed since) |
| 7.20 | Durable record 3,670.7 µs (3.67 ms) with `fsync`, on real storage; PSS curve | `durability/results/pi5.json`, `t4_20261003/`; `r2_footprint/results/pi5_scale.json` | 9775592 / 04a31db, 09-02 / 10-03 | T, M | 3.67 ms within T, scratch confirmed not tmpfs; memory within M |
| 7.22 | S9 bounds: OOM, forks capped, CPU 25.1% at a 25% cap, `ENOSPC` at the disk cap; 13 of 13 | `framework/confine/selftest_resources.py` log | 10-05 suites | E, T | all four trip; CPU within ±2 points of the cap |
| 7.23 | Uniform corpus (seed 20260902): 37/40 (92%) clean in both arms | `compat/results/uniform_baseline.json`, `uniform_con*`, `figures/hacs_corpus_manifest_uniform.json` | 54e97e4, 10-03 | E | the same 37; the same 3 failing, same reasons |
| 7.24 / 7.31.11 | Egress shape: aiodns share 17% on a /16 (not 96%); 4 of 6 integrations' API names via aiodns | `egress_shape/results/rerun_20261003/` | 1f63011, 10-03 | E, L | the 4 of 6 exactly; the share within ±5 points, on a /16 |
| 7.25 | Two sandboxes, each denied the other's host; audit `[True, False]` | `selftest_egress_sandboxed` log | 10-05 suites | E | the same decision pair |
| 7.27 | `nordpool` against its real API: loads, publishes, value equals the unconfined one; 3 granted, 3 denied | `end_to_end/results/pi5_nordpool_egress.json`; `flood/results/pi_20261005/egress_nordpool.json` | 10-05 | V, E, L | 16/16 checks |
| 7.29 | C1: 75 tree comparisons, zero source changes, zero diff lines | `compat/results/c1_baseline.json`, `c1_declared_core.json` | 10-03 | E | zero and zero, every tree |
| 7.30 | T12: a v1-permitted request denied under v2; v2's host granted; `describe` before run | `selftest_t12` log | 10-05 suites | E | 29+ checks, unchanged count |
| 7.31 | Three more real integrations (`smhi_brandrisk`, `regensburg_transport`, `dwd_weather`); end-to-end cost none; 17/37 and 26/37 unchanged; footprint 56.5 MB | `end_to_end/results/rerun_20261003/`, `pi5_*_egress.json`, `unstrip/results/rerun_20261003/` | e4d63e2 / 7b8f4d2, 10-03 | V, E, L, M | each subject's checks; the sets of 17 and 26 identical; memory within M |
| 7.32 | Durable log in every harness; records reconcile, chains verify | `durability/results/t4_20261003/` | 04a31db, 10-03 | E | `reconcile` empty and chains intact in every harness's summary |
| 7.33 | API surface, uniform corpus: 37.5% and 17.5%; no granularity decision moves | `figures/api_surface_uniform.json` | 10-03 | E | identical counts |
| 7.34 | `pirateweather` with a valid key; key absent from every record | `end_to_end/results/t3_20261003/` | 5773839, 10-03 | V, L, E | loads and fetches; a scan of every output finds the key 0 times |
| 7.35 | Audit directory fsync; footprint series monotonic and exact | `r2_footprint/results/item12_20261003/`, `unstrip/results/item12_20261003/` | e9ec2b1, 10-03 | M, E | monotonic; within M |
| 7.36 | Push loop: 0 of 3 undeclared changes delivered (4 of 4 unconfined); 10.9 µs per delivery; record before act | `push_loop/results/w1_step1_20261004/`, `prefix_20261004/` | 4222ab0, 10-04 | E, T | 0 of 3 exactly, with the mutation; 10.9 µs within T |
| 7.37 | Against (A): 15 of 15 registry rows, survive a restart; push 0.71 ms median, 1.57 ms worst | `real_platform/results/w1_step2_20261004/`, `w1_final_20261004/` | 0187f5e, 10-04 | E, T | 15 of 15 before and after a restart; median within T |
| 7.38 | A user's command reaches the integration in 16 ms; no sandbox fails in 2 ms | `real_platform/results/w1_step2b_20261004/` | 0187f5e, 10-04 | T, V | within T; the refusal cases unchanged |
| 7.39 | Bytecode: `powercalc`'s deps 0/84 and component 0/80 from cache; with compiled bytecode its time to report 2.47 → 1.87 s | `bytecode_cache/results/w2c_20261004/` | 4bb3f12, 10-04 | E, T | the from-cache counts exactly; times within T |
| 7.40 | `midea_ac_lan` via local TCP: loads confined; device sees only the host; nothing undeclared reaches it | `local_tcp/results/w2a_20261004/` | 3a05e8f, 10-04 | V, E | three arms' verdicts and the device's log |
| 7.41 | `localtuya` asyncio discovery confined equals unconfined; 2 decisions | `local_tcp/results/w2b_20261004/` | cd26992, 10-04 | V, E | the same devices discovered; 2 listens |
| 7.42 | `trakt_tv` refresh inside the sandbox; spent token refused 400; control refused | `oauth/results/w2d_20261004/` | 9040671, 10-04 | V | runs 1, 3 and C as before (run 2 consumes no fresh token) |
| 7.43 | The retest's table | `retest/results/review_20261004/` | 9e49522, 10-04 | — | superseded by this campaign's own regression |
| 7.44 | Flood: 100 refusals, one cutoff, 0.81 s on disk; neighbour 235 answers, worst 26.1 ms; Repairs within 302 ms | `flood/results/pi_20261005/` | 2056e92, 10-05 | E, T | 100 and one exactly; under 1 s; the Repairs path end to end |

**Reading-only sections** (§7.21, §7.26, §7.28) make claims about the report itself. They are checked
by the document-consistency phase (plan §7.9), not by a re-run.

**Base evidence outside Chapter 7** that these rows depend on, and that also re-runs: the
`selftests/results/final_20261003/` suite logs (superseded by each campaign run), and
`host_isolation_probe`, `cgroup_placement` and `base_component` from August, which Chapter 5 and 6's
design claims rest on (Tier C).

## C — every remaining candidate, triaged

`verify/triage_claims.py` gives each of the 1,980 candidates a disposition, recorded in
`verify/triage.jsonl`; **none is left unplaced**. The rules run in order: front-matter structure;
dated history; a Chapter 7 candidate goes to the Tier B row for its own section; a candidate citing
a §7 section goes to that row; then every remaining subsection goes to the Tier A row or Tier C
group that tests it. Twenty-four claims, read one by one in the security-critical subsections, get
rows of their own (CS01–CS16).

| Disposition | Candidates | Meaning |
|---|---|---|
| Tier B row (`B 7.n`, `ref 7.n`) | 942 | tested by that measurement's re-run and the re-derivation of its numbers |
| Tier A row | 74 | tested through A1, A2 or A5 |
| Tier C group C01–C16 | 614 | tested by the group's suites, mutants and base experiments, below |
| Tier C single row CS01–CS16 | 24 | tested one by one, below |
| history | 191 | a dated past state kept on purpose; checked only that it is dated |
| argued | 53 | design rationale; checked only that it reads as argument (plan §7.9) |
| structure | 82 | the report describing itself (contents, glossary); checked by `toc.py` |
| **Total** | **1,980** | recounted from `triage.jsonl`, not added by hand |

### C01–C16 — mechanism groups (Chapters 5, 6 and 8)

| Group | What its claims say | Candidates | Test | Criterion |
|---|---|---|---|---|
| C01 | How the integration runs (R2) and the API surface it uses (§5.6) | 34 | `base_component` re-run; B 7.33; RD | figures as stated, or dated |
| C02 | Isolation: namespaces, cgroups, placement, preflight, the sandbox's build (§5.7, §6.3, §6.4) | 74 | `host_isolation_probe`, `cgroup_placement` re-run; L1; X13–X15; FI | every isolation property demonstrated on the tag |
| C03 | The manifest, its schema, parse-time rejection, `describe` (§5.9, §5.10, §6.6, §6.7) | 90 | `selftest_policy`, `_c3`, `_describe`; X1, X3, X17 | suites green; mutants killed |
| C04 | Mediator and channel: identity from the socket, verbs, framing, latency (§5.11, §6.5) | 33 | `selftest_channel`, `_fdpass`, `_socket_pinning`; X2, X16; B 7.19 | as stated |
| C05 | Identity and the audit record (§5.12, §6.8) | 27 | `selftest_audit`, `_integrity`; X7, X8; FI (disk full) | as stated |
| C06 | Defence in depth and the adversarial cases (§5.13, §6.9) | 49 | `selftest_adversary` paired; independent attacks | every layer's claim holds or is argued |
| C07 | The design drawn and the controls checked (§5.14) | 37 | figures regenerated from the model; DC | figure equals model; mapping consistent |
| C08 | What the design does not do (§5.15) | 30 | DC against current state | still true, or dated |
| C09 | The bridge (§6.10) | 20 | `selftest_bridge`, `selftest_real_platform` | as stated |
| C10 | Un-stripping and its cost (§6.12) | 37 | `unstrip` re-run (B 7.31, 7.35) | M |
| C11 | The declared profile and the core package set (§6.13, §6.14) | 77 | `compat` declared-core arm re-run (B 7.12) | E |
| C12 | Chapter 7's method: axes, criteria, schedule, validity, obligations (§7.1–§7.11, except §7.5–§7.7) | 48 | DC; obligations register reconciled | every obligation discharged or stated open |
| C13 | Status claims: "not built" (§6.11), limitations (§8.6), future work (§8.7) | 46 | DC against today's code | each still true, or dated |
| C14 | §8.5: the baseline loads a median of 52 components where a sandbox sets up 2 (head) and 0 (uniform) | 4 | RD from the compat results | the medians exactly |
| C15 | §8.8: R3, no scoped credential exists; the mediator's token reachable seven ways | 4 | CI against HA 2026.8.3's auth source; B 7.15 | still true of the pinned release |
| C16 | "The artifact": what the repository contains and how to run it | 4 | clean-checkout reproduction (plan §7.2) | every step works as written |

### CS01–CS16 — single claims

| ID | Claim | Where | Test | Flag |
|---|---|---|---|---|
| CS01 | Nothing but the socket crosses the boundary: no route, a private IPC namespace, no path to any other socket | §5.11 | independent attacks; X13, X15 | |
| CS02 | Every response carries the clause that decided it; the pointer is built by the deciding branch, so a clause-less decision is unconstructible | §5.11, §5.12, §6.6 | exercise each refusal path with a durable log | **F03** |
| CS03 | ~33,000 requests per second; 0.30 ms of mediation per polling cycle (Ch5), 0.36 ms (Ch6) | §5.11, §6.5 | RD from today's latency | **F09: three versions of one figure (0.30, 0.36, and ~0.32 ms from 31.5 µs)** |
| CS04 | With the mediator gone, the sandbox reaches nothing | §5.11 | FI | |
| CS05 | Each run record carries the full identity, provenance and **resolved dependency versions** | §5.12 | read the run records; code read | **F08** |
| CS06 | Modifying, deleting or reordering any record breaks every link after it | §5.12 | `selftest_audit` (strong form); X8 | |
| CS07 | The log is unreachable from the sandbox: outside its mount namespace, and no verb writes to it | §5.12 | independent attacks | |
| CS08 | The MAC key is generated at start and held only in the mediator's memory | §5.12, §6.8 | code read; scan disk and logs for the key | |
| CS09 | An integration cannot learn where on the host it was installed | §6.4 | independent attack: read `/proc/self/mountinfo` from inside | **F11: Withdrawn — mountinfo and the host-path binds reveal the layout and user name; corrected in §6.4, Ch. 4, §8.6.3 #18** |
| CS10 | Every declared path is verified in the new root before the sandbox runs; construction fails loudly | §6.4 | mutant (skip the check); `selftest_bridge` | |
| CS11 | Seccomp is a deny-list; a syscall not on it is allowed (a stated residual) | §6.4 | compare the list with the text; X13 | |
| CS12 | Over-broad and unsafe declarations are rejected at parse time, not at use | §6.6 | `selftest_policy`; X17 | |
| CS13 | Someone who can write the log cannot forge the HMAC chain; a stored hash is never an input to verification | §6.8 | `selftest_audit`; mutant (verify from the stored hash) | |
| CS14 | The sandbox's bridge is not an enforcement point; every forwarded request is checked again by the mediator | §6.10 | independent attack: raw requests on the socket, bypassing the bridge | |
| CS15 | Cross-integration services (`homeassistant.turn_on`) are routed through the mediator | §6.3 | test with an undeclared target | |
| CS16 | The instance is started last, so `RestoreEntity` restores; measured in both arms | §6.3 | R (the round trip) | |

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
| F07 | Experiment READMEs | Nine results sections (§7.16, 7.19, 7.22, 7.25, 7.29, 7.30, 7.32, 7.38, 7.41) are named by no experiment README, so a reader cannot follow those figures from the claim to the data. `durability/` has no README at all | Minor (traceability) |
| F08 | §5.12, `audit.py`, §8.6.3 #3 | The run record should carry **resolved** dependency versions; the identity hashes the **declared** requirements, with a comment saying installation "is not built yet", although per-run installation has existed since September, and §8.6.3 #3 still calls it unresolved. Three statements to reconcile, and possibly a small fix | Minor to Major, open |
| F09 | §5.11, §6.5 | Mediation per polling cycle stated as 0.30 ms (Ch5) and 0.36 ms (Ch6); today's 31.5 µs gives about 0.32 ms for ten reads | Minor |
| F10 | `selftest` | The home-absent check holds only when the configuration root is outside home; realistic placement makes home a skeleton | Minor (test design) |
| F11 | §6.4, CS09 | `/proc/self/mountinfo` reveals the host paths of the component and data directories | Major claim, low impact |
| F05 | Experiments | The adversary pair (§7.13) and mediation latency (§7.19) were last run before the mediator's October changes | Re-measure (plan Phase 3) |
