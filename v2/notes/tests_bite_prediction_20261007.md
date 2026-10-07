# Do the tests catch mistakes? Mutants for F45's gate, and branch coverage (2026-10-07)

Committed before either run. Younes asked whether the suites only confirm. The campaign's answer so
far rests on 18 hand-chosen mutants (4.3), controls for the positive security verdicts (4.4), and the
defects that fuzzing, fault injection and review found. Two gaps remain in that answer:

1. **F45's gate was never mutated.** `require_mediator` in the bridge was added after 4.3 ran. A test
   for it exists (`selftest_real_platform`, "another ordinary user, not the designated one, is refused
   by the bridge"), but nothing shows that test fails when the gate is wrong. That is F39's shape.
2. **Nobody knows which code no test runs.** 18/18 says those 18 changes are caught; it says nothing
   about the code no mutant touched. Branch coverage shows which branches the 26 suites never execute.

This is verification on the cut-off candidate, `verify-2026-10-f45`. Any fix follows the campaign's
rule: a new tag, and a regression on it.

## (a) Mutants M18a–M18c: the bridge's gate

Each is one exact replacement in `framework/ha_bridge/confine_bridge/__init__.py`, added to
`verify/mutants/mutants.py` like the others.

| Mutant | What is broken | Claim |
|---|---|---|
| M18a | the gate admits every authenticated user | F45: only an admin or the designated mediator may use the bridge |
| M18b | the gate admits every user once *some* mediator is designated (`designated` instead of `user.id == designated`) | the same, the subtler mistake |
| M18c | `designate_mediator` loses `require_admin`, so any user may name itself the mediator | naming the mediator is an admin's act |

**How it runs, and why it differs from 4.3.** The bridge runs inside (A), not in the suites' process.
`house_a up` copies the bridge from the tree it is run from, so each mutant needs (A) brought up from
the mutated tree. 4.3's runner never did this; no mutant then touched the bridge, so nothing was lost,
but a bridge mutant run that way would test the unmutated bridge and could only "survive". Per mutant:
`house_a down`; a fresh copy of the tag's `framework/` and `experiments/`; the patch; `house_a up` from
that copy; all 26 suites with 4.3's runner settings (300 s per suite, own `TMPDIR`); `house_a down`.
Afterwards (A) is brought up from the unmutated tag and all 26 run again as the control.

**Criteria** are 4.3's: killed when at least one suite exits non-zero, each kill read and recorded by
the failing check, a kill by an unrelated crash reported as weak.

**Predictions.**
- M18a killed, by exactly the one check named above, and by nothing else. (Every other suite uses the
  designated mediator or an admin, which both pass a gate that admits everyone.)
- M18b killed by the same check: the other user is not the designated one, and a mediator is designated.
- **M18c survives.** No test has a non-admin call `confine_bridge/designate_mediator`. If so, it is a
  test gap of F22's kind (Minor, the code was right): a check is added to `selftest_real_platform`,
  shown to fail under M18c and pass unmutated, and M18c is re-run.

## (b) Branch coverage of the 26 suites

**Tool.** `coverage` 7.10.7 (pinned), installed with `pip install --target` into a directory of its
own per interpreter, outside both interpreters the measurements use (system Python 3.13 and
`ha314`'s 3.14). Nothing is installed into either. A `sitecustomize.py` in a directory on
`PYTHONPATH` starts measurement in every Python process that inherits that variable, when
`COVERAGE_PROCESS_START` is set; it also runs Debian's own `sitecustomize` so nothing else changes.
Branch coverage on, parallel data files, `patch = _exit` so a process ending in `os._exit` still saves.

**What it can and cannot see.**
- *Seen:* every process started by a suite with the environment inherited: the suites themselves, the
  mediator and supervisor in them, and `confine.enter` up to the sandbox's `pivot_root` (`spawn.py`
  keeps the caller's `PYTHONPATH`).
- *The bridge, inside (A).* `house_a` starts `hass` with `PYTHONPATH` set to `houseA-deps`, so the
  `sitecustomize.py` is copied there for the run only and removed by its literal path afterwards; a
  listing of `houseA-deps` with checksums is taken before and compared after. If (A) under
  measurement is too slow for the suites' timeouts, the bridge is read by hand instead, and that is
  stated.
- *Not seen:* code that runs inside a sandbox after `pivot_root`: `sandbox.build_root`'s tail,
  `seccomp.install`, `sandbox_runtime.py`, `egress_shim.py`. The sandbox's environment is fixed
  (`enter.BASE_ENV`) and the data file's path does not exist there. These are tested by behaviour
  (M13, M14, M15 killed in 4.3; the adversary suite), not by coverage, and the result says so.

**Scope of the reading.** All of `confine/` is measured. Every unexecuted branch is read and put in
one of four classes in the **enforcement files**: `mediator.py`, `manifest.py`, `channel.py`,
`audit.py`, `egress.py`, `supervise.py`, `spawn.py`, `enter.py` (pre-pivot part), `cgroup.py`,
`real_platform.py`, and the bridge:

- **G, test gap on a security path:** a decision, refusal, check or record that no test executes.
  Each G is a finding (Minor if the code is right on reading, Major if it is wrong). It gets a test
  that fails first against a mutant of that branch, as in F22.
- **E, error handling:** a defensive path (I/O failure, malformed input, race) whose absence would not
  change a security outcome. Listed, not a finding, unless reading shows it is wrong.
- **D, dead:** unreachable. Listed; removed only if the writing turns it up.
- **U, unmeasurable:** runs where coverage cannot see (above).

Other files (harnesses, `compat.py`, `endtoend*`, the self-tests) are reported in the per-file table
and not read branch by branch.

**Predictions** (numbers before the run).
- Branch coverage of the enforcement files, combined: **75–90%**. `mediator.py` alone 80–90%.
- Most unexecuted branches in the enforcement files are class E, chiefly F33's exception boundary
  and I/O failures in `audit.py`.
- **At least one class G** in the enforcement files. Reasoning: 4.3 found one survivor in 18 chosen
  points, and coverage looks at every branch, not chosen ones.
- In the bridge, `designate_mediator`'s two error replies (`not_set_up`, `no_such_user`) are
  unexecuted; class E.
- The bridge under measurement starts slower but within the suites' timeouts.

## Outputs

`experiments/verify/results/phase4/mutants_f45/` and `experiments/verify/results/phase4/coverage/`,
each with a README of what ran and its result; findings from F47 in the plan's §11; the report's
record in §7.45.12.
