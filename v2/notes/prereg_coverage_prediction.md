# `verify/prereg.py` widened to every prediction note: prediction (2026-10-15)

**Written before the script is changed or run.** Never revised after the run.

## Why

§8.6 (approved) says the repository holds 34 prediction notes and that a script checks each was
committed before its first result. On 2026-10-15 there are 35 notes and the script verifies 29:

- its glob `*_prediction.md` misses `tests_bite_prediction_20261007.md` and
  `f48_f49_prediction_20261007.md`;
- `f08_t06`, `final_pass` and `minor_findings` name no result path and have no entry in `RESULTS`,
  so they print UNCHECKED;
- `integrity_consistency` is skipped by design (it registers the check itself).

## The change

1. The glob becomes `*prediction*.md`, and a note's name is the file name with `_prediction` and
   anything after it removed.
2. `RESULTS` gains the first commit holding each of the three notes' results, read from the log
   (the first commit after the note touching `experiments/*/results`, and its message read to confirm
   it reports that note's work):
   - `f08_t06` → `7271291` (F08 regression on `verify-2026-10-f08`), +7 min
   - `minor_findings` → `aa072c2` (F04, F06, F07, F12, F15 closed), +3 min
   - `final_pass` → `d739e77` (final pass on `verify-2026-10-final`), +8 min
   - `f48_f49_20261007` names only harness paths, so it also needs an entry: `b22c306` (4.12 closed,
     F48 and F49 resolved), about +2 h
3. `integrity_consistency` stays skipped. This note becomes the 36th; its own result is the run below.

## Prediction

- **P1.** All 35 notes other than `integrity_consistency` print `ok`: order holds and no prediction
  line changed after results. Confidence: high for the order (the gaps above are positive and each
  result commit descends from its note); medium for "no line changed", since three of the six were
  never checked for edits.
- **P2.** No note prints UNCHECKED, and the summary reads `0 note(s) to look at`.
- **P3.** The 29 already passing are unchanged.

**If any note prints CHECK,** it is logged as finding F61, reported as found, and §8.6 says so.

Result: `experiments/verify/results/prereg_20261015/prereg.txt`.

## Outcome (added 2026-10-15, after the run)

**P1 held.** All 34 notes other than `integrity_consistency` and this one print `ok`, including the five
not verified before: `f08_t06` +7 min, `minor_findings` +3, `final_pass` +8, `f48_f49` +119,
`tests_bite` +134 (found by its own paths once the glob took it), each with 0 prediction lines changed
(`experiments/verify/results/prereg_20261015/prereg.txt`). No F61.

**P2 missed, on this note alone.** The run printed `UNCHECKED prereg_coverage`: this note names its
result path, but the result was not yet committed when the script ran, so it had nothing to compare.
Not foreseen when P2 was written. After the result was committed (`git log` on that path), a second
run gave 35 `ok` and `0 note(s) to look at` (`prereg_after_commit.txt`).

**P3 held.** The 29 that passed before are unchanged, same commits and gaps.

§8.6 now reads 36 notes, each checked except the note that defines the check; §6.2's uncounted notes
are nine (this one added).
