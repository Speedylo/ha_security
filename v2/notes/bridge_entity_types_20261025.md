# The bridge stands in for three entity types only (found 2026-10-25) — REMEDIATED 2026-10-25

**Status (2026-10-25, end of day): remediated in five steps, each with its own prediction note.** The bridge now
stands in for 11 types: sensor, binary_sensor, switch, button, text, select, number, climate,
alarm_control_panel, calendar, weather. Notes: `bridge_types_step1..5_prediction_20261025.md`.
- Step 1 display of button/text/select/number; step 2 the mediator's command rule per type (exact data,
  injection-checked, refused data logged by kind); step 3 climate and alarm panel (codes never logged);
  step 4 questions with answers (calendar events, weather forecasts; answers shape-checked, logged by shape);
  step 5 the fifteen end to end against the real (A): E2 37/38, the miss `scheduler`'s `triggered` switch.
- Findings on the way: F66 (unknown numeric state), F67 (timestamp/date sensors), F69 (house_a zombie,
  harness), all fixed; F68 (designate_mediator check not awaited) open.
- Still not bridged (future work): camera, image, media_player, vacuum, notify, remote, fan, cover, lock,
  light, water_heater, humidifier, siren, valve, update, event, time, date, datetime, device_tracker, scene.
  Coverage of the 37 head integrations by platform file name (rough): **11 of 37** provide only bridged
  types (5 of 37 before), and 156 of their 257 type uses are bridged (75 before). Lights, covers, fans and
  locks would add most next (20 of 37 with them); the media tier is needed for all 37.


**Status: open, to be remediated (Younes, 2026-10-25).** For now (option 1) the limit is stated in
the reports and the extra end-to-end runs record, for each integration, which of its entity types
the bridge supports. The fix — extending the bridge — comes later, with its own prediction and tests.

## What

`framework/ha_bridge/confine_bridge/const.py`: `SUPPORTED = ("sensor", "binary_sensor", "switch")`.
`ws_publish` (`__init__.py:223`) refuses any other domain: *"the bridge cannot stand in for a {domain}
entity"*. So a confined integration's light, climate, alarm panel, weather, calendar, cover, lock,
camera, media player, select, number, button… cannot appear in the household's Home Assistant.

## Why no run saw it

Every end-to-end run publishes to the harness's stand-in for the house (`platform.Platform`), which
accepts any domain. `experiments/end_to_end/README.md` says so: "What crossed the boundary is real;
what a live Home Assistant would do with it is not tested." The import-level compatibility runs never
publish to (A) at all. Neither report states the limit.

## How much it matters

From the platform files each of the 37 head-corpus integrations ships (a file-name count, rough):
**5 of 37** provide only sensor / binary_sensor / switch entities (`adaptive_lighting`, `nordpool`,
`scheduler`, `solarman`, `thermal_comfort`); **32 of 37** provide at least one other type. Of the 13
run end to end, at least `midea_ac_lan` (climate), `pirateweather` and `dwd_weather` (weather) publish a
refused type; `waste_collection_schedule`'s calendar and `alarmo`'s alarm panel would be refused too.

What still holds: everything measured inside the sandbox (imports, setup, the 13 working against the
stand-in, security, cost). What does not yet hold: that a household would *see* most confined
integrations' devices.

## Remediation, when it is done

- Extend `SUPPORTED` and the bridge's platforms to the entity types the corpus uses, starting with the
  commonest (the count above gives the order), each with a test that fails first.
- Commands back to the integration (`call_service` → handler in (B)) exist for switches; each new type
  needs its own command path (e.g. `alarm_arm_away`, `climate.set_temperature`).
- Then re-run the end-to-end set against the real house (A) through the bridge, not the stand-in.

## Reports

- Interim §7.2's closing sentence ("an integration that works in a household's installation today was
  not found to stop working when confined") overclaimed; corrected 2026-10-25 (AI-use log 21). §8.3
  states the limit.
- Final report: record as finding F64 (Table 12.3's note, §9.8, §14) when it is rebuilt.
