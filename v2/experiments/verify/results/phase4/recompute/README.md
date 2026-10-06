# Phase 4.1 — every headline number, re-derived (2026-10-06)

`verify/recompute.py` recomputes each figure from the raw result files the report cites, and
separately reads the figure back out of every place the report states it, with a pattern that
captures whatever is written there. A claim is EQUAL only when every stated copy matches the
recomputation. The two survey claims (credential count, cloud share) need the corpus, rebuilt with
`figures/fetch_hacs_corpus.py --rebuild`.

**Coverage: 39 claims, 63 stated copies.**
- The abstract (18).
- The tables of §8.2's three assertions (10).
- One or more headlines from each of §7.13, §7.14, §7.22, §7.29, §7.31.11, §7.33, §7.36, §7.39 and
  §7.44 (11).

**Result (`recompute.txt`, `recompute.json`): 37 EQUAL, 2 DIFFERS.**

| Claim | Stated | Recomputed | Finding |
|---|---|---|---|
| A1.13, end-to-end integrations | Ten | Thirteen (§7.40–§7.42 added three) | F01 |
| A1.22, the push path's worst case | 1.57 ms | 2.23 ms in the run the 0.71 ms median comes from; 1.49–2.91 ms across 15 committed runs; 1.57 ms in none | F23 |

**Found by building the claims rather than by the final run:**
- F24: "77 integrations" counts measurements; 75 are distinct.
- F25: the abstract's suite counts mix two conventions.
- F26: §8.2.3 said 269 and 272 decisions/s two rows apart, a drift introduced by F17's own
  correction. Fixed.
- F27: "26 of 37 need a credential" had no committed survey. A whole-directory scan reproduces it
  exactly, and a scan of `config_flow.py` alone gives 19.

**Control (`control_planted.txt`).** On a copy of the report with three figures changed (the abstract's
92%, §7.44's 235 answers, §7.33's `bus` 17.5%), each of the three is reported DIFFERS. The first stage's
control planted three others (3.67 ms, §8.2.1's 0 of 20, 92%), and all were caught.

**What this does not cover.** Chapters 5 and 6 keep their own historical figures by convention, and
are not checked against today's data. Verdict-type claims (an integration loads, a request is refused)
were judged by Phase 2's L3 comparison and Phase 3a. Figures stated only in experiment READMEs are not
read back, except where a finding names one.

**After the corrections (`recompute_after_corrections.txt`): 39 of 39 EQUAL.** F01, F02, F23, F24,
F25 and F27 corrected on 2026-10-06 and recorded in §7.45.4. Where a figure was corrected by a dated
pointer, the claim reads the pointer, because the original line is kept as written.
