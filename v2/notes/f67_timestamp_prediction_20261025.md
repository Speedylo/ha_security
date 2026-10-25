# F67: the bridge passes a timestamp sensor's state as a string — prediction (2026-10-25)

**Committed before the fix.** Found by bridge step 5's complete real-house run
(`notes/bridge_types_step5_prediction_20261025.md`, outcome): `dwd_weather` publishes two sensors with
device class `timestamp`; (A) refused to add both — *"Invalid datetime: … has timestamp device class
but provides state 2026-10-25 15:00:00+00:00:<class 'str'>"* — so they were registered but have no
state. Home Assistant requires a `datetime` as the native value of a `timestamp` sensor and a `date`
for a `date` sensor; the bridge passed the published string. The stand-in accepted it.

## The fix

A bridged sensor whose device class is `timestamp` takes its state as an ISO date-time (with or
without the `T`; a time zone added if it has none) and one whose class is `date` as an ISO date; a
state that does not parse gives no value, as `unknown` does (F66). The restore does the same.

The step-5 check E2 compares a published and a shown state as strings; (A) writes a timestamp with a
`T`, so the same instant published with a space would count as different. `real_house.in_house`
compares two states that both parse as ISO date-times as times. (Recorded here because it changes how
a check decides.)

## Predictions

New cases in `selftest_bridge_types` (Pi, (A) fresh):

| | Prediction |
|---|---|
| V1 | A `timestamp` sensor published `2026-10-25 15:00:00+00:00` (with a space, as `dwd_weather` publishes it) is in (A) with the state `2026-10-25T15:00:00+00:00` |
| V2 | One published `2026-10-25T18:00:00+00:00` shows that state; republished `unknown`, (A) shows `unknown` |
| V3 | A `date` sensor published `2026-10-28` shows `2026-10-28` |
| V4 | **Fails first:** at the commit before the fix, V1–V3 fail ((A) cannot add the entities, so they have no state) |

Outcome appended below.
