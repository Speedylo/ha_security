# The last experiments on the old instance, re-run: prediction

**Written 2026-10-03, before any of the runs.** Never revised after them.

§7.31.10 listed §7.14, §7.15 and Chapter 6's `unstrip` as built on `build_hass` and not re-measured.
Reading them before predicting refined that list. **`experiments/unstrip/unstrip.py` carries its own
frozen copy of `build_hass`** (line 59), as `r2_footprint/measure.py` does, so its per-component
costs (§6.12's `http` +37.8 MB and the rest) are untouched by §7.31 and are not re-run. What *does*
go through the framework is `scale.py`, which spawns sandboxes on `sandbox_runtime`, and the
`minimal` and `unstripped` compatibility profiles behind §6.11's 46% and §6.12's 70%.

| Run | Recorded | Prediction | Confidence |
|---|---|---|---|
| `selftest_reads --json` (§7.14, S3) | unconfined 36 visible, 7 reads, 4 churned; confined 1 visible, 1 mirrored, 15 decisions | identical counts | high — a world of states and the mediator's decisions; no setup, no fetch |
| `selftest_gc --json` (§7.15, S1) | unconfined 7 hits, credential found; confined 0, mediator 7 | identical hit counts; `heap_size` may differ and is not a claim | high |
| `compat --profile minimal` (§6.11) | 17/37 | 17/37, same members | high — loading the `network` singleton does not put `network` in `hass.config.components`, so `needs_component` rows stay |
| `compat --profile unstripped` (§6.12) | 26/37 | 26/37, same members | high |
| `scale.py --profile minimal`, 6 sandboxes | 54.5 MB PSS each, capacity 44 | rises by 0–4 MB per sandbox (frame, template, `network` singleton now built at startup); capacity 41–44 | medium |
| `scale.py --profile unstripped`, 6 sandboxes | 130.4 MB, capacity 18 | within ±4 MB — `http` already loaded the `network` singleton here, so the new cost is mostly the frame and template helpers | medium |

**What would matter:** a compatibility member changing, or the minimal footprint rising by more than
~5 MB, since §6.12's +75.9 MB and the capacity figures in §7.20 are argued from these.
