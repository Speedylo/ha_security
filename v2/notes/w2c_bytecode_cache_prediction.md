# W2 (c) — does a confined sandbox read the bytecode cache? Design and prediction

**Written 2026-10-04, before any code.** §4 is never revised; outcomes are appended below it.

## 1. The question

§7.35.2 found that §5.6.3's 176 MB first-sandbox figure was a **cold start**: the run that compiled
Home Assistant's bytecode for the first time. A warm sandbox is 161 MB, and cold costs about 16 MB
and 4–5 s more. §7.35.4 left open whether a *confined* sandbox is ever warm. The sandbox binds the
interpreter, the platform's dependencies and the integration read-only. So any module without a
valid `.pyc` already on disk is compiled on every start, and the result can never be saved.

## 2. How it is measured

Not by inference from memory or time, but module by module. Python's `SourceFileLoader` uses
`__pycache__/<name>.cpython-<ver>.pyc` when the file exists and its 16-byte header is valid: the
magic number, then flags, then the source's modification time and size, unless the file was
written in hash-checked mode. Reading needs no write access. So at the end of a confined run, the
sandbox checks every loaded module's `__cached__` against its source exactly as the loader does,
and counts **from cache** against **compiled**, grouped by where the module lives: the standard
library, the pinned environment (`ha314`), the shared `platform-deps`, the run's own `deps`, and the
integration's own directory.

The subject is `thermal_comfort` on the stand-in platform, the usual end-to-end run with the
measurement switched on.

## 3. Why it matters

If the per-run trees compile on every start, the fix belongs to the installer, not the sandbox:
compile bytecode at install (`uv pip install --compile-bytecode`, or `compileall`), while the tree
is still writable. That is one flag, but the report currently states footprint figures for a warm
sandbox without saying whether a confined one is ever warm.

## 4. Predictions

| | Prediction | Confidence |
|---|---|---|
| **B1** | The standard library and `ha314` load almost entirely **from cache** (≥ 95% of their modules), because earlier unconfined runs, which had write access, compiled them | medium — `uv` does not compile by default, so it depends on what ran unconfined before |
| **B2** | The run's own `deps`, installed fresh by `uv` for each run, load **0%** from cache, so they are compiled on every confined start | high |
| **B3** | The integration's own component, copied fresh for each run, loads **0%** from cache | high |
| **B4** | `platform-deps` is mixed, with some modules cached and some not | low |
| **B5** | Installing the per-run trees with `--compile-bytecode` turns B2 and B3 into ≥ 95% from cache, and shortens the sandbox's start measurably | medium |
| **B6** | Something not listed is found | medium |

---

## 5. Outcomes, 2026-10-04 (appended; §4 is unchanged)

Evidence: `experiments/bytecode_cache/results/w2c_20261004/`. Three subjects × three modes on the Pi,
one run per cell. **The control holds:** with `--cold` (an empty `PYTHONPYCACHEPREFIX` inside the
sandbox), the probe reports 0 modules from cache in every tree, so it can tell the two apart.

| | Outcome |
|---|---|
| **B1** | **Held, more strongly than predicted.** Standard library and `ha314`: 100% from cache in all three subjects (212–218 and 245–508 modules) |
| **B2** | **Held.** The run's own `deps`: 0/3 (`watchman`), 0/84 (`powercalc`), compiled on every start |
| **B3** | **Held, but only after a confound was removed.** The integration's own code: 0/4, 0/18, 0/80. The first run said 4/4, because the harness copied the corpus's `__pycache__`, written by the 2026-09-02 unconfined runs, into every confined run. A fresh HACS download has none. The harness now leaves it out |
| **B4** | **Wrong.** `platform-deps` was 100% from cache (560–846 modules), not mixed |
| **B5** | **Held.** With `--compile-bytecode` (deps) and `compileall` (component), both are 100% from cache. Time at report: `powercalc` 2.47 → 1.87 s (−24%), `watchman` 1.24 → 1.18 s, `thermal_comfort` 0.92 → 0.91 s. A cold platform, for scale, costs 3–4.6 s more |
| **B6** | **Held: the confound in B3.** Every earlier confined end-to-end run was warm for the integration's own code, because of the copied cache. No reported figure depends on start time, so nothing changes |

**The answer.** A read-only mount does not make a confined start cold: the sandbox reads whatever
bytecode already exists. What it cannot do is create any. The platform's trees are warm because
something with write access compiled them; the integration and its dependencies are compiled on every
start unless the installer compiles them. That is one installer flag, and §7.35.4's open question
is closed.
