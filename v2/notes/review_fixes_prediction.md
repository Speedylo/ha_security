# Security and code review (verification 4.7): findings F32–F35 and their fixes, written before the code

**2026-10-06.** Phase 4.7 had three parts: a manual read of the enforcement files, a fuzz of every
operation and field the mediator reads (`verify/fuzz_mediator.py`, committed with its first results
in `810a365`), and an independent code review of the F28–F31 fixes. They found four things. Younes
chose to fix all of them before the cut-off. As with F28–F31, each fix below names the test that
must **fail against today's code** and pass after it, and the regression that closes the batch.

## F34 — the sandbox shares the supervisor's terminal (Critical)

`DEV_NODES` binds `/dev/tty` into every sandbox, and `spawn.start` does not give the sandbox a
session of its own. A sandbox started from an interactive terminal therefore has that terminal as
its controlling terminal. On the Pi the kernel still allows the legacy terminal-input ioctl
(`/proc/sys/dev/tty/legacy_tiocsti` is `1`), and that ioctl lets a process push characters into its
controlling terminal's input queue, where the shell that started the supervisor reads them as typed
commands. That would be an escape from every isolation layer at once, so S8 would not hold for a
supervisor started from a terminal. The supervisor under systemd, with no terminal, is not
exposed. I have not tried to exploit it, and won't: the fix does not depend on showing the attack.

**Fix.** Two independent layers, so that neither is the only one:
1. the sandbox starts in a new session (`start_new_session=True` where `spawn_confined` is called),
   so it has no controlling terminal at all;
2. `tty` leaves `DEV_NODES`, so the sandbox's `/dev` holds five nodes.

**Test.** `selftest.py` asks, from inside the sandbox, what `/dev` holds and what its controlling
terminal is (`tty_nr`, field 7 of `/proc/self/stat`; 0 means none). The criterion: `/dev` has no
`tty`, and `tty_nr` is 0. It must fail against today's code when run with a terminal attached
(`script -qc` on the Pi supplies one; without one, `tty_nr` is 0 anyway and the test proves nothing).

## F33 — a malformed request crashes the mediator for everyone (Major)

The fuzz sent 4,864 requests and found 26 distinct ways for a sandbox's request to raise out of
`_handle_ready`, which stops the mediator and with it every confined integration. Examples:
`"entity": []` (`'list' object has no attribute 'partition'`), `"timeout": null`, a non-object
`data` or `attributes`, an unhashable `command` in an answer, and a UDP peer that answered with an
ICMP port-unreachable (the next send raises `ConnectionRefusedError`). One integration's bad input
must cost that integration, never the others.

**Fix.** One boundary in `_handle_ready` around the policy call and around the act. An exception
there of a kind that bad data or the network produce (`TypeError`, `ValueError`, `AttributeError`,
`KeyError`, `IndexError`, `OverflowError`, `OSError`) becomes a refusal: recorded with its clause,
answered to the sandbox, and counted toward the refusal flood limit like any other refusal. A crash
in the act is recorded **after** the grant, as an act's refusal is now. Two kinds still stop the
mediator, deliberately: an audit-write failure (no record, no decision; F28's fail-closed), which
cannot come from inside this boundary because `_record` is outside it, and `PlatformLost`, a
`RuntimeError`, which the supervisor handles (F29). The answer path validates its `command` field
before using it as a key.

**Tests.** (1) `fuzz_mediator.py` reports **0** escapes (26 today). (2) A new `selftest_flood` case:
two sandboxes; one sends `"entity": []`; its request is refused with a durable record, the other
sandbox is still served, and enough malformed requests reach the cut-off. (3) The audit-failure
case in `selftest_audit` (F28) still stops the mediator.

## F32 — a manifest can loosen its own resource bounds (Major: a stated claim is false)

§7.22.3 says a `resources` declaration "can only be read as a request to be bound **more** tightly
than the default, never less". The code does the opposite in two places. `Manifest.resources`
replaces the default with whatever the manifest declares, up to the parse-time bounds (8,192 MB of
memory, 4,096 processes, 4,096 MB of scratch); and the supervisor and the three harnesses apply
`max(declared memory, 640)`, so a **tighter** memory declaration is ignored. `describe.py` shows the
installer the declared figures, so what the installer reads would at least be accurate, but the
claim is not.

**Fix.** Make the code do what §7.22.3 says. `Manifest.resources` takes each declared member as the
smaller of it and the framework default (`cpu_percent` has no default, so a declaration always
tightens it). The `max(…, 640)` goes from all four call sites. `describe.py` shows the effective
figure. No corpus integration declares `resources`, so no measured number moves, and this is
checked by the regression rather than assumed.

**Tests.** A new `selftest_resources` case: a manifest declaring 8,192 MB, 4,096 processes and
4,096 MB gets 640, 64 and 64. A manifest declaring 192 MB keeps 192 MB through the supervisor's
launch path (today it gets 640).

## F35 — the code review's findings on the F28–F31 fixes (Minor to Major)

The review returned ten items. One (R6) is in a verification script and nine in the framework. I
checked each against the code and all ten hold.

| | What happens | Fix |
|---|---|---|
| R1 | A cut-off while (A) is down is never delivered: no Repairs issue appears once (A) is back, so nobody has a button to restart the integration. With no platform attached at all, the attempt is not even listed in `undelivered`. | The mediator keeps each undelivered cut-off and delivers it when a platform is attached again |
| R2 | A restarted supervisor overwrites the killed run's report and Home Assistant log (`<domain>-run1.json`/`.log`, opened `wb`) | Reports carry the same start-time and pid stem as that start's audit log |
| R3 | `_clear_predecessors` counts a cgroup cleared even when it could not be removed, and the next sandbox is then created inside it, beside the survivor | Check that each stale cgroup is gone. If one is not, the supervisor refuses to start and says so (fail-closed) |
| R4 | `SandboxCgroup.remove` reads the pid list once and kills each pid, which races with `fork` | Write `1` to `cgroup.kill` (kernel ≥ 5.14), which kills the whole cgroup atomically. Keep the pid loop as a fallback where it is absent |
| R5 | After a restart, a user's command goes to the old, dead channel first, and the user sees an error although the integration is running | `stop()` unregisters the stopped sandbox's channels (`Mediator.drop`, shared with the cut-off) |
| R6 | `verify/phase2_l23.sh` still copies `decisions.jsonl`, which no longer exists, and hides the failure | Copy `decisions-*.jsonl` |
| R7 | The supervisor treats a successful login to (A) as "(A) is back", but (A) accepts logins while still starting. The owners snapshot can then miss entities the house has not created yet | `RealPlatform` refuses to connect until `get_config` reports `state: RUNNING` |
| R8 | A refused token or a missing token file makes the reconnect loop retry forever, saying nothing | Say each distinct reason once, in a plain line, and keep retrying, so a corrected token is picked up |
| R9 | If the first append to a new audit file fails, its directory is never `fsync`ed afterwards | Record the directory as synced only after the `fsync` succeeds |
| R10 | `_clear_predecessors` kills the sandbox of a supervisor that is still running, which then leaves the integration down | Each supervisor names its cgroups `sup-<domain>-<pid>-<n>`, and clears only those whose supervisor pid is no longer alive |

**Tests.** R5, R1 and R9 get stand-in cases (`selftest_flood`, `selftest_audit`), each failing first.
R2, R3, R4 and R10 are tested on the Pi with the supervisor, in `verify/review_pi.sh`. That script
checks four things. A planted process in a stale cgroup is killed and removed. A second supervisor
started beside a live one leaves the first one's sandbox running. After a SIGKILL and a restart,
both runs' reports exist. A process placed in an unremovable position is reported, and nothing is
started beside it. R7 and R8 are checked by FI1 again, plus a run with the token file moved aside:
its log must name the reason within one retry. R6 is checked by running the script.

## Regression

A new tag after the fixes. All 25 suites and the base self-test, twice; `nordpool` end to end;
`fuzz_mediator.py` (0 escapes); `faults.py`; `faults_pi_fixed.sh` (FI1, FI4 and the backstop) and
`review_pi.sh`; `drive_demo`; `recompute.py` 39/39.

**What would change the report.** F34 and F32 are claims (S8's isolation, §7.22.3) that held only
partly. Each gets a dated pointer beside the original text and a §7.45.6 write-up. F33 qualifies
§5.15's single-loop availability argument until it is fixed. F35 changes nothing the report claims,
except that R7 and R1 complete what §7.45.5 says F29 does.

## Outcomes (2026-10-06)

Every test registered above failed against the old code where it could be made to, and passes
now. Before the fixes: base self-test under a terminal, `/dev/tty` present and `tty_nr` 34816;
`selftest_flood` 25/32; `selftest_audit` R9 failing; `selftest_resources` F32 failing;
`review_units` 0/8; `review_pi` P1 640 MB applied for 192 MB declared, P2 the first supervisor's
sandbox killed, P3 one report where two were expected. After: all pass. Results are in
`experiments/verify/results/phase4/review/`. R7 could not be made to fail first: its check is FI1,
where the integration was running again 4 s after (A) answered. R6 was checked by running the
script.

The regression on `verify-2026-10-review` (`experiments/verify/results/phase4/regress_review/`)
held throughout: suites 26/26 twice, `nordpool` 16/16, (A)'s restart 48/48, `drive_demo`,
`faults.py` 11/11, FI1/FI4/backstop, fuzz 0 escapes, `review_units` 8/8, `review_pi` P1–P4.
`recompute.py` gave 39/39 on the Pi, with both corpora.

The manual read of `manifest.py` and `mediator.py`, the two files not read before, found nothing
new. One note: an entity pattern such as `sensor.foo*` is accepted and then matched literally, so
it grants nothing. That fails closed and is not a finding.
