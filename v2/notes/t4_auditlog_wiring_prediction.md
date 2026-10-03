# T4 — the durable audit log engaged in every harness: prediction

**Written 2026-10-03, before any code was changed or run.** Never revised after.

## Why

`AuditLog` — the hash- and MAC-chained, fsynced record S7 rests on — is attached to a mediator in
one harness (`endtoend_egress.py`). Every other experiment records to `mediator.audit`, an
in-memory list with no chain, no MAC and no fsync. The one time the durable log carried real work
(§7.27.6) it produced three defects in a session. This engages it everywhere a mediator decides
something real, and after each run **reconciles** the durable record against the in-memory one,
decision by decision. Latency and memory harnesses are excluded deliberately: an fsync per
decision would change the quantity they measure, and §7.20.1 measured durability on its own.

## Found by reading, before any run

1. **No run record is ever written outside the self-tests.** `Mediator.register()` takes
   `run_id=""` by default and no harness passes one; `AuditLog.run()` is called only by
   `selftest_audit` and `selftest_t12`. So in `endtoend_egress.py` every durable decision names run
   `""`, which no run record carries. §7.30.1's "each decision names the run that made it" is true
   only inside the suite that calls `run()` itself — §7.30.6's shape again.
2. **Protocol errors never reach the durable log.** `_handle_ready` records a malformed frame in
   `mediator.audit` only. That is precisely what a hostile sandbox produces.
3. **The sandbox chooses the logged target.** `decision()` takes `entity` before `service`, so a
   `service.call` for `lock.unlock` that also carries `"entity": "sensor.harmless"` is decided on the
   service and *recorded* against the sensor. The decision is right and the record of it says
   something else, chosen by the party being audited.

## Predictions

| | Prediction | Confidence |
|---|---|---|
| **P1** | With (1)–(3) fixed, every wired harness reconciles exactly: same decision count, same op, verdict and clause per decision, every decision naming a run record for the same integration | medium — the in-memory list has its own non-decision entries (protocol errors) that a naive count would trip on |
| **P2** | Every chain verifies, hash and MAC, in every harness | high |
| **P3** | A new adversary case — `lock.unlock` carrying a decoy `entity` — is recorded with target `lock.unlock` after the fix, and **would have been recorded as the decoy before it** (shown by running the case against the unfixed `decision()`) | high |
| **P4** | A malformed frame from a sandbox appears in the durable log after the fix, and the sandbox loses its channel as before | high |
| **P5** | The fsync cost does not push any wired harness past its timeouts | high — §7.20.1 measured 3.67 ms per durable decision, and no harness makes more than a few hundred |
| **P6** | Something not listed here is found | medium — the project's own argument says yes |
