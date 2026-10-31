# Bridge extension, batch B4a: media player — prediction (2026-10-31)

**Committed before any code.** Younes accepted recommendations 1, 3, 4, 5 and, after the research below, option (c) for 2, on 2026-10-31 ("accept all recommendations, go ahead"). Same method as B1–B3:
from Home Assistant 2026.8.3 (`~/ha-src/core/homeassistant/components/media_player/`), written
against what the entity's method receives in (A); shape, not meaning; refused data recorded by
kind. Integrations completed by this kind alone: `alexa_media`, `meross_lan`, `sonoff`, `webrtc`,
`xiaomi_home` (5; 29 of 37 by kind afterwards). `alexa_media` stays partial: its notifications
are the legacy service (B3, decision 5).

**Tests touched, searched first:** no test publishes a media player through the bridge
(`home.py`'s `media_player.living_room_tv` is (A)'s own simulated device; `sandbox_runtime.py`
only lists the platform name).

## What reaches the entity (sources, `__init__.py`)

- **No data**: turn_on, turn_off, media_play, media_pause, media_stop, media_next_track,
  media_previous_track, clear_playlist, unjoin (l. 293–348, 468).
- **Renamed before the entity**: volume_set {volume_level 0–1} → `async_set_volume_level(volume)`;
  volume_mute {is_volume_muted} → `async_mute_volume(mute)`; media_seek {seek_position ≥ 0} →
  `async_media_seek(position)` (l. 350–381, `_rename_keys` l. 264). The bridge sends the
  *service's* field names back, because the sandbox runs the service again.
- **With data**: select_source {source}; select_sound_mode {sound_mode}; shuffle_set {shuffle};
  repeat_set {repeat: off, all or one} (l. 389–476).
- **play_media** (l. 190–198, 422–436): content type and id (required), `enqueue` (add, next, play,
  replace) or `announce`, and `extra`, a free mapping, default `{}`. The entity receives
  `async_play_media(media_type, media_id, enqueue=…, announce=…, extra=…)`.
- **Worked out by the base class only if the integration has no method of its own**:
  `toggle`, `volume_up`, `volume_down`, `media_play_pause` (l. 1026–1086). Each first checks
  `hasattr(self, "toggle")` (etc.) and runs the integration's own if there is one; otherwise it
  computes from the published state. `volume_up` computes only for a player with VOLUME_SET: a
  player that steps its volume without setting it does nothing (l. 1050). See decision 1.
- **Questions with large answers**: browse_media, search_media (l. 437–460). See decision 3.
- **join** {group_members: (A)'s entity ids} (l. 383). See decision 4.
- **Artwork**: `entity_picture` is a link to the sandbox's own image proxy, which (A) cannot reach.
  See decision 5.

## Decisions (Younes, 2026-10-31: every recommendation accepted; 2 as option (c), below)

1. **`toggle`, `volume_up`, `volume_down`, `media_play_pause`: forward them as themselves.**
   Unlike the kinds before, Home Assistant's base class here defers to the integration's own
   method when it has one, and a step-volume player has no other way to change volume. Forwarding
   the service lets the sandbox run exactly what the integration would unconfined (its own method,
   or the same computation). It adds four no-data commands. *Recommended: yes.*
2. **`play_media`**: forward type and id (strings, the id ≤ 4096: it can be a long link),
   `enqueue` (one of add, next, play, replace) or `announce` (true/false), and `extra` (plain JSON,
   ≤ 4 KiB, as a vacuum's parameters). **Limit to state:** content that only (A) can resolve —
   its media library, text-to-speech, links to (A) itself — does not play, because the integration
   resolves it inside the sandbox, which has neither (A)'s media sources nor a route to (A).
   Content the integration understands itself (its own service's ids, a public link on a host it
   declares) does. *Recommended: forward, and state the limit.*
3. **Browsing and searching media**: *recommended a limit* (the bridge drops BROWSE_MEDIA and
   SEARCH_MEDIA from the published features, so (A) offers neither). They are questions whose
   answers are large trees with thumbnails, the same text-and-image path as B4b.
4. **Grouping (`join`/`unjoin`)**: `join` names other players by (A)'s entity ids, which mean
   nothing in the sandbox. *Recommended a limit* (GROUPING dropped); joining only players of the
   same integration, translated to its own ids, is possible later.
5. **Artwork**: *recommended not shown* (the bridge drops `entity_picture`) until B4b decides how
   images cross; title, artist, album and position still show.

## Decision 2, researched (Younes asked, 2026-10-31: "research about this and come up with an educated suggestion")

**How Home Assistant plays its own media.** (A)'s media library, text-to-speech and other *media
sources* are addressed by ids of the form `media-source://<source>/<item>`. A player that supports
them resolves the id itself in `async_play_media`, with two helpers: `media_source.async_resolve_media`
(`media_source/helper.py` l. 115) turns it into a link on the instance, and
`async_process_play_media_url` (`media_player/browse_media.py` l. 34) signs that link for 24 hours
(`CONTENT_AUTH_EXPIRY_TIME`, `const.py` l. 8) and makes it absolute. A source the instance does not
have raises `UnknownMediaSource` (a `ValueError`, wrapped as `Unresolvable`, `helper.py` l. 39–47,
l. 130). `tts.speak` plays an announcement exactly this way: `play_media` with a
`media-source://tts/...` id.

**What the five integrations do with an id** (read from the corpus on the Pi, `~/r2exp/corpus`):

| Integration | `play_media` | Confined, forwarding the id unchanged |
|---|---|---|
| `sonoff` | Strips `media-source://` and sends the rest as a **ringtone file name on the device** (`ring/ring5.mp3`); never resolves | Works. Resolving in (A) would **break** it: a link where a file name belongs |
| `webrtc` | Resolves, signs, then hands the link to **go2rtc**, which fetches it (`ffmpeg:<link>`); go2rtc is the binary it runs itself at `localhost:1984`, or a server the user configures | Fails: the sandbox has no (A) media sources. Resolved in (A) first, it works only with an **external** go2rtc; the bundled one runs inside the sandbox and has no route to (A) |
| `alexa_media` | For TTS (`music` + announce): resolves, **downloads the audio itself**, converts it with ffmpeg into **its own config folder**, and tells Amazon to fetch it from (A)'s public `/local/` path. Its other types (sequence, routine, sound, skill, Amazon music) are Amazon's own ids | TTS through the player fails either way: the download needs a route to (A), and a file written in the sandbox's config is not served by (A). The Amazon-id types work. (Its main TTS path is the legacy notify, already a limit, B3 decision 5) |
| `meross_lan`, `xiaomi_home` | No `play_media` | Nothing to decide |

**Options.**
- (a) Forward every id unchanged. `sonoff` works; (A)'s TTS and library fail everywhere.
- (b) Resolve every media-source id in (A). Breaks `sonoff`.
- (c) **Resolve in (A) only the ids (A) can resolve; forward any other id unchanged.** (A) knows
  which sources it has: an id naming one of them (tts, the media library, a camera) becomes a
  signed link to (A); an id naming a source (A) does not have (sonoff's `ring/...`, or a source the
  confined integration registers itself) raises `UnknownMediaSource` and goes on as it was, for the
  integration's own instance to handle.

**Suggestion: (c).** It is the only option that breaks no integration, and it makes (A)'s
announcements reach any confined player whose device fetches the link itself (webrtc with an
external go2rtc). It is also what each integration would do unconfined with an id (A) owns, done
on the side that owns the media. **Costs and limits to state:**
- A signed link to one file on (A), valid 24 hours, reaches the confined integration (and through
  it the device or its cloud). Unconfined it receives the same link; nothing beyond it.
- Media the *integration* must fetch from (A) still fails, because the sandbox has no route to (A):
  `webrtc` with its bundled go2rtc, `alexa_media`'s TTS (which also needs (A) to serve a file the
  integration wrote).
- None of the five is in the end-to-end set, so (c) is tested against (A) with a test player only;
  the per-integration readings above are from their code, not from runs.

## Proposed rule (with recommendations 1–5)

| Service | Data (optional unless *required*) |
|---|---|
| `turn_on`, `turn_off`, `toggle`, `media_play`, `media_pause`, `media_play_pause`, `media_stop`, `media_next_track`, `media_previous_track`, `clear_playlist`, `volume_up`, `volume_down` | none |
| `volume_set` | volume_level: number, *required* |
| `volume_mute` | is_volume_muted: true or false, *required* |
| `media_seek` | seek_position: number, *required* |
| `select_source` | source: string, *required* |
| `select_sound_mode` | sound_mode: string, *required* |
| `shuffle_set` | shuffle: true or false, *required* |
| `repeat_set` | repeat: off, all or one, *required* |
| `play_media` | media_content_type: string, *required*; media_content_id: string ≤ 4096, *required*; enqueue: add, next, play or replace; announce: true or false; extra: plain JSON ≤ 4 KiB |

**Artwork elsewhere, found while writing decision 5:** every bridged kind passes attributes it
does not take into its own properties through as ordinary attributes, so a published
`entity_picture` (an image link the sandbox chooses) would reach (A)'s UI on a sensor, a switch, and
so on. The media player drops it here; the other kinds go to B5's display check.

## Predictions

**Offline, `selftest_commands`** (laptop and Pi), new cases:

| | Prediction |
|---|---|
| K29 | Allowed and pushed exactly: the twelve no-data services; volume_set 0.4; volume_mute true; media_seek 30; select_source; select_sound_mode; shuffle_set; repeat_set all; play_media with type and id; with `enqueue` add; with `announce` true; with `extra` holding a mapping; with a 4096-character id |
| K30 | Refused under `COMMAND_DATA`: volume_level as a string; is_volume_muted `"yes"`; repeat `twice`; enqueue `later`; play_media with no id; a 4097-character id; `extra` over 4 KiB; `extra` as a string; an extra `entity_id` |
| K31 | Refused under `COMMAND_SERVICES`: `join`, `unjoin`, `browse_media`, `search_media` |
| K32 | **Fails first**: before the change, K29's 24 and K30's 9 fail (K30's refused, but under `COMMAND_SERVICES`); K31's 4 pass already. Run on the laptop before this note was committed: **218/251** |

**Against (A), `selftest_bridge_types`** (Pi, fresh clone, (A) `down`, `up --fresh`):

| | Prediction |
|---|---|
| T28 | A published player (playing, volume 0.5, title, source Radio of Radio/AUX, every feature including browse, search and grouping, and an `entity_picture` link) is a registry row of its domain owned by the bridge; (A) shows it playing with its volume, title and source list, **no `entity_picture`**, and its features without BROWSE_MEDIA, SEARCH_MEDIA and GROUPING |
| T29 | From a user in (A), the sandbox receives: `volume_set` 0.4 as `{"volume_level": 0.4}`; `volume_mute` true as `{"is_volume_muted": true}`; `media_seek` 30 as `{"seek_position": 30.0}`; `media_play_pause`, `volume_up` and `toggle` as themselves with no data; `select_source` AUX as `{"source": "AUX"}`; `repeat_set` all as `{"repeat": "all"}`; `play_media` music `spotify:track:1` as `{"media_content_type": "music", "media_content_id": "spotify:track:1", "extra": {}}`. Each call succeeds |
| T30 | **Decision 2 (c)**: `play_media` with `media-source://ring/ring5.mp3`, a source (A) does not have, reaches the sandbox **unchanged**; with `media-source://media_source/local/selftest.mp3`, a file in (A)'s own media library, it reaches the sandbox as an absolute `http` link to (A) containing `/media/local/selftest.mp3?authSig=` |
| T31 | `media_player.join` fails in (A) (grouping is not offered), and no command decision is recorded |
| T32 | Every suite passes with (A) up |

**Fails first for T28–T31**: run on the Pi against `bridge-b4a-pre`, they fail (the bridge refuses
media players), except T31's second check (nothing is sent). Outcome appended after the runs.

**Not tested here**: the five integrations themselves (none is in the end-to-end set); the
per-integration readings in decision 2 come from their code.
