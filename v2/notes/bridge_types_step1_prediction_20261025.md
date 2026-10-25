# Bridge extension, step 1: button, text, select, number — prediction (2026-10-25)

**Committed before the code.** Younes chose (2026-10-25) to extend the bridge
(`notes/bridge_entity_types_20261025.md`), aiming first at the entity types the fifteen end-to-end
integrations publish, and said "start". Step 1 is the four value types: `watchman` publishes a
button and a text; select and number follow the same pattern and are used by 19 and 18 of the 37
head integrations.

## Scope of this step: the household **sees** them, correctly described

A published entity of each type becomes a registry-backed entity of that type in (A), with the
state and the attributes Home Assistant needs to draw its control: a select's `options`; a
number's `min`, `max`, `step`, `mode` and unit; a text's `min`, `max`, `pattern` and `mode`.

**Operating them is step 2, not this one.** Pressing the button or setting a value sends a
command, and the mediator forwards only `turn_on` and `turn_off` today (`mediator.py`,
`COMMAND_SERVICES`). Which services it forwards for each type is a security decision for Younes
(step 2). Until then a command on one of these is refused by the mediator, recorded, and the user
sees the refusal — which this step checks too, so nothing silently half-works.

A button's state in Home Assistant is the time it was last pressed **in that instance**
(`ButtonEntity.state` is final); it is not mirrored from the sandbox. It reads `unknown` in (A) until
pressed there, as a native button does.

## Predictions

New suite `confine/selftest_bridge_types.py`, against (A) like `selftest_real_platform`, with the
mediator and an in-process sandbox. Run on the Pi from a fresh clone, (A) `up --fresh`.

| | Prediction |
|---|---|
| T1 | For each of button, text, select, number: the publish is allowed, and (A) gets an entity-registry row of that domain, platform `confine_bridge`, `unique_id` naming the integration |
| T2 | text, select, number: (A) holds the published state; select's `options`, number's `min`/`max`/`step`/`mode`/unit and text's `min`/`max`/`pattern`/`mode` are in its attributes as published; a button reads `unknown` |
| T3 | An update republished from the sandbox changes the state in (A) (text, select, number) |
| T4 | A command on one of them (`number.set_value`) is refused by the mediator under `COMMAND_SERVICES`, recorded, and fails the user's call in (A) with that reason |
| T5 | A type still not supported (`light`) is refused at publish, as before |
| T6 | **Fails first:** before the change T1–T3 fail (the bridge refuses the four domains) |
| T7 | Every suite `experiments/selftests/suites_all.sh` runs still passes, with (A) up |

T6 is run on the laptop's reading only as far as it can go without (A): the suite is run on the Pi
against the pre-change commit first, then against the change. Outcome appended below.

---

## Outcome (appended 2026-10-25, after the runs)

Pi, fresh clones of `bridge-s1-pre` (`0638f2a`) and `bridge-s1` (`90ab606`), clean before and after.
Results: `experiments/real_platform/results/bridge_types_20261025/` (`s1-pre/`, `s1/`).

| | Outcome |
|---|---|
| T6 | Held: before the change, 2/16 — T1–T4 failed with *"the bridge cannot stand in for a button entity"* (and text, select, number); T5 and the chain check passed. T6 named only T1–T3; T4 failed too, since there was no entity to command |
| T1–T5 | Held: after the change, **16/16**. Each type is a registry row of its own domain owned by the bridge; (A) holds the state, the select's options, the number's range, step, mode and unit, the text's limits and mode; the button reads `unknown`; republishes change the state; `number.set_value` is refused by the mediator under `COMMAND_SERVICES`, recorded, and the user's call fails at once with the reason; a light is still refused |
| T7 | Held: 30 of 30 suites exit 0 (the new suite included), with (A) up |

(A)'s own log, `~/r2exp/houseA/home-assistant.log`, has no error from the bridge. (The driver's line
"bridge errors in (A) log: 0" read a path that does not exist and counts nothing; the real log was
checked by hand afterwards.)

**A void first run, kept as `s1-void-a-not-restarted/`.** The first driver ran `house_a up --fresh`
without `down`; (A) was already running from the pre-change run, so `up` refused ("something already
answers on 8123") and the suite ran against the old bridge: 2/16, the pre-change result again. It
measured nothing about the change; it was stopped during the suites, the driver corrected to stop (A)
first, and the run made again from the same clone. Recorded because it is a repeat, not to obtain a
pass: the cause is the driver, and the void run's result is the pre-change one.
