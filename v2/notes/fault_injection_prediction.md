# Fault injection (verification 4.5) — criteria and predictions, written before any fault is injected

**2026-10-06.** Plan §7.5 lists nine faults. N3 asks that a failure have a stated mode: the framework
fails closed and says why, and never carries on with a control silently gone. For each fault below,
the **criterion** is what the design requires, and the **prediction** is what I expect the code to do,
from reading it today. A criterion is judged as written. A prediction that turns out wrong is
reported as wrong.

## Inventory of what already exists

| Fault | Already exercised by |
|---|---|
| FI5 malformed frame | `selftest_audit` (lost channel, durable `protocol_error`), `selftest_fdpass` (descriptor closed) |
| FI7 a sandbox that never reads | `selftest_push` P7 (pushes), D7 (datagrams) |
| FI6 oversized frame | the receive-side check (`channel.py`, before the read); **no test sends one** |
| FI2 sandbox dies | `selftest_resources` OOM-kills one; **nothing dies mid-frame on the channel** |
| FI1 (A) stops, FI3 audit disk full, FI4 mediator restart, FI8 network gone, FI9 clock jump | **nothing** |

FI5 and FI7 are re-run as they are. The other seven get new cases in `verify/faults.py` (stand-in
level, run locally and on the Pi) and `verify/faults_pi.sh` (FI1 and FI4, which need (A) and the
supervisor on the Pi).

## The cases

**FI1 — (A) stops while the mediator is connected, then comes back.**
*Criterion:* while (A) is down, nothing is acted on and nothing is recorded as done; the failure is
stated. *Prediction:* `RealPlatform.pump()` raises `PlatformLost`, which leaves `Mediator.serve()`;
`supervise.py` stops the sandbox and exits. Nothing reconnects when (A) returns, so the integration
stays down until the supervisor is started again. Fail-closed: **holds**. Recovery: **does not exist**,
and nothing in the report says so — expected to be a finding.

**FI2 — a sandbox dies mid-frame.** *Criterion:* its channel is dropped and recorded; every other
sandbox is still served. *Prediction:* `truncated frame` raises `ProtocolError`, the channel is
unregistered and a `protocol_error` is recorded. **Holds.**

**FI3 — the audit log's disk is full.** *Criterion (the hard one):* no act runs without its record.
*Predictions:* (a) the act does not run: **holds**, because `_record` raises before `act()` is reached;
(b) the `OSError` leaves `serve()`, so the mediator stops for every sandbox, not only the one asking:
**likely**; (c) the failed append can leave a **partial line** in the log, because the text is written
before the `fsync` that fails or the write itself is cut short; `verify()` then reports the log
unreadable from that line, and every record appended after space is freed sits behind it. A full disk
would then make the log permanently unverifiable: **likely, and a defect if so.**

**FI4 — the mediator restarts during the push loop** (the supervisor is killed with `SIGKILL` while
a confined integration is subscribed, then started again). *Criterion:* no sandbox runs without a
mediator; after the restart the integration's subscriptions are re-established by a fresh sandbox.
*Prediction:* the sandbox's channel closes, and the runtime's next request fails. Whether the
sandbox then exits, or lingers as an orphan with no mediator until something reaps it, I cannot
tell from reading: **uncertain**. A lingering orphan can do nothing, because every reach goes through
the channel, but a restarted supervisor would start a second one beside it.

**FI6 — a frame declaring more than `MAX_FRAME`.** *Criterion:* refused before any allocation, the
channel dropped and recorded, others served. *Prediction:* **holds** (the check precedes the read).

**FI8 — the network is gone during an egress request** (the broker runs in a network namespace with
no route). *Criterion:* refused with a stated reason within the connect timeout, recorded, and nothing
hangs. *Prediction:* `connect` fails at once with `ENETUNREACH`; the broker raises `EgressRefused`
naming the address; the act's refusal is recorded after the grant. **Holds.**

**FI9 — the wall clock jumps** (an hour back and an hour forward, during a flood and during audit
writes). *Criterion:* the flood cut-off and the audit chain are unaffected. *Prediction:* the flood
window uses `time.monotonic()` and the chain does not include time in its ordering, so **holds**. The
records' `time` fields will run backwards across the jump, which is cosmetic and is reported.

## What would change the report

FI3 (c) and FI1's missing recovery, if they behave as predicted: the first is a defect in S7's
mechanism, and the second is a stated limitation the report does not yet have.

## Outcomes (2026-10-06, after the runs)

Run by `verify/faults.py` locally and on the Pi (identical: 9 of 11 criteria), and by
`verify/faults_pi.sh` on the Pi with (A) and the supervisor (`experiments/verify/results/phase4/faults/`).
FI5 and FI7 are the existing cases, passing in today's 26/26 suite runs.

| Fault | Criterion | Prediction | Outcome |
|---|---|---|---|
| FI1 (A) stops | held: the supervisor died on an uncaught `PlatformLost` and took the sandbox with it | no recovery | **as predicted**: 30 s after (A) returned, no supervisor and no sandbox. The failure is a traceback, not a stated message, and nobody in the house is told |
| FI2 dies mid-frame | held | holds | as predicted |
| FI3 disk full | **(a) held**: 25 acts, 25 complete records, none without | (b) leaves `serve()` | (b) as predicted: `OSError ENOSPC` leaves the handler |
| | | (c) partial line, log unverifiable | **(c) as predicted, and worse**: once space was freed the mediator acted and recorded again, appending onto the partial line, so every record from the failure on is unverifiable for good |
| FI4 mediator SIGKILLed | **failed**: the sandbox survived as an orphan with no mediator | uncertain | orphan confirmed; the restarted supervisor started a second sandbox beside it. **Unpredicted:** the restarted supervisor appended a new chain (seq 0, genesis) to the same `decisions.jsonl`, so `verify()` reports sequence and link breaks that look exactly like deleted records |
| FI6 oversized frame | held (refused in under a millisecond, recorded) | holds | as predicted |
| FI8 network gone | held (refused in 14 ms, recorded granted then refused) | holds | as predicted |
| FI9 clock jump | held | holds | as predicted; record times step back 3,600 s, cosmetic |

The MAC failures in FI4's log are not a finding: the key is generated per mediator and never stored,
which §6.8.4 states and §8.6 lists as limitation 7. The hash chain is the part a restart breaks.

## The fixes, written before the code (2026-10-06; Younes chose to fix all four)

**F28 — a failed append leaves nothing behind.** `AuditLog._append` notes the file's size before
writing; if the write, flush or `fsync` fails, it truncates the file back to that size, `fsync`s, and
re-raises. The chain state is not advanced, as now. The mediator still stops on the error: with no
record possible, no decision is possible, so fail-closed stays the behaviour.
*Criteria:* (1) a new `selftest_audit` case, an append whose `fsync` fails, leaves the file as it was
and the next record continues the chain (fails against today's code: the unsynced line stays, and the
next record repeats its sequence number); (2) FI3 on a real full disk: the log verifies after the
failure, and after space is freed and records are written again.

**F31 — one log file per mediator start.** `supervise.py` writes `decisions-<start time>.jsonl`, so
a file is never two chains. `drive_demo.py` reads the newest. *Criterion:* after FI4's kill and
restart, every file in the audit directory has no sequence, link or hash break. MAC breaks for the
killed run are expected and stated (§6.8.4).

**F30 — no sandbox outlives its supervisor.** Two parts, because the first is inside the sandbox and
so cannot be the guarantee:
- the runtime exits when the mediator's channel closes, instead of only ceasing to read it;
- a starting supervisor removes every `sup-<domain>-*` cgroup it finds, killing what is in it, before
  it launches, and says how many it cleared. This is outside the sandbox's reach, so it holds even
  against an integration that ignores the first.

*Criteria:* (1) FI4: 10 s after the supervisor is `SIGKILL`ed, no sandbox is running; after the
restart, exactly one; (2) with a process placed by hand in a stale `sup-demo_flood-*` cgroup, a starting
supervisor kills it and removes the cgroup.

**F29 — the supervisor survives (A) going away.** On `PlatformLost` it stops the sandbox (fail-closed,
as now), says so in one plain line rather than a traceback, and tries to reconnect every 5 s. When (A)
answers, it attaches the new connection (`Mediator.detach_platform`, new), rebuilds the acting policy
on it, and starts the integration again if it was running when (A) went away. Nobody is asked to do
anything, so no Repairs issue is raised. While (A) is down nothing can be shown in it, and once it is
back the integration is running again. *Criteria:* FI1: within 60 s of (A) returning, exactly one
supervisor and one sandbox are running, with no traceback in the supervisor's log.

**Regression:** a new tag; all 25 suites and the base self-test, twice; `nordpool` end to end; FI1–FI9;
`selftest_real_platform` and `drive_demo` (the supervisor's own path).
