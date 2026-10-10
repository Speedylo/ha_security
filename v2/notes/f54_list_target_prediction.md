# F54, a confined command that loses its target: predictions for the fix

**Written 2026-10-10, before the test is changed and before any run.** Younes decided on 2026-10-09
to fix F54 rather than state it as a limitation. This note fixes what the failing test must show
before the fix, what the fix changes, and what every run after it must show. Commit before the test
runs; do not edit after a run (`verify/prereg.py`). Results go to `experiments/verify/results/f54/`.

## 1. What F54 is

The 2026-10-09 retest (`notes/e2e_functional_retest_prediction.md` §7) found two defects in one
path. The first is in the bridge. `Bridge._forward_service_call` (`sandbox_runtime.py`) forwards a
service call's data only where a value is a `str`, an `int` or a `float`. `scheduler` names its
target as a list (`"entity_id": ["light.living_room"]`), so its confined `light.turn_on` reached the
platform as `{"brightness": 200}`. A call with no target controls nothing, so the schedule fired and
the lamp did not change.

The second is in the record, and it is wider than `scheduler`. The mediator's durable decision
record (`AuditLog.decision`, `audit.py`) keeps the sandbox's own claims in `requested`, but it reads
them from the request's top level only, and a service call's targets are inside `data`. No service
call has ever had its entity in the record. `adaptive_lighting`'s call in the same retest reached
the platform with `"entity_id": "light.living_room"`, and its decision record still says only
`light.turn_on`. The audit trail can therefore say which service was granted, but not which device
it was used on.

## 2. Why fixing it widens nothing

A `services.call` clause grants a service, not a device: `light.turn_on` declared means any light
(`platform.py`, `ActingPolicy`, the `service.call` branch). A single string target is forwarded
today, so a confined integration can already turn on any light, one call at a time. Forwarding a
list lets it name several lights in one call, which is the same authority in fewer calls. Without a
target, Home Assistant's entity services act on no entity at all (`helpers/service.py`,
`_get_permissible_entity_candidates`, at 2026.8.3: the candidates are the referenced entities, and
none are referenced). The defect therefore only ever made a granted call do less, and the fix
restores what the clause already granted. The same code shows how wide that grant already was. A
string `"entity_id": "all"` selects every entity the service applies to, and a string `area_id`,
`device_id`, `floor_id` or `label_id` selects whatever it contains. All five are forwarded today as
strings. A list adds no target that a string could not already name.

The record must not repeat T4's mistake. T4 found that `decision()` once chose its `target` from
whichever field the sandbox sent, so a `lock.unlock` was recorded against `sensor.harmless`. The
`target` stays what the decision was made on, the service (`target_of`). The entities go into
`requested`, which holds what the sandbox asked about and is labelled as its claim.

## 3. The fix

1. **Bridge.** Forward each value of a service call's data that `_plain` accepts: a scalar
   (`str`, `int`, `float`, `bool`, `None`) or a list of scalars. `_plain` is already the rule for
   attributes on the way out (W1 step 2), so the boundary gets one rule for both directions in place
   of two. The plan of 2026-10-09 said "lists of strings". `_plain` is slightly wider: it also lets
   through lists of numbers (`rgb_color`) and `None`, which no service clause polices either. Dicts
   are still dropped, and §12 states that as a limitation.
2. **Record.** For a `service.call`, `requested` gains each of Home Assistant's five target fields
   (`entity_id`, `device_id`, `area_id`, `floor_id`, `label_id`, the fields `TargetSelection`
   reads) that the sandbox put in `data`, copied whatever its shape. `target` is unchanged.

Nothing else changes: not the policy, the manifest, the channel or the in-memory `mediator.audit`.

## 4. The test, written first

`selftest_bridge` already sends `lock.lock` from inside a real sandbox through real Home Assistant,
but always with empty data (`probe_services`). The test adds an opt-in spec key,
`probe_service_data`, so that this suite's `lock.lock` is called with
`{"entity_id": ["lock.front_door", "lock.back_door"], "area_id": "hall"}`. The list is F54's
case; the string `area_id` already reaches the platform today, so it tests the record alone. Every
other user of `probe_services` is unchanged. It adds two checks:

- **F54a** the platform received `lock.lock` with exactly that data;
- **F54b** the durable decision record for that call has `target` `lock.lock`, and in `requested`
  the same `entity_id` list and `area_id` `"hall"`.

## 5. Predictions

**P1, the test before the fix** (the commit that adds the test, run on the Pi): F54a fails, and the
platform's call shows data `{"area_id": "hall"}`, the list dropped. F54b fails, and `requested`
holds `service` alone.
Every check that existed before passes, including "the platform saw only the permitted call". The
suite exits 1. If either new check passes before the fix, the test does not test F54, and the fix
waits until it does.

**P2, the test after the fix** (tag `fix-2026-10-f54`): every check passes, F54a and F54b
included, and the suite exits 0.

**P3, the regression at the tag**, from a fresh clone on the Pi, with (A) brought up first: all 27
suites exit 0, twice; `nordpool` end to end 16/16, by the standing rule after a change on the
mediator's path. The mutants that patch `audit.py`, M08a and M08b, still apply after this fix moves
their lines, and are still killed.

**P4, the retest's `scheduler` variants rerun at the tag** (`endtoend_function.py --only
scheduler,scheduler-no-read,scheduler-no-service`, the same command as `retest_20261009` otherwise):

- `scheduler` confined: exactly one `light.turn_on`, `brightness` 200, `entity_id`
  `["light.living_room"]`, so the row that failed on 2026-10-09 passes;
- `scheduler-no-read` and `scheduler-no-service` confined: zero calls, zero service decisions, as on
  2026-10-09, because neither reaches the bridge's forwarding;
- the switch still ends `triggered`, not `off`, in both arms. This is unrelated to F54 and was wrong
  in both arms on 2026-10-09.

This rerun keeps the durable log's summary only, not its records, so F54b is checked by P2 alone.

## 6. What the report then changes

F54 moves to resolved in the findings log (`notes/verification_plan_20261005.md` §11) and in
Appendix F's Table F.2, with the tag. In §12.2, Table 12.3 gives `scheduler` as acting confined.
§12 also says that a confined service call's targets are now in the record, and that dict-valued data
is still dropped.
