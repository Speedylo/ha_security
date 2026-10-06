# Phase 4.3 — mutation testing of the enforcement points (2026-10-06)

Each mutant removes or inverts one security-relevant check (`verify/mutants/mutants.py`, one exact
replacement each, with the patch it generates beside it). `verify/mutants/run_mutants.sh` applied each
to a fresh copy of a clean checkout on the Pi and ran all 26 suites. Criteria were fixed before the run:
a mutant is killed when at least one suite fails, and each kill is read so that a kill by an unrelated
crash counts only as weak. The plan listed 17 mutants; M08 was split into its two independent chains.

**Result: 17 of 18 killed on the first run, every kill by the check that guards the mutated point.
M16 survived every suite.** A test was added for it, and it is now killed (`run2_m16/`); the unmutated
tree still passes 26/26 with that test (`unmutated_after_m16_test/`).

| Mutant | Claim | Removed or inverted | Killed by |
|---|---|---|---|
| M01 | S6 | a request matching no clause is granted | 10 suites, e.g. `selftest_policy` "entity.read of an undeclared sensor: permit" |
| M02 | S1, T02 | identity from the request's `integration` field | `selftest_channel` "demo_b entity.read: expected deny" |
| M03 | S4, F3 | egress clause ignores the port | `selftest_policy` "declared host on another port: permit" |
| M04 | T10 | `is_public` accepts RFC 1918 | `selftest_egress` 4b "192.168.1.50 must not count as public" |
| M05 | T10 | `is_lan` accepts public addresses | `selftest_local_tcp` "8.8.8.8 is refused", `selftest_udp` 2d |
| M06 | T11 | resolved address not re-checked | `selftest_egress` 4d "**T11** … it connected to loopback" |
| M07 | S7, §5.11.3 | acting decision recorded after the act | `selftest_audit` "an action that dies leaves its record on disk: 0 records" |
| M08a | S7 | MAC chain not checked | `selftest_audit` "cannot rebuild one link of the MAC chain" |
| M08b | S7 | hash-chain link not checked | `selftest_audit` "repairing its own hash does not help: 0 link breaks" |
| M09 | T12, §8.7 #14 | manifest not re-read at registration | 5 suites; `selftest_t12` "the respawn is bound to v2" |
| M10 | S3 | subscription filter bypassed | `selftest_push` "no change to an undeclared entity arrives" |
| M11 | T19 | the cut-off counts nothing | `selftest_real_platform` "the fifth refusal cuts the integration off"; `selftest_flood` ran to its 300 s limit |
| M12 | T19 | a cut-off integration may register again | `selftest_flood` "cannot be registered again: registered" |
| M13 | S8 | seccomp allows what it lists | 7 suites: the preflight exercises the filter, finds `unshare`, `ptrace`, `keyctl` allowed, and refuses to confine (N3) |
| M14 | C1, S8 | own directory mounted read-write | `selftest` "its own directory: present, writable" |
| M15 | T15 | host `/proc` bound in | `selftest` "the PID namespace shows more than the sandbox itself" |
| **M16** | §7.38, C7 | a command's answer accepted from any channel | **survived.** Now `selftest_audit` "an answer from another sandbox's channel is refused" |
| M17 | S5 | `lock.*` accepted at parse | `selftest_policy`, `selftest_c3` "a wildcard service: lock.* ACCEPTED" |

**Why M16 survived.** The only test of the answer path sent an answer naming a command that was never
sent, which an id check refuses whether or not it also checks the channel. Under M16, a sandbox
answering a command sent to *another* sandbox had its answer relayed to the house as that command's
result. The real code always refused it; nothing showed that it did. The new check sends a real
command's answer from a second sandbox's channel, and then confirms the right channel can still answer.

**A note on depth.** Eleven of the eighteen are killed by exactly one check. Each claim has a test, but
most have one, so a later edit to that test could silently leave a claim untested again.

**A side effect, found by the F28–F31 regression.** A suite killed by the runner's 300 s limit does not
clean its temporary directory. Under M11 `selftest_flood` flooded its log to 1.2 GB in `/tmp` (a 2 GB
tmpfs on the Pi) before it was killed, and the directory stayed until it made a later `nordpool` run
fail for space. A mutation runner should give each mutant its own `TMPDIR` and remove it afterwards.
