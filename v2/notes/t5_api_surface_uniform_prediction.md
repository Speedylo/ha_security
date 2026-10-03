# T5 — the API-surface parser on the uniform corpus: prediction

**Written 2026-10-03, before the run.** Never revised after it.

Contribution 1 (§2.8, §8.3) is an account of the API surface community integrations depend on. Its
community half was measured on `hacs-top150` — 144 integrations by install count — and its own
§6 said a uniform sample was "worth running before Chapter 7 reports coverage". §7.23 drew a uniform
corpus of 40 for compatibility and never ran this parser over it. This runs
`figures/api_surface.py` unchanged, under Python 3.14 as before, over `~/r2exp/corpus_uniform`.

**n = 40, so one integration is 2.5 points.** Differences under ~10 points are not distinguishable
from sampling at this size and will not be read as findings.

| | Head (144) | Prediction for uniform (40) | Confidence |
|---|---|---|---|
| **P1** zero parse failures | 0 | 0 | high |
| **P2** `config_entries` is still the most-used handle | 94.4% | ≥ 85% and still first | high — 38 of 40 have a config flow |
| **P3** `states` — the figure that rules out blanket state denial | 41.0% | 25–45%: lower, and **still far too common for a blanket denial** | medium |
| **P4** `config.path` — why file access must be path-scoped | 33.3% | 15–35%: still non-zero, so absolute denial still breaks integrations | medium |
| **P5** `auth` stays rare | 5.6% | ≤ 10% | high |
| **P6** fewer integrations register services | 56.2% | 30–50% — the uniform tail is simpler, as §7.23's 92% compatibility suggested | medium |
| **P7** cross-component reach | 71.5% | 45–70%, lower | low-medium |
| **P8** none of §5.10's six schema decisions is contradicted | — | holds | medium-high |

What would matter is P3 or P4 falling near zero — that would mean the decisions they support were
artefacts of sampling the head.
