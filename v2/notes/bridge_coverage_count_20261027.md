# Which kinds of device the bridge still cannot show — careful count (2026-10-27)

Asked by Younes while reading interim §7.2: "we need an account of how many devices are still missing".
**To tackle later (Younes, 2026-10-27):** extending the bridge to the kinds below, and the `dwd_weather`
camera check. Not started; the interim states the limit (§7.2, §8.3).

## Method

Each of the 37 head-weighted integrations' files was listed at the commit actually measured
(`experiments/compat/results/hacs_corpus_manifest.json`, the entry with a commit; for `scheduler`,
`govee`, `solarman` that is the copy on disk), through the GitHub trees API. A kind counts when its
platform file exists (`<kind>.py` in the integration directory), against `PLATFORM_NAMES` in
`framework/confine/sandbox_runtime.py` — the harness's own rule. For the 32 integrations whose lists
the harness recorded (`experiments/compat/results/f65_20261025/post/compat_egress.json`, arm A) the
lists are identical; the other 5 (`bambu_lab`, `bermuda`, `hacs`, `spook`, `tapo_control`) failed to
import before that step and come from the fetch only. A platform file is a kind the integration *can*
provide; how many devices a household sees depends on what it owns.

Bridged (11): sensor, binary_sensor, switch, button, text, select, number, climate,
alarm_control_panel, calendar, weather.

## Result

- **12 of 37 provide only bridged kinds:** adaptive_lighting, battery_notes, llmvision, nordpool,
  pirateweather, powercalc, scheduler, solarman, solcast_solar, thermal_comfort,
  waste_collection_schedule, watchman.
- **25 also provide at least one of 18 unbridged kinds.** Kind uses: 249, bridged 155 (62%).
  (The 2026-10-25 rough count, 11/37 and 156 of 257, double-counted `button`, which appears twice in
  `PLATFORM_NAMES`, and was off by one on the integrations; AI-use log row 30.)

| Kind | Integrations |
|---|---|
| light | 13: alexa_media, bambu_lab, browser_mod, govee, homematicip_local, localtuya, meross_lan, midea_ac_lan, smartthinq_sensors, sonoff, tapo_control, xiaomi_home, xiaomi_miot |
| fan | 9: bambu_lab, govee, localtuya, meross_lan, midea_ac_lan, smartthinq_sensors, sonoff, xiaomi_home, xiaomi_miot |
| camera | 8: bambu_lab, browser_mod, dreame_vacuum, dwd_weather, eufy_security, frigate, tapo_control, xiaomi_miot |
| media_player | 7: alexa_media, browser_mod, meross_lan, sonoff, webrtc, xiaomi_home, xiaomi_miot |
| update | 6: bambu_lab, frigate, hacs, homematicip_local, meross_lan, tapo_control |
| cover | 6: homematicip_local, localtuya, meross_lan, sonoff, xiaomi_home, xiaomi_miot |
| event | 6: alarmo, govee, homematicip_local, octopus_energy, spook, xiaomi_home |
| time | 6: meross_lan, midea_ac_lan, nodered, octopus_energy, spook, xiaomi_miot |
| water_heater | 5: midea_ac_lan, octopus_energy, smartthinq_sensors, xiaomi_home, xiaomi_miot |
| humidifier | 5: govee, midea_ac_lan, smartthinq_sensors, xiaomi_home, xiaomi_miot |
| device_tracker | 5: bermuda, ble_monitor, eufy_security, xiaomi_home, xiaomi_miot |
| vacuum | 4: dreame_vacuum, localtuya, xiaomi_home, xiaomi_miot |
| notify | 3: alexa_media, homematicip_local, xiaomi_home |
| image | 3: bambu_lab, eufy_security, frigate |
| lock | 3: eufy_security, homematicip_local, midea_ac_lan |
| remote | 2: sonoff, xiaomi_miot |
| siren | 2: homematicip_local, tapo_control |
| valve | 1: homematicip_local |

Missing kinds per integration: 1 kind — hacs (update), webrtc (media_player), alarmo (event), nodered
(time), dwd_weather (camera), bermuda and ble_monitor (device_tracker); 2 — spook, dreame_vacuum;
3 — alexa_media, frigate, browser_mod, octopus_energy; 4 — localtuya, tapo_control, govee,
smartthinq_sensors, eufy_security; 5 — sonoff, bambu_lab; 6 — meross_lan, midea_ac_lan;
8 — homematicip_local; 10 — xiaomi_home; 11 — xiaomi_miot.

Order that completes the most integrations per kind added (greedy): device_tracker → 14 of 37,
camera 15, media_player 16, light 17, update 18, event 19, time 21, water_heater 22, vacuum 23,
notify 24, image 25, fan 26, cover 28, humidifier 31, lock 33, remote 35, siren 36, valve 37.
By integrations touched, light (13) and fan (9) matter most.

## Open, for later

1. **Extend the bridge** to the commonest unbridged kinds (light, fan, cover, lock first; camera and
   media player need a stream/image path, a bigger design), each with a prediction, a fails-first test
   and a command rule as in steps 1–5 (`bridge_types_step*_prediction_20261025.md`).
2. **`dwd_weather` ships `camera.py`** (a radar image) and is one of the fifteen run end to end. The
   real-house run (`experiments/real_platform/results/bridge_types_20261025/s5c/`) showed no refused
   publication, so the camera was probably not created with the options used — not confirmed. Interim
   §7.2 says every device the fifteen published appeared in (A); confirm before the final report.
3. Final report: carry the 12 / 25 / 18 kinds account (F64's write-up).
