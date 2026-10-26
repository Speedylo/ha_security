# A bridged switch shows the state its integration published — prediction (2026-10-26)

**Committed before the change.** Younes chose option (a) on 2026-10-26: mirror the published state.

## What is wrong

Home Assistant declares a switch's state to be `on` or `off` (`ToggleEntity.state`, marked
`@final`, which is a hint for type checkers and is not enforced when the code runs). `scheduler`
overrides it: its switch reports `on` (enabled, waiting), `off` (disabled), `triggered` (for the 60 s
after a time slot fires, `switch.py:294`) and `completed` (a one-off schedule that has run). The
bridged switch takes the published state as `state == "on"` (`confine_bridge/switch.py`), so
anything else shows `off` in (A). During the trigger minute the house shows the switch off while
the integration is running it: the opposite of its state. Bridge step 5 recorded this as E2's one
miss (37 of 38).

## The change

The bridged switch keeps the published state as it is and reports it as its state, overriding
`ToggleEntity.state` the way `scheduler`'s own switch does. `unknown` and `unavailable` are handled
as before (unknown; unavailable by F66). `is_on` is unchanged (`True` only for `on`), so a switch
that publishes `on` or `off`, as every other integration's does, behaves exactly as before.

What stays different from `scheduler` unconfined, by design of this change: `scheduler` counts
`triggered` as on, so its `switch.toggle` service turns a triggered schedule off; the bridged
switch counts it as off, so `switch.toggle` sends `turn_on`. Turning it on or off explicitly is
unaffected. Forwarding `toggle` itself to the sandbox would remove the difference, but it widens the
command list Younes approved in bridge step 2 (switch: `turn_on`, `turn_off`), so it is not part of
this change.

No new exposure: a sensor already shows any string its integration publishes, and Home Assistant
refuses any state over 255 characters for every entity.

## Predictions

New cases in `selftest_bridge_types` (Pi, (A) fresh); X4 only with `--restart`, which the driver
passes and `suites_all` does not:

| | Prediction |
|---|---|
| X1 | A switch published `triggered` is a switch entity owned by the bridge, and (A) shows `triggered` |
| X2 | Republished `on`, `off`, `completed`, `unknown`, then `triggered`, (A) shows each |
| X3 | After (A) restarts, the switch shows `triggered`, its last published state |
| X4 | **Fails first:** at this note's `-pre` tag, X1 fails ((A) shows `off`), X2 fails for `completed` and the final `triggered`, X3 fails; `on`, `off`, `unknown` pass; every other check passes |

Then, from the change's tag with (A) fresh:

| | Prediction |
|---|---|
| X5 | The end-to-end function set against (A) (`endtoend_function --platform real`): `bridge_step5_verdicts` holds for every arm (run D of step 5 was 11 of 12, `scheduler`'s the miss), so E2 is 38 of 38 |
| X6 | `retest_e2e_verdicts` stays 43 of 45, the same two rows failing: P4's "switch `off` after a single run", in both arms. Those rows check what `scheduler` itself does (its switch is still `triggered` when the run ends, unconfined too), not what the bridge shows |
| X7 | Every suite passes, 34 of 34 |

Outcome appended below.

---

## Outcome (appended 2026-10-26)

Pi, from fresh clones of `switch-mirror-pre` and `switch-mirror`, (A) fresh before each step
(`experiments/real_platform/results/switch_mirror_20261026/`). **Every prediction held.**

- X4: at `-pre`, 59/63, the four failures exactly those predicted, (A) showing `off` each time.
- X1–X3: after the change, `selftest_bridge_types --restart` 63/63; the switch shows `triggered`,
  `on`, `off`, `completed`, `unknown`, `triggered`, and `triggered` again after (A) restarts.
- X5: `bridge_step5_verdicts` 12/12 on the function set against (A), so E2 is 38 of 38.
- X6: `retest_e2e_verdicts` 43 of 45, the same two P4 rows. Confined, the switch is `triggered` at
  the end, as before. Unconfined, the row's detail differs from step 5's run D: the switch's history
  is the same (`unknown`, `on`, `triggered`), but this time it is absent from the end-of-run snapshot,
  where run D had it `triggered`. That arm does not use the bridge; the likely reading, not
  established, is that `scheduler` removed the finished one-off schedule within the settle window.
- X7: every suite passed, 34 of 34.
