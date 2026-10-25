# F69: `house_a.stop` mistakes a zombie (A) for a running one — prediction (2026-10-25)

**Committed before the fix.** Found by bridge step 5 (`notes/bridge_types_step5_prediction_20261025.md`):
twice, the function set stopped before `watchman`'s unconfined arm with *"(A), pid …, did not stop
within 60 s"*, and (A) was gone as soon as the harness exited.

## The mechanism, reproduced on the Pi (`~/r2exp/bridge-run/hang/`)

The end-to-end harnesses call `become_subreaper()`, so orphaned descendants are re-parented to them.
Bridge step 5's `real_house.house_stopped` restarts (A) from inside the harness (`house_a up`), whose
`keep` wrapper daemonises and is therefore re-parented to the harness. When the harness later stops
(A), `keep` and `hass` exit at once — but `keep` stays a zombie until its parent reaps it, which the
harness never does. `stop` tests liveness with `os.kill(pid, 0)`, which succeeds on a zombie, so it
waits its 60 s and raises. Reproduced: powercalc's three arms then watchman's unconfined arm, inside
one harness, timed out; the same arms followed by `house_a down` after the harness had exited
stopped in 2 s; no connection to (A) was open during the timed-out stop (the last closed at the
moment the stop began). Not a defect of the bridge or of Home Assistant: of the harness's tooling.

## The fix

`house_a` decides liveness by `/proc/<pid>/stat`: a process in state `Z` (zombie) has exited. If the
zombie is this process's own child, it is reaped.

## Predictions

| | Prediction |
|---|---|
| Z1 | New offline suite `selftest_house_a`: a child that has exited and not been waited for (a zombie) is reported not alive; a running child is alive; a pid that does not exist is not alive. **Fails first** on the zombie case (`os.kill(pid, 0)` succeeds) |
| Z2 | On the Pi, the function set runs to the end with `--platform real`: no "did not stop" (the rest of step 5's E3 is judged as that note says) |

Outcome appended below.
