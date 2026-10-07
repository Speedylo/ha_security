# Verification 4.12 (b): branch coverage of the 26 suites (2026-10-07)

Predictions and method: `notes/tests_bite_prediction_20261007.md` (90055f9, committed before the
run). Tools: `verify/coverage/` (`coverage` 7.10.7 in directories of its own, started in every
inheriting process by `sitecustomize.py`; branch coverage, `patch = _exit`). Tree: the tag
`verify-2026-10-f45` plus F47's new check. (A) was brought up from the same tree with measurement on,
so the bridge inside (A) is measured too.

**Files:** `report.txt` (every file, with missing lines and branches), `coverage.json` (the same,
machine-readable), `run.txt`, `suites/` (the 26 logs), `house_a.log`, and the `houseA-deps` checksums
before, after, and after removing the one file measurement left there (identical to before).

## Result

Enforcement files, combined: **statements 1541/2014 (77%), branches 461/624 (74%).**

| File | Branches | | File | Branches |
|---|---|---|---|---|
| `mediator.py` | 127/144 (88%) | | `real_platform.py` | 47/58 (81%) |
| `manifest.py` | 100/114 (88%) | | `spawn.py` | 13/18 (72%) |
| `audit.py` | 77/88 (88%) | | `seccomp.py` | 9/14 (64%) |
| `egress.py` | 14/18 (78%) | | `bridge/__init__.py` | 17/28 (61%) |
| `channel.py` | 27/36 (75%) | | `cgroup.py` | 28/58 (48%) |
| `enter.py` | 2/8 (25%) | | `supervise.py` | **0/40 (0%)** |

`provenance.py` (0%) was listed as an enforcement file in the predictions by mistake: it records
experiment runs and is used only by the harnesses.

**Every unexecuted branch in these files was read** and put in one class:

- **G, test gap on a security path:** `supervise.py` whole, and `cgroup.py`'s kill and remove paths
  (F48); nine decision or boundary branches across `manifest.py`, `mediator.py`, `egress.py` and
  `channel.py` (F49). On reading, the code at each is right.
- **E, error handling:** most of the rest: OSError and KeyError cleanups, (A) lost mid-call,
  malformed manifests rejected at load, `designate_mediator`'s two error replies, the bridge's
  pending-command bound, seccomp and cgroup set-up failures.
- **U, unmeasurable:** what runs inside the sandbox after `pivot_root`: `sandbox.py` 203–292,
  `enter.py` 100–138, `sandbox_runtime.py`, the filter's installation. Tested by behaviour (M13–M15).
- **Artefacts of this run (F51):** the bridge's publish-new-entity path (232–242, `entity.py`
  112–116) is unexecuted because (A) was not fresh; `selftest_resources` failed one check, its fork
  control, because each forked child loads `coverage` (it passed unmeasured the same hour).

Found on the way, not a coverage number: a declared `event.fire`, `event.subscribe` or
`config_entries.list` is permitted and answered `ok`, and nothing acts on it (F50).

## Predictions against the result

| Prediction | Result |
|---|---|
| enforcement files combined 75–90% | **74%: missed**, by `supervise.py`'s 0% |
| `mediator.py` 80–90% | 88%, right |
| most unexecuted branches class E | right |
| at least one class G | right: F48, F49 |
| `designate_mediator`'s error replies unexecuted, class E | right |
| the bridge under measurement within the suites' timeouts | right (no suite timed out) |
