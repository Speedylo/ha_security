# The final pass before the cut-off — criteria, written before it runs (2026-10-06)

Younes agreed the order: a final tag, then the timings on it, then the mutants on it, then the claim
register's statuses. This note fixes what the first two must show.

## The final tag

`verify-2026-10-final` is the code state the cut-off declares. Its framework is byte-identical to
`verify-2026-10-minor`, whose suites passed 26/26 twice. The commits since change only verification
scripts and documents. The final run still runs every suite twice on the final tag itself (exit
criterion 3), so the result cites the tag and does not need that argument.

## Timings and memory on the final tag (exit criterion 4)

**Why again.** Phase 3's three passes ran on the first frozen tag. Since then, three fixes touch the
paths those figures measure:
- F28: audit writes are unbuffered, with the file's size noted before each record;
- F33: every request's policy call and act sit inside an exception boundary;
- F08: each registration hashes the installed distributions.

**Run.** One pass of `verify/phase3_timing.sh` on a clone of the final tag (`verify/final_timing.sh`
sets the paths, and the pass is named `final`), with (A) restarted from that clone first.

**Criteria**, the register's, unchanged from Phase 3:
- **T** (timing): within ±20% of the figure the report states now. For one-client mediation latency,
  that is §7.45.1's corrected 43 µs (F17), not §7.19's original 31.5, which the report no longer
  claims. `verify/timing_stats.py` is updated to say so before the run.
- **M** (memory): within ±5%.

A figure outside its criterion is reported and corrected, not averaged away.

**Predictions.** Every figure stays within its criterion. The audit path is the one most likely to
move. Unbuffered writes add no `fsync`, which already dominates the durable record's 3.67 ms, so I
expect the durable-record figure to move by less than 5%. The exception boundary is a `try` with no
exception raised, which costs nothing measurable at 43 µs. Mediation latency should land within
40–47 µs.

**Statistics owed since Phase 3** (plan §6), computed by `timing_stats.py` over the four runs (three
Phase 3 passes and the final one):
- the **median** across runs;
- the **p99** where the run records one: mediation latency and the durable record, from each run's
  own 2,000 samples;
- a **bootstrap 95% interval** of the median across runs (10,000 resamples). With four runs it is
  close to the observed range, and is reported as that;
- **warm or cold**, where the harness defines it. Latency and the durable record discard a warm-up,
  so they are warm. `bytecode_cold` drops the caches, so it is cold. Everything else is stated as
  not controlled.

## Mutants on the final tag (exit criterion 5)

All 18 mutants (M01–M17, with M08 split) are applied to the final tag's framework and run against
every suite. **Criterion:** every mutant is killed, meaning at least one suite fails. A patch that
no longer applies is regenerated against the final code, keeping the mutation's meaning, and the
regenerated patch is committed before it runs. **Prediction:** all 18 still apply or need only
context changes. M07, the record written after the act, touches `_handle_ready`, which F33
rewrapped, so it is the likeliest to need regenerating. All 18 are killed, and the suites added
since (F33, F34, F35, F39) kill some mutants that were killed only once before.
