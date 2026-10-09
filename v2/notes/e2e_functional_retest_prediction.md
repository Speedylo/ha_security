# The five platform-only end-to-end integrations, retested for function: predictions

**Written 2026-10-09, before any harness change and before any run.** Owed since 2026-10-08
(Younes): Table 12.3 says these five *load* confined, but only `thermal_comfort` was checked against
a value. This note fixes, for each one, a stimulus, the value its own code says it must produce, and
what each arm must show. Commit before the harness change; do not edit after a run (`verify/prereg.py`).

## 0. What the 2026-10-03 rerun did and did not show

Read from `experiments/end_to_end/results/rerun_20261003/`, both arms:

| Integration | Published | What that shows | What it does not |
|---|---|---|---|
| `thermal_comfort` | 15 sensors; dew point 9.96 °C at 21.4 °C / 48% | It works: physically correct value, both arms; the W1 push run moved it | — |
| `powercalc` (fixed 5 W) | `lamp_power_power = 5.00`, both arms | It read the lamp as *on* and applied its mode | Any calculation: a fixed value is the same at every brightness |
| `watchman` | status `pending`, `processed_files = 0` | Its entities exist | **It never scanned.** Its first scan runs 10 s after a late setup (`DEFAULT_DELAY`), and the harness stops at once (`settle_seconds 0`) |
| `adaptive_lighting` | 4 switches | Its entities exist | It controls no light: lights are set in its **options** flow, which the harness never drives, so the `light.living_room` read it declares was never used |
| `scheduler` | nothing | It loads | It does anything: entities appear only when a schedule is added |

Table 12.3's "13 entities", "7 entities" and "5 entities" are therefore counts of a structure, not
evidence of function, for four of the five.

## 1. Common to every check

- **Both arms** use the same `build_hass` recipe: London (51.5, −0.12), UTC, metric, the same
  `WORLD` (`light.living_room` on at brightness 180, temperature 21.4, humidity 48). The confined
  arm uses the stand-in `Platform`, as the 10-03 rerun did.
- **A third arm, clause withheld**, for each integration that reaches outside itself, as Table 12.3's
  network integrations had. Two different predicted shapes:
  - a withheld **entity read** → the entity is absent in the sandbox (the bridge mirrors declared
    entities only), so the integration sees `None`, not a refusal;
  - a withheld **service call** → the service is not registered in the sandbox, so the call raises
    `ServiceNotFound` *inside* the sandbox and **the mediator records nothing**. No refusal record is
    predicted, and finding one would be a finding.
- **Pass** means the predicted value appears in the arm's report. Every value is read from the
  report, never from the log by eye.

## 2. Harness changes this needs (test instruments only; no framework code)

1. Record each published entity's **attributes** as well as its state, in both arms.
2. **Per-subject settle time**: the run stays up for a given number of seconds after setup.
3. **Stimuli after setup**, in order, at given offsets: set a `WORLD` entity's state and attributes
   (confined: through `platform.set_state`, which pushes to subscribers; unconfined: `hass.states`);
   call a service of the integration's own; drive an **options flow** with given input.
4. **Files in the config directory** before start (for `watchman`).
5. **A recording double for `light.turn_on`** in the unconfined arm's world, so a call has somewhere
   to land and is recorded as the stand-in's `platform.calls` records it confined.
6. A `--subjects` filter and a `--withhold` switch for the third arm.

Whether these count as "fixes the writing turns up" under the cut-off is Younes's call (§6).

## 3. Predictions, per integration

### P1. `powercalc` — linear mode, a calculation that depends on the input

Flow: menu `virtual_power`, `entity_id: light.living_room`, `mode: linear`, `min_power: 1`,
`max_power: 11`, name `lamp power`. Declares: read **and subscribe** `light.living_room`.

Its own formula (`strategy/linear.py`, light range 0–255, gamma 1, standby 0):
`power = 1 + 10 × brightness / 255`.

| Step | Stimulus | Predicted `sensor.lamp_power_power` |
|---|---|---|
| a | none (brightness 180) | **8.06** |
| b | brightness → 51 | **3.00** |
| c | light → `off` | **0.00** (standby; `OFF_STATES`) |

Both arms identical. Withheld arm (no read clause): the light is absent in the sandbox, so the sensor
is `unavailable` or `unknown`, never a number. Withheld subscribe only (read kept): 8.06 at a,
**unchanged at b and c**, because no change is delivered: this is the arm that shows the push path
is what carries the calculation.

### P2. `watchman` — a report about the instance it runs in

Config directory gets one file, `automations.yaml`, referring to:
`sensor.living_room_temperature` (declared), `light.living_room` (exists in the world, **not
declared** in the confined arm), `sensor.does_not_exist`, and the action `notify.nobody_here`.
Settle **45 s** (first scan at 10 s after setup).

| | Unconfined | Confined, `temperature` declared | Confined, both declared |
|---|---|---|---|
| `sensor.watchman_status` | not `pending` (scan done) | same | same |
| `sensor.watchman_processed_files` | **≥ 1** | same | same |
| `sensor.watchman_missing_entities` | **1** (`does_not_exist`) | **2** (+ `light.living_room`) | **1** |
| `sensor.watchman_missing_actions` | **1** (`notify.nobody_here`) | **1** | **1** |

The middle column is the prediction worth having: confinement changes `watchman`'s answer, correctly,
because inside the sandbox an undeclared entity does not exist. Stated as a behaviour of the design,
not a fault. (Risk to the prediction: `missing_actions` may differ between arms if `watchman` also
checks other services the configuration names; only one is named.)

### P3. `adaptive_lighting` — controls a light

Flow: name `confined test`. Then its **options** flow with `lights: [light.living_room]`, all else
default. Declares: read + subscribe `light.living_room`, `services.call light.turn_on` for that
entity. Settle **30 s** (it adapts on setup and every 90 s).

Predicted, both arms:
- the main switch's attributes carry `brightness_pct` and `color_temp_kelvin`, the two arms within the
  sun's movement between their runs (run back to back: brightness within 2 points, colour within 50 K);
- **one or more `light.turn_on` calls for `light.living_room`** with
  `brightness = round(255 × brightness_pct / 100)` from that same attribute, and **no colour
  attribute**, because the world's light supports only `brightness`;
- no `transition` key (the light declares no `supported_features`).

Withheld arm (no `services.call`): the attributes as above, **zero calls in `platform.calls`, zero
decisions for `light.turn_on`**, and the integration's own error for an unknown service in its log.

### P4. `scheduler` — runs an action at a time

Flow: empty (as before). Then the service `scheduler.add` with one timeslot starting at the **next
whole minute + 1** (UTC), action `light.turn_on` on `light.living_room` with `brightness: 200`,
`repeat_type: single`, name `retest`. Declares: `services.call light.turn_on`. Settle until 30 s after
the start time.

Predicted, both arms:
- a `switch.schedule_*` entity published, state `on`, after the `add`;
- **exactly one `light.turn_on` call** for `light.living_room` with `brightness: 200`, at the start
  time (± 5 s), not before it;
- with `single`, the switch's state after the run is `off` (completed) — *least certain prediction
  here; written as read from the service description, not the code path.*

Withheld arm: the switch is published, the action at the start time fails inside the sandbox
(`ServiceNotFound`), **no call reaches the platform, no decision recorded**.

### P5. `thermal_comfort` — already value-checked; carried for completeness

No new stimulus. Re-run in both arms to show the changed harness did not move it: dew point
**9.96 °C** (9.95645… unconfined, as on 10-03), 15 entities.

## 4. What updates if these hold

Table 12.3's four rows gain a value each (`powercalc` 8.06 → 3.00 → 0.00; `watchman` 1 vs 2 missing;
`adaptive_lighting` a brightness command; `scheduler` a command at its time), the "setup only"
qualifier in §12.2 is dropped, and the paragraph gains the `watchman` observation. If one fails in
the confined arm only, it is a finding against Assertion B and is logged as F54.

## 5. Where it runs

On the Pi, from a clean clone of `main` at the commit that adds the harness changes, tagged
`retest-2026-10-e2e`; results to `experiments/end_to_end/results/retest_20261009/`.

## 6. Decisions for Younes before the harness is touched

1. **The cut-off.** §2's changes are to the test harness (`endtoend.py`, `endtoend_unconfined.py`,
   `sandbox_runtime.py`'s driver), not to enforcement. The runtime file is copied into every sandbox,
   so a change to it is a change to what runs confined. Proposed: allowed, under its own tag, with the
   27 suites run once after it to show the framework's behaviour is unchanged.
2. **Stand-in or (A).** Proposed: the stand-in, for comparability with 10-03. (A) is the stronger
   test for P3 and P4 (a real light, a real call), and could follow.

## 7. Amendment — 2026-10-09, after a smoke run, before the recorded run

A smoke run of every variant from an uncommitted copy on the Pi (`~/r2exp/retest`, not a result)
gave 30 of 34 checks as predicted. Three misses are recorded here as they fell, and the harness and
one variant change before the recorded run. **No predicted value in §3 is edited.**

1. **`adaptive_lighting` unconfined: 0 calls recorded — a harness fault.** `light` is set up as a
   component in that arm and registers its own `light.turn_on`, so the recording double stepped
   aside and the call went unrecorded. Fixed: the unconfined arm records every call from the bus's
   `call_service` event. (Confined, the call was recorded 11 ms after the options flow: brightness
   47 from 18.55%, entity named, no colour, no transition, as P3 predicted. It adapts when its
   options reload, not only on its 90 s interval: P3's "adapts on setup" was right for that reason.)
2. **`scheduler` confined: fired (`triggered`), and no call reached the platform — a fault in this
   note's variant, not the framework.** `scheduler` checks that each target entity exists before
   acting (`actions.py`, `is_available`), and the variant declared `services.call` without a read of
   `light.living_room`, so inside the sandbox the lamp did not exist and it declined, logging nothing
   above debug. The variant now declares the read; the old one is kept as `scheduler-no-read`, whose
   outcome (fires, no call, no decision) is **observed in the smoke run, not predicted**. A
   manifest for an integration that acts on a device must let it see the device: a point for §9.
3. **`scheduler` ends `triggered`, not `off`, in both arms.** The least certain prediction, wrong in
   both arms; it stays wrong in the record.

**New prediction, written before the recorded run.** Unconfined, `scheduler` passes the target as a
list (`"entity_id": ["light.living_room"]`). The bridge forwards only `str`, `int` and `float`
values of a service call's data (`sandbox_runtime.Bridge._forward_service_call`), so **confined,
with the read declared, the call reaches the platform with `brightness: 200` and without
`entity_id`**: a command that has lost its target. If so, it is a framework defect against Assertion
B, logged as F54. (`adaptive_lighting` passes a single string and is unaffected.) The verdict script
checks for the target and will fail this row; that failure is the prediction.

The recorded run is from a clone of the tag `retest-2026-10-e2e`, taken from a bundle of this
repository (not from GitHub, so nothing is pushed for it).
