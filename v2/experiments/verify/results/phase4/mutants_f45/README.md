# Verification 4.12 (a): mutants of F45's gate (2026-10-07)

Predictions and criteria: `notes/tests_bite_prediction_20261007.md` (90055f9, committed before the
run). Mutants: `verify/mutants/mutants.py` (M18a–c) and their patches; runner
`verify/mutants/run_bridge_mutants.sh`, which brings (A) up from each mutated tree and checks that
the bridge (A) loaded is the mutated one (`bridge_in_A=mutated` in each `run.txt`).

| Mutant | Broken | Predicted | Result |
|---|---|---|---|
| M18a | the gate admits every authenticated user | killed by the one check | **killed**, `selftest_real_platform` "another ordinary user, not the designated one, is refused by the bridge" (50/51); no other suite failed |
| M18b | the gate admits every user once some mediator is designated | killed by the same check | **killed**, the same check, the same single failure |
| M18c | `designate_mediator` loses `require_admin` | survives | **survived** all 26 (finding F47). A check was added (62d8b92, committed before it ran): **killed** with it (51/52, "it was accepted"); unmutated 52/52 and 26/26 |

Three predictions, three right.

## The directories

- `run1_crashed/`: M18a and M18b complete. During M18c's `selftest_real_platform` the Pi's SD card
  dropped out: every read returned an I/O error until a reboot (F51). M18c's 20 earlier suites
  passed.
- `run2_m18c_control/`: M18c again from a fresh work directory (26/26 passed, so it survived), then
  the unmutated control with (A) brought up from the pristine tag (26/26).
- `m18c_new_check/`: the new check against M18c (fails) and unmutated (passes), then all 26 suites
  unmutated with the check in place.

The kill counts are read from each `summary.txt`; each kill was read in its log (`grep FAIL`).
