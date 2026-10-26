# F68: designating the mediator never checks that the user exists — prediction (2026-10-26)

**Committed before the fix.** Found in (A)'s log during bridge step 5
(`notes/bridge_types_step5_prediction_20261025.md`): a `RuntimeWarning: coroutine
'AuthManager.async_get_user' was never awaited` from the bridge.

## What is wrong

`ws_designate_mediator` (`framework/ha_bridge/confine_bridge/__init__.py`) is a plain callback, and
it calls `hass.auth.async_get_user(user_id)` without `await`. The call returns a coroutine, which is
never `None`, so the "no such user" refusal can never happen: an admin who names an id that matches
no user is told the designation succeeded. The bridge then admits no mediator at all, because no
user has that id, and the real mediator is refused until an admin designates it again.

This fails safe. Only an admin can designate (F45, mutant M18c), and an id with no user behind it
cannot log in, so nobody gains access. The harm is a check that does nothing, and a mistyped id that
silently cuts the mediator off.

## The fix

The handler becomes asynchronous (`@websocket_api.async_response`, `async def`, as `ws_publish`
already is) and awaits `async_get_user`. Nothing else changes.

## Predictions

New checks in `selftest_real_platform`'s F45 block (Pi, (A) fresh):

| | Prediction |
|---|---|
| G1 | An admin designating an id that matches no user is refused |
| G2 | The refusal's code is `no_such_user` |
| G3 | The real mediator can still subscribe to commands afterwards |
| G4 | **Fails first:** at this note's `-pre` tag, G1 and G2 fail (the designation is accepted) and every other check passes; G3 passes there too, only because the test designates the real mediator again after an accepted designation, which is the repair an admin would have to make |

Then every suite on the Pi from the fix's tag (33 expected to pass), with (A) fresh, and (A)'s log
checked for the `never awaited` warning: present at `-pre`, absent after the fix. Outcome appended
below.

---

## Outcome (appended 2026-10-26)

Pi, from fresh clones of `f68-pre` and `f68-fix`, (A) fresh before each
(`experiments/real_platform/results/f68_20261026/`). **Every prediction held.** At `f68-pre`,
`selftest_real_platform` 53/55, the two failures G1 and G2 ("it was accepted"), and (A)'s log has the
`never awaited` warning once. After the fix, 55/55: the refusal is `no_such_user` and the mediator
still subscribes (G3); the warning is absent. Every suite passed, 34 of 34 (one more than bridge step
5's 33: `selftest_house_a`, added with F69).
