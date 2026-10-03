# §8.7 item 12 — two footprint debts: prediction

**Written 2026-10-03, before either run.** Never revised after it.

§8.7 item 12 carries two measurement debts, both described there as "neither load-bearing on any
claim". This note predicts both before they are paid.

## Part A — `r2_footprint` on the corrected builder (§7.20.4)

§5.6.3's figures, 176 MB for the first sandbox and 136 MB for each one after it, were produced by a
builder that marks the instance running with `set_state(CoreState.running)`, which never fires
`EVENT_HOMEASSISTANT_START`. §7.20.4 said the defect affects deferred callbacks, not process size, so
the figures were "unlikely to move". It also said unlikely is not measured.

`measure.py` and `measure_scale.py` now take `--builder corrected`. The corrected builder starts the
instance with `async_start()` after the integration is set up (§6.3.3), and adds the `frame` and
`template` helpers and the `network` singleton (§7.31). It **keeps the base `homeassistant`
component**, so it differs from the original only in what §7.20.4 asked about. Dropping that
component is §6.3.2's separate result (90 MB PSS, 26 sandboxes) and is not being re-measured here.
The default stays `original`, so §5.6.3's figures remain reproducible from the same file.

Both builders run on the Pi on the same day, one after the other: a single-sandbox run and a
six-sandbox scale run each.

| | §5.6.3 (2026-08-24) | Prediction | Confidence |
|---|---|---|---|
| **A1** The start event fires under `corrected` and not under `original` | not measured | holds. This is the defect itself, now observed by a listener rather than read from the recipe | high |
| **A2** The probe reaches `LOADED` and publishes `sensor.*` under both builders | yes (original) | holds for both | high |
| **A3** Single-sandbox RSS with the integration up | 176.1 MB | corrected within ±8 MB of today's original | medium-high |
| **A4** Six-sandbox PSS per sandbox | 136.4 MB | corrected within ±5% of today's original | medium |
| **A5** Marginal cost (`MemAvailable` delta) | 136.5 MB | corrected within ±10% of today's original. This figure is noisier than PSS | medium |
| **A6** Today's `original` against 2026-08-24's | — | within ±5% on A3 and A4. The platform and the dependencies are the same release; the kernel and page cache are not | medium |

**If A3–A5 hold**, §5.6.3's figures stand without the caveat §7.20.4 attached, and §7.20.4 gets a
dated pointer. **If any moves by more than its band**, the start event's deferred work has a memory
cost, and every figure derived from §5.6.3 inherits the movement, so each has to be traced.

## Part B — PSS against declaration depth, with enough sandboxes to resolve (§7.20.3)

§7.20.3 measured three points at three sandboxes each and reported a non-monotonic series, which it
declined to read as a curve:

| Declared components | PSS per sandbox |
|---|---|
| none | 136.3 MB |
| `http`, `websocket_api` | 95.7 MB |
| `frontend`, `http`, `websocket_api`, `lovelace` | 115.8 MB |

**A hypothesis was formed before this run, and this run tests it.** The 136.3 MB "none" point sits
where the ten-component `unstripped` profile measures (130.4 MB on 2026-08-25, 135.7 MB on 2026-10-03),
and far from `minimal` (54.5 and 56.5 MB). `experiments/unstrip/scale.py`'s `--components` defaulted
to the empty string, and an empty value fell through to the default profile, `unstripped`. The run's
command line and raw output were never committed and do not survive in any transcript or on the Pi,
so the hypothesis cannot be checked against the record. It can only be checked by measurement.
`scale.py` now refuses an empty `--components`.

Four points, in rounds: each round runs all four in turn, and there are three rounds. That gives
**six sandboxes per point and three repetitions**, twice the sandboxes and three times the runs.
`platform-deps` is August's set (`~/r2exp/t2/platform-deps-aug`), as §7.31.12's re-run used.

| Point | `scale.py` arguments |
|---|---|
| none | `--profile minimal` |
| two | `--components http,websocket_api` |
| four | `--components frontend,http,websocket_api,lovelace` |
| ten | `--profile unstripped` |

| | Prediction | Confidence |
|---|---|---|
| **B1** The series is monotonic: none < two ≤ four ≤ ten, in the mean over three rounds | holds | medium-high |
| **B2** Within a point, the three rounds' per-sandbox PSS spread by ≤ 6 MB | holds for all four points | medium |
| **B3** "none" measures 50–62 MB, near `minimal`'s 56.5 MB, so it was never 136 MB | holds | high |
| **B4** "ten" measures within ±6 MB of 136.3 MB, so **§7.20.3's first row is reproduced by the ten-component profile** | holds. This supports the mislabelling hypothesis without proving it, since the original command is lost | medium |
| **B5** "two" lands within ±10 MB of 95.7 MB and "four" within ±10 MB of 115.8 MB, so §7.20.3's other two rows were sound | holds | low-medium. Three sandboxes per point may have been off by more than that |

**What would matter.** B1 failing with six sandboxes and three rounds would mean the non-monotonicity
was real and not the sample size or a label. That would need explaining before any curve is drawn.
B3 failing would kill the hypothesis.

**What this is for.** If B1 holds, §6.3.2's budget can be stated over the corpus's declaration
distribution (§6.13: twelve set up no components, median two) instead of only at the extremes. That
is what §7.10's item 4 asked for.
