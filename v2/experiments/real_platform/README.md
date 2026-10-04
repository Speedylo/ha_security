# Experiment — the mediator acting on the house's real Home Assistant, (A)

**Run:** 2026-10-04 · **Target:** Pi 5, aarch64, (A) = Home Assistant 2026.8.3 from `~/r2exp/ha314`,
frontend 20260729.7 from `~/r2exp/houseA-deps` · **Feeds:** §7.37 · **Discharges:** §8.7 #2 (in
part: commands into a sandbox are step 2b) · **Predictions:** `notes/w1_step2_real_platform_prediction.md`

## Reproduce

On the Pi, from `~/r2exp/v2/framework`:

    python3 -m confine.house_a down; python3 -m confine.house_a up --fresh
    python3 -m confine.selftest_real_platform --restart
    systemd-run --user --scope -q python3 -m confine.endtoend --corpus ~/r2exp/corpus \
        --python ~/r2exp/ha314/bin/python --only thermal_comfort --push --platform real \
        --json out.json

The token is written to `~/.config/capstone/house_a.token` (mode 600) and appears in no log.

## What is here (`results/w1_step2_20261004/`)

| File | |
|---|---|
| `selftest_real_platform_fresh.log` | 23/23 on a fresh (A): registry identity against a bare state, ownership, service execution, the filter, latency, restart |
| `e2e_real_thermal.json` | `thermal_comfort` confined against (A), with a real pushed change; includes `registry`, read back from (A) |
| `names_and_restart.json` | friendly names in (A) against (B), enum options, and the 15 entities across a restart of (A) |
| `e2e_standin_thermal_after_order_fix.json` | the stand-in run after the push-handler ordering fix, unchanged from §7.36 |
| `r2_restart_thermal.json` | the first restart check, before the naming fix |
| `suites/` | all 24 suites on the Pi |

## Result

| | |
|---|---|
| Registry rows for the confined integration | 15 of 15, with config entry and device; a bare `/api/states` post gets none |
| After restarting (A) | 15 of 15 rows, 15 of 15 states identical |
| Dew point after a real `input_number.set_value` to 30 °C | 9.96 → 17.81 °C |
| Change in (A) to the mediator's push | median 0.71 ms, worst 1.57 ms |
| Friendly names in (A) equal to (B)'s | 15 of 15 |
