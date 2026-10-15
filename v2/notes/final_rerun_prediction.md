# The final rerun at the final tag — what runs, in what order, and what each step must show

**Written 2026-10-15, before any step below has run.** Lines here are not edited after the first result
is committed; outcomes are appended with dates, as in every other prediction note.

## 0. Why, and the rules

§8.6 of the submission promises "one full rerun of every measurement, mutant, suite and fault … at the
final tag", and the decision of 2026-10-10 fixed it as one rerun after the last fix, predictions first.
The code changed after the cut-off (`verify-2026-10-tests`) through the fixes in the ledger
(`notes/rewrite_plan_outline_mapping.md`: F54, F56, F57–F57d, F58, F59, F60, the T06 pair harness) and
one verification script (`verify/prereg.py`, 2026-10-15). Each fix had only a targeted regression. This
rerun is what lets every figure in the submission cite one code state.

**The final tag.** `final-2026-10`, cut on the commit that follows this note. No framework or harness
file changes after the tag; a defect found by the rerun is reported as a finding and fixed, if at all,
under its own tag, with the affected steps rerun and both runs kept.

**Rules for every step.**
1. Run from a fresh clone of the tag on the Pi (`~/r2exp/final`), not from a working tree. The
   laptop runs only what is stated as laptop.
2. Disk-backed figures use `~/r2exp/disktmp` (ext4), never `/tmp` (tmpfs).
3. (A) is restarted from the clone before any step that uses it, and **stopped for every unconfined
   end-to-end arm** (F56: both bind port 8123).
4. Processes are stopped by recorded PID, never by pattern.
5. A step that fails for an infrastructure reason (the Pi reboots, the network drops, a live service is
   down) is logged as such and run again whole; the failed attempt is kept, labelled. A step is never run
   again to get a better number.
6. A figure outside its criterion is a finding (F61 onwards), reported in the submission, not averaged
   away.
7. Results go to `experiments/verify/results/final_20261015/<step>/`, each with its provenance record
   (`<result>.run.json`: command, commit, clean tree, interpreter, host, resolve moment).

## 1. The steps, in order

| # | Step | Harness | Submission location it checks |
|---|---|---|---|
| 1 | Preflight, then every suite, twice | `confine.preflight`; `experiments/selftests/suites_all.sh` | §12.1, Table 12.6, D3 |
| 2 | All 53 mutants | `verify/mutants/run_mutants.sh`, `run_bridge_mutants.sh` (M18a–c) | §8.6, Table 12.6 |
| 3 | Fault injection | `verify/faults.py` (laptop and Pi), `verify/faults_pi_fixed.sh` | §8.6 |
| 4 | Fuzzing the mediator | `verify/fuzz_mediator.py` | Table 12.6 |
| 5 | Compatibility, both corpora, both arms | `experiments/compat` (the four runs of `notes/ch7_31_compat_rerun_prediction.md`) and C1's count | Table 12.2, §3 C1 |
| 6 | The attacks, paired | `selftest_gc`, `selftest_adversary_baseline`, `selftest_reads` (in step 1's logs) | Table 12.1 |
| 7 | The end-to-end subjects | `verify/phase2_l23.sh` (stand-in, real platform, five live services, two local devices, OAuth, `drive_demo`) | Table 12.3 |
| 8 | The functional retest | `confine.endtoend_function` and `confine.endtoend_unconfined` as at `retest-2026-10-e2e`, judged by `verify/retest_e2e_verdicts.py`; unconfined arms with (A) down | Table 12.3, §12.2 |
| 9 | T06's pair | `experiments/pair_subscriptions/run.sh` | Appendix C, T06 |
| 10 | Timings and memory, five passes | `verify/phase3_timing.sh` via `verify/final_timing.sh`, then `verify/timing_stats.py` | Table 12.5 |
| 11 | Memory against declaration depth | `experiments/unstrip/results/item12_20261003/depth.sh` | §10, Table 12.5 |
| 12 | The API surface | `figures/api_surface.py` over both corpora | Table 12.4, §9.3 |
| 13 | The record | `verify/prereg.py`, `verify/consistency.py`, `verify/recompute.py` | §8.6 |

Steps 1–4 come first because a failing suite or a surviving mutant invalidates what follows. The
timings (step 10) come after the functional steps so that a defect found earlier is known before five
passes are spent; their first pass starts on a fresh boot.

## 2. Criteria and predictions

**Step 1 — suites.** *Criterion:* the preflight exits 0, and all 29 suites exit 0 in both runs.
*Prediction:* 29 of 29, twice. `selftest_supervise` and `selftest_keep` are the likeliest to need (A)
restarted between them, as at `fix-2026-10-f59`; a restart is part of the procedure, not a failure.

**Step 2 — mutants.** *Criterion:* every mutant is killed (at least one suite fails with it applied),
except M25, recorded as equivalent on Python 3.13 and 3.14. A patch that no longer applies is
regenerated with the same meaning, committed before it runs, and listed. *Prediction:* 52 killed, M25
survives as equivalent, and every patch applies, at most with offsets, since the last regression
(`fix-2026-10-f59`) ran all of them and only F60's change, which M50 targets, landed after it.

**Step 3 — faults.** *Criterion:* each fault ends as the post-fix criteria of
`notes/fault_injection_prediction.md` state (FI1 recovers, FI3 leaves a verifiable log, FI4 leaves no
orphan and one chain per file, the rest hold), and `faults.py` passes all 11 criteria on both hosts.
*Prediction:* all hold, as in the regression on `verify-2026-10-review`.

**Step 4 — fuzzing.** *Criterion:* no request escapes into an unhandled exception that stops the
mediator; every malformed request becomes a recorded refusal. *Prediction:* 0 escapes.

**Step 5 — compatibility.** *Criterion, exact:* head corpus 31 of 37 in both arms, uniform corpus 37 of
40 in both arms, the same failing members, the same error message in both arms for each, and no
integration passing unconfined and failing confined; C1 counts zero changed source files.
*Prediction:* all exact. The fixes since the cut-off touch registration, approval and service
forwarding, none of which `inspect()` reaches.

**Step 6 — the attacks.** *Criterion:* unconfined, the heap walk reaches the victim's credential and the
2021 pattern recovers 2 of 2 canaries; confined, the walk finds only the attacker's objects with the
credential live in the mediator, 0 of 2 canaries are recovered, and undeclared reads fall from 36 of 36
to 1 of 36 (20 of 20 to 0 of 20). The object count varies from run to run and is not a criterion.
*Prediction:* all hold.

**Step 7 — end-to-end subjects.** *Criterion:* each subject loads confined, publishes, and, where it has
an unconfined arm, gives the same value as unconfined within the run (live values: same issue time,
same price, or a reading taken within a minute; local devices: the same entity, traffic only from the
mediator's host); with its clause withheld, each network request is refused with the clause named.
*Prediction:* all thirteen as in Table 12.3, unless a live service is down or has changed its API,
which rule 5 treats as infrastructure. `trakt_tv` spends its stored refresh token and stores a new one;
the run must keep the data directory, or later runs log out (F59's design).

**Step 8 — functional retest.** *Criterion:* the 45 predictions of
`notes/e2e_functional_retest_prediction.md`, judged by `retest_e2e_verdicts.py`. *Prediction:* 43 of
45. The confined `scheduler` call now carries its target (F54 fixed), so that row passes where it
failed on 2026-10-09; the two rows that misread `scheduler`'s switch (`triggered`, not `off`) fail again
in both arms, because the prediction, not the framework, was wrong.

**Step 9 — T06's pair.** *Criterion and prediction:* P1–P6 of `notes/t06_true_pair_prediction.md` hold
again: unconfined 3 of 3 undeclared changes delivered, confined 0 of 3 with the declared change
delivered, the control 3 of 3, one decision on disk with a clean chain.

**Step 10 — timings and memory.** *Criterion,* as §11 states it: the median of the five passes within
±20% of Table 12.5's figure for each timing and ±5% for each memory figure; p99 recorded where the
harness records it. *Prediction:* every figure within its criterion. The memory medians will sit at the
verification passes' values rather than the development figures, 58.7 MB with no components (+3.9%
against 56.5) and 141 MB with all ten (+4.0% against 135.6), both inside 5% but close to it; if either
crosses, Table 12.5 is restated from this rerun. Mediation latency lands within 40–47 µs, and the
durable record within 3.5–3.8 ms. None of the fixes since the cut-off sits on a timed path except F54's
service-data forwarding, which runs once per command and adds well under a millisecond to the 11–16 ms
command path.

**Step 11 — declaration depth.** *Criterion:* 56.5, 92.3, 111.6 and 135.6 MB per sandbox (none, two,
four, ten components), each ±5%, and monotonic. *Prediction:* monotonic, each within 5%, and the same
spread as on 2026-10-03 (0.1 MB across three rounds).

**Step 12 — API surface.** *Criterion, exact:* Table 12.4's twelve rows for both samples. The analysis
is static over pinned corpora, so any change is a defect in the script or the corpus, not variation.
*Prediction:* identical to `figures/api_surface_hacs.json` (head) and `figures/api_surface_uniform.json`.

**Step 13 — the record.** *Criterion:* `prereg.py` reports 0 notes to look at, this note included once
its results are committed; `consistency.py` passes; `recompute.py` reports every headline EQUAL or
explains each difference. *Prediction:* prereg and consistency pass. `recompute.py` reads the working
report (`report/`), not the submission, so it checks the figures against the record they came from;
the submission's copies are checked against this rerun in week 6's read-through.

## 3. What would change the submission

Any criterion missed is a finding, with its own line in Appendix F and a correction wherever the
submission states the figure. Three outcomes would matter beyond a correction: a suite failing or a
mutant surviving at the tag (§8.6's claim that every check is guarded), a compatibility member changing
(Assertion B), and a memory figure leaving its band (the 17-sandbox floor in §1, §10 and §15).

## 4. Known gaps, fixed before the tag rather than by the rerun

- `REPRODUCE.md` §10 says 27 suites; there are 29.
- `REPRODUCE.md` §9's instruction to stop (A) before unconfined runs stays; step 8 relies on it.
- F18 stays open: the guide followed on a freshly imaged card needs a spare card.
