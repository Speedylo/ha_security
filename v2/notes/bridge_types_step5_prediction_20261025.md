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
