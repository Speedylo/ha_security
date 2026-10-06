# Phase 4.5 — fault injection (2026-10-06)

Criteria and predictions: `notes/fault_injection_prediction.md`, committed before any fault was
injected, with outcomes appended. Cases: `verify/faults.py` (FI2, FI3, FI6, FI8, FI9; namespaces
for the full disk and the missing network, no privilege needed) and `verify/faults_pi.sh` (FI1, FI4,
with (A) and the supervisor). FI5 and FI7 are existing suite cases.

| Fault | Result |
|---|---|
| FI1 (A) stops mid-run | fail-closed held; **no recovery** when (A) returns (F29) |
| FI2 sandbox dies mid-frame | held |
| FI3 audit disk full | record-before-act held; **a partial record makes the log unverifiable for good** (F28) |
| FI4 supervisor `SIGKILL`ed | **the sandbox survives as an orphan; a restart starts a second** (F30); **the restarted log breaks the file's hash chain** (F31) |
| FI5 malformed frame | held (existing suites) |
| FI6 oversized frame | held |
| FI7 sandbox never reads | held (existing suites) |
| FI8 network gone during egress | held |
| FI9 wall clock jumps | held |

`local_wsl.txt` and `pi/pi_local.txt`: 9 of 11 criteria, the same two failing (FI3). `pi/results.txt`:
FI1 and FI4, with each supervisor's log and audit directory.
