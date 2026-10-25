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

---

## Outcome (appended 2026-10-25, after both runs)

Run from a fresh clone of `e2e-ext-2026-10` (`7324f49`), clean before and after, 17:36–17:42 on the Pi.
Results: `experiments/end_to_end/results/ext_20261025/` (`verdicts.txt`, `waste.log` with the harness's
checks, the raw JSON, the driver).

**Every prediction held: P1–P4 and P7 10/10 (`verify/e2e_ext_verdicts.py`); P5, P6 and P8 16/16
(`endtoend_egress`'s checks).**

- `alarmo`: in both arms the alarm panel went `disarmed → arming → armed_away → disarmed`, both commands
  accepted; the confined arm made no refused request. Record: it published `alarm_control_panel` only
  (no `event` entity appeared in either arm), which the real bridge refuses — in a real house today its
  panel could not appear. The unconfined arm's log ends with `KeyError: 'recorder'`, which touched no
  check.
- `waste_collection_schedule`: unconfined and confined published the same six sensors with the same
  dates (WET `on Tue, 27.10.2026`, RM1 `on Fri, 30.10.2026`, …); the only granted destination was
  `ead.darmstadt.de:443`; nothing was refused with the clause; without it, every connection was refused
  with the egress clause and the flow stopped at its own `fetch_error`, so no entry was created. No
  second host: arm A's recorder resolved `ead.darmstadt.de` and two local addresses.

**Not predicted — a partial cost of confinement (finding F65, cause not established).** Confined, the
integration's calendar entity is missing: the calendar component depends on `http`, whose setup failed in
the sandbox with *"Could not determine source ip because the system does not have any enabled IPv4
addresses and creating a socket failed"*. Unconfined, the calendar exists. `alarmo`, which also depends on
`http`, set up without error in `endtoend_function`, so the failure is specific to the egress harness's
sandbox; the likely mechanism (not verified) is that `network.async_get_source_ip` opens a UDP socket
towards a public address, which the egress shim intercepts. The sensors carry the schedule, so the
integration works, but one of its two kinds of entity is lost to confinement — the first such loss in a
run where the unconfined arm has it. (The calendar would also be refused by the real bridge, F64.)
