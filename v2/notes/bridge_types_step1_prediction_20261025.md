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
