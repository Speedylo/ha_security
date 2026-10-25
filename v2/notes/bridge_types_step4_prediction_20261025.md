# Bridge extension, step 4: calendar and weather, and questions with answers — prediction (2026-10-25)

**Committed before any code.** Younes approved the design on 2026-10-25 ("the design is fine, write
the prediction"). Subjects in the end-to-end set: `waste_collection_schedule` and `trakt_tv`
(calendar), `pirateweather` and `dwd_weather` (weather).

## The design

Until now data crossed in two directions only: states out of the sandbox, commands into it. A
calendar view and a forecast card **ask** the integration a question and need an answer. So:

1. **A question is a command with an answer.** It travels the command path (decided, recorded,
   pushed to the owning sandbox, answered on that channel only), with two services added to the
   mediator's list:

   | Type | Question | Data, exactly |
   |---|---|---|
   | calendar | `get_events` | `start`, `end`: ISO 8601 date-times, strings of at most 40 characters |
   | weather | `get_forecasts` | `type` ∈ {daily, hourly, twice_daily} |

   The sandbox runs Home Assistant's own response service (`calendar.get_events`,
   `weather.get_forecasts`, `return_response=True`) on its entity and answers with the list.

2. **The answer comes from the untrusted side**, so the mediator checks its shape before (A) sees it:
   - an answer is a list of at most **500** items, at most **256 KiB** as JSON;
   - a calendar event has exactly `summary` (string ≤ 255, required), `start` and `end` (ISO date or
     date-time strings ≤ 40, required), and optionally `description` (string ≤ 4,096) and
     `location` (string ≤ 255) — the fields Home Assistant's own `get_events` returns
     (`calendar.const.LIST_EVENT_FIELDS`);
   - a forecast entry has `datetime` (ISO string ≤ 40, required), optionally `condition` (string
     ≤ 64), `is_daytime` (boolean), `wind_bearing` (number or string ≤ 8), and the numbers
     `temperature`, `templow`, `apparent_temperature`, `dew_point`, `pressure`, `wind_speed`,
     `wind_gust_speed`, `precipitation`, `precipitation_probability`, `humidity`,
     `cloud_coverage`, `uv_index` (finite, or null) — `weather.Forecast`'s display fields;
   - nothing else. An answer that fails is not relayed: the user's question fails with the reason.
   - An answer attached to an ordinary command (a switch's `turn_on`) is never relayed.

3. **The log records each question, and each answer by its shape** — how many items, how many
   bytes, accepted or refused — under a new clause `QUERY_ANSWER`, never the event titles or the
   forecast values.

4. **The bridge** gains a calendar and a weather platform. A calendar's state (`on` while an event
   is running) and its current event come from the published attributes (`message`, `start_time`,
   `end_time`, `all_day`, `location`, `description`); its `async_get_events` asks the question. A
   weather's state is its condition, its current values and units come from the attributes (the
   sandbox's units, metric), and its forecasts are asked for; when the sandbox republishes, open
   forecast cards are told to ask again (`async_update_listeners`).

## Predictions

**Offline, new suite `selftest_queries`** (laptop and Pi):

| | Prediction |
|---|---|
| Q1 | `calendar.get_events` with ISO `start`/`end`, and `weather.get_forecasts` with each of the three types, are allowed and pushed exactly |
| Q2 | Refused, nothing pushed: `get_events` with an extra key, a non-ISO `start`, a 41-character `start`; `get_forecasts` type `monthly` (`COMMAND_DATA`); `get_forecasts` on a calendar, `get_events` on a weather or a sensor (`COMMAND_SERVICES`) |
| Q3 | A well-formed answer (two events; three forecast entries) is relayed to the platform unchanged, with the question's id |
| Q4 | Refused under `QUERY_ANSWER` and not relayed — the platform is told the question failed: an event with no `summary`; with an extra key; a 256-character `summary`; a 4,097-character `description`; a non-ISO `start`; 501 events; 300 events over 256 KiB; a forecast entry with no `datetime`; a string `temperature`; a NaN `temperature`; an extra key; an answer that is not a list |
| Q5 | Neither an accepted nor a refused answer's content is in the durable log (an event titled `Dentist, Dr Example` is absent); each answer's record gives its item count and size |
| Q6 | An answer attached to a switch's `turn_on` result is not relayed (the platform receives no answer) |
| Q7 | **Fails first:** before the change, Q1, Q2's four data cases (refused, but under `COMMAND_SERVICES`), Q3, Q4 and Q5's record check fail; Q5's content check and Q6 pass trivially, since no answer is relayed at all. Run on the laptop before this note was committed: 6/29 |
| Q8 | `selftest_commands` still passes (57/57) |

**Against (A), `selftest_bridge_types`** (Pi, fresh clone, (A) `down`, `up --fresh`):

| | Prediction |
|---|---|
| W1 | A published calendar and weather each become a registry row of their domain owned by the bridge; (A) holds the calendar's state and `message`, and the weather's condition, `temperature` and `temperature_unit` |
| W2 | A user in (A) calls `calendar.get_events` with a response: the sandbox receives `get_events` with `start` and `end`; it answers two events; the user's response lists those two summaries |
| W3 | `weather.get_forecasts` type daily: the sandbox receives `{"type": "daily"}`; it answers three entries; the user's response has three entries with their temperatures |
| W4 | A malformed answer (an event with an extra key) fails the user's call, and nothing of it reaches (A) |
| W5 | The event summaries are not in the run's durable log |
| W6 | Every suite passes with (A) up, the real-house suite included twice on the same (A) |

Before the change W1–W5 fail (the bridge refuses both domains). Outcome appended below.
