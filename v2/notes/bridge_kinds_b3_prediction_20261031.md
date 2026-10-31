# Bridge extension, batch B3: update, event, time, device tracker, notify — prediction (2026-10-31)

**Committed before any code.** Younes accepted the list and all five recommendations on 2026-10-31 ("accept all recommendations, go ahead"). Same method as B1 and
B2: from Home Assistant 2026.8.3 (`~/ha-src/core`), written against what each entity's method
receives in (A); shape, not meaning; refused data recorded by kind. Which base class each of the
corpus integrations actually uses was read from the corpus on the Pi (`~/r2exp/corpus/*/<kind>.py`),
because three of these kinds come in variants.

**Tests touched by this batch, searched first:** none of the five kinds appears in any test outside
the B3 cases to be written (the refused-kind probes are a to-do list).

## What reaches the entity, per kind (sources, `components/<kind>/`)

**update** (`__init__.py` l. 96–180, 359–375)
- install {version: string, optional; backup: boolean, default false}; skip; clear_skipped; and a
  websocket question, release notes (`websocket_release_notes`, l. 532).
- (A) refuses an install with nothing to install, a specific version the entity does not support,
  a backup it does not support, or one already in progress (`async_install`, l. 132), then calls
  `async_install(version, backup)`. **`skip` and `clear_skipped` are `@final` and kept in (A)
  itself** (the skipped version is (A)'s own state, l. 359–372): nothing reaches the integration.
- Corpus: `bambu_lab`, `homematicip_local`, `meross_lan`, `tapo_control` (device firmware), `hacs`
  (a new version of a repository it manages), `frigate` (its own class).
- **Entity receives**: install {version?, backup}. See decisions 1 and 2.

**event** (`__init__.py` l. 161–219)
- No services. The state is the time of the last event and is `@final`: (A) sets it itself when
  `_trigger_event(event_type, attributes)` is called (l. 162), and refuses an event type the entity
  does not list. See decision 3.
- Corpus: `govee`, `homematicip_local`, `xiaomi_home` (`EventEntity`); `alarmo`, `octopus_energy`,
  `spook` (their own classes).

**time** (`__init__.py` l. 45)
- set_value {time}: (A) parses it (`cv.time`) and hands the entity a time of day.
- **Forwarded as**: set_value {time: "HH:MM:SS"}, which the integration's instance parses again.

**device_tracker** (`entity.py` l. 168–737)
- No entity services (the `see` service is the legacy kind, not an entity). Two families:
  **GPS trackers** (`TrackerEntity`: latitude, longitude, accuracy, or a location name), whose state
  (A) works out itself from **(A)'s own zones** (`state`, l. 396), and **scanners**
  (`ScannerEntity`/`BaseScannerEntity`: connected or not, IP, MAC, host name; Bluetooth or router),
  whose state is home or not_home.
- Corpus: `eufy_security`, `xiaomi_home` (GPS); `bermuda`, `ble_monitor` (scanners); `xiaomi_miot`
  (both).
- Display only: the bridged tracker picks the family from the published `source_type` (gps, or
  router/bluetooth/bluetooth_le), and a GPS tracker's home or away is worked out by (A) from the
  published coordinates, not taken from the sandbox (whose instance has no zones of the house).

**notify** (`__init__.py` l. 84–91)
- send_message {message: string, title: string, optional} → `async_send_message(message, title)`.
- Corpus: `homematicip_local`, `xiaomi_home` (`NotifyEntity`). **`alexa_media`'s notify is the
  legacy kind** (`BaseNotificationService`): a service the integration registers, not an entity,
  so the bridge cannot stand in for it (decision 5).

## Proposed rule

| Kind | Service | Data (optional unless *required*) |
|---|---|---|
| update | `install` | version: string; backup: true or false (decision 1) |
| time | `set_value` | time: "HH:MM" or "HH:MM:SS", *required* |
| notify | `send_message` | message: string ≤ 4096, *required*; title: string ≤ 255 (decision 4) |
| event, device_tracker | — | none: display only |

## Decisions (Younes, 2026-10-31: every recommendation accepted)

1. **`update.install`.** Pressing Install in (A) would make the confined integration install a new
   version: new firmware on its device (bambu_lab, homematicip_local, meross_lan, tapo_control),
   or, for `hacs`, a new version of an integration it manages. It acts with the integration's own
   permissions only (its declared hosts), exactly as unconfined, and only when a user asks.
   Options: (a) forward it; (b) refuse it, so updates are shown but installed only from the
   device's own app. *Recommended: (a).* For the report: if an install replaces a confined
   integration's *own* code, its identity changes and the approval gate (F57) should require a new
   approval before that code runs — **argued from the design, not tested in this batch**.
2. **Release notes** are a question (like a calendar's events) whose answer is a long text drawn in
   (A)'s UI. *Recommended: a limit for now*: (A) shows the published summary and the release link,
   not the full notes. Supporting it means a text answer through the question path, and (A)
   rendering text from the sandbox — which B5's display check is about.
3. **Event times.** (A) stamps an event itself when the bridge triggers it, so the time shown is
   when the event reached (A), milliseconds after the integration saw it. Options: (a) trigger in
   (A) on each new event the sandbox publishes (native behaviour: automations on the event work);
   (b) override the `@final` state to show the integration's own time, as F70 did for the switch.
   *Recommended: (a)*: the difference is the bridge's delay, and (b) would bypass what makes
   automations fire. A republish of the same event (e.g. after a restart) must not fire it again.
4. **Notification text in the log.** An allowed command's data is logged as sent, so every
   notification's text would be written to the durable log. Messages can be personal. *Recommended:
   withhold `message` and `title` from the log as codes are (the record keeps their length)*; and
   4096 characters for a message, 255 for a title.
5. **`alexa_media`'s notifications** use the legacy notify service, not an entity. *Recommended:
   state it as a limit* (forwarding services rather than entities is a new path).

## Two details from the source, settled in the design

- **A scanner is built on `BaseScannerEntity`, not `ScannerEntity`.** `ScannerEntity` replaces the
  entity's unique id with the published MAC address and attaches the entity to a network device in
  (A)'s registry by that MAC (`entity.py` l. 634–720). That would drop the bridge's identity
  (`<integration>:<entity>`) and link a confined integration's tracker to (A)'s own devices. The
  IP, MAC and host name stay visible as ordinary attributes.
- **An update never advertises release notes** (feature 16 is removed in (A)), per decision 2, so
  (A) offers no button that would ask for them.

## Predictions

**Offline, `selftest_commands`** (laptop and Pi), new cases:

| | Prediction |
|---|---|
| K23 | Allowed and pushed exactly: update install `{"backup": false}` and `{"version": "1.2.3", "backup": true}`; time set_value `"07:30:00"` and `"07:30"`; notify send_message with a message, and with a message and a title |
| K24 | Refused under `COMMAND_DATA`: a time "25:00"; a time as a number; install with a numeric version; backup `"no"`; install with an extra `entity_id`; a 4097-character message; a 256-character title; a numeric title; send_message with no message |
| K25 | Refused under `COMMAND_SERVICES`: update `skip` and `clear_skipped` (kept in (A)); device_tracker `see`; event `trigger`; notify `send` |
| K26 | **No notification text in the durable log**: after an allowed message and a refused 4097-character one, neither text nor the title is in the log file, and the records say `(withheld)` |
| K27 | **Fails first**: before the change, K23's 6, K24's 9, and K26's allowed case and its "withheld" record check fail (a refused message is recorded by kind, `str, length 20`, not `(withheld)`); K25's 5 and K26's log-text check pass already. Run on the laptop before this note was committed: **197/214** |
| K28 | Every earlier check still passes |

**Against (A), `selftest_bridge_types`** (Pi, fresh clone, (A) `down`, `up --fresh`):

| | Prediction |
|---|---|
| T22 | One update, event, time, notify, GPS tracker and scanner each become a registry row of its domain owned by the bridge. The update (1.0.0 installed, 1.1.0 latest, features install, progress, backup and release notes) shows `on` with both versions, and its features without release notes (13). The time shows `06:45:00`. The event first shows `unknown` with its event types |
| T23 | **(A) works out a GPS tracker's state from its own zones**: published at (A)'s home coordinates, with the sandbox's state `not_home`, it shows `home`; moved one degree north, `not_home`. A Bluetooth scanner published `home` shows `home`, then `not_home`; its MAC is an attribute and its unique id is the bridge's |
| T24 | **Events**: a published `press` event fires once in (A) (a new timestamp, `event_type` press, its attribute `button`); republishing the same event leaves (A)'s state unchanged; a later `double_press` fires again; an event type the entity does not list leaves (A)'s state unchanged and the bridge working |
| T25 | From a user in (A): `update.skip` turns the update `off` and no command decision is recorded; `clear_skipped` turns it back `on`, again with none; `update.install` reaches the sandbox as `install {"backup": false}`, and once 1.1.0 is published as installed (A) shows `off`; `time.set_value` "07:30" reaches it as `{"time": "07:30:00"}`; `notify.send_message` reaches it as `{"message": "Door left open", "title": "Home"}`. Each call succeeds |
| T26 | "Door left open" is not in the run's durable log |
| T27 | Every suite passes with (A) up |

**Fails first for T22–T26**: run on the Pi against `bridge-b3-pre`, they fail (the bridge refuses
these kinds), except T26, which passes before (nothing is sent). Outcome appended after the runs.

**Not tested here**: no real integration publishes these kinds in the end-to-end set (B5); the
F57 argument in decision 1.
