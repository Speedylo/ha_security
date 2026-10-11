# F57, the rest: the house is told, and can allow, when an integration is not started: predictions for the fix

**Written 2026-10-11, before the test is written and before any run.** F57 was resolved at
`fix-2026-10-f57b` with one part not done (`notes/f57_approval_gate_prediction.md` §2, "What this
does not do"): when the supervisor refuses to start an integration that no one approved, it prints
the reason on its own output, and nobody in the house sees it. An updated integration would stop
silently, and the only way to start it is a command typed on the Pi. **Younes decided on 2026-10-11**
that the household is not expected to be technical, so the house is told in Home Assistant's Repairs
panel, and an administrator can read what the integration asks for there and **allow it**, with one
button that says what it does. Approval and restart stay separate acts: "Allow and start" grants
exactly the permissions on the screen; "Try again" (F59's reason) grants nothing. Commit this note
before the test runs; do not edit it after a run (`verify/prereg.py`). Results go to
`experiments/verify/results/f57c/`.

## 0. A change of scope, stated

The working report left a consent flow out on purpose: "**A consent flow.** Buttons, prompts, a
wizard. §3.7 puts the interaction out of scope" (`report/06_implementation.md`, the list in
`describe.py`'s header). F57's gate makes the interaction necessary, because without it a household
cannot start an integration the gate stopped. This fix therefore adds **an approval interaction**.
It does not add a claim about **comprehension**: §3.7's exclusion stands, nothing here tests whether
a household understands the list, and F4 stays rated on availability. The report gets a dated
correction where it says the consent flow was left out.

## 1. The rule

1. When the supervisor does not start an integration because its approval is missing or no longer
   matches, the bridge in (A) raises a Repairs issue for it, `not_started_<domain>`, with the reason
   as its translation key (`not_approved`; F59 adds `too_much_data`).
2. **The issue's screen shows what the integration asks for, in the words `describe` already uses**:
   what it will be able to do, what it will not be able to do (at the same weight, F4), who declared
   the permissions, and, when an approval existed, what changed since (its code, its permissions or
   both, `describe`'s existing three cases). One button: **Allow and start**.
3. **Allow records an approval of exactly what was shown.** The screen carries the identity and the
   grant digest it was rendered from. On Allow, the supervisor recomputes both; if either differs, it
   records nothing, does not start, and raises the issue again with a new screen. If both match, it
   records the approval in the approvals file, as `describe --approve` does, with
   `"by": "an administrator, from the Repairs panel"`, and starts the integration.
4. **Only an administrator can allow.** Home Assistant already restricts Repairs fix flows to admins
   (`require_admin(permission=POLICY_EDIT)`, `components/repairs/websocket_api.py:114` at 2026.8.3).
   It does not tell the flow *which* admin, so the record names the role, not the user.
5. **The integration cannot allow itself.** Allow travels on (A)'s command stream to the supervisor.
   No operation a sandbox can send to the mediator records an approval; one named `approve` is denied
   by absence (S6).
6. When the integration next starts, by Allow or by an operator's `describe --approve` and a restart
   of the supervisor, the issue is removed.
7. A failure to reach (A) changes nothing the supervisor does: the integration stays stopped, and the
   supervisor says it could not tell the house.

Author-supplied values on the screen (entity names, hosts, file paths) are escaped for Markdown, so a
manifest cannot add lines of its own to what the administrator reads.

## 2. The change

- **`describe.py`.** `describe_markdown(manifest, changed)`: the same sentences as `describe`, as a
  Markdown list, values escaped, no title or underline (the issue has its own). And
  `approve_shown(component, approvals, manifest, shown_identity, shown_grant, by)`: recompute, compare,
  record or refuse. Pure, so it is tested without (A). `AuditLog.approval` gains an optional `by`.
- **`ha_bridge/confine_bridge/__init__.py`, `repairs.py`, `const.py`.** Two commands, each accepted
  only from the designated mediator (`require_mediator`, as `cut_off` is):
  `confine_bridge/not_started` (`integration`, `reason`, `details` (the Markdown), `identity`, `grant`)
  creates the persistent, fixable issue `not_started_<domain>`; `confine_bridge/started`
  (`integration`) deletes it. The fix flow for a `not_started` issue shows one form whose description
  is the details, and on submit sends `{"approve": ..., "identity": ..., "grant": ...}` (or
  `{"retry": ...}` for F59's reason) down the command stream. The cut-off's flow is unchanged.
- **`strings.json`, `translations/en.json`.** The words (below).
- **`real_platform.py`.** `not_started(...)`, `started(identity)`; and `approve_handlers` /
  `retry_handlers`, dispatched from the command stream beside `restart_handlers`.
- **`supervise.py`.** `launch` answers `NotApproved` with `not_started`, carrying `describe_markdown`,
  the current identity and grant; a successful start with `started`. An approve request for its own
  integration, while it is not running, goes through `approve_shown`, then `launch`. The handlers are
  attached again to the new connection after (A) returns (F29's path).

The words, for review. The issue's summary in the Repairs list:

> **{name} was not started**
>
> **{name}** was not started because the permissions it asks for have not been approved, or because
> it has changed since they were approved, for example after an update. Open this to see what it asks
> for.

The screen behind it:

> **Allow {name}?**
>
> {details}
>
> Select **Allow and start** to let it do the things listed above, and nothing else. If you do not
> recognise it or do not want it to have these permissions, close this window: it will stay stopped.

## 3. The test, written first

**In `selftest_approval`** (no (A)), four checks after its ten:

11. `approve_shown` with the identity and grant of the current integration records an approval, with
    its `by`, and registration then succeeds.
12. With a grant digest from before the derived file was widened: refused, nothing recorded, still not
    registered.
13. With an identity from before the code changed: refused, nothing recorded.
14. A sandbox request `{"op": "approve"}` is denied (S6).

**At the end of `selftest_supervise`** (against (A), as an administrator and an operator act):

1. A supervisor for `demo_flood` started with no approval on record says "not started"; no sandbox.
2. (A) shows `not_started_demo_flood` from `confine_bridge`, key `not_approved`, fixable.
3. Its screen, opened as the panel does, shows `describe`'s lines ("It will not be able to" and
   "control anything").
4. The mediator's own, non-admin token cannot open it (HTTP 401).
5. **Allow and start** submitted: a sandbox starts (run 1), and the integration publishes its switch.
6. The issue is gone, and the approvals file holds a record with `"by": "an administrator, from the
   Repairs panel"`.
7. A second supervisor, after the derived permissions are widened (`--permissions` with a service),
   is refused again, and its screen says the permissions changed.
8. The operator's way: that supervisor ended, the grant approved with `record_approval`, a new
   supervisor started: it starts, and the issue is gone (removed by `started`, not by a flow).

## 4. Predictions

**C1, the test before the fix**, at the test commit: `selftest_approval` fails checks 11–13 (no
`approve_shown`, an `ImportError` the suite reports as one failure and stops) and passes 1–10, exit 1;
check 14 is not reached. `selftest_supervise` passes every existing step and step 1, and stops at
**step 2**, exit 1.

**C2, after the fix**, (A) restarted so it copies in the new bridge: `selftest_approval` 14/14 on the
laptop and the Pi; `selftest_supervise` every check on the Pi.

**C3, `selftest_describe`** passes, unchanged in what it checks (`describe`'s text is unchanged).

**C4, mutants** at the tag: M31–M35 (`supervise.py`), M39 and M40 (the gate) stay killed, and new ones:
**M41**, `launch` does not call `not_started`: killed by `selftest_supervise` step 2;
**M42**, `launch` does not call `started`: killed by step 8 (step 6's issue is removed by the flow
itself, so only the operator's way shows the difference);
**M43**, `approve_shown` does not compare the grant: killed by `selftest_approval` check 12;
**M44**, `approve_shown` does not compare the identity: killed by check 13.

The full suite run (×2) is not done at this tag: F59 follows directly and changes the same files, so
its tag runs every suite twice, which covers this one.

## 5. After the runs

Ledger line; Appendix F's F57 row ("not done" removed); the findings table; the dated correction to
`report/06_implementation.md` on the consent flow; §9 (what a household sees and does when an
integration is not approved, and the approval authority now reachable from (A)'s admins); §14; and the
threat model's statement of who can approve: an operator on the Pi, or an administrator of (A).
