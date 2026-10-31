# Bridge extension, batch B5: the house check — prediction (2026-10-31)

**Younes, 2026-10-31: "accept all recommendations, go ahead".** Committed with the tests, before the
fix and before any counted run. B5 closes the bridge
extension (B4b, camera and image, deferred by Younes). It has four parts:

1. a finding (F71) and its fix;
2. the display check;
3. the fifteen run again against the real house;
4. a recount.

Each part follows the usual method: prediction, fails-first test, change, run.

## Facts gathered for the draft

- **(A)'s UI loads an entity's picture link by itself.** In (A)'s frontend (`home-assistant-frontend`
  20260729.7, `houseA-deps`), the icon of every entity is drawn as
  `url(attributes.entity_picture_local || attributes.entity_picture)` when either is set. That happens
  on the dashboard, in the more-info dialog and in the entity lists. The bridge drops both only for
  `update` and `media_player` (B3, B4a). On the other 25 kinds, `entity_picture` passes through as an
  extra attribute (`entity.py`: not in `RESERVED`, not described). A survey of the frontend's other
  attribute reads found no other link it loads unprompted. `still_url` and `stream_url` belong to a
  camera's setup preview, not to an entity's state. An update's `release_url` is a link the user
  clicks.
- **`dwd_weather` has a camera only as a map.** `__init__.py` sets up `camera` only for an entry of
  type map (`CONF_ENTITY_TYPE_MAP`, l. 112–133). The harness's entry is a station (10865, München-Stadt),
  which sets up `weather` and `sensor`. So step 5's run published no camera because, with these
  options, there is none (the 2026-10-27 note's open point 2).
- **The 2026-10-27 count went by file name**, as its method states. `alarmo/event.py` is not a
  platform: it defines an `EventHandler` that fires bus events, and alarmo sets up only
  `alarm_control_panel` (`__init__.py` l. 86). Other false positives of the same kind are possible.
- **A browser is available**: Chromium 141 on the Pi, next to (A).

## F71: a confined integration chooses a link the household's browser loads

A confined integration can publish an `entity_picture` (or `entity_picture_local`) on a sensor, a
switch or any other bridged kind. Whoever opens (A)'s UI then has their browser fetch that address,
from inside the household, at a time the integration does not control but can expect. This goes around
the egress allowlist in two ways:

- the integration can put anything it has read into the address (`https://anyhost/<data>`);
- it can point the household's browser at a device on the home network.

The sandbox itself still reaches only its declared hosts. The browser is a path out of the
confinement that the framework does not see.

## Decisions for Younes

1. **F71's fix: drop `entity_picture` and `entity_picture_local` on every kind.** These two are added
   to what the bridge never passes on, for every kind, the way `update` and `media_player` already
   drop them. (A) then shows the kind's own icon. *Recommended.* Alternative: keep a picture only if it
   is a path on (A) itself (`/api/...`, `/local/...`). That still lets the integration choose which of
   (A)'s own addresses the browser fetches, so it is not recommended. Limit stated with the fix: an
   update's `release_url` stays a link the user may click.
2. **The display check: automated, in Chromium on the Pi, plus screenshots for you.**
   - The harness opens (A)'s UI through Chromium's DevTools protocol, logged in with a token, on the
     default dashboard and on each hostile entity's dialog.
   - Hostile text goes in a state, an attribute and a name:
     - `<img src=x onerror=…>`;
     - `<script>…</script>`;
     - a `javascript:` link;
     - a markdown link.
   - It passes when the text appears literally and no payload ran: a marker set by the payload stays
     unset, and the browser requests no marker address.
   - A screenshot of each page is saved for you to look at.

   *Recommended.* Alternative: you check by hand in your browser over Tailscale. That's simpler, but
   it leaves no record a reader can repeat. Scope: the default dashboard, the more-info dialog,
   history and logbook. Cards a user configures themselves (markdown cards) are out of scope and
   stated as such.
3. **The recount counts a kind only when its file is an entity platform.** The file must define
   `async_setup_entry` or `async_setup_platform`, checked by reading the code. Whether the platform
   is set up depends on the integration's options, as dwd's camera shows; that is stated, not counted.
   *Recommended.* Expected: `alarmo` loses `event`, and other figures may move. The 12 / 25 / 18
   account and today's 29 of 37 are recomputed from scratch, not adjusted.
4. **The fifteen against the real house: the same runs as step 5's runs C and D**, at the tag with
   F71 fixed. (A) is brought `down` then `up --fresh`, from a fresh clone. *Recommended.*

## Decisions (accepted)

1, 2, 3 and 4 as recommended above.

## The display suite, and its shakedown before this commit

`framework/confine/selftest_display.py` is new. Its first runs, in a scratch copy on the Pi against
(A) before F71's fix, built the instrument. They are disclosed here because they also showed results.

- **Chromium waits for a desktop keyring** over SSH and loads no `http` page. It loads only
  `data:` pages until it is given `--password-store=basic`.
- **The pages had to change.**
  - This frontend's overview shows areas, not entities. The page that lists a device in no area is
    `/home/other-devices`, so that page is used.
  - The dialog shows attributes only in its menu's "Details" view, which the suite opens.
  - (A) loads no history or logbook: `house_a.py`'s configuration has no recorder. Those two pages
    are dropped from the agreed scope rather than changing (A) for every other run. That is stated
    as a limit.
- **What the shakedown showed, before the fix:**
  - The control (D0) was seen.
  - Every hostile string appeared as literal text on the devices page, in the dialog and in its
    details, with no tag interpreted and no script run.
  - The devices page loaded both published picture links (the sensor's `entity_picture`, the
    switch's `entity_picture_local`), and the details listed the picture address as a clickable
    link. That is F71, seen in the browser.
  - 13 of 14 checks passed; D4 failed.

## Predictions

**Fails first** (tag `bridge-b5-pre`, (A) `down` then `up --fresh` from that clone):

- `selftest_bridge_types` **170 of 173**. The three T32 checks fail: (A) shows each published
  picture attribute.
- `selftest_display` **13 of 14**. D4 fails, with `/picture/sensor…` and `/picture/switch`
  requested.

**After the fix** (tag `bridge-b5`, (A) fresh, the same run):

- `selftest_bridge_types` **173 of 173**, and `selftest_display` **14 of 14**. No `/picture/`
  request, and nothing else changes in the display checks.
- The house test `selftest_real_house` passes.
- **The fifteen, as step 5's run C** (now including the function set, which F69 cut short in run C):
  - **E1:** every publish of every confined-declared arm is accepted.
  - **E2:** `verify/bridge_step5_verdicts.py` on the run directory gives **38 of 38**. That is run
    C's 26, plus the function set's 12, with F70 having brought `scheduler`'s switch in line.
  - **E3:** `retest_e2e_verdicts` **43 of 45**, the same two `scheduler` rows. alarmo's P1–P4
    **8/8**.
    - `nordpool`, `waste_collection_schedule`, `smhi_brandrisk` and `regensburg_transport` pass
      their own comparisons.
    - `trakt_tv` as before.
    - `localtuya` finds both simulated devices, unconfined and confined-declared.
    - `midea_ac_lan` reaches its device in both arms, both timing out as before.
    - `dwd_weather` and `pirateweather` fail on the two known misses that do not involve the
      bridge: `www.dwd.de`'s clause, and the minutes-apart A-vs-B value.
    - A service that is down is recorded, not charged to the bridge.
  - **`dwd_weather` publishes no camera**, and nothing is refused at publish in any arm.
- **E4: `suites_all` 35 of 35**, with `selftest_display` the 35th.
- **(A)'s log** has no error from the bridge.

**The recount** is computed, not predicted. It is done offline from the corpus with the rule of
decision 3, and only the file check changes the figures. `alarmo` loses `event`.

## Outcome (2026-10-31, 19:41–21:11)

Runs:
- `bridge-b5-pre` (`0470c7f`), then `bridge-b5` (`32787e7`), each from a fresh clone with (A)
  fresh. Results in `experiments/real_platform/results/bridge_kinds_20261031/b5/`, with
  screenshots (`shots_pre/`, `shots/`) and the verdict outputs (`verdicts_*.txt`).
- `bridge-b5b` (`7b8be15`, the display suite's fix, below), on the (A) the B5 run left. Results in
  `b5b/`.

| | Predicted | Measured |
|---|---|---|
| Fails first | bridge 170/173 (T32 ×3), display 13/14 (D4) | **Held**: 170/173, the three T32 checks showing the published `entity_picture` / `entity_picture_local`; 13/14, D4 with `/picture/sensor…` and `/picture/switch` requested |
| After the fix | bridge 173/173, display 14/14, house test passes | **Held**: 173/173, 14/14 (no `/picture/` request), `selftest_real_house` 6/6 |
| E1, E2 | every publish accepted; "38 of 38" | **Held, but the figure was mine wrong**: `bridge_step5_verdicts` **36 of 36**, 65 entity rows each in (A) as published, nothing refused. Step 5's 38 was a count of checks, not entities: 26 in run C, which included 2 from its unfinished function set, plus run D's 12. One complete run therefore has 24 + 12 = 36. I carried the figure over without recomputing it (AI-use log 37) |
| E3 | 43/45, alarmo 8/8, the egress/local/OAuth subjects as in run C | **Held** (details below) |
| dwd camera | none published | **Held**: `dwd_weather` published `sensor` and `weather` only |
| E4 | suites 35/35 | **Missed: 34 of 35** (below). After `bridge-b5b`: 35 of 35 |
| (A)'s log | no bridge error | **Held**: no ERROR from `confine_bridge`. The only warnings are the cut-off and not-approved notices the suites cause on purpose |

**E3 in detail:**
- `retest_e2e_verdicts` gave 43 of 45, the same two `scheduler` P4 rows.
- alarmo's P1–P4 passed 8/8. (`e2e_ext_verdicts` also checks waste's P7 against the date predicted
  on 2026-10-25, `27.10.2026`; that date has passed, so 8/10. P7 is not a B5 prediction.)
- `nordpool`, `waste_collection_schedule` and `regensburg_transport` passed 16/16 each, and
  `smhi_brandrisk` 20/20.
- `localtuya` found both simulated devices, unconfined and confined-declared, and none
  undeclared.
- `midea_ac_lan` reached its device in both arms; both timed out, as before.
- `trakt_tv` behaved as before.
- `dwd_weather` and `pirateweather` failed only on the two known misses: `www.dwd.de` refused (the
  clause miss), and the A-vs-B value.

**The miss, E4.** In `suites_all`, `selftest_display` failed D1 on the settings page's entity
list. The list draws only the rows in view. By then (A) held 121 entities, the fifteen's included,
so the published row was not drawn. Every other check of that suite passed, D3 and D4 included. On
a fresh (A) it had passed (14/14). This is the third check this week to assume a fresh (A) (AI-use
log 32, 33, 36).

The suite now types the name into the list's search box, as a person would (`bridge-b5b`). It
focuses the second of the list's two search inputs, the one drawn: focusing the first did not filter.

On the reused (A), with the bridge in (A) identical to `bridge-b5`'s: `selftest_display` passed
15/15 alone and 15/15 in `suites_all`, and `suites_all` passed 35 of 35.

**Recount** (committed in `5ac29ae`, `b5/recount.txt`):
- The file rule reproduces 2026-10-27's 249 kind uses.
- The platform rule gives 248 kind uses, 236 bridged (95%), and **28 of 37** integrations whose
  every kind is bridged.
- The unbridged kinds are camera (8), image (3) and legacy notify (1, `alexa_media`).
- `alarmo/event.py` is not a platform.
- "29 of 37" (B4a) was one too many (AI-use log 35). With camera and image, the most is 36.

**Seen, not checked:** after T18 switches (A) to °F and back, the bridged water heater shows its
last °F figures with a °C unit (`shots/devices.png`, "Eco 122 °C") until the sandbox publishes
again. A native water heater keeps its last written state the same way.

**Limits for the report:**
- An update's `release_url` remains a link the user may click.
- The display check covers the overview's devices page, the dialog and its details, and the
  settings entity list. It does not cover history or logbook, which (A) does not load, or cards a
  user writes, such as markdown.
- Links are not clicked.
