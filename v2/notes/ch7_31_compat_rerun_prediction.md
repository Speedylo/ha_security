# §7.31 follow-up — the compatibility arms, re-run on the corrected `build_hass`: prediction

**Written 2026-10-03, before any of the four runs.** Never revised after a run.

## Why

§7.31 changed `sandbox_runtime.build_hass` — it now calls `frame.async_setup` and
`template.async_setup`, and loads the `network` singleton, as a real bootstrap does — and added
`/etc/ssl/certs` to the sandbox's read-only runtime paths. `build_hass` sits under every runtime,
including `compat`'s `inspect()`, so every compatibility figure in §7.12, §7.23 and §7.29 was
measured on the instance §7.31 found deficient. The figures must be re-measured, not assumed.

## The four runs, identical to the last recorded ones except for the code

| Run | Corpus | Profile | Last result |
|---|---|---|---|
| `c1_baseline` | head (37) | `baseline` + platform-deps | 31 ok · 3 undeclared_dependency · 2 other · 1 needs_component |
| `c1_declared_core` | head (37) | `declared` + platform-deps | identical |
| `uniform_baseline` | uniform (40) | `baseline` + platform-deps | 37 ok · 1 undeclared_dependency · 2 other |
| `uniform_confined` | uniform (40) | `declared` + platform-deps | identical |

## Prediction

**P1 — all four reproduce their category counts and their failing members exactly, so the paired
result (zero import-level cost of confinement, on both corpora) is unchanged.** Confidence: high.
Every non-`ok` row was read before writing this: `aiofiles` missing (×3 head, ×1 uniform),
`hacs_frontend` absent from the corpus, `spook` not found, and three platform import errors on
APIs the 2026.8 release removed (`SOURCE_TYPE_GPS`, `COLOR_MODE_BRIGHTNESS`, and
`next_rocket_launch.sensor`). None is the frame helper, the `network` singleton or TLS, and
`inspect()` imports modules rather than setting up config entries, which is where all three
§7.31 defects live.

**P2 — C1 still counts zero source changes in both head arms.** High.

**What would falsify P1 in an interesting way:** an integration whose *import* path touches
`frame.report_usage` at module level, or a platform that builds a coordinator at import. If any
row moves, it is reported per member with its traceback, in both arms, before any rate is restated.
