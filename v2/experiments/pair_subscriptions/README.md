# Experiment — T06's subscription half, paired on one platform

**Run:** 2026-10-13, twice · **Target:** Pi 5, Home Assistant 2026.8.3 in both arms; Python 3.14
(`~/r2exp/ha314`) for the unconfined arm, the system 3.13.5 for the mediator · **Tag:**
`pair-2026-10-t06` · **Feeds:** Appendix C, Table C.4's T06 row · **Predictions:**
`notes/t06_true_pair_prediction.md`

## What is here

| Path | What it holds |
|---|---|
| `run.sh` | Stops (A), runs the unconfined arm, brings (A) up fresh, runs the confined arm |
| `results/run1/`, `results/run2/` | `unconfined.json`, `confined.json` and `commit.txt` for each run |
| `results/run2.log` | run 2's console output |

## Reproduce

On the Pi, from a clone's `v2/`:

    experiments/pair_subscriptions/run.sh <out-dir>

## Result (identical in both runs)

| | Unconfined | Confined |
|---|---|---|
| Undeclared changes delivered (`sensor.bedroom_occupancy`, `lock.front_door`, `person.younes`) | **3 of 3** | **0 of 3** |
| The declared change delivered | yes | yes |
| Control: filter bypassed at (A)'s watched set and the mediator's table | — | **3 of 3** seen |
| Decisions on disk | — | 1 (the grant); none from deliveries or the control; chain verifies |
| Platform, host | 2026.8.3, raspberrypi | 2026.8.3, raspberrypi |

All six predictions held in both runs.
