# Bridge extension, batch B4b: camera, image — prediction (2026-11-01)

**Committed before any code.** Drafted 2026-10-31; decisions taken by Younes on 2026-11-01 (below).
Unlike B1–B4a, this batch needs a new path: picture bytes crossing from the sandbox into (A).
Sources: Home Assistant 2026.8.3 (`~/ha-src/core/homeassistant/components/camera/__init__.py`,
`image/__init__.py`, `camera/img_util.py`, `websocket_api/http.py`), the corpus on the Pi
(`~/r2exp/corpus/*/camera.py`, `image.py`), and the framework's own limits (`channel.py`
`MAX_FRAME` = 1 MiB). Integrations completed by these kinds: `bambu_lab`, `browser_mod`,
`dreame_vacuum`, `dwd_weather`, `eufy_security`, `frigate`, `tapo_control`, `xiaomi_miot`
(8; 36 of 37 by kind afterwards — `alexa_media`'s notify is the legacy kind, which the bridge
does not cover). **"By kind" overstates three of them**: see the limits.

**Tests touched, searched first (2026-11-01):** no test publishes a camera or an image, fetches
`/api/camera_proxy` or `/api/image_proxy`, or uses either as a refused-kind probe
(`grep` over `framework/confine/*.py`; only `sandbox_runtime.PLATFORM_NAMES` names them).

## How (A) shows a picture (sources, read 2026-11-01)

- **Camera.** (A)'s UI never loads a picture from the integration directly: it asks (A) at
  `/api/camera_proxy/<entity>?token=…` (the entity's own `entity_picture`, l. 477), and (A) calls the
  entity's `async_camera_image(width, height)` (l. 598), with the `width` and `height` of the
  request, if any (l. 891–892). A JPEG is then scaled **in (A)**, by libjpeg-turbo, only when both
  are given (l. 197–206; `img_util.py` l. 39, which first reads the JPEG's header). A "live" view
  without a stream is a series of such snapshots every `frame_interval` (0.5 s by default, l. 130,
  447, 520). Services: turn_on, turn_off, enable/disable_motion_detection (no data, l. 377–384);
  `snapshot` (writes the picture to a file **in (A)**); `play_stream`, `record` (need a stream).
  State: recording, streaming or idle (l. 627); attributes: access_token, model_name, brand,
  motion_detection (l. 675). Features: ON_OFF 1, STREAM 2 (l. 117).
- **Image.** (A) calls `async_image()` (l. 285), which keeps the first picture it gets
  (`_cached_image`). If the entity has an `image_url`, **(A) downloads the picture from that link
  itself** (`_async_load_image_from_url`, l. 264). The state is the time the image last changed
  (`@final`, l. 301). `ImageEntity.__init__` needs `hass` (an HTTP client for `image_url`, unused here).
- **Corpus.** Every camera and image in the corpus implements a snapshot. Five cameras also give a
  live stream (`stream_source`, RTSP: `bambu_lab`, `eufy_security`, `frigate`, `tapo_control`,
  `xiaomi_miot`); `frigate` also WebRTC; `bambu_lab` takes stills from its stream
  (`use_stream_for_stills`).
- **Size on the way.** Sandbox → mediator: one channel frame, 1 MiB. Mediator → (A): one websocket
  message; `http.py` l. 98 sets no limit, so aiohttp's default applies (4 MiB; to be confirmed on the Pi).

## Decisions (Younes, 2026-11-01)

1. **512 KiB per picture, stated as a limit** (≈ 683 KiB as base64, inside the 1 MiB frame).
2. **(A) reuses each picture for 2 s**, and the bridged camera announces a 2 s frame interval.
   Every question stays a durable record (S7 unchanged, record before act unchanged). Discussed:
   logging accepted pictures in bulk would have answered the same questions afterwards (refusals
   are still individual), but would have qualified S7 and reopened §7.36.1's ordering; rejected.
3. **Snapshots only; no live video.** The STREAM feature is dropped; `play_stream`, `record` and
   WebRTC are not offered. Passing the stream's address would make (A) connect to an address the
   sandbox chooses, outside the egress allowlist, and feed bytes the sandbox controls to FFmpeg in
   (A). **Future work**: a stream only to an `rtsp`/`rtsps` host already on that sandbox's egress
   allowlist and on the local network; it narrows the first problem, not fully the second, and
   moves the camera's password into (A).
4. **Commands**: turn_on, turn_off, enable/disable_motion_detection go on, with no data;
   `snapshot` stays in (A) (it writes (A)'s copy of the picture to a file in (A)).

## Design

**A picture is a question**, as calendar events and forecasts are (bridge step 4):

- (A)'s bridged camera asks `camera_image` {width?, height?}; the bridged image asks `image` {}.
  These are not services anyone can call in (A): only the bridged entity sends them.
- The sandbox's own instance answers with `camera.async_get_image(hass, entity, width=, height=)` or
  `image.async_get_image(hass, entity)` (so a JPEG camera's picture is scaled there, where it can
  be), as `{"content_type": …, "data": <base64>}`.
- The mediator relays it only if it is **exactly** those two keys; `content_type` is one of
  image/jpeg, image/png, image/gif, image/webp; `data` is strict base64; the bytes are at most
  512 KiB; and **the first bytes are that type's signature** — JPEG `FF D8 FF`, PNG's 8-byte
  signature, `GIF87a`/`GIF89a`, `RIFF`…`WEBP`. Home Assistant's own table (`image/__init__.py`
  l. 75) is not reused: it lists only some JPEG markers, so it would refuse valid camera JPEGs,
  and it takes any `RIFF` file (a WAV, an AVI) as WebP. A new rule, `PICTURE_ANSWER`, names it.
- Recorded by type and size only, never the picture.
- (A) never fetches a link the sandbox gives: the bridged image has no `image_url`; the published
  `entity_picture` (F71), `access_token`, and `frontend_stream_type` are not passed on. The picture
  link (A)'s UI uses is (A)'s own proxy, with (A)'s own token.
- **Reuse**: the bridged camera keeps its last picture per requested size (at most 4 sizes) for 2 s;
  the bridged image keeps its picture until the published time changes.

## Limitations (to state as they are, in the report too)

1. **No live video for any confined camera.** `frigate`, `eufy_security` and `tapo_control` exist
   mainly for live video; they are covered "by kind" but lose their main use. `xiaomi_miot`'s
   cameras lose their stream too. `bambu_lab` takes stills from its stream: whether its
   sandboxed instance can read that stream, and so give any picture, is **not checked** (no
   printer). Coverage is reported as **36 of 37 by kind, of which 3 lose their main use**.
2. **A "live" view is a picture every 2 s**, not every 0.5 s as unconfined. A different picture
   size (another card) asks on its own.
3. **The sandbox learns when someone is looking.** Each question tells the confined integration
   that a person in the house has the camera open, and when (to 2 s). Inherent in asking only
   when needed; hiding it would mean pictures pushed on a timer whether watched or not.
4. **Larger than 512 KiB: no picture**, and (A) shows an error. Scaling happens in the sandbox only
   for a JPEG, only when (A) asks both a width and a height, and only if the sandbox's instance has
   TurboJPEG (not checked); a PNG, GIF or WebP is never scaled. How large real snapshots are is
   not measured.
5. **The picture's content is not checked**, only its type signature and size. A picture can show
   anything (a false scene). Its bytes are parsed by the household's browser, as any picture is,
   and **in (A) by libjpeg-turbo** when (A) scales a JPEG (`img_util.py`). That is a parser in (A)
   reading sandbox-controlled bytes — far smaller than FFmpeg (decision 3), but not none.
6. **Log volume**: up to about 1,800 records an hour per open camera view and size, each fsynced
   (bytes not measured).
7. **A camera turned off in its integration** is not known to (A) (`is_on` is not a published
   attribute): (A) still asks, and shows an error when the integration cannot give a picture.
8. The eight integrations themselves are not run (none is in the end-to-end set, and there is no
   camera in the house): tests use a test camera and a test image.

## Predictions

**Offline, `selftest_commands`** (laptop and Pi), new cases:

| | Prediction |
|---|---|
| K33 | Allowed and pushed exactly: camera turn_on, turn_off, enable_motion_detection, disable_motion_detection (no data); camera_image with no data and with width 640, height 360; image `image` with no data |
| K34 | Refused under `COMMAND_DATA`: camera_image width as a string; width 0; width 16385; an extra key; image with any data; turn_on with data |
| K35 | Refused under `COMMAND_SERVICES`: camera snapshot, play_stream, record; image `camera_image` |

**Offline, `selftest_queries`**, new cases (after Q6, so Q5's count stays 14):

| | Prediction |
|---|---|
| Q7 | A JPEG (`FF D8 FF E1`, Exif), a JPEG starting `FF D8 FF E8` (not in Home Assistant's table), a PNG, a GIF89a and a WebP, each well under the cap, are relayed unchanged to (A) |
| Q8 | Exactly 512 KiB of JPEG is relayed |
| Q9 | Refused under `PICTURE_ANSWER`, not relayed: an HTML page labelled image/png; JPEG bytes labelled image/png; image/svg+xml; image/tiff; a `RIFF…WAVE` file labelled image/webp; 512 KiB + 1; `data` not base64; an extra key; no `content_type`; a list; empty data |
| Q10 | No picture's base64 is in the log; each picture's record gives its type and size |

**Against (A), `selftest_bridge_types`** (Pi, fresh clone, (A) `down`, `up --fresh`):

| | Prediction |
|---|---|
| T33 | A published camera (idle; brand, model_name, motion_detection true, supported_features 3, the sandbox's `access_token`, `entity_picture` and `frontend_stream_type`) is a registry row of its domain owned by the bridge; (A) shows it idle with its brand, model and motion detection, supported_features 1 (no STREAM), no `frontend_stream_type`, and an `entity_picture` that is (A)'s own `/api/camera_proxy/<entity>?token=` with a token that is not the sandbox's |
| T34 | Fetching (A)'s camera proxy: the sandbox is asked `camera_image` with no data; (A) answers with exactly the sandbox's JPEG bytes as image/jpeg. With `?width=640&height=360`, it is asked with those two |
| T35 | A second fetch within 2 s asks the sandbox nothing and returns the same bytes; a fetch after 2 s asks again |
| T36 | An answer of 600 KiB, and an HTML page labelled image/png: (A)'s proxy answers an error, without the HTML; the next valid picture is served (the bridge keeps working) |
| T37 | From a user in (A): turn_off and enable_motion_detection reach the sandbox as themselves with no data; `camera.play_stream` fails in (A) and no command decision is recorded |
| T38 | A published image (its time; the sandbox's `entity_picture` and `access_token`) shows that time as its state and (A)'s own `/api/image_proxy/` link; fetching it asks `image` once and returns the bytes; fetching again, after 2 s, asks nothing; republished with a new time, the next fetch asks again |
| T39 | Every suite passes with (A) up |

**Fails first**: before the change, K33 fails (camera and image are not kinds the mediator lists:
refused under `COMMAND_SERVICES`), K34 fails where the clause is `COMMAND_DATA` (refused under
`COMMAND_SERVICES` instead), K35 passes; Q7 and Q8 fail (the question is never pushed); Q9's
refusals fail (no question pushed, so nothing to refuse under `PICTURE_ANSWER`); T33–T38 fail
against (A) (the bridge refuses cameras and images at publish), except T37's last check (nothing
is sent). Exact counts in the outcome, from the runs.

**Run on the laptop before this note was committed** (no code yet): `selftest_commands`
**255/268** (K33's 7 and K34's 6 fail, each refused under `COMMAND_SERVICES`; K35's 4 pass);
`selftest_queries` **30/49** (Q7's 6, Q8, Q9's 11 and Q10's count fail; Q10's first check passes
with nothing to find, as before any picture is logged).

## Outcome (2026-11-01, Pi, fresh clones of both tags, (A) `down` then `up --fresh` before each)

Results: `experiments/real_platform/results/bridge_kinds_20261031/b4b/`.

| | `bridge-b4b-pre` (`2394446`) | `bridge-b4b` (`f1f4053`) |
|---|---|---|
| `selftest_commands` | 255/268 (K33, K34 fail as predicted) | **268/268** |
| `selftest_queries` | 30/49 (Q7–Q9, Q10's count fail as predicted) | **49/49** |
| `selftest_bridge_types` | 176/194 | **194/194** |
| every suite (`suites_all`, on the same (A)) | — | **35/35**; no bridge error in (A)'s log |

**One prediction did not hold as written.** Before the code, 18 of T33–T38's 21 checks failed,
not 20: besides T37's last check (nothing recorded), T37's two "the call succeeds" checks passed.
With no camera in (A), Home Assistant accepts `camera.turn_off` on an entity that does not exist
and reports success. Alone, those checks show nothing; they mean something only beside the
"reaches the sandbox" check before them, which failed as predicted (AI-use log 39).

Every other prediction held: (A)'s own picture link and token (not the sandbox's), no STREAM and no
`frontend_stream_type`; exactly the sandbox's bytes through (A)'s proxy; width and height passed on;
no question within 2 s, a question after; a 600 KiB picture and an HTML page labelled image/png give
an error without the content, and the next picture is served; `play_stream` fails in (A) with no
decision recorded; the image asked once, not again for the same time, again for a new time.

**Bridge now 29 kinds; 36 of 37 integrations by kind, of which 3 (`frigate`, `eufy_security`,
`tapo_control`) lose their main use, live video, and `bambu_lab`'s pictures are unchecked.** The
limitations above stand as written; none was tested away.
