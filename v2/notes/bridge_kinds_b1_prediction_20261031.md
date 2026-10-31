# Bridge extension, batch B1: light, fan, cover, lock — prediction (DRAFT, 2026-10-31)

**Committed before any code.** Younes decided the three open points and approved the list on 2026-10-31 ("go ahead"). Once approved, this note
and the failing tests are committed alone (tag `bridge-b1-pre`), then the code (`bridge-b1`), as in
steps 1–5 (`bridge_types_step*_prediction_20261025.md`). Part of the decision of 2026-10-31: the
bridge covers the 18 missing kinds before the final report (`bridge_coverage_count_20261027.md`).

## The rule for what the mediator forwards

The list below is **derived from Home Assistant 2026.8.3** (`~/ha-src/core`, the pinned version), not
chosen. Three steps, applied to each kind:

1. **Start from what Home Assistant defines**: every service the kind registers
   (`async_register_entity_service`) and every field of its schema.
2. **Keep what actually reaches the bridged entity in (A).** A user's command is a service call in
   (A). (A)'s Home Assistant validates it against the schema, may convert or drop fields, and then
   calls the bridged entity's method. That method is what sends the command to the mediator, and the
   sandbox runs it again as the same service on the same entity in the integration's own instance
   (`sandbox_runtime.py`, `blocking=True`). So the mediator's rule is written against **the
   arguments the entity's method receives**, which is narrower than the service schema and can be
   stated exactly.
3. **Services worked out in (A) never reach the mediator.** `toggle`, a fan's `increase_speed` and
   `decrease_speed`, and a cover's `toggle_tilt` are implemented by Home Assistant's base classes in
   terms of the other methods (e.g. `toggle` calls `turn_on` or `turn_off` from the published state).
   They arrive as one of the listed services, as `select_next` and `increment` already do
   (`COMMANDS`' comment in `mediator.py`). They are not "left out"; they need no entry.

**Shape, not meaning**, as before: ranges, option membership and codes are checked by (A) before the
call and again by the sandbox's instance; the mediator checks that what crosses has exactly the
expected keys, each of the expected kind. Where Home Assistant fixes a value to a small set
(`flash`: short or long), the mediator checks the set, as it does for HVAC modes.

**One change to the rule's form.** Until now each service lists its allowed shapes exactly. A light's
`turn_on` carries any subset of eleven optional fields; listing every combination is not practical.
B1 adds **optional keys** to a shape: the data must contain only listed keys, each of its kind, and
every required key. Required keys are none for the four kinds here except where marked.

## What reaches the entity, per kind (sources)

**light** (`components/light/__init__.py`)
- Schema: `LIGHT_TURN_ON_SCHEMA` (l. 183): profile, transition, brightness, brightness_pct,
  brightness_step, brightness_step_pct, color_name, color_temp_kelvin, hs_color, rgb_color,
  rgbw_color, rgbww_color, xy_color, white, flash, effect. `LIGHT_TURN_OFF_SCHEMA` (l. 218):
  transition, flash.
- Before the entity: `preprocess_turn_on_alternatives` (l. 232) turns `profile` and `color_name`
  into colour values and `brightness_pct` into `brightness`; `process_turn_on_params` (l. 321)
  resolves the brightness steps into `brightness`, converts a colour into one the light supports,
  and turns `white: true` into the light's brightness; `filter_turn_on_params` (l. 287) drops
  `effect`, `flash`, `transition` and every colour the light's published features and colour modes
  do not support. `turn_off` keeps only `transition` and `flash` (`filter_turn_off_params`, l. 258).
- `toggle`: `LightEntity.async_toggle` (l. 1113) runs the same processing and filtering, then
  `turn_on` or `turn_off`. A `turn_on` with brightness 0 becomes `turn_off` (l. 509).
- **So the entity receives**: `turn_on` with any of brightness, color_temp_kelvin, hs_color,
  rgb_color, rgbw_color, rgbww_color, xy_color, white, effect, flash, transition; `turn_off` with
  any of transition, flash.

**fan** (`components/fan/__init__.py`, `async_setup`)
- Services: turn_on {percentage, preset_mode}, turn_off, toggle, increase_speed and decrease_speed
  {percentage_step}, oscillate {oscillating}, set_direction {direction}, set_percentage {percentage},
  set_preset_mode {preset_mode}.
- Before the entity: a preset mode is checked against the fan's published `preset_modes`
  (`async_handle_turn_on_service`, l. 306; `async_handle_set_preset_mode_service`, l. 264).
  `increase_speed`/`decrease_speed` compute a new percentage from the published one and the speed
  count and call `async_set_percentage` (`_async_adjust_speed`, l. 238–257). `toggle` is
  `ToggleEntity.async_toggle` (`helpers/entity.py` l. 1779): `turn_on()` or `turn_off()`.
- `set_direction`'s field is optional in the schema, but `async_set_direction(direction)` (l. 291)
  requires it: a call without it fails in (A) and nothing is sent.
- **So the entity receives**: `turn_on` with percentage and/or preset_mode, or neither; `turn_off`;
  `set_percentage`; `set_preset_mode`; `oscillate`; `set_direction`.

**cover** (`components/cover/__init__.py`, l. 102–169)
- Services: open_cover, close_cover, stop_cover, set_cover_position {position}, open_cover_tilt,
  close_cover_tilt, stop_cover_tilt, set_cover_tilt_position {tilt_position}, toggle, toggle_tilt.
- `toggle` (l. 340) picks open, close or stop from the published state; `toggle_tilt` (l. 409) picks
  open or close tilt from the published tilt position.
- **So the entity receives** the eight services other than the two toggles, with only `position` or
  `tilt_position` as data.

**lock** (`components/lock/__init__.py`)
- Services: lock, unlock, open, each with an optional `code` (`LOCK_SERVICE_SCHEMA`, l. 44: any
  string, no length limit). `open` only for a lock that publishes the OPEN feature (l. 77).
- Before the entity: `add_default_code` (l. 133) takes the user's code, or **(A)'s default code for
  that lock** if the user gave none, checks it against the lock's published `code_format`, and passes
  it on only if it is not empty. A stored default code is used only if the lock publishes a
  `code_format` it matches (`_async_read_entity_options`, l. 300–313); with no format it is ignored.
- **So the entity receives**: `lock`, `unlock`, `open`, each with no data or with `code`.

## The proposed rule

| Kind | Service | Data (keys optional unless marked *required*) |
|---|---|---|
| light | `turn_on` | brightness: number; color_temp_kelvin: number; hs_color: 2 numbers; rgb_color: 3 numbers; rgbw_color: 4; rgbww_color: 5; xy_color: 2; white: number or empty (`null`); effect: string ≤ 255; flash: `short` or `long`; transition: number |
| light | `turn_off` | transition: number; flash: `short` or `long` |
| fan | `turn_on` | percentage: number; preset_mode: string ≤ 255 |
| fan | `turn_off` | none |
| fan | `set_percentage` | percentage: number, *required* |
| fan | `set_preset_mode` | preset_mode: string ≤ 255, *required* |
| fan | `oscillate` | oscillating: true or false, *required* |
| fan | `set_direction` | direction: string ≤ 255, *required* |
| cover | `open_cover`, `close_cover`, `stop_cover`, `open_cover_tilt`, `close_cover_tilt`, `stop_cover_tilt` | none |
| cover | `set_cover_position` | position: number, *required* |
| cover | `set_cover_tilt_position` | tilt_position: number, *required* |
| lock | `lock`, `unlock`, `open` | code: string ≤ 64 (as the alarm panel's) |

"Number" is the existing `_number`: an int or float, finite, not a boolean. A colour is a JSON list of
exactly that many numbers (Home Assistant's tuples arrive as lists). Everything else is refused under
`COMMAND_DATA` or `COMMAND_SERVICES` and recorded by kind, as today.

**A lock code is never written to the log**, allowed or refused (`WITHHELD` already covers `code`).

## Decided (Younes, 2026-10-31)

1. **Bounds kept: strings ≤ 255, codes ≤ 64.** Their purpose is to bound the log, not to stop
   injection: an allowed command's data is recorded as sent, so without a bound anything in (A) that
   can call the service could write arbitrarily large records. 255 is Home Assistant's limit on a
   state (already used in step 2); 64 for codes is a judgement made in step 3, not derived, and is
   reported as such.
2. **(A)'s default lock code reaches the integration: accepted and stated.** A code stored as the
   lock's default in (A) is added by (A) to a command that had none, and the mediator cannot tell it
   from a typed one. The integration receives it, as it would unconfined; it is never logged.
3. **`white` may be empty.** `white: true` becomes the light's brightness in (A) (l. 474–476), which
   is `None` when (A) does not know it. Refusing it would make the confined light fail where the
   unconfined one would not, for no security gain; `null` carries nothing.

**What stops injection, stated for the report.** The mediator stops a command from being redirected
(owner check; the sandbox writes the entity id last), widened (listed services only) or smuggling
parameters (exact keys, each of its kind); Home Assistant validates values in (A) and again in the
sandbox. Nothing checks the *content* of an allowed string: if an integration misuses one, the
damage is contained by confinement (declared hosts only, no house access beyond its own entities,
the system-call filter), and only someone who can already operate devices in (A) can send it. The
claim is containment, not prevention.

## Predictions

**Offline, `selftest_commands`** (laptop and Pi), new cases:

| | Prediction |
|---|---|
| K12 | Each listed shape is allowed under `AMBIENT` and pushed exactly: light turn_on with no data, with brightness alone, with brightness + rgb_color + transition, with each colour form alone, with `white` as a number and as `null`, with effect, with flash; light turn_off with transition; fan turn_on with none, percentage, preset_mode, both; set_percentage; set_preset_mode; oscillate true; set_direction reverse; cover's six no-data services; set_cover_position; set_cover_tilt_position; lock, unlock, open with and without a code |
| K13 | Refused under `COMMAND_DATA`, nothing pushed: light turn_on with `profile`, `color_name`, `brightness_pct` or `brightness_step` (never reach the entity); rgb_color of 2 or 4 numbers; a string in a colour; flash `medium`; NaN brightness; a 256-character effect; an extra `entity_id`; fan set_percentage with none; oscillate `"yes"`; cover set_cover_position with a string; lock with a numeric code; lock with a 65-character code |
| K14 | Refused under `COMMAND_SERVICES`: light `toggle`; fan `increase_speed`; cover `toggle_tilt`; lock `turn_on`; light `set_percentage` |
| K15 | **No lock code in the durable log**: after an allowed unlock with `"5820"` and a refused one with a 65-character code, neither string is in the log file; both records say `(withheld)` |
| K16 | **Fails first:** before the change, K12's 39 cases, K13's 19 and K15's allowed case fail (the kinds are not listed; K13's are refused, but under `COMMAND_SERVICES`). K14's 8 and K15's two log checks already pass (nothing is forwarded), and must still pass after. Run on the laptop before this note was committed: **67/126** (the 57 earlier checks, K14's 8, K15's 2) |
| K17 | Every earlier `selftest_commands` check still passes |

**Against (A), `selftest_bridge_types`** (Pi, fresh clone, (A) `down`, `up --fresh`), with a test
integration publishing one entity of each kind:

| | Prediction |
|---|---|
| T11 | A published light, fan, cover and lock each become a registry row of their domain owned by the bridge; (A) holds the state and the attributes Home Assistant needs to draw each (light: colour modes, brightness, colour; fan: percentage, speed count, preset modes, oscillating, direction; cover: position, tilt, opening/closing; lock: code format) |
| T12 | From a user in (A): `light.turn_on` with brightness_pct 50 reaches the sandbox as `{"brightness": 128}` (the conversion done in (A)); with `color_name: red` on an RGB light as `{"rgb_color": [255, 0, 0]}`; `light.toggle` on a light published on reaches it as `turn_off` with `{}`; `fan.increase_speed` from 50 % on a 4-speed fan as `set_percentage` `{"percentage": 75}`; `cover.toggle` on a closed cover as `open_cover`; `lock.unlock` with code 5820 as `{"code": "5820"}`; each call succeeds and (A) shows the new state |
| T13 | `fan.set_preset_mode` with a mode the fan does not publish fails in (A), and no command decision is recorded (checked before the bridge, as T4″ for numbers) |
| T14 | The run's durable log contains neither `5820` (typed) nor `5821` (stored, T16) |
| T16 | **Decision 2, tested**: with `5821` stored as the lock's default code in (A) (entity registry options), `lock.lock` with no code reaches the sandbox as `{"code": "5821"}`; the call succeeds and (A) shows locked |
| T15 | Every suite passes with (A) up (`suites_all.sh`) |
| T5 | Changed: the unsupported kind refused at publish is now a vacuum (a light until B1) |

**Fails first for T11–T14 and T16**: run on the Pi against `bridge-b1-pre`, they fail (the bridge
does not publish these kinds). The changed T5 passes before and after: the old bridge refuses every
kind outside its eleven. Outcome appended below after the runs.

**Not tested here.** None of the fifteen end-to-end integrations is known to publish one of these
kinds in its runs (`midea_ac_lan` ships light, fan and lock platforms, but its run published a
climate only). The real-integration check comes in B5's rerun.
