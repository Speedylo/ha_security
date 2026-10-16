# F61 — the fault harnesses were never given F57's approval step

**Written 2026-10-16, before the fix and before any run of it.** Lines here are not edited after the
first result is committed; outcomes are appended with dates.

## What was found

The final rerun (`notes/final_rerun_prediction.md`) ran step 3's laptop half from a fresh clone of
`final-2026-10`. `verify/faults.py` stopped in its first case (FI2/FI6) with
`confine.manifest.NotApproved` raised from `Mediator.register` → `ActingPolicy.bind` →
`require_approval` (`experiments/verify/results/final_20261016/step03_faults/faults_laptop_attempt1.*`).

F57 (`80daf82`, 2026-10-10) made every registration that names its component require an approval on
record, and gave the harnesses that register components `approve_as_experimenter`. The two fault
harnesses were not among them: `verify/faults.py` last changed on 2026-10-06 and
`verify/faults_pi_fixed.sh` before that, and neither ran in any regression after F57. The supervisor
started by `faults_pi_fixed.sh` reads its approvals from the component's configuration root by
default, where none is recorded, so FI1 and FI4 would wait for an approval that never comes.

This is a defect in the harnesses, not in the framework: the gate refused exactly what F57 says it
must refuse. It is also a gap in the verification record: from 2026-10-10 to this rerun, no fault
case ran against the code the submission describes.

## The fix (harness only)

1. `verify/faults.py`, `component()`: after writing the test component's manifest, record the
   experimenter's approval with `approve_as_experimenter(directory)`, as F57 did in `compat` and
   `endtoend`. It is written to `<root>/confine/audit/decisions.jsonl`, where `ActingPolicy.bind`
   looks by default, inside each case's temporary directory. FI3's mediator uses a plain function
   policy that never binds, so the approval changes nothing there.
2. `verify/faults_pi_fixed.sh`: before the first supervisor starts, record the approval of the grant
   the supervisor will load (a derived manifest that declares nothing, `{"schema_version": 1}`) in
   `$OUT/approvals.jsonl`, exactly as `selftest_supervise` does; start every supervisor with
   `--approvals "$OUT/approvals.jsonl"` and `--keep-dir "$OUT/kept"`, so nothing is written into the
   clone.

No file under `framework/` changes. The fix is tagged `fix-2026-10-f61`; only step 3 runs from that
tag. Steps 1, 2 and 4–13 stay on `final-2026-10`, because the two tags differ only in these two
harness files and this note.

## Criteria and predictions

- **G1, the diff.** `git diff --stat final-2026-10 fix-2026-10-f61` lists only `verify/faults.py`,
  `verify/faults_pi_fixed.sh` and this note. *Prediction:* holds.
- **G2, laptop.** `faults.py` runs to the end and passes all 11 criteria. *Prediction:* 11 of 11, as
  in the regression on `verify-2026-10-review`, because F57 changed only who may register, and every
  case registers the component it has just approved.
- **G3, Pi.** `faults.py` passes all 11 on the Pi as well. *Prediction:* 11 of 11.
- **G4, FI1 and FI4 on the Pi.** `faults_pi_fixed.sh` meets the post-fix criteria of
  `notes/fault_injection_prediction.md` ("The fixes"): FI1 recovers within 60 s of (A) returning with
  one supervisor and one sandbox, FI4 leaves no orphan and one chain per file. *Prediction:* every
  line `ok`. The approval adds one record before the first start and is read once per registration,
  so it does not touch the restart timings FI1 measures.
- **G5, the failed attempt is kept.** The attempt at `final-2026-10` stays in the results beside the
  run at `fix-2026-10-f61`, labelled. *Prediction:* holds by construction.

If G2–G4 hold, the submission states F61 in Appendix F and §8.6 as a harness defect found by the
final rerun, and gives step 3's figures from `fix-2026-10-f61`.

## Outcome, 2026-10-16 (appended; nothing above edited)

- **G1 — holds in substance, not as written.** `git diff --stat final-2026-10 fix-2026-10-f61` also lists
  step 1's results, committed between the two tags. Restricted to everything outside
  `experiments/verify/results/`, it lists exactly the three files named.
- **G2 — held.** Laptop, fresh clone of the fix tag: 11/11.
- **G3 — held.** Pi: 11/11.
- **G4 — held.** `faults_pi_fixed.sh`: every line `ok`; FI1 running again 3 s after (A) answered.
- **G5 — held.** The attempt at `final-2026-10` is kept (`step03_faults/faults_laptop_attempt1.*`).

Results: `experiments/verify/results/final_20261016/step03_faults*`, `verdicts_steps_2_4.txt`.
Found while preparing step 7, decided by Younes as a clause of F61: `verify/phase2_l23.sh` changes
into the frozen tree `~/r2exp/verify/v2` and starts its supervisor unapproved; step 7's driver
issues its commands against the clone, with the approval recorded as here.
