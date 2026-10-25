# F66: the bridge passes "unknown" to a numeric sensor as its value — prediction (2026-10-25)

**Committed before the fix.** Found by bridge step 5's first real-house run
(`notes/bridge_types_step5_prediction_20261025.md`), the first time the end-to-end set published to
(A) rather than to the stand-in.

## What was seen

`powercalc`'s power sensor (`device_class: power`, `state_class: measurement`, unit W) is published
with the state `unknown` before it has a reading. The bridge's sensor sets its native value to the
string `"unknown"`; Home Assistant then refuses to write the state, because a sensor with a device
class, state class and unit must have a numeric value (`sensor/__init__.py:737`), and the publish
fails in (A) with *"Error handling message: Unknown error"*. (A)'s log of 20:06–20:07 has ten such
tracebacks, all `sensor.lamp_power_power`. The stand-in accepted any value, so no earlier run saw it.

The same holds for any entity published `unavailable`: the bridge has no notion of availability, so
(A) shows such an entity as some other state, not as unavailable. And a restart restores a sensor's
last state with the same assignment, so a sensor last seen `unknown` would fail on (A)'s start too.

## The fix

- A sensor's native value is `None` when the published state is `unknown` or `unavailable` (as the
  binary sensor already does), and the restore does the same.
- Every bridged entity is unavailable in (A) while its published state is `unavailable`
  (`_attr_available`), whatever its type.

## Predictions

New cases in `selftest_bridge_types` (Pi, (A) fresh), `U1`–`U4`:

| | Prediction |
|---|---|
| U1 | A sensor with device class power, state class measurement and unit W, published `unknown`, is accepted, and (A) shows `unknown` |
| U2 | Republished `12.5`, (A) shows `12.5`; republished `unavailable`, (A) shows `unavailable` |
| U3 | A switch published `unavailable` shows `unavailable` in (A) |
| U4 | **Fails first:** before the fix, U1 fails (the publish is refused by (A)) and U3 fails ((A) shows `unknown`) |

Then step 5's real-house runs are made again from a fresh clone (step 5's note, E1–E4), since its
first complete run had this defect in it. Outcome appended below.

---

## Outcome (appended 2026-10-25)

Pi, run C of bridge step 5 (`experiments/real_platform/results/bridge_types_20261025/s5c/`).
**Every prediction held**, U4 slightly understated: it named U1 and U3, and U2's `unavailable` check failed first too (the old sensor showed `12.5`). Fails first at this note's `-pre` tag (`bridge_types_f66-pre.log`: U1–U3
failed, 49/52; `bridge_types_f67-pre.log`: V1–V3 failed, 53/56); after the fix, `selftest_bridge_types`
56/56, and in step 5's real-house runs every affected entity is in (A) in its published state.
