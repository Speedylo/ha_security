# Bridge extension, step 2: the commands the mediator forwards, per type — prediction (2026-10-25)

**Committed before the code.** Step 1 (`notes/bridge_types_step1_prediction_20261025.md`) made
buttons, texts, selects and numbers visible in (A); operating them was refused by the mediator,
which forwards `turn_on` and `turn_off` only, for any entity. Younes approved the list below on
2026-10-25: "the list is fine. Just be careful about what is passed and potential injection".

## The rule

| Type | Commands forwarded | Data, exactly |
|---|---|---|
| switch | `turn_on`, `turn_off` | none |
| button | `press` | none |
| text | `set_value` | `value`: a string of at most 255 characters |
| select | `select_option` | `option`: a string of at most 255 characters |
| number | `set_value` | `value`: an int or float, finite, not a boolean |

The type is the entity id's domain; the entity must be owned by the integration, as today.
Everything else is refused and recorded: an unlisted service, a listed one on the wrong type, a
missing key, **any extra key** (an `entity_id` in the data above all, see below), a value of the
wrong type, an over-long string, NaN or infinity. 255 is Home Assistant's own limit on a state
(`MAX_LENGTH_STATE_STATE`). The order of checks: owner, service, data, queue.

**Shape, not meaning.** Whether 22 is inside a number's range, or "away" among a select's options,
is checked by (A)'s Home Assistant before the bridge sends the command (its entity services
validate against the entity's own limits). The mediator checks that what crosses is exactly the
expected kind of value — which is what an injection would have to get past.

**Two defences in depth.**
- Inside the sandbox, the command is run as `{"entity_id": entity, **data}` today, so a key
  `entity_id` in the data would replace the target. The mediator refuses it; the sandbox side is
  changed to put the target last, so it cannot be overridden even if a refusal were ever missed.
  That ordering change is not separately tested (it runs inside the sandbox's runtime).
- A command refused for its data is recorded with each value's **type and length**, not the value,
  so an oversized or hostile value is not written into the durable log.

The clause names: `COMMAND_SERVICES` now reads "only the services listed for the entity's type";
a new `COMMAND_DATA`, "only the data listed for that service, of its kind".

## Predictions

**New offline suite** `confine/selftest_commands.py` (no (A); laptop and Pi), driving
`Mediator.command` with a stand-in for the house that owns one entity of each type:

| | Prediction |
|---|---|
| K1 | Each listed command, with exactly its data, is allowed under `AMBIENT` and pushed to the owning sandbox with that data and nothing more |
| K2 | Refused under `COMMAND_SERVICES`, recorded, nothing pushed: `turn_on` on a number; `press` on a switch; `unlock` on a switch; `set_value` on a select |
| K3 | Refused under `COMMAND_DATA`, recorded, nothing pushed: switch `turn_on` with any data; text `set_value` with an extra `entity_id`; with no `value`; with a dict as `value`; with a 256-character value; number `set_value` with `"22"` (a string), `True`, NaN, infinity; select `select_option` with a list |
| K4 | A refused data value is not in the durable record: a 10,000-character text value is refused, and the record holds its type and length only |
| K5 | **Fails first:** before the change, K1's button/text/select/number cases, K2's `turn_on` on a number and every K3 case fail (today they are refused, or allowed, for the wrong reason) |

**Against (A)** (`selftest_bridge_types`, Pi, fresh clone, (A) `down` then `up --fresh`):

| | Prediction |
|---|---|
| T4′ | Step 1's T4 is replaced: from a user in (A), `button.press`, `text.set_value`, `select.select_option` and `number.set_value` each reach the owning sandbox with exactly its data; once the sandbox answers and republishes, the user's call succeeds and (A) shows the new value (the button: its last-pressed time is set in (A)) |
| T4″ | A value (A) itself rejects — `number.set_value` to 99, outside 5–30 — never reaches the mediator: the user's call fails in (A), and no `entity.command` decision is recorded |
| T7 | Every suite passes, with (A) up; `selftest_audit`'s F3 check still names `COMMAND_SERVICES` for `unlock` on a switch |

Outcome appended below.

---

## Outcome (appended 2026-10-25, after the runs)

Pi, fresh clones of `bridge-s2-pre` (`2bf559c`) and `bridge-s2` (`b7a2d69`), clean before and after,
19:08–19:10; (A) `down` then `up --fresh`. Results:
`experiments/real_platform/results/bridge_types_20261025/s2/`.

| | Outcome |
|---|---|
| K5 | Held: before the change, 6/24 (laptop and Pi). It also showed two holes in the old rule: `turn_on` on a number, and a switch `turn_on` carrying arbitrary data, were both **allowed and pushed** |
| K1–K4 | Held: 24/24 after (laptop and Pi). Every listed command pushed with exactly its data; four wrong services refused under `COMMAND_SERVICES`; ten malformed payloads (an `entity_id` redirect, a dict, 256 characters, a string number, a boolean, NaN, infinity, a list, no value, data on a switch) refused under `COMMAND_DATA`; a 10,000-character value recorded as `str, length 10000` |
| T4′ | Held: from a user in (A), press, set_value (text), select_option and set_value (number) each reached the sandbox with exactly its data (the number as `22.0`); each call succeeded and (A) showed the result (the button its press time) |
| T4″ | Held: `number.set_value` 99 failed in (A) (*"outside valid range 5.0 - 30.0"*) and no command decision was recorded |
| T7 | **Missed as written: 30 of 31 suites.** `selftest_bridge_types` passed alone (23/23), then failed one check inside `suites_all`, which runs it again against the same (A): T2 expected the button to read `unknown`, and it read the time T4′ had pressed it. (A) was right — a button's state is its last press, kept — and the test's assumption of a fresh (A) was wrong. `selftest_audit` passed, with `COMMAND_SERVICES` for `unlock` on a switch |

(A)'s log: no error from the bridge. The test is corrected (`T2` accepts `unknown` or a valid
last-pressed time for a button) and is verified in step 3's runs, not by repeating this one.

**Process, recorded.** The rule's code was written before the prediction and the failing suite were
committed. Both were written, and the suite run against the old code (6/24), before any code; they
were then committed alone (`2bf559c`) ahead of the code (`b7a2d69`). The sandbox-side ordering
(`entity_id` last) is not separately tested, as predicted.
