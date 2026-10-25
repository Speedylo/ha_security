# The "26 of 37 need a credential" survey, broken down (2026-10-25)

Asked by Younes during his review of interim §5: of the head-weighted integrations not run end to end,
which need only an account anyone can open, and which need something he cannot get (a device, being a
customer).

**Method.** Head corpus rebuilt from the pinned commits into the scratchpad
(`figures/fetch_hacs_corpus.py --rebuild experiments/compat/results/hacs_corpus_manifest.json`, 37
directories). `verify/recompute.py` A1.13b's regex reproduces **26 of 37** exactly. Each of the 26 was then
checked by reading its `config_flow.py` setup step; what a product needs to be useful (a device, a customer
account) is from the integration's own description and general knowledge of the product, **not verified
further** — Younes to check.

## Finding: the regex overcounts

The scan matches any credential-like word anywhere in an integration's Python files, not what its setup asks.
Read directly:

| Integration | Regex hit | What setup actually asks |
|---|---|---|
| `alarmo` | `password` | Nothing: one click creates the entry (`async_create_entry(..., data={})`) |
| `spook` | `token` | Nothing: a confirmation step only |
| `bermuda` | `username`, `password` | Nothing at setup; the hit is commented-out template code (line 118). Needs a Bluetooth adapter to do anything |
| `ble_monitor` | `password` | No credential (optional per-device encryption keys); needs a Bluetooth adapter and BLE sensors |
| `waste_collection_schedule` | many | Country and collection source; most sources need only an address. The hits come from its ~1,000 source modules |

So **at least three** (`alarmo`, `spook`, `bermuda`) and arguably five need no credential, and the statement
"26 of the 37 require an API key, token, password, user name, host or e-mail address before their
configuration can complete" (final §11, §12.2; interim §5.3) is not right as worded. `alarmo` and `spook` could
have been run end to end. **Decision for Younes** (affects the final report too).

## The 26, classified

Three of the 26 were run end to end anyway: `pirateweather` (free API key), `midea_ac_lan` and `localtuya`
(simulated devices). The other 23:

**No credential at setup (regex false positives)** — 5
`alarmo`, `spook`, `bermuda` (Bluetooth adapter for useful output), `ble_monitor` (Bluetooth adapter + sensors),
`waste_collection_schedule` (an address)

**A free account or self-hosted software** — 4
- `hacs`: a GitHub account (free), authorised by device login
- `solcast_solar`: a free hobbyist API key (rooftop site registered with Solcast)
- `frigate`: a Frigate server (open source, self-hostable); cameras for useful output
- `webrtc`: a go2rtc stream server (open source) and a camera stream (a test stream would do)

**Paid account or local model** — 1
- `llmvision`: an API key from an AI provider (paid), or a local model server

**A device, an appliance or a customer account** — 13
`alexa_media` (Amazon Echo), `bambu_lab` (Bambu Lab 3D printer), `dreame_vacuum` (Dreame/Xiaomi vacuum),
`eufy_security` (eufy cameras + a eufy-security-ws server), `govee` (Govee devices; API key issued to an
account), `homematicip_local` (Homematic hub, CCU), `meross_lan` (Meross devices), `smartthinq_sensors` (LG ThinQ
appliance), `sonoff` (eWeLink devices), `tapo_control` (Tapo camera), `xiaomi_home` (Xiaomi account + devices),
`xiaomi_miot` (Xiaomi device host and token), `octopus_energy` (an Octopus Energy UK customer account)

Note: `midea_ac_lan` and `localtuya` show a device-bound integration can be run against a simulated device,
so "needs a device" is a cost, not an absolute bar.

## Decision (Younes, 2026-10-25): extend the end-to-end set, later

Load results checked against the final rerun (`experiments/verify/results/final_20261016/step05_compat/`).
Scope agreed:

- **Run end to end, both arms:** `alarmo` (no account; stimulus: arm, expect armed after the exit delay),
  `waste_collection_schedule` (an address; egress harness as `nordpool`; next collection date equal across
  arms), `solcast_solar` (free hobbyist API key — Younes to sign up). Named set 13 → 16.
- **Report by name with the reason, not run:** `spook` (setup links sub-integrations into the integrations
  folder and restarts the platform; read-only confined by design, and the harness cannot survive a restart;
  its earlier `not_found` was a harness artifact), `hacs` (import fails in both arms: `hacs_frontend` is built
  separately), `bermuda` (import fails in both arms: undeclared `aiofiles`; needs Bluetooth), `ble_monitor`
  (loads; needs Bluetooth sensors, and the framework has no Bluetooth clause, a real confinement cost).
- **Stated limits:** `frigate`, `webrtc` (a video server and camera stream; `webrtc` starts its own
  downloaded server), `llmvision` (paid key or local model).

Order when resumed: prediction note `notes/e2e_extension_prediction.md` → Younes reads → commit → fresh clone
on the Pi at a new tag → run → correct "26 of 37" in final §11.3, §12.2 and interim §5.3 from the results.
Not started.
