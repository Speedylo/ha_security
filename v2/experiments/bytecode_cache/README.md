# Experiment — does a confined sandbox read the bytecode cache? (W2 (c))

**Run:** 2026-10-04 · **Target:** Pi 5, `~/r2exp/ha314` (HA 2026.8.3, Python 3.14) · **Feeds:** §7.39 ·
**Answers:** §7.35.4's open question · **Predictions:** `notes/w2c_bytecode_cache_prediction.md`

    systemd-run --user --scope -q python3 -m confine.endtoend --corpus ~/r2exp/corpus \
        --python ~/r2exp/ha314/bin/python --only powercalc --bytecode \
        [--compile-bytecode | --cold] --json out.json

`--bytecode` makes the sandbox classify every loaded module the way `SourceFileLoader` does
(`sandbox_runtime.bytecode_report`). A `.pyc` written after the process started counts as compiled.

| `results/w2c_20261004/` | |
|---|---|
| `matrix/<subject>_<mode>.json` | `thermal_comfort`, `watchman`, `powercalc` × default / compiled / cold, one run each |
| `bytecode_*_1.json`, `_2.json` | the first runs, **confounded**: the harness still copied the corpus's `__pycache__` |
| `suites/` | all suites on the Pi after the harness change |

Modules from cache / loaded, `powercalc`:

| | stdlib | ha314 | platform-deps | deps | component | time at report |
|---|---|---|---|---|---|---|
| as installed | 218/218 | 508/508 | 846/846 | 0/84 | 0/80 | 2.47 s |
| compiled at install | 218/218 | 508/508 | 846/846 | 84/84 | 80/80 | 1.87 s |
| cold (control) | 0 | 0 | 0 | 0 | 0 | 7.05 s |
