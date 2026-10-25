# Bridge extension, step 5: the fifteen end to end against the real house — prediction (2026-10-25)

**Committed before any code.** Younes: "go ahead with step 5", then "option 1, go ahead" — (A)'s
living-room light gains a brightness level so the real world matches the stand-in's scripted one.

Every end-to-end result so far published to the harness's stand-in for the house
(`platform.Platform`), which accepts any entity type. Steps 1–4 extended the bridge to the types the
fifteen publish. This step runs the fifteen's **confined** arms against (A), the house's real Home
Assistant, through the bridge, and checks that what they publish appears and works there.

## What changes

1. **(A)'s light can be dimmed.** `house_a.py`'s configuration gains
   `input_number.living_room_brightness` (0–255, initially 180), and the template light
   `light.living_room` gains a `level` from it and a `set_level` action that sets it and switches the
   light on. Its colour mode becomes `brightness`, as the stand-in's `WORLD` light is.
2. **`confine/real_house.py`**, shared by the harnesses: reset (A)'s world to `WORLD`'s values
   (temperature 21.4, humidity 48, light on at 180); apply a scripted world step as a real service
   call (`light.turn_on` with its brightness, `light.turn_off`); stop and start (A) around an
   unconfined arm (F56: both want port 8123); and, after a confined arm, read back from (A) each
   entity the integration published — its registry row, domain and state.
3. **`--platform real`** on `endtoend_function` and on `endtoend_egress` (whose `run_confined`
   `endtoend_local` and `endtoend_oauth` reuse, so they gain it too). The stand-in stays the default,
   so every earlier run remains reproducible. In real mode a confined arm acts on (A) through
   `RealPlatform`; the unconfined arm runs with (A) stopped, as it always has, and (A) is started
   again (not fresh) for the confined arms. The integration's own steps, verdicts and harness checks
   are unchanged.

## Predictions

**H, the house** — new suite `selftest_real_house` (Pi, (A) `up --fresh`):

| | Prediction |
|---|---|
| H1 | `light.living_room` reports `supported_color_modes` `["brightness"]` and brightness 180; `light.turn_on` with brightness 51 leaves it on at 51; `light.turn_off` leaves it off; the reset restores on at 180, 21.4 and 48 |
| H2 | Stopping (A) frees port 8123 and starting it again (not fresh) keeps the bridge's config entry and the mediator's user |
| H3 | **Fails first:** before the change, H1 fails (no brightness) |

**E, the fifteen against (A)** (Pi, a fresh clone, (A) `down` then `up --fresh` once before the
set). For every integration, the confined arm's report gains `in_house`:

| | Prediction |
|---|---|
| E1 | **Every publish is accepted** by (A): no `accepted: false` in any confined-declared arm of the fifteen |
| E2 | **Every published entity is in (A)**: a registry row owned by `confine_bridge`, of the domain it was published under, and — except a button, whose state is its last press in (A) — (A)'s state at the end of the run equals the last state the sandbox published for it |
| E3 | **The integrations' own outcomes are unchanged**: `retest_e2e_verdicts.py` on the function set gives 43 of 45 with the same two rows failing as in the final rerun (scheduler's switch, both arms); `e2e_ext_verdicts.py`'s alarmo checks P1–P4 hold (8/8); each egress, local and OAuth subject passes its harness's own checks, as in its latest stand-in run |
| E4 | Steps 2 and 3's corrected checks (button T2, code K9/T9) are verified: `suites_all.sh` passes, with `selftest_bridge_types` run twice on the same (A) |

**What the fifteen published in their latest runs** (so E1–E2 cover these types): sensors (most),
`weather` (`dwd_weather`, `pirateweather`), `climate` (`midea_ac_lan`), `switch` (`adaptive_lighting`,
`scheduler`), `button` and `text` (`watchman`), `alarm_control_panel` (`alarmo`). `localtuya`'s
confined arm published no entity of its own (it finds the simulated device); `waste_collection_schedule`
published six sensors and, since F65's fix, a calendar. Every type is now one the bridge supports.

**External services.** The six internet-facing subjects depend on their services answering now; a
service that is down is recorded as such and is not charged to the bridge (the rule of every earlier
run). Values change between runs (prices, weather, collection dates), so E3 uses each harness's own
comparisons (B against A within one run), not values from earlier runs.

Outcome appended below; no run is repeated to obtain a pass.

---

## Outcome of the first complete run (appended 2026-10-25, after the run)

Two runs, results in `experiments/real_platform/results/bridge_types_20261025/` (`s5-void-blocking/`,
`s5/`, with (A)'s two logs `s5/a_s5.log*`).

**The first run is void** (`bridge-s5`, `d4e95fe`, 20:01). `real_house._service` and the house's test
sent `"blocking": true` with a WebSocket `call_service`, which (A) refuses (*"extra keys not allowed"*);
every world reset failed. Fixed in `e88010a` (`bridge-s5b`): a WebSocket call already waits. Before it
stopped, the pre-change arm measured **H3: held** — (A)'s old light reported `supported_color_modes`
`["onoff"]` and no brightness.

**The second run** (`bridge-s5b`, `e88010a`, 20:04–20:35, clean before and after). Verdicts:
`verify/bridge_step5_verdicts.py`, 21/24.

| | Outcome |
|---|---|
| H1 | **3 of 4.** The light dims (180, then 51, then off). The reset check missed as written: humidity reads `48.0` after `input_number.set_value`, `48` at (A)'s start; the test compared strings, the value is restored |
| H2 | Held: (A) stopped (port 8123 free) and started again, with its bridge entry and the mediator's user |
| E1 | Held as measured in every confined-declared arm (no publish recorded as refused). **But E1 is weaker than intended:** the sandbox records a publish as accepted when (A)'s bridge answered, and (A) can fail to *add* the entity afterwards; E2 is the check that caught that |
| E2 | **Missed: 21 of 24 held.** The three misses are two bridge defects, both found by this run: **F66** — a numeric sensor published `unknown` gets the string as its value and (A) refuses it (`powercalc`'s `sensor.all_standby_energy`, `smhi_brandrisk`'s `…fruset_nederbord`; also on (A)'s restart, when the roster is restored); **F67** — a timestamp sensor's state is passed as a string and (A) refuses to add it, *"Invalid datetime"* (`dwd_weather`'s two time sensors). Every other entity of every subject is in (A), owned by the bridge, of its type, in the published state — `nordpool`, `pirateweather` (weather and sensor), `regensburg_transport`, eleven of `smhi_brandrisk`'s twelve, `waste_collection_schedule` (six sensors **and its calendar**), `trakt_tv` |
| E3 | **Incomplete.** The function set stopped after `powercalc`: before `watchman`'s unconfined arm, (A) did not stop within 60 s (cause not established; (A)'s log ends 20:07:13 with nothing about stopping), so `retest_e2e_verdicts` and alarmo's checks were not reached. Of the others: `nordpool`, `waste_collection_schedule`, `smhi_brandrisk`, `trakt_tv` passed their own checks. `dwd_weather` missed one: arm B was refused `www.dwd.de:443`, a second host the integration now reaches, outside the clause read from its source — reported as such, not added. `pirateweather` and `regensburg_transport` each missed the "one value equals arm A's" check, on values that do not involve the bridge (the sandbox's own record): `10.1` against `10.1111111111111` (the confined arm's state rounded to the sensor's display precision), and a departure at 21:34 against 21:35. `midea_ac_lan` did not run: its fake device could not bind `10.126.83.113`, the Pi's LAN address hard-coded in `endtoend_local.py`, which DHCP has since changed to `10.126.85.243`; for the same reason `localtuya`'s device saw nothing in any arm, so its run shows loading only |
| E4 | 32 of 33 suites: `selftest_real_house` (H1's string comparison). `selftest_bridge_types` and `selftest_commands` passed, so step 2's button check and steps 3–4's quoted code search hold on a reused (A) |

(A)'s log has eight bridge errors, all F66 or F67.

**Before a complete run:** F66's fix (`55d8d6d`) and F67's, each with its fails-first test; the house
test's reset check compared as numbers; `endtoend_local` given the Pi's current LAN address. The
comparison fragility (`pirateweather`'s rounding) and the timetable minute are recorded, not changed.
