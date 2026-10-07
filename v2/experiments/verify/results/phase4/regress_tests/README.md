# F48, F49, F52: regression and every mutant on `verify-2026-10-tests` (2026-10-07)

Predictions: `notes/f48_f49_prediction_20261007.md` (committed before the tests were written; its
addendum before `run2_m31`). Report: §7.45.12. Findings: F47–F53 in the plan's log.

## `run1/`: `verify/regress_tests.sh`

| Step | Result |
|---|---|
| 27 suites, twice | 27/27 both times |
| (A)'s restart suite | 55/55 |
| `nordpool` end to end | 16/16 |
| `drive_demo.py`, now judged | all 8 values ok |
| fault scripts, now exiting on a failure | 11 + 5 judgements ok, no FAIL |

**Mutants** (`mutants/run.txt`, each mutant's suite logs beside it; the bridge's in `bridge_mutants/`):

| Mutant | Killed by |
|---|---|
| M19 | `selftest_policy` "config_entries.list with read_all: false is DENIED" |
| M20 | `selftest_policy` "event.fire of another event is DENIED by the same manifest" |
| M21 | `selftest_policy` "an identity with no manifest bound is DENIED, with a clause pointer (S6)" |
| M22 | `selftest_flood` "the sandbox is told it was refused, not that it was granted" |
| M23 | `selftest_flood` "each failed act is a durable refusal naming why" |
| M24 | `selftest_push` "and the relay socket it opened is watched by the mediator" |
| **M25** | **survived, as predicted: equivalent on Python 3.13** (the unwrap changes nothing there; on 3.12 it does, see F49) |
| M26 | `selftest_local_tcp` "open_local given a refused decision refuses with that decision's reason" |
| M27 | `selftest_channel` "a valid object of more than MAX_FRAME bytes is refused before it is read" |
| M28 | `selftest_channel` "a frame carrying two descriptors is refused, saying two, and neither is kept" |
| M29 | `selftest_channel` "a frame that is not a JSON object is refused" |
| M30 | `selftest_channel` "a message over MAX_FRAME is not framed for sending" |
| **M31** | **survived, not predicted** — see `run2_m31/` |
| M32 | `selftest_supervise` "run 2 started, a new process" |
| M33 | `selftest_supervise` "run 3 started" |
| M34 | `selftest_supervise` "the second reports clearing what the first left" |
| M35 | `selftest_supervise` "and starts nothing in its place" |
| M36 | `selftest_channel` "a length prefix cut short by a hang-up is refused" |
| M37 | `selftest_channel` "a frame shorter than its declared length is refused, even when what came is valid" |
| M01–M17 (18) | all killed; failing-suite counts per mutant in `run1/mutants/run.txt` (4.3's originals: `../mutants/`) |
| M18a–c | all killed; M18c by F47's check. Unmutated control 27/27 |

Each new mutant failed exactly one suite, the one holding its check.

## `run2_m31/`: after M31's survival (`verify/rerun_m31.sh`)

M31 removes the supervisor's kill on a cut-off. `demo_flood` stops by itself when the mediator closes
its channel ("exited by itself (status 0)" one second after the cut-off), so step 2 passed without the
kill. `experiments/flood/demo_stubborn` blocks its own event loop and cannot stop itself;
`selftest_supervise` step 8 checks that it is killed. On the moved tag: 27 suites twice (27/27 both,
`selftest_supervise` 36/36), then M31–M35 again:

| Mutant | Killed by |
|---|---|
| M31 | step 8, "its sandbox's process is gone" |
| M32 | "run 2 started, a new process" |
| M33 | "run 3 started" |
| M34 | "the second reports clearing what the first left" |
| M35 | "and starts nothing in its place" |

Afterwards no sandbox, supervisor or `sup-*` cgroup was left on the Pi.

**Totals:** 40 mutants, 39 killed, each by the check written for it; 1 equivalent on this interpreter.
