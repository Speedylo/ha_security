# Bridge extension, step 3: climate and alarm panel — prediction (2026-10-25)

**Committed before any code.** Younes approved the command list on 2026-10-25 ("the list is fine,
include alarm_trigger"). Subjects in the end-to-end set: `midea_ac_lan` (climate) and `alarmo`
(alarm panel).

## What changes

**The bridge** gains a climate and an alarm-panel platform. A climate's state is its HVAC mode; its
attributes give the modes, the temperature range and step, the current and target temperatures
(one target, or a low and a high), the fan, preset and swing modes, humidity, the action and the
supported features. An alarm panel's state is the alarm state; its attributes give the code format,
whether arming needs a code, and the supported features. **The temperature unit is °C**, because the
sandbox's instance is always metric (`sandbox_runtime.py`, `hass.config.units = METRIC_SYSTEM`):
a house in °F shows and accepts °F, and Home Assistant converts to the entity's °C before the bridge
sends the command.

**The mediator** forwards, in addition to step 2's list:

| Type | Command | Data, exactly one of these shapes |
|---|---|---|
| climate | `turn_on`, `turn_off` | none |
| climate | `set_hvac_mode` | `hvac_mode` ∈ {off, heat, cool, heat_cool, auto, dry, fan_only} |
| climate | `set_temperature` | `temperature`; or `target_temp_low` + `target_temp_high`; either may add `hvac_mode` as above. Temperatures finite numbers |
| climate | `set_fan_mode` / `set_preset_mode` / `set_swing_mode` / `set_swing_horizontal_mode` | `fan_mode` / `preset_mode` / `swing_mode` / `swing_horizontal_mode`: a string ≤ 255 |
| climate | `set_humidity` | `humidity`: a finite number |
| alarm_control_panel | `alarm_disarm`, `alarm_arm_home`, `alarm_arm_away`, `alarm_arm_night`, `alarm_arm_vacation`, `alarm_arm_custom_bypass`, `alarm_trigger` | none; or `code`: a string ≤ 64 |

Step 2's rule becomes a list of allowed shapes per service; data must match one shape exactly (same
keys, each value of its kind). **An alarm code is never written to the durable log**, allowed or
refused: the record holds `"code": "(withheld)"`. And **a refused command's data, whatever the
reason, is recorded by kind** (type and length), not only when refused for its data: written first,
the K9 check showed that step 2 records verbatim the data of a command refused for its *service*, so
a code sent with a wrong service would have reached the log. Only an allowed command's data is
recorded as sent (codes still withheld). Ranges, option membership and whether the code is
correct are checked by (A) and by the integration, not by the mediator (as in step 2).

## Predictions

**Offline, `selftest_commands`** (laptop and Pi), new cases:

| | Prediction |
|---|---|
| K6 | Each new shape is allowed under `AMBIENT` and pushed exactly: climate turn_on; set_hvac_mode cool; set_temperature {temperature}; {temperature, hvac_mode}; {low, high}; set_fan_mode; set_preset_mode; set_swing_mode; set_humidity; alarm disarm with code; arm_away with no code; arm_home, arm_night, arm_vacation, arm_custom_bypass, trigger |
| K7 | Refused under `COMMAND_DATA`, nothing pushed: hvac_mode "plasma"; set_temperature with temperature **and** low/high; low without high; a string temperature; NaN; an extra key on set_fan_mode; a numeric code; a 65-character code; disarm with an extra `entity_id` |
| K8 | Refused under `COMMAND_SERVICES`: climate `alarm_disarm`; alarm panel `set_temperature`; alarm panel `turn_on`. A command refused for its service with data `{"note": "secret-note"}` is recorded by kind: `secret-note` is not in the log |
| K9 | **No code in the durable log**: after an allowed disarm with code `"4917"` and a refused one with a 65-character code, neither string appears in the log file, and both records say `(withheld)` |
| K10 | **Fails first:** before the change, K6's and K7's climate/alarm cases fail, K8's record check and K9 fail (the data is in the record). Run on the laptop before this note was committed: 27/56 before the K8 record check was added |
| K11 | Step 2's 24 checks still pass |

**Against (A), `selftest_bridge_types`** (Pi, fresh clone, (A) `down`, `up --fresh`):

| | Prediction |
|---|---|
| T6 | A published climate and alarm panel each become a registry row of their domain owned by the bridge; (A) holds the climate's HVAC mode, `hvac_modes`, `min_temp`/`max_temp`, `current_temperature`, `temperature`, `fan_modes`, and the panel's alarm state and `code_format` |
| T7′ | From a user in (A): `climate.set_temperature` 23 reaches the sandbox as `{"temperature": 23.0}`; `set_hvac_mode` cool as `{"hvac_mode": "cool"}`; `alarm_arm_away` with code 4917 as `{"code": "4917"}`; `alarm_trigger` as `{}`; each call succeeds once the sandbox answers and republishes, and (A) shows the new state |
| T8 | **Unit**: with (A) switched to US customary units, `set_temperature` 73.4 °F reaches the sandbox as 23.0 °C (to 0.01); (A) is switched back to metric afterwards |
| T9 | The durable log of the run does not contain `4917` |
| T10 | Every suite passes with (A) up (`suites_all.sh`), the corrected button check of step 2 included: it is verified here, run twice against the same (A) (alone, then inside the suites) |

**Fails first for T6–T9**: run on the Pi against the pre-change commit, they fail (the bridge refuses
both domains). Outcome appended below.
