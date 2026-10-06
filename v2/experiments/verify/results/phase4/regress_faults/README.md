# The regression for F28–F31 — verify-2026-10-faults, 2026-10-06

A fresh clone of the tag on the Pi, run by `verify/regress_faults.sh` (committed before it ran),
against the criteria in `notes/fault_injection_prediction.md` ("The fixes").

| Step | Result |
|---|---|
| All suites, twice (`suites_1/`, `suites_2/`) | 26 of 26 both times (25 suites and the base self-test) |
| `selftest_real_platform --restart` | 48/48 |
| `drive_demo` under the supervisor | press 11 ms; cut-off 0.49 s later after 102 decisions; Repairs issue, fix flow, restarted in 0.10 s, issue gone; as in Phase 2 |
| `verify/faults.py` | 11/11 criteria |
| `faults_pi_fixed.sh` (FI1, FI4, F30's backstop) | every criterion held: the integration back 4 s after (A) answered, no traceback; no orphan 10 s after a `SIGKILL`; one sandbox after the restart; two log files, no sequence, link or hash break; a planted process in a stale cgroup killed, and said so |
| `nordpool` end to end | **failed at first**: `No space left on device` writing its spec file to `/tmp`. `/tmp` (a 2 GB tmpfs) held a 1.2 GB directory left at 12:27 by the mutation run, where mutant M11 (no cut-off) flooded `selftest_flood`'s log until the time limit killed it. Removed, and re-run: **16/16** (`egress_nordpool_rerun.*`). Against Phase 2's run, only live values differ, plus one more connection attempt in the unconfined arm, which has no mediator |
