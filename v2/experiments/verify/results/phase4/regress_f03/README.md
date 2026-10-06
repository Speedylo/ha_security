# F03's regression — verify-2026-10-f03, 2026-10-06

The tag `verify-2026-10-f03` (6a72c4a) cloned fresh into `~/r2exp/verify-f03` on the Pi and run by
`verify/regress_f03.sh` (committed before it ran). Criteria were fixed in the findings log's F03 note
before the code was written.

| Criterion | Result |
|---|---|
| (1) `Decision` with no clause, or an empty one, raises | ✅ `selftest_audit` F3 section |
| (2) `AuditLog.decision` with no clause raises and writes nothing | ✅ 0 records written |
| (3) every path that once built a clause-less decision now names a rule | ✅ no manifest → `/permissions`; four command refusals and the granted command recorded with their rules; both answers to a command result carry `(command: answered only on the channel it was sent to)`; 6 decision records on disk, 0 without a clause. *Criterion (3) said all seven paths "write a decision record". The two answer paths do not and never did: they are replies, and the command they answer was recorded when it was decided. They are judged by the clause in the reply. Stated rather than re-read.* |
| (4) 26/26 suites; `nordpool` end to end; flood and command paths unchanged | ✅ 26/26 exit 0. Against this morning's clean-checkout logs (same scratch location), with numbers masked, only `selftest_audit` differs beyond scratch paths and random identifiers, by its new section. `selftest_flood` and `selftest_push` are identical. `nordpool` passes 16/16, and `verify/compare.py` against Phase 2's run finds only live values (the price moved 0.001 → 0.002 in **both** arms, sun times, a rotated DNS answer) |

**Control.** On a scratch copy with the guard removed and three paths set back to `clause=None`, the
F3 section fails 7 of 7. The test can see what it claims to check.
