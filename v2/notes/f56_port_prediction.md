# F56, the unconfined arm beside (A): predictions for the fix

**Written 2026-10-10, before the change and before any run.** F56 (`notes/verification_plan_20261005.md`
§11): the unconfined end-to-end arm's `http` binds port 8123, which (A) holds while it is up, so a
run beside (A) loses `http`, `websocket_api` and everything that depends on them, and reports only
"not loaded". Results go to `experiments/verify/results/f56/`.

## The change

The arm itself is not changed, so that every recorded unconfined run stays comparable with the next.
What changes is that the condition is named. Before it builds Home Assistant,
`endtoend_unconfined.run` tries to bind port 8123 the way `http` does (all addresses, with address
reuse). If the bind fails, the report gains `instance_fault`, naming the port and the error, and
`endtoend_function` prints that fault in place of "not loaded". A run that is not a valid baseline
can then no longer pass for a result. Choosing another port for the arm was rejected, because it
would change the instance that every earlier run used.

## Predictions

**Q1, with (A) up** (`endtoend_function --only scheduler --arm unconfined`, at the commit with the
change): the report has `instance_fault` naming port 8123, `http` and `websocket_api` are `False`
in `components_setup`, the printed line names port 8123, and `scheduler` does not load. Before the
change, the same run printed "not loaded" and nothing named the port (F54's regression,
`experiments/verify/results/f54/regress/p4_scheduler.json`).

**Q2, with (A) down**, the same command: no `instance_fault`, `http` and `websocket_api` `True`,
`scheduler` loads. The verdict script gives 3 of 4, as in `results/f54/diag_unconfined_A_down/`,
where the switch ends `triggered`.

**Q3:** `selftest_*` do not run this arm, so they are not re-run for this change. Of the harnesses
that do, `endtoend` and `endtoend_egress` gain the field only, and nothing they judge reads it.

## Outcome (added 2026-10-10, after the runs)

**Q1 held.** At `abe3789` with (A) up, the report's `instance_fault` reads "port 8123 in use
([Errno 98] Address already in use): this arm's http cannot start (F56)". `http` and `websocket_api`
are `False`, `scheduler` did not load, and the printed line names the port
(`experiments/verify/results/f56/q1_A_up.*`).

**Q2 held.** With (A) down, there is no `instance_fault`, `http` and `websocket_api` are `True`,
`scheduler` loads, and the verdict script gives 3 of 4, the switch again ending `triggered`
(`q2_A_down.*`). (A) was brought up again afterwards. **Q3:** nothing was re-run, as predicted.
