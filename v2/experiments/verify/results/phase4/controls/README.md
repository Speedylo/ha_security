# Verification 4.4 — a negative control for every positive security result (2026-10-06)

Plan §7.4. A security result says a protection stopped an attack. Its **control** shows that the
attack works when the protection is gone, so the result belongs to the protection and not to
something else: an attack that was broken anyway, a test that never reached the code, or another
limit of the host. Three kinds of control count here:

- **pairing**: the same attack run against an unconfined installation, on the same host and release;
- **a mutant**: the protection removed from the code (§7.45.3, `verify/mutants/`), and the
  verdict's own check fails;
- **attribution by the kernel**: a counter the kernel keeps for the mechanism itself, which can
  only rise if that mechanism acted.

| Verdict | Control | Kind |
|---|---|---|
| T01, S1 — garbage-collector technique | unconfined: the token reached 7 ways (§7.15.3) | paired |
| T02 — identity per request | M02 (identity from the request): `selftest_channel` fails | mutant |
| T03 — mediator unreachable from the address space | T01's pair: unconfined, the same technique reaches the platform's objects; there is no mediator to reach | paired through T01; the verdict already says "unpairable by construction" |
| T04, S2 — no credential recoverable | unconfined `LEAKED`, confined `EMPTY` (§7.13) | paired |
| T05 — unlock refused under `lock.lock` | M01: `selftest_policy`, `selftest_c3` "unlock … denied" fail; M17: `lock.*` accepted at parse | mutant |
| T06, S3 — reads and subscriptions | reads paired (36/36 → 1/36); subscriptions M10 | paired + mutant |
| **T07 — writes to declared entities only** | **none until today (F39).** Every write refusal in the suites was denial by absence, or the platform's ownership rule refusing it as well, so under M01 they all still passed. `selftest_policy` now has a write declared for one entity and refused for another: it fails under M01 and passes unmutated (`selftest_policy_under_M01.txt`, `selftest_policy_unmutated.txt`) | mutant, added |
| T08, S4 — per-integration egress | M01: `selftest_egress_sandboxed` "S4 … allowed=[True, True]"; M03: port ignored | mutant |
| T10, T11 — LAN and resolve-then-pin | M04, M05, M06 | mutant; verdict says "at the decision layer" |
| T12 — update through the authorised path | M09 (manifest not re-read): `selftest_t12` fails | mutant |
| T14, T15, S8 — filesystem and process isolation | unconfined 2/2 canaries, confined 0/2; M13 (seccomp), M14 (own directory writable), M15 (host `/proc`) | paired + mutant |
| T16, S9 — memory | the cgroup's `oom_kill` counter rises (`memory.events`) | kernel attribution |
| T16, S9 — CPU | the cgroup's `throttled_usec` rises (`cpu.stat`) | kernel attribution |
| **T16, S9 — processes** | **added today:** the same 200 forks under a cap of 512 all succeed (`selftest_resources_with_controls.txt`) | control run |
| **T16, S9 — disk space** | **added today:** the same 64 MB into a 128 MB private `/tmp` is all written | control run |
| T17 — unconfined baseline attack | paired (§7.13.2) | paired |
| T18, S7 — attributed, tamper-evident log | M07 (record after the act), M08a/M08b (a chain not checked) | mutant |
| T19 — denial of service against the audit log | M11 (no cut-off), M12 (cut-off integration re-registers) | mutant |
| F33, F34 and F35's fixes (§7.45.6) | each test failed against the code before its fix | failing first |
| T09, T13 | retained by decision, no protection claimed | — |

**Every positive security verdict now has a control.** One gap was real (T07, finding F39), and it
was a gap in the tests, not in the code: the manifest's own write check was correct, but no test
would have noticed its removal. It is the same kind of gap as F22 (mutant M16). Two controls were
missing but implied (processes and disk). Both were run and held.
