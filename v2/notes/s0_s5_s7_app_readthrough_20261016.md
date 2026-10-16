# Front matter, §1–§5, §7 and the appendices: week-6 read-through — 2026-10-16

Nothing in the submission changes until Younes chooses.

## Checked and correct

- Abstract and §1: 669,743; 75 integrations; thirteen end to end; about sixty times; at least 17; 4.02.
- Front matter: F01–F62; T01–T19; M01–M50 (53 patches, with the letter variants M08a/b and M18a–c).
- §2: 4,220; 3,095; 2021, eight integrations; XZ Utils about two and a half years.
- §3: twenty requirements, two narrowed (Appendix B); eight manifest clauses (as §9.3); D3 29 suites and 53
  mutants; D6 nineteen threats (now explained in §8.4); D7 62 findings.
- §4, §5, §7: 17 to 43, 75, 20, 3,095 of 4,220, 4.02: as §10 and §12.
- Appendices B–F: verdicts and counts agree with §12 as revised today; Appendix F's totals add up (62).
- The framework code is unchanged since `final-2026-10`. Only `verify/` scripts changed (F61's fault
  scripts and `prereg.py`'s RESULTS entries).

## O7. Table 1.1: a reader who divides gets 5.02, not 4.02

1,904,297 ÷ 379,326 = 5.02. The 4.02 in the table excludes the Community Store's own 379,326 installs, which
the total includes (`figures/ecosystem_scale.json`; `notes/s1_introduction_plan.md`: "(1,904,297 − 379,326)
/ 379,326"). Proposed row label: "Mean community integrations per Community Store installation, the store
itself not counted | 4.02". The 4.02 used everywhere else stays correct.

## O8. Appendix F, F62's row still speaks of Table 12.5 as it was

It says "30% below the 0.71 ms stated in Table 12.5 … the table gave a single figure and its range omitted
F46's faster runs | Table 12.5 restated from the final rerun, 0.50 ms; Section 12.3 reports the range
0.5–0.9 ms across all runs". Table 12.5 now gives 0.50 ms with a range of 0.50–0.93 ms over ten passes.
Proposed: "the 0.71 ms Table 12.5 then stated … its range then omitted F46's faster runs | Table 12.5
restated: 0.50 ms from the final rerun, with the range across all ten passes, 0.50–0.93 ms; Section 12.3
gives 0.5–0.9 ms across every run on record".

## O9. Appendix A doesn't name the version the report describes, or the reproduction guide

An examiner needs the tag the report's numbers were checked at, and D8's guide is not in the index. Proposed
two rows:
- | Version | Tag `final-2026-10`, at which every measurement, mutant, suite and fault was rerun; the fault
  scripts at `fix-2026-10-f61` (F61). The framework's code is identical at both. Results in
  `v2/experiments/verify/results/final_20261016/` |
- | Reproduction | `v2/REPRODUCE.md`, followed from a fresh clone; on a freshly imaged device still open
  (F18) |

## Applied 2026-10-16 (Younes: O7, O8, O9)
