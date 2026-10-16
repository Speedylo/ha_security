# §6, §13, §14, §15 week-6 read-through — 2026-10-16

Nothing in the submission changes until Younes chooses.

## Checked and correct

- §13: 53 deliberate defects; working report "about 141,000 words" (141,681 now); 91% of 1,482.
- §14: 53 hand-written defects; row 7's three implementation gaps match Table 9.2 (dictionary service data,
  F50, F53); row 6 covers the stored-data size.
- §15: the four High residual risks named as R1, R2, R5, R3, matching §8.5 as fixed today; six statements;
  at least 17 sandboxes; about sixty times.

## C7. The prediction count stops before the final rerun (§6 Table 6.1, §6.2, §15)

Table 6.1 was scored on 2026-10-15 from the 35 notes then in the repository (`notes/s6_logic_model_plan.md`).
It says it scores "every prediction that can be counted individually". Two counted notes have been added since:

| Note | Predictions | Held, scored against the first run (§6's rule) |
|---|---|---|
| `final_rerun_prediction.md` | 13 steps | 10 or 11. Held: 1, 2, 4–9, 11, 12. Missed: 3 (at `final-2026-10` the faults stopped at FI2, F61), 10 (the push row, F62). Step 13 depends on how it's scored: consistency and recompute held, but prereg "held only once the pairing is corrected, which the script as committed does not do" |
| `f61_fault_harness_approval_prediction.md` | G1–G5 | 4. G1 "holds in substance, not as written", which is a miss under the strict rule |

(`prereg_coverage_prediction.md`, 2026-10-15, is already among the nine uncounted notes.)

Proposed new row: | Final rerun, 16 October | 2 | 14 | 18 |, with step 13 scored as a miss, since the
prediction as written did not hold without a change. Totals 219 of 247. If step 13 is scored as held: 15 of
18, 220 of 247.

Text that follows:
- §6.2: "Their 18 misses" → 22 (or 21); "None of the 24 misses" → 28 (or 27). The new misses concern the test
  tools (F61, prereg) and one timing figure that came in faster than stated (F62), none of them the
  framework's central properties, so the sentence stays true.
- §15: "205 of the 229 that can be counted held" → "219 of the 247" (or 220).

## C8. §6 "the record of 153 claims and 60 findings" → 62 findings (Appendix F)

## O6 (minor). Table 9.2 says "Section 14 prices the ones that future work could remove", but one row is in no item of §14

The OAuth first login under the supervisor is not covered by any of §14's ten items. Either add it to row 7
("Four implementation gaps … and an OAuth first login, which needs a person's browser") or leave it as is.
It is the only gap.

## Applied 2026-10-16 (Younes: strict scoring; C8; O6)

Table 6.1 row "Final rerun, 16 October | 2 | 14 | 18", total 219 / 247; §6.2 22 and 28 misses; §15 219 of 247. §6 62 findings. §14 row 7 four gaps incl. the OAuth first login; text: the first three fixable without changing the architecture, the fourth needs the browser step carried through (A). Counted notes 1+16+10+2 = 29, + 9 uncounted = 38, as §8.6.
