# The final pass on `verify-2026-10-final` (2026-10-06)

Criteria and predictions: `notes/final_pass_prediction.md`, committed before the run. Run by
`verify/final_timing.sh` on a fresh clone of the tag, on the Pi (up 7 h 20 min, not a fresh boot), with
(A) restarted from that clone.

**Suites:** 26/26, twice (`suites_1/`, `suites_2/`), exit criterion 3.

**Timings and memory** (`../../phase3_timing/final/`, judged by `verify/timing_stats.py`, output in
`../../phase3_timing/final_stats.txt`, exit criterion 4):

- **All 13 figures are within their criterion on the median across the four runs**, which is the
  register's rule: Phase 3's three passes plus this one.
- **On the final pass alone, two are outside**, against my prediction that none would be:
  - marginal memory per added sandbox, 131 MB, +5.5% (F43). The four runs give 126–134 MB, and
    §7.35 had already called this figure unreproducible;
  - a user's command, 11.6 ms, −27%, in the faster direction (F44). The four runs give 15.7, 15.7,
    13.4 and 11.6 ms, and why it fell is not established.

  Both are now stated as ranges, with dated pointers.
- **The fixes since Phase 3 left their paths where they were:** mediation latency 41.2 µs, inside
  the predicted 40–47; the durable record 3.67 ms, unchanged.
- **Statistics owed since Phase 3:** each figure's median across the four runs and a bootstrap 95%
  interval of it (10,000 resamples). With four runs that interval is close to the observed range,
  and is reported as such. The p99 is given where a run records one: mediation latency 53.2–62.1 µs,
  the durable record 5.0–8.0 ms. Each figure is labelled warm, cold, or not controlled by its
  harness (`stats.json`).
