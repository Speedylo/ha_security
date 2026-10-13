# T06's subscription half, paired on one platform: predictions

**Written 2026-10-13, before the harness exists and before any run.** Younes decided on 2026-10-13
that T06's subscription verdict needs a true pair. Commit before the harness runs; do not edit after
a run (`verify/prereg.py`). Results go to `experiments/pair_subscriptions/results/`.

## 1. Why the current figure is not a pair

Appendix C's Table C.4 and §7.14's register row say "undeclared changes delivered 4 of 4
unconfined, 0 of 3 confined". The two numbers come from two experiments:

- **4 of 4** is §7.14 (`reads_unconfined.py`, August): real Home Assistant 2026.8.3 in process,
  four changes to `device_tracker.younes_phone`, `binary_sensor.bedroom_occupancy`,
  `lock.front_door` and `alarm_control_panel.home_alarm`.
- **0 of 3** is §7.36 (`selftest_push`, 2026-10-04): the real mediator over the **stand-in**
  platform, three changes to `sensor.bedroom_occupancy`, `lock.front_door` and `person.younes`.
  Its control is the in-suite bypass (M10's mutation): with the subscription table widened, the
  same observer sees 3 of 3.

Appendix C defines *paired* as the threat also shown to succeed against the unconfined arm on the
same host and platform release. The stand-in is not a platform release, and the two arms changed
different entities. So the row compares two experiments, not two arms of one.

## 2. The design

One harness, `confine/pair_subscriptions.py`, run on the Pi, both arms against Home Assistant
2026.8.3 and the same four entities:

| | |
|---|---|
| Declared | `sensor.pair_declared`, the one entity the integration subscribes to |
| Undeclared | `sensor.bedroom_occupancy`, `lock.front_door`, `person.younes` (§7.36's three) |
| The change | the platform's own state write: `hass.states.async_set` in process, `POST /api/states/<id>` in (A), which calls the same method. Each entity is seeded `0`, then set to `on` |
| Counted | which of the three undeclared changes reach the integration's observer |

- **Unconfined arm.** `confine/pair_unconfined.py`, run by the Pi's Python 3.14 (`~/r2exp/ha314`).
  It builds Home Assistant with `build_hass` (no `http`, no port), registers a listener on
  `EVENT_STATE_CHANGED` as any integration may, and makes the four changes. The observer is that
  listener. (A) is down while it runs, per the rule from F56.
- **Confined arm.** The real `Mediator` and `RealPlatform` against (A), freshly built, with
  `selftest_push`'s `Sandbox` on the far end of the channel (identity from the socket, as in every
  real run). The sandbox subscribes to the declared entity only, and the four changes are made in
  (A) over its REST API. The observer is the sandbox's `on_push`.
- **Control, confined arm only.** Then the filter is bypassed in the harness, as `selftest_push`
  does for M10: the three undeclared entities are added to the mediator's subscription table and to
  (A)'s watched set, and the three are changed again to `leaked`. This shows the zero comes from the
  filter, not from an observer that cannot see. Two layers are bypassed because two exist on the
  real platform: (A) is asked only for subscribed entities (§7.37, R4), and the mediator forwards
  only to subscribed channels (§7.36).

The script `experiments/pair_subscriptions/run.sh` stops (A), runs the unconfined arm, brings (A)
up with `--fresh`, and runs the confined arm, writing one JSON per arm.

## 3. Predictions

| # | Prediction | Falsified by |
|---|---|---|
| P1 | Unconfined: **3 of 3** undeclared changes delivered, and the declared change too | fewer than 3 |
| P2 | Confined: **0 of 3** undeclared changes delivered | any undeclared change delivered |
| P3 | Confined: the declared change is delivered (the observer works) | the declared change missing within 5 s |
| P4 | Confined control: with both layers bypassed, **3 of 3** `leaked` changes seen | fewer than 3 |
| P5 | The decision log holds the subscription grant, its chain verifies, and no delivery wrote a record | a delivery record, or a chain break |
| P6 | Both arms report Home Assistant 2026.8.3 and the same host | any difference |

## 4. What follows from each outcome

- **All six hold.** Table C.4's T06 row and its sources read "0 of 3 confined, 3 of 3 unconfined,
  paired on Home Assistant 2026.8.3; the filter's role shown by the bypass". §7.14's 4 of 4 stays
  as history. The harness joins the week-5 rerun.
- **P1 fails.** The unconfined arm under-counts, so the harness, not the design, is wrong; find out
  why before any figure is used.
- **P2 fails.** A finding: an undeclared change crosses on the real platform. Rated and logged in
  Appendix F before anything else is written.
- **P3 or P4 fails.** The zero proves nothing in that run; the T06 row keeps its current wording,
  marked as unpaired.

## 5. Result (2026-10-13, appended after the runs)

Two runs at tag `pair-2026-10-t06`, identical: **P1–P6 all held** (unconfined 3 of 3; confined 0 of
3, declared change delivered, control 3 of 3; one decision on disk, chain clean; 2026.8.3 on the
Pi in both arms). One fault before any measurement: `run.sh` called `realpath` on a directory not
yet created; fixed at the same tag before the first run. Results in
`experiments/pair_subscriptions/`. Per §4, Table C.4's T06 row now cites this pair.
