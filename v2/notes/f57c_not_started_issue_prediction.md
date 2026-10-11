# F57, the rest: a Repairs issue when an integration is not started: predictions for the fix

**Written 2026-10-11, before the test is written and before any run.** F57 was resolved at
`fix-2026-10-f57b` with one part not done (`notes/f57_approval_gate_prediction.md` §2, "What this
does not do"): when the supervisor refuses to start an integration that no one approved, it prints
the reason on its own output, and nobody in the house sees it. A household would find an updated
integration silently stopped. **Younes decided on 2026-10-11** that the house is told through a
Repairs issue that explains and offers **no button**: approving grants permissions, and the rule
for the household's interface (2026-10-05) is that its one action never widens them. Commit this
note before the test runs; do not edit it after a run (`verify/prereg.py`). Results go to
`experiments/verify/results/f57c/`.

## 1. The rule

1. When the supervisor does not start an integration because its approval is missing or no longer
   matches, the bridge in (A) raises a Repairs issue for it, `not_started_<domain>`, in plain
   language, **not fixable** from the panel.
2. When the supervisor next starts that integration, the issue is removed.
3. A failure to reach (A) does not change what the supervisor does: the integration stays stopped
   and the supervisor says it could not tell the house, as it does for a cut-off.

The issue is one id per integration with the reason as its translation key, so F59's second reason
(too much stored data, `notes/f59_kept_storage_prediction.md`) uses the same issue, and a later
start clears whichever reason was showing.

## 2. The change

- **`ha_bridge/confine_bridge/__init__.py`.** Two commands, each accepted only from the designated
  mediator (`require_mediator`, as `cut_off` is): `confine_bridge/not_started` (`integration`,
  `reason` in `{"not_approved"}`, optional `detail` for the log) creates the issue, persistent,
  severity error, `is_fixable=False`; `confine_bridge/started` (`integration`) deletes it if present.
  `const.py` gains `ISSUE_NOT_STARTED = "not_started_{}"`.
- **`strings.json`, `translations/en.json`.** The issue's words (below).
- **`real_platform.py`.** `not_started(identity, reason, detail)` and `started(identity)`, each one
  call to (A).
- **`supervise.py`.** `launch` answers `NotApproved` by telling (A) through `not_started`, and a
  successful start by `started`. Each is wrapped so that (A) refusing or being away is said in a
  line and changes nothing else. `CutOff` keeps its own issue and is not reported twice.

The words, for review (the household is not technical; no file names, no commands):

> **{name} was not started**
>
> **{name}** was not started because the permissions it asks for have not been approved, or
> because it has changed since they were approved, for example after an update.
>
> This protects your home from an integration getting access that nobody agreed to. Ask the person
> who looks after this system to review it. Once they have approved it and restarted it, this
> message goes away by itself.

## 3. The test, written first

Added at the end of `selftest_supervise` (no new suite; 28 stays 28), against (A), as a household
and an operator act:

1. A supervisor for `demo_flood` started **with no approval on record** says "not started".
2. (A) shows a Repairs issue `not_started_demo_flood` from `confine_bridge`.
3. Its translation key is `not_approved`, and it is **not fixable**.
4. No sandbox was started (no "started (run 1" line).
5. That supervisor ended, the grant approved (`record_approval`), and a new supervisor started:
   its sandbox starts.
6. And the issue is gone.

## 4. Predictions

**C1, the test before the fix** (the test commit, on the Pi with (A) up): every existing step
passes; step 1 passes (the supervisor already prints "not started"), and the suite stops at
**step 2**, because nothing raises the issue. Exit 1.

**C2, after the fix** (with (A) restarted, so it copies in the new bridge): `selftest_supervise`
passes every check, exit 0.

**C3, `selftest_approval`** passes 10/10 at the tag (the gate itself is unchanged).

**C4, mutants** at the tag: M31–M35 (`supervise.py`) stay killed, and two new ones:
**M41**, `launch` does not call `not_started`, killed by `selftest_supervise` step 2;
**M42**, `launch` does not call `started`, killed by step 6.

The full suite run (×2) is not done at this tag: F59 follows directly and changes the same files,
so its tag runs every suite twice, which covers this one.

## 5. After the runs

Ledger line, Appendix F's F57 row ("not done" removed), the F57 row of the findings table, and
§9's sentence on what a household sees when an integration is not approved.
