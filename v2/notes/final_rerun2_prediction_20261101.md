# The second final rerun, at the frozen code — what runs, in what order, and what each step must show

**Written 2026-11-01, before any step below has run.** Lines here are not edited after the first
result is committed; outcomes are appended with dates, as in every other prediction note. Younes,
2026-11-01: "yes to D1, D2 and D3, go ahead. If possible, break down the runs into chunks instead of
one big 12 hours run that has to happen continuously" (§6).

## 0. Why, and the rules

The interim's figures come from three code states: most from `final-2026-10` (2026-10-16), the
compatibility counts from the re-measurement with the egress shim (2026-10-25, F65), and the bridge
figures from B5 (2026-10-31). The code changed after each: F64–F71, the bridge from 3 to 29 kinds,
questions and picture answers through the mediator, the sandbox runtime and the shim. Younes froze
the engineering on 2026-11-01 at `e890519` (code: `bridge-b4b`, `f1f4053`). This rerun repeats the
16 October method (`notes/final_rerun_prediction.md`) on the frozen code, so that **every figure in
the final report cites one code state**.

**What changed under each interim figure** (from `git diff final-2026-10..bridge-b4b -- framework`):

| Figure | Code under it since it was measured | Expected |
|---|---|---|
| Attacks (heap walk, canaries, undeclared reads) | Isolation code (`namespaces`, `seccomp`, `cgroup`, `enter`) unchanged; egress shim changed (F65) | holds |
| Compatibility 31/37, 37/40 | Re-measured with the shim on 10-25; the sandbox runtime changed after (bridge questions, run time only) | holds, exact |
| The fifteen end to end | Last run at B5; B4b changed the mediator's command routing after | holds |
| Mediation latency, durable record, push | Request path, audit write and push path unchanged; the record of a command grew | within band |
| A user's command reaching the integration | Changed: per-kind data checks in the mediator; the bridge in (A) rewritten (F70's switch) | within band, re-measured |
| Memory per sandbox | Sandbox runtime and egress shim changed | within band, close to its edge |
| Platform parts used (Table 7.4) | Static over the pinned corpora | identical |
| Bridge coverage | Superseded (29 kinds) | as the B4b recount |

**The tag.** `final-2026-11`, cut on the commit that follows this note (and D1's mutants, if
accepted). Its framework and harness files are those of `bridge-b4b`. A defect found by the rerun is
a finding (F72 onwards), fixed, if at all, under its own tag, with the affected steps rerun and both
runs kept.

**Rules for every step**, as on 16 October:
1. Run from a fresh clone of the tag on the Pi (`~/r2exp/final2`), not from a working tree.
2. Disk-backed figures use `~/r2exp/disktmp` (ext4), never `/tmp` (tmpfs).
3. (A) is restarted fresh from the clone before any step that uses it, and **stopped for every
   unconfined end-to-end arm** (F56: both bind port 8123).
4. Processes are stopped by recorded PID, never by pattern.
5. A step that fails for an infrastructure reason (reboot, network, a live service down) is logged as
   such and run again whole; the failed attempt is kept. A step is never run again for a better number.
6. A figure outside its criterion is a finding, reported in the final report, not averaged away.
7. Results to `experiments/verify/results/final2_2026110x/<step>/` (the date of the run), each with its
   provenance record. Three scripts name stale locations (F61's clause: `verify/phase2_l23.sh`,
   `verify/final_timing.sh`, `experiments/unstrip/results/item12_20261003/depth.sh`); the drivers call
   them against the clone, as on 16 October, and the scripts are not edited.

## 1. The steps, in order

| # | Step | Harness | Report location it checks |
|---|---|---|---|
| 1 | Preflight, then every suite, twice | `confine.preflight`; `experiments/selftests/suites_all.sh` | suites, D3 |
| 2a | Mutants M01–M50 (53) | `verify/mutants/run_mutants.sh` restricted to M01–M50 (it globs `M*`, which now also matches M51–M79); `run_bridge_mutants.sh` (M18a–c) | the tests bite |
| 2b | Mutants M51–M79, M51b (30) | `verify/mutants/run_kind_mutants.sh` (control, then each in its own copy, (A) fresh from the mutated tree) | the bridge's tests bite |
| 2c | D1's mutants for B5 and B4b, if accepted | `run_kind_mutants.sh` | the same |
| 3 | Fault injection | `verify/faults.py` (laptop and Pi), `verify/faults_pi_fixed.sh` | faults |
| 4 | Fuzzing the mediator | `verify/fuzz_mediator.py` | fuzzing |
| 5 | Compatibility, both corpora, both arms, and C1 | `experiments/compat` (four runs) | Table 7.2 |
| 6 | The attacks, paired | `selftest_gc`, `selftest_adversary_baseline`, `selftest_reads` (step 1's logs) | Table 7.1 |
| 7 | The end-to-end subjects, stand-in and unconfined arms | `verify/phase2_l23.sh` | Table 7.3 |
| 8 | The functional retest | `endtoend_function`, `endtoend_unconfined`, `retest_e2e_verdicts.py`; (A) down for unconfined arms | Table 7.3 |
| 8b | **New:** the fifteen against the real (A), as B5 | `selftest_real_house`; `endtoend_function`, `endtoend_egress` (six), `endtoend_local` (two), `endtoend_oauth` with `--platform real`; `bridge_step5_verdicts.py`, `retest_e2e_verdicts.py`, `e2e_ext_verdicts.py` | the bridge in a real installation |
| 9 | T06's pair | `experiments/pair_subscriptions/run.sh` | T06 |
| 10 | Timings and memory, five passes, first on a fresh boot | `phase3_timing.sh` (via the driver), `timing_stats.py` | Table 7.5 |
| 11 | Memory against declaration depth | `item12_20261003/depth.sh` (via the driver) | memory |
| 12 | The API surface | `figures/api_surface.py`, both corpora | Table 7.4 |
| 13 | The record | `verify/prereg.py`, `verify/consistency.py`, `verify/recompute.py` | the record |
| 14 | **New:** bridge coverage | `verify/bridge_coverage_recount.py` over the head corpus | coverage |

Steps 1–4 first, because a failing suite or a surviving mutant invalidates what follows; 8b after 8,
because both use (A)'s port; the timings after the functional steps, starting on a fresh boot (Younes
reboots the Pi before step 10). Estimated Pi time: 13–15 h (16 October's 10–12 h, plus 2b ≈ 1 h and
8b ≈ 1.5 h).

## 2. Criteria and predictions

**Step 1 — suites.** *Criterion:* the preflight exits 0, and all 35 suites exit 0 in both runs.
*Prediction:* 35 of 35, twice (as at `bridge-b4b`, 2026-11-01). The second run uses an (A) the first
has filled; `selftest_display` searches the entity list by name since `bridge-b5b`, so it no longer
depends on a fresh (A).

**Step 2a — M01–M50.** *Criterion:* every mutant killed (at least one suite fails with it applied),
except M25, recorded as equivalent. *Prediction:* 52 killed, M25 survives; every patch applies without
offset (checked 2026-11-01 with `patch --dry-run -p1`: all 83 apply cleanly).

**Step 2b — M51–M79, M51b.** *Criterion:* control passes (`selftest_commands` 268/268,
`selftest_queries` 49/49, `selftest_bridge_types` 194/194; the runner gained the queries suite on
2026-11-01, for D1's picture mutants); each mutant killed, or survives as equivalent with the reason.
*Prediction:* 29 killed, **M65 survives as equivalent**: M65 removes `entity_picture` from the media
player's own list of attributes it takes, but since F71 (`bridge-b5`) `entity.py`'s `NOT_PASSED` drops
it for every kind, so the mutant changes nothing. A mutant made equivalent by a later fix, not a test
that stopped biting; T28 and T32 still check the behaviour.

**Step 2c — D1's mutants M80–M88** (accepted; the table in D1, patches written by
`mutants_kinds.py M80 … M88`, each applying cleanly). *Prediction:* each killed by the check named;
M87 also by Q5 (it records list answers in full too).

**Step 3 — faults.** *Criterion:* each fault ends as the post-fix criteria state, and `faults.py`
passes 11 of 11 on both hosts. *Prediction:* 11/11 on both, as at `fix-2026-10-f61`.

**Step 4 — fuzzing.** *Criterion:* no escape; every malformed request a recorded refusal.
*Prediction:* 0 escapes, 4,864 requests (the cases are the product of `manifest.OPERATIONS`, the
fields and the odd values, none of which changed).

**Step 5 — compatibility.** *Criterion, exact:* head 31 of 37 and uniform 37 of 40 in both arms, the same
failing members, the same error message in both arms for each, none passing unconfined and failing
confined; C1 zero. *Prediction:* all exact, as on 2026-10-16 and 2026-10-25 (with the shim).

**Step 6 — the attacks.** *Criterion:* unconfined, the heap walk reaches the victim's credential and the
2021 pattern recovers 2 of 2 canaries; confined, the walk finds only the attacker's objects with the
credential live in the mediator, 0 of 2 canaries, undeclared reads 36/36 → 1/36 (20/20 → 0/20). The
object count is not a criterion. *Prediction:* all hold.

**Step 7 — end-to-end subjects (stand-in, unconfined arms).** *Criterion:* as on 16 October (Table 12.3
of the working report). *Prediction:* every subject as it states, `dwd_weather` 15/16 and
`pirateweather` 16/17 as then, unless a live service is down or changed (rule 5). `phase2_l23.sh` has
not run since 16 October; the `endtoend_*` modules gained `--platform real` with the stand-in as
default, so the stand-in arm should be unaffected. `trakt_tv` must keep its data directory.

**Step 8 — functional retest.** *Criterion:* the 45 predictions, judged by `retest_e2e_verdicts.py`.
*Prediction:* 43 of 45, the same two `scheduler` rows.

**Steps 7–8, the two integrations added on 2026-10-25** (added before the first chunk ran):
16 October's steps predate `alarmo` and `waste_collection_schedule` (`e2e-ext-2026-10`). Chunk F
also runs `endtoend_egress --subject waste_collection_schedule` (both arms, (A) down) and judges
`alarmo` from step 8's `endtoend_function` run, both with `verify/e2e_ext_verdicts.py`.
*Criterion:* alarmo P1–P4 in both arms; waste's two arms read the same next collection date.
*Prediction:* alarmo 8 of 8; waste's two arms agree; the script's P7 rows fail, as in B5, because P7
names the date predicted on 2026-10-25 (27.10.2026), which has passed: a stale expectation, not a finding.

**Step 8b — the fifteen against the real (A).** *Criterion and prediction,* as B5's outcome:
`selftest_real_house` passes; every publish of every confined-declared arm accepted;
`bridge_step5_verdicts` **36 of 36** with 65 entity rows each in (A) as published; `retest_e2e_verdicts`
43 of 45 (the same two rows); alarmo 8 of 8; the egress, local and OAuth subjects as in B5. B4b added
no kind any of the fifteen publishes (dwd_weather's camera exists only for a map entry), so nothing
should change.

**Step 9 — T06's pair.** *Prediction:* P1–P6 hold.

**Step 10 — timings and memory.** *Criterion,* as on 16 October: the median of five passes within ±20%
of Table 12.5's figure for each timing and ±5% for each memory figure. *Predictions:*
- Mediation latency, one sandbox, 40–47 µs; 26 sandboxes, 794–816 µs; durable record 3.6–3.8 ms; push
  cost 11.3–11.7 µs; flood to cut-off 0.80–0.82 s; `powercalc` start-up 1.87–1.94 s. None of these
  paths changed.
- A change in (A) reaching the sandbox: about 0.50 ms, as at the last rerun (F62), inside 0.5–0.9 ms.
- **A user's command reaching the integration: within 11–16 ms.** It is the timed path that changed
  most (per-kind data checks, microseconds; the bridge's switch, F70), so it is re-measured, not argued.
- **Memory: 58.6–59.0 MB with no components, 94.7–95.0 MB with two, 141 MB with ten**, each inside 5% of
  56.5 / 92.3 / 135.6 but close to its edge (+4%), as in the ten passes before. The sandbox runtime
  gained a few small tables, one standard-library import (`base64`) and the shim's fix; none of
  that should move a figure by more than a fraction of a megabyte (not measured). If a figure crosses 5%, it is a finding and Table 7.5 is restated
  from this rerun, with the 17-sandbox floor recomputed.

**Step 11 — depth.** *Prediction:* 57.0, 92.9, 112.0, 135.6 MB ±5%, monotonic, spread ≤ 0.1 MB.

**Step 12 — API surface.** *Criterion, exact:* both parses equal `figures/api_surface_hacs.json` and
`figures/api_surface_uniform.json`. *Prediction:* identical. The head sample is no longer on the Pi (`~/r2exp/final-run/top150`
is gone); chunk D fetches the 144 `in_sample` rows of `figures/hacs_top150_manifest.json` at their
recorded commits (one per domain, so order does not matter) with `fetch_hacs_corpus.fetch_one`, as
`verify/rebuild_top150_finish.py` did. A failed fetch is infrastructure (rule 5); a fetched sample
that parses differently is a finding.

**Step 13 — the record.** *Criterion:* `prereg.py` 0 notes to look at (this note counted once its
results are committed), `consistency.py` passes, `recompute.py` EQUAL or each difference explained.
*Prediction:* consistency passes; recompute differs where the working report (`report/`) states counts
the bridge work changed (suites, findings, kinds) — each listed and explained, not fixed here: the
final report is rebuilt from this rerun.

**Step 14 — coverage.** *Criterion, exact:* 29 kinds bridged; 36 of 37 by platform, 247 of 248 kind
uses; only `alexa_media`'s legacy notify left. *Prediction:* as `b4b/recount.txt`.

## 3. What would change the final report

Any criterion missed is a finding with its own line and a correction wherever the report states the
figure. Four outcomes matter beyond a correction: a suite failing or a mutant surviving that is not
equivalent (the claim that every check is guarded); a compatibility member changing (Assertion B); a
memory figure leaving its band (the 17-sandbox floor); one of the fifteen failing against the real (A)
(the bridge claim).

## 4. Decisions for Younes

- **D1. Mutants for the code added after the 31 October mutant run** (F71 and B4b), written and
  committed before the tag, run in step 2c. Nothing tests yet that each of their checks can fail on
  its own: B5 and B4b only failed first coarsely (the whole kind refused). *Recommended: yes*, nine:

  | Mutant | Behaviour broken | Predicted killer |
  |---|---|---|
  | M80 | `NOT_PASSED` empty: the sandbox's picture link shown on every kind (F71) | T32 |
  | M81 | a picture's signature not checked | Q9 (an HTML page labelled image/png), T36 |
  | M82 | the picture cap 1 MiB instead of 512 KiB | Q9 (512 KiB + 1), T36 (600 KiB) |
  | M83 | image/svg+xml a listed picture type | Q9 (image/svg+xml) |
  | M84 | the camera keeps STREAM | T33 (supported_features 1) |
  | M85 | no reuse: the camera asks every time | T35 (a fetch within 2 s asks nothing) |
  | M86 | the image ignores the published time and asks every time after 2 s | T38 (same time, asks nothing) |
  | M87 | a picture answer recorded in full | Q10 (no base64 in the log) |
  | M88 | the sandbox's `access_token` passed through on a camera | T33 (the token is not the sandbox's) |

- **D2. When.** 13–15 h of Pi time (an overestimate: §6), the Pi on throughout, and Younes reboots it before step 10. It does
  not depend on the supervisor's feedback; the final report's results chapter is written from it.
- **D3. If a memory figure crosses 5%:** restate Table 7.5 from this rerun (as decided for F62),
  rather than keep the development figure. *Recommended.*

## 5. Known gaps, not fixed by the rerun

- `REPRODUCE.md` names 29 suites; there are 35. To be corrected with the final report, not before the tag.
- F18 stays open (a guide followed on a freshly imaged card needs a spare card).
- The eight camera and image integrations themselves are not run (B4b's limit 8); step 8b covers the
  fifteen only.

## 6. The run in chunks (Younes, 2026-11-01)

The 16 October run took about five hours of Pi time once its steps are added up (mutants 2.4 h,
end to end 0.75 h, the rest minutes), not the 10–12 h estimated then or the 13–15 h in D2 above. It is
split into chunks, each a driver of its own that brings (A) up fresh from the clone, records the commit,
the tree's cleanliness and the uptime, and ends with `ALLDONE`. The Pi can be switched off between
chunks. A chunk is launched only after the previous one's results are read; a chunk that fails for an
infrastructure reason is run again whole (rule 5), its failed attempt kept.

| Chunk | Steps | Pi time (16 Oct, or estimate) | Before it |
|---|---|---|---|
| A | 1 (preflight, suites ×2); step 6 read from its logs | ≈ 15 min | — |
| B | 2a (M01–M50, M18a–c) | ≈ 2.5 h | A held |
| C | 2b, 2c (control, M51–M88) | ≈ 1.5 h | A held |
| D | 3 (Pi half), 4, 9, 12, 14; step 3's laptop half on the laptop | ≈ 15 min | A held |
| E | 5 (compatibility, four runs, (A) down) | ≈ 30 min | A held |
| F | 7, 8 (stand-in and unconfined arms, live services) | ≈ 1 h | A held |
| G | 8b (the fifteen against the real (A)) | ≈ 1.5 h | F done (both use port 8123) |
| H | 10, 11 (timings, depth) | ≈ 45 min | **a fresh boot** (Younes reboots the Pi just before) |
| I | 13 (the record), on the laptop, after the results are committed | minutes | all others |

Drivers are kept outside the clone, so the tagged tree stays clean, and copied into the results.

## 7. Outcome (chunks A–H, 2026-11-01; I to follow)

Every chunk ran from `~/r2exp/final2` at `a3ba4a1` (`final-2026-11`), tree clean before and after.
Results in `experiments/verify/results/final2_20261101/<chunk>_<step>/`, drivers in `drivers/`.

| Step | Prediction | Outcome |
|---|---|---|
| 1 | 35/35 twice | **held**: preflight 0; 35/35, 35/35 (chunk A) |
| 2a | 52 killed, M25 survives, no offset | **held**: M01–M50 49 killed (M25 failed_suites=0), M18a–c killed with the bridge loaded mutated in (A); control 0 failed; no patch failed, no offset or fuzz in any log (chunk B, 12:40–17:34) |
| 2b | control 268/49/194; 29 killed, M65 equivalent | **held**: control 268/268, 49/49, 194/194 (C and C2); M51–M79 and M51b killed except M65 (failed=0, bridge loaded mutated) |
| 2c | M80–M88 each killed by the check named; M87 also by Q5 | **held**: each killed by its named check (M81 and M82 also T36; M87 by Q5 and Q10) (C2) |
| 3 | 11/11 on both hosts | **held**: laptop 11/11 (`step03_faults_laptop`), Pi 11/11; FI1, FI4, F30 all ok |
| 4 | 0 escapes, 4,864 requests | **held** |
| 5 | 31/37 and 37/40 both arms, same members and messages; C1 zero | **held**: failing members bambu_lab, bermuda, eufy_security, hacs, spook, tapo_control / bermuda, lightwave2, next_rocket_launch, each with the same message in both arms and as on 16 October; C1 0 files, 0 lines |
| 6 | all hold | **held** (from chunk A's suites): unconfined walk reaches the credential, 2/2 canaries; confined 8,942 objects all the attacker's, credential live in the mediator, 0/2; reads 36/36 → 1/36, 20/20 → 0/20 |
| 7 | as 16 October; dwd 15/16, pirateweather 16/17, unless a live service changed | **held, one live value moved**: nordpool 16/16, dwd 15/16 (the kept `www.dwd.de` refusal), pirateweather **17/17**, waste 16/16, smhi 20/20, **regensburg_transport 15/16**; stand-in, real-platform, local and OAuth subjects identical to 16 October in every outcome field except the readings themselves; flood demo cut off and reinstated once |
| 7–8 (added) | alarmo 8/8; waste's arms agree; P7 stale | **held**: alarmo 8/8; both arms read 10.11.2026; P7 A and B fail on the 27.10.2026 named on 2026-10-25 |
| 8 | 43/45, the same two scheduler rows | **held** |
| 8b | real house passes; 36/36, 65 entities; 43/45; alarmo 8/8; egress, local, OAuth as B5 | **held, one live value moved**: real house 6/6; `bridge_step5_verdicts` 36/36, 65 entities; 43/45 (same rows); alarmo 8/8; waste P7 stale; egress as B5 except **regensburg_transport 15/16** (B5 16/16) |
| 9 | P1–P6 hold | **held**: unconfined 3/3 undeclared delivered, confined 0/3, declared delivered both arms, control 3/3, one decision, no delivery record, no chain break, both 2026.8.3 on the Pi |
| 12 | both parses identical | **held**: 144 of 144 fetched at their commits; hacs and uniform IDENTICAL |
| 10 | each timing ±20% of Table 12.5, each memory figure ±5%; ranges in §2 | **held against the criterion; two predicted memory ranges 0.1–0.2 MB low** (see below) |
| 11 | 57.0, 92.9, 112.0, 135.6 MB ±5%, monotonic, spread ≤ 0.1 | **held**: 57.2, 93.0–93.1, 112.1, 135.8 MB in all three rounds; monotonic; spread ≤ 0.1 MB; about 17 sandboxes fit at ten components |
| 14 | as `b4b/recount.txt` | **held**: identical |

**The live check F2.** F2's third line asks that at least one value the confined arm publishes equal
the unconfined arm's, fetched from the same API minutes apart. On `regensburg_transport` it failed
twice, in steps 7 and 8b, each time by one minute of the real-time departure (`… at 21:02` against
`21:03`; `22:33` against `22:32`); on 16 October and in B5 it held. `pirateweather` held it today and
failed it on 16 October (12.41 against 12.39 °C). Both are the service's value moving between arms,
which the line cannot tell apart from a wrong value; the other two F2 lines (LOADED while confined,
a fetched value published through the mediator) held for both. Recorded as on 16 October, not run
again (rule 5); in the report, a limit of that check, not of confinement.

**Run deviation (chunk C).** The Pi's card filled (chunk B's mutant work copies, 3.8 GB) while chunk C
copied M72; the runner recorded M72–M88 as "patch failed" without running them, and a non-ASCII byte
cut off M62's line in the printed summary (its own record shows it killed). The work copies were
deleted by path and M72–M88 run again as chunk C2 (`chunkC2_step02c`, same runner and code, disk
recorded before and after: 5.8 GB and 4.5 GB free). Chunk C's attempt is kept. The resources suite's
"No space left on device" lines in chunk B are its own 8 MB cap, as in chunk A.

**Step 10 in detail** (chunk H, after Younes rebooted the Pi: start 22:06, "up 1 minute"; five passes
22:06–22:29, each exit 0). Judged with `verify/timing_stats.py` over these five passes only, in a scratch
tree, as on 16 October; read against Table 12.5 / the interim's Table 7.5 and §2's ranges.

| Figure | Median (passes) | Against | Predicted | |
|---|---|---|---|---|
| mediation latency, one sandbox | 42.1 µs (40.9–43.4) | 43 µs, −2.1% | 40–47 | held |
| mediation latency, 26 sandboxes | 802 µs (797–814) | 800 | 794–816 | held |
| durable record | 3.69 ms (3.68–3.71) | 3.67, +0.4% | 3.6–3.8 | held |
| push, mediator cost | 11.4 µs (11.4–11.7) | 10.9 | 11.3–11.7 | held |
| a change in (A) reaching the sandbox | 0.49 ms (0.49, 0.49, 0.49, 0.68, 0.50) | 0.5–0.9 ms | about 0.50 | at the range's lower edge (0.5 at the table's one decimal); F62's gap to 0.71 persists |
| a user's command reaching the integration | 12.5 ms (12.0–12.9) | 11–16 ms | 11–16 | held |
| flood to cut-off | 0.816 s (0.807–1.07) | 0.81 | 0.80–0.82 | held; the first two passes after boot 1.01 and 1.07 s |
| `powercalc` start-up, compiled | 1.89 s (1.88–1.89) | 1.87, +1.1% | 1.87–1.94 | held |
| memory, no components (PSS) | 59.1 MB (all five) | 56.5, +4.6% | 58.6–59.0 | inside ±5%; predicted range 0.1 MB low |
| memory, two components | 95.2 MB (95.1–95.2) | 92.3, +3.1% | 94.7–95.0 | inside ±5%; predicted range 0.2 MB low |
| memory, ten components | 141.2 MB (141.1–141.2) | 135.6, +4.1% | 141 | held |

Not criteria, recorded: one sandbox's RSS 161 MB (−0.2% against §7.35); marginal memory per added
sandbox median 133 MB (126–139; +6.6% against §7.35's 124.4; 16 October 130, 127–134); `powercalc`
default install 2.27 s (first pass after boot 3.0 s). No memory figure crossed 5%, so D3 does not
apply and Table 7.5 keeps its figures; the 17-sandbox floor holds (step 11: about 17 fit at ten).
The timing passes write their outputs into the clone (`phase3_timing/final2_pass1–5` and
`mediation_latency/_manifest`, all untracked), hence "dirty after=6", as on 16 October; no tracked file changed.
