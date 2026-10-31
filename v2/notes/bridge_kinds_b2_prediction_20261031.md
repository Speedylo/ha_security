# Bridge extension, batch B2: humidifier, water heater, vacuum, valve, siren, remote — prediction (2026-10-31)

**Committed before any code.** Younes accepted the list and all five recommendations on 2026-10-31 ("accept all recommendations, go ahead"). Same method as B1
(`bridge_kinds_b1_prediction_20261031.md`): the list is derived from Home Assistant 2026.8.3
(`~/ha-src/core`), written against **what each entity's method receives in (A)**, and services
(A) works out itself (`toggle`, ...) need no entry. Shape, not meaning; strings ≤ 255 unless a
decision below says otherwise; refused data recorded by kind.

**Tests touched by this batch, searched first (AI-use log 32):** only `selftest_bridge_types` T5 and
`selftest_real_platform`'s refused-publish probe use one of these kinds (a vacuum). Both move to a
`todo` list, a kind none of the 37 integrations provides and the bridge will not stand in for.

## What reaches the entity, per kind (sources, `components/<kind>/`)

**humidifier** (`__init__.py` l. 95–112)
- turn_on, turn_off, toggle (no data); set_mode {mode: string}; set_humidity {humidity: 0–100}.
- (A) checks the humidity against the published min/max (`async_service_humidity_set`, l. 295) and
  works out `toggle`. The mode is not checked in (A); the integration checks it.
- **Entity receives**: turn_on, turn_off (no data); set_mode {mode}; set_humidity {humidity}.

**water_heater** (`__init__.py` l. 79–123, 346–436)
- turn_on, turn_off; set_temperature {temperature, operation_mode optional}; set_operation_mode
  {operation_mode}; set_away_mode {away_mode: boolean}.
- (A) converts the temperature to the entity's unit (°C, as the bridged climate), checks an operation
  mode against the published list (`async_handle_set_operation_mode`, l. 346; not on the
  set_temperature path), and turns set_away_mode into `async_turn_away_mode_on`/`_off` (l. 411).
- **Forwarded as**: turn_on, turn_off; set_temperature {temperature, operation_mode?};
  set_operation_mode {operation_mode}; set_away_mode {away_mode: true or false} (the service the
  sandbox then runs).

**vacuum** (`__init__.py` l. 97–155, 446–514, 583–618)
- start, pause, stop, return_to_base, clean_spot, locate (no data); set_fan_speed {fan_speed};
  send_command {command: string, params: a mapping or a list, optional}; clean_area {cleaning_area_id}.
- `clean_area` is worked out from (A)'s own area mapping, stored in (A)'s registry for the entity,
  into the integration's segment ids, and calls `async_clean_segments` — a method with no service the
  sandbox could run. See decision 4.
- **Entity receives**: the six no-data services; set_fan_speed {fan_speed}; send_command {command,
  params?}.

**valve** (`__init__.py` l. 63–94; `entity.py` l. 132–184)
- open_valve, close_valve, stop_valve, toggle (no data); set_valve_position {position: 0–100}.
- (A) turns open/close of a valve that reports a position into set_valve_position 100/0, and works
  out `toggle` from the published state.
- **Entity receives**: open_valve, close_valve, stop_valve; set_valve_position {position}.

**siren** (`__init__.py` l. 54–122)
- turn_on {tone: integer or string, duration: positive integer, volume_level: 0–1, each optional};
  turn_off; toggle.
- (A) drops what the siren does not support and checks the tone against the published
  `available_tones`; when that is a mapping, (A) replaces a tone *name* with its *key*
  (`process_turn_on_params`, l. 54). See decision 5.
- **Entity receives**: turn_on {tone?, duration?, volume_level?}; turn_off.

**remote** (`__init__.py` l. 57–133, 199–220)
- turn_on, turn_off, toggle {activity optional}; send_command {command: list of strings, device?,
  num_repeats (default 1), delay_secs?, hold_secs (default 0)}; learn_command {device?, command?
  list, command_type?, alternative?, timeout?}; delete_command {command list, device?}.
- (A) adds the defaults (`num_repeats` 1, `hold_secs` 0) before the entity sees the call.
- **Entity receives**: all but toggle, as listed.

## Proposed rule

| Kind | Service | Data (optional unless *required*) |
|---|---|---|
| humidifier | `turn_on`, `turn_off` | none |
| humidifier | `set_mode` | mode: string, *required* |
| humidifier | `set_humidity` | humidity: number, *required* |
| water_heater | `turn_on`, `turn_off` | none |
| water_heater | `set_temperature` | temperature: number, *required*; operation_mode: string |
| water_heater | `set_operation_mode` | operation_mode: string, *required* |
| water_heater | `set_away_mode` | away_mode: true or false, *required* |
| vacuum | `start`, `pause`, `stop`, `return_to_base`, `clean_spot`, `locate` | none |
| vacuum | `set_fan_speed` | fan_speed: string, *required* |
| vacuum | `send_command` | command: string, *required*; params: a mapping or a list, plain JSON, at most 4 KiB serialised (decision 1) |
| valve | `open_valve`, `close_valve`, `stop_valve` | none |
| valve | `set_valve_position` | position: number, *required* |
| siren | `turn_on` | tone: integer or string ≤ 255 (sent by name when the tones are a mapping, decision 5); duration: number; volume_level: number |
| siren | `turn_off` | none |
| remote | `turn_on`, `turn_off` | activity: string |
| remote | `send_command` | command: 1–64 strings of at most 4096 characters, *required* (decision 2); device: string; num_repeats: number; delay_secs: number; hold_secs: number |
| remote | `learn_command` | device: string; command: list of strings; command_type: string; alternative: true or false; timeout: number; command as for send_command (decision 3) |
| remote | `delete_command` | command: as for send_command, *required*; device: string (decision 3) |

## Decisions (Younes, 2026-10-31: every recommendation accepted)

1. **A vacuum's `send_command` carries free-form `params`** (any mapping or list; Home Assistant
   does not define its contents — it is the integration's raw device command). The exact-shape rule
   cannot check it. Options: (a) forward it as plain JSON data (no objects, NaN or infinity),
   **at most 4 KiB** serialised, contents unchecked — like any allowed string, and contained the same
   way; (b) refuse `send_command`, so raw vacuum commands work only unconfined.
   *Recommended: (a)*: it reaches only the integration's own device, which is what it is for.
2. **A remote's command strings can be raw codes** (some integrations accept an encoded IR code as
   the command), which can be longer than 255 characters; not measured. Options: (a) **4096
   characters per command, at most 64 commands** per call; (b) keep 255. *Recommended: (a)*, since
   255 could break raw codes; the bound still protects the log.
3. **`learn_command` and `delete_command`** change the integration's own stored codes (learning puts
   the device into learning mode). They act only on the integration's own data and device, like any
   command. Forward them? *Recommended: yes.*
4. **A vacuum's `clean_area`** needs (A)'s mapping from its rooms to the integration's segments, and
   then a call no service in the sandbox takes. Supporting it means a new path (a "clean these
   segments" question to the sandbox) — new design, as for B4. *Recommended: state it as a limit*:
   the vacuum cleans, docks, spot-cleans and takes raw commands, but cleaning by room from (A) does
   not work confined.
5. **Siren tones named by a mapping with numeric keys** (e.g. `{1: "fire", 2: "burglar"}`) arrive in
   (A) with string keys (`"1"`), because attributes cross as JSON. (A) would then send `"1"`, which
   the integration's own instance rejects. *Recommended: the bridged siren sends the tone's name
   (the mapping's value), which the integration's instance maps back to its own key*; for a list of
   tones it sends the tone as received.

## Predictions

**Offline, `selftest_commands`** (laptop and Pi), new cases:

| | Prediction |
|---|---|
| K18 | Each listed shape is allowed under `AMBIENT` and pushed exactly, for all six kinds (including a vacuum send_command with a mapping and with a list as params, and a remote send_command with a 1000-character command, if decisions 1–2 are (a)) |
| K19 | Refused under `COMMAND_DATA`, nothing pushed: humidity as a string; set_mode with no mode; set_temperature with no temperature; away_mode `"yes"`; set_fan_speed with a list; send_command params of 5 KiB; params holding NaN; set_valve_position with a string; siren volume_level as a string; remote send_command with a string instead of a list; a list with a number in it; 65 commands; a 4097-character command; an extra `entity_id` on each kind |
| K20 | Refused under `COMMAND_SERVICES`: humidifier `toggle`; valve `toggle`; siren `toggle`; remote `toggle`; vacuum `clean_area`; vacuum `turn_on` |
| K21 | **Fails first**: before the change, K18's 35 and K19's 23 fail (the kinds are not listed; K19's are refused, but under `COMMAND_SERVICES`); K20's 7 pass already. Run on the laptop before this note was committed: **133/191** (the 126 earlier checks and K20) |
| K22 | Every earlier check still passes |

**Against (A), `selftest_bridge_types`** (Pi, fresh clone, (A) `down`, `up --fresh`):

| | Prediction |
|---|---|
| T17 | One entity of each kind becomes a registry row of its domain owned by the bridge; (A) holds its state and the attributes that describe it (humidity range and modes; operation list and temperature; fan speeds; valve position; available tones; activity list) |
| T18 | From a user in (A), the sandbox receives what (A) worked out: `humidifier.set_humidity` 45 as `{"humidity": 45}`; `water_heater.set_temperature` 122 °F (house in US units) as about 50 °C; `water_heater.set_away_mode` true as `set_away_mode {"away_mode": true}`; `valve.open_valve` on a valve with a position as `set_valve_position {"position": 100}`; `siren.turn_on` with tone `"fire"` on a siren whose tones are `{"1": "fire", "2": "burglar"}` as `{"tone": "fire"}`; `vacuum.start` as `start {}`; `remote.send_command` ["power"] as `{"command": ["power"], "num_repeats": 1, "hold_secs": 0}` (`delay_secs` has no default in the schema, so (A) adds none). Each call succeeds and (A) shows the new state |
| T19 | `humidifier.set_humidity` 95 on a humidifier published with max 80 fails in (A), and no command decision is recorded |
| T20 | The refused-publish probes (T5 here, and `selftest_real_platform`'s) now use a `todo` list, refused |
| T21 | Every suite passes with (A) up |

**`set_temperature` reaches the entity with the whole service data** (`async_service_temperature_set`
iterates `service.data`, l. 428), so the bridged water heater forwards only `temperature` and
`operation_mode`, as the bridged climate does; T18's °F case checks that nothing else arrives.

**Fails first for T17–T19**: run on the Pi against `bridge-b2-pre`, they fail (the bridge refuses
these kinds). Outcome appended after the runs.

**Not tested here**: no real integration publishes these kinds in the end-to-end set; that is B5.

---

## Outcome (appended 2026-10-31, after the runs)

Pi, fresh clones of `bridge-b2-pre` (`5ace7d4`) and `bridge-b2` (`d0e5af1`), clean before and after,
14:33–14:40; (A) `down` and `up --fresh` before each arm. Results:
`experiments/real_platform/results/bridge_kinds_20261031/b2/`. **Every prediction held.**

| | Outcome |
|---|---|
| K21 | Held: before, `selftest_commands` 133/191 (laptop and Pi) |
| K18–K20, K22 | Held: 191/191 after (laptop and Pi) |
| Fails first, T | Held: `selftest_bridge_types` 89/115 against (A) with the old bridge; the 26 failures are T17 (12), T18 (13, the °F case included) and T19's first check, all because (A) refused the six kinds. T19's second check and T20 passed before, as expected |
| T17 | Held: a humidifier, water heater, vacuum, valve, siren and remote, each a registry row of its domain owned by the bridge, with its state and the attributes that describe it |
| T18 | Held: `set_humidity` 45 reached the sandbox as `{"humidity": 45}`; `set_away_mode` true as `set_away_mode {"away_mode": true}`; `open_valve` on a valve with a position as `set_valve_position {"position": 100}`; a siren tone `"fire"` from tones `{"1": "fire", "2": "burglar"}` as `{"tone": "fire"}` (by name, decision 5); `vacuum.start` as `start {}`; `remote.send_command` "power" as `{"command": ["power"], "num_repeats": 1, "hold_secs": 0}`; with (A) in US units, 122 °F as 50 °C and nothing else in the data. Each call succeeded and (A) showed the new state; (A) back in metric afterwards |
| T19 | Held: `set_humidity` 95 (published 30–80) failed in (A), and no command decision was recorded |
| T20 | Held: a to-do list is refused at publish, here and in `selftest_real_platform` (55/55) |
| T21 | Held: **34 of 34 suites**; `selftest_bridge_types` 115/115 alone and inside the suites |

(A)'s log: no error from the bridge.

**Recorded, for the report:** an allowed command's data is logged as sent, so the largest remote
command the rule allows (64 × 4096 characters) makes a record of about 256 KiB. The bound still
caps every record; it is a looser cap than the 255-character strings elsewhere.
