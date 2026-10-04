# Experiment — the push loop and the per-spawn re-check, against the stand-in platform

**Run:** 2026-10-04 · **Target:** Pi 5, aarch64, HA 2026.8.3; Python 3.13.5 for the decision layer,
`~/r2exp/ha314` (3.14) for the spawned run · **Feeds:** §7.36 · **Discharges:** S3's subscription
half (at the stand-in), §8.7 items 1 and 14 · **Predictions:** `notes/w1_push_loop_prediction.md`

## What is here

| Directory | What it holds |
|---|---|
| `results/prefix_20261004/` | The two new cases run against the code **before** the change: `selftest_t12` (31/33, the respawn decided by v1) and `selftest_audit` (an allowed action that dies leaves 0 records on disk). The evidence that each case tests what it claims |
| `results/w1_step1_20261004/e2e_push_thermal.json` | `thermal_comfort` in a real sandbox with `--push`: the full report, including `publish_history`, where `<push>` marks the moment the temperature changed |
| `results/w1_step1_20261004/suites/` | All 22 suites on the Pi after the change, one log each, and `summary.txt` |
| `results/w1_step1_20261004/selftest_push_p7_delay.log` | `selftest_push` after the cross-sandbox delay case was added: 23/23 |

## Reproduce

On the Pi, from `~/r2exp/v2/framework`:

    python3 -m confine.selftest_push
    python3 -m confine.selftest_t12
    systemd-run --user --scope -q python3 -m confine.endtoend --corpus ~/r2exp/corpus \
        --python ~/r2exp/ha314/bin/python --only thermal_comfort --push --json out.json

## Result

| | |
|---|---|
| Undeclared changes delivered | 0 of 3; 3 of 3 with the subscription table bypassed |
| `thermal_comfort` after a pushed 30.0 °C | dew point 9.96 → 17.81 °C, heat index 20.85 → 30.74 |
| Mediator cost per delivered push | 10.9 µs (11.3 µs in the later run) |
| Reading sandbox's median delivery, alone / beside a stalled one | 20.9 / 24.9 µs |
| A non-reading sandbox's backlog | 278 frames (the kernel's socket buffer), then one state per entity |
