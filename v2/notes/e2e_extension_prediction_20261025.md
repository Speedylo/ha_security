# End-to-end extension: `alarmo` and `waste_collection_schedule` — prediction (2026-10-25)

**Committed before either run.** Younes decided (2026-10-25) to run, before the interim submission, the
two integrations that `notes/credential_survey_breakdown_20261025.md` showed need no account; the third
(`solcast_solar`) waits for its key. Option 1 of the bridge question applies
(`notes/bridge_entity_types_20261025.md`): both run against the harness's stand-in for the house, like
the other thirteen, and each run records which of its entity types the real bridge could represent.

## Environment

Raspberry Pi 5, 4 GB; Home Assistant 2026.8.3 (`~/r2exp/ha314`); the head corpus at its pinned commits
(`~/r2exp/corpus`); a fresh clone of this repository at tag `e2e-ext-2026-10`, as the final rerun used.
Results to `experiments/end_to_end/results/ext_20261025/`. Verdicts: `verify/e2e_ext_verdicts.py`, plus
`endtoend_egress`'s own checks for the second run.

## Run 1 — `alarmo` (`confine.endtoend_function --only alarmo`, both arms)

Alarmo's first setup (`store.async_factory_default`) creates one area, "Alarmo", whose entity is
`alarm_control_panel.alarmo`, with Away enabled (60 s exit delay) and Home enabled, and no code needed to
arm or disarm. Stimulus, in each arm, as a command inside the integration's own platform (the path
`scheduler`'s retest used): `alarm_control_panel.alarm_arm_away` at 5 s, `alarm_disarm` at 85 s;
settle 100 s. Permissions: none (it needs nothing from the house).

| | Prediction | Criterion |
|---|---|---|
| P1 | The entry is LOADED in both arms | `loaded` true in each |
| P2 | `alarm_control_panel.alarmo` is published and starts `disarmed`, in both arms | first collapsed state `disarmed` |
| P3 | It goes `disarmed → arming → armed_away → disarmed`, in both arms | that order within its collapsed history |
| P4 | Both commands are accepted in both arms | two step records, each `ok` |

`arming` before `armed_away` is what shows the 60 s exit delay was applied; the disarm at 85 s leaves
about 20 s of margin after it ends. Recorded, not criteria: the confined arm's refused decisions (none
expected, since alarmo reaches for nothing outside itself, but its panel and MQTT hooks may try), and the
entity types it publishes. **Expected record:** `alarm_control_panel` (refused by the real bridge) and
`event` (refused) — so in a real house today its alarm panel could not appear.

## Run 2 — `waste_collection_schedule` (`confine.endtoend_egress --subject waste_collection_schedule`)

Source `ead_darmstadt_de` (the Darmstadt waste service), street "Stresemannstraße", the source's own first
test case. Its only URL is `ead.darmstadt.de`, read from the source before any run, so the declared clause
is `ead.darmstadt.de:443`. It fetches with `requests` during the setup flow (the argument check) and after
setup. With no sensor configured, setup creates one sensor per collection type, each stating the next
date. A probe of the source on the Pi on 2026-10-25 (the source alone, not the integration) returned 180
dates, the next being WET on 27 October.

The harness's own checks apply, as for the other internet-facing integrations:

| | Prediction | Criterion (`endtoend_egress`) |
|---|---|---|
| P5 | A, unconfined: loads and publishes fetched sensor values | its A checks pass |
| P6 | B, confined with the clause: loads; publishes sensors through the mediator; at least one value equals A's; the only granted destination is `ead.darmstadt.de:443`; nothing refused; the record's chains verify | its B checks pass |
| P7 | The WET sensor reads `on Tue, 27.10.2026` in A and in B | `verify/e2e_ext_verdicts.py` |
| P8 | C, confined without the clause: no fetched value crosses; the refusal is recorded with the egress clause; the flow fails at its argument check, so no entry is created | its C checks pass |

There is no arm D (one host). **If arm A's recorder shows a second host** (a redirect, say), it is a miss
in the clause read from the source and is reported as such, not added afterwards — the rule the
`dwd_weather` subject set. **Expected record:** `sensor` (supported) and `calendar` (refused).

## What a failure means

A prediction that fails is reported, with the unconfined arm consulted before anything is charged to
confinement. Neither run is repeated to obtain a pass; a repeat for a cause outside the project (the
Darmstadt service down, say) is recorded with that cause. The outcome is appended to this note.
