# F62 in the submission — record (2026-10-16)

Applied to `submission/` on 2026-10-16 (Younes: "yes to all three, draft F62").

**What was measured.** Final rerun step 10, five passes at `final-2026-10` on a freshly rebooted Pi:
the change in (A) reaching the mediator's push had medians 0.50, 0.50, 0.50, 0.50, 0.52 ms against
Table 12.5's 0.71 ms (−29.6%; criterion ±20%). `experiments/verify/results/final_20261016/step10_timing/timing_stats.txt`.

**Why it is a restatement and not a defect.** F46 (2026-10-06) had already found this median moving
between runs: 0.71–0.74 ms in phase 3, 0.93 ms after F45, 0.50–0.66 ms in six alternating runs that
evening; the working report read it as 0.5–0.9 ms. Table 12.5 kept the single 0.71 ms and a range of
0.71–0.93 ms that left out the faster runs, so Appendix F's F46 row ("Reported as a range, 0.5–0.9 ms")
and Table 12.5 disagreed. The rerun's 0.50 ms lies in F46's range.

**Cause.** Not established. Untested hypothesis: step 9's `house_a up --fresh` gave (A) a newly created
configuration a few hours before step 10.

**Changes.**
1. Appendix F: F62 row after F61 (Minor); closing paragraph 62 findings, 38 Minor, "F61 and F62 from the final rerun".
2. Table 12.5: push row 0.50 ms | 0.50–0.52 ms (final rerun); the paragraph before the table says why one row is from the rerun.
3. §12.3: the push sentence gives 0.50 ms, the run-to-run spread with F46 and F62, and "a range of 0.5 to 0.9 ms".
4. §8.6: one sentence pointing to F62; 36 → 38 notes; F61's stale-path clause names three scripts (also in its App F row).
5. `00_front_matter.md` F01–F62; D7 "62 findings".

**Left for week 6.** The other rows of Table 12.5 still give the verification passes' ranges; restating the
whole column from the rerun would make the "(final rerun)" label on the push row unnecessary.
