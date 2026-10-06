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
| Change in (A) to the mediator's push | median 0.71 ms, worst **2.23 ms** *(written 1.57 ms until 2026-10-06; no committed log contains that figure, F23)* |
| Friendly names in (A) equal to (B)'s | 15 of 15 |

## Step 2b — commands from (A) into a sandbox (`results/w1_step2b_20261004/`)

    systemd-run --user --scope -q python3 -m confine.endtoend --corpus ~/r2exp/corpus \
        --python ~/r2exp/ha314/bin/python --only adaptive_lighting --push --platform real \
        --command --json out.json

| File | |
|---|---|
| `e2e_real_adaptive_command.json` | `adaptive_lighting` confined against (A); a user turns its sleep-mode switch on from (A). `command` holds the user's outcome and the state in (A) after. (`--push` also fires the temperature trigger; `adaptive_lighting` subscribes to no temperature, so nothing is delivered) |
| `selftest_real_platform_2b.log` | 36/36, including C2–C7 |
| `e2e_real_thermal_after_2b.json` | step 2's run repeated after 2b's changes: unchanged |
| `suites/` | all 24 suites on the Pi after 2b |

| | |
|---|---|
| A user's `switch.turn_on` in (A), through the real integration | success in 16 ms; the switch reads `on` in (A) |
| No sandbox running | fails to the user in 2 ms, recorded |
| Sandbox never answers | fails at 10.0 s; another sandbox answered in 1.0 ms meanwhile |
