# Documented literature search, 2024-12-01 to 2026-10-15 — results

Protocol: `notes/lit_search_2025_2026_protocol.md` (§9 decisions, §10 field amendment). Searches run
2026-10-15 18:49–18:50 UTC by `search.py`; raw responses in `raw/` (gzipped); decisions in
`decisions.py`, applied to `screening.csv`. Full texts read are kept locally in `fulltext/`, not
committed.

## Counts

| Stage | Records |
|---|---|
| Found, all sources (OpenAlex 641 incl. 496 full-text S1 sweep and 11 forward citations; Semantic Scholar 76; arXiv 4) | 721 |
| After de-duplication (DOI, then normalised title; the seed [25] removed) | 626 |
| Excluded on title | 579 |
| Screened on abstract | 47 |
| Excluded on abstract or full text (C) | 43 |
| **B — adjacent** | **3, and 1 pending (B?)** |
| **A — closes the gap** | **0, pending one full text** |

Full text was read for R0003, R0048, R0226, R0261. It could not be obtained (publisher blocks,
paywall) for R0057, R0231, R0281, R0497, R0611; those were judged on their abstracts, as §5.3 allows.
Google Scholar (S1, by hand) is **not yet run** — Younes, §9.1.

## Against the prediction (§6)

- **A: zero** — holds provisionally. One record, TAPShield (R0497), cannot be settled without its
  full text; see below.
- **B: zero to five** — holds: P3CRID (R0226), SHERLOC (R0057), the ESPHome/MQTT analysis (R0003),
  and TAPShield if it stays B.
- **Forward citations of [5], [15], [33], [25] since 2024-12-01: fewer than 30** — holds: 11
  (4, 6, 0, 1). None builds or evaluates confinement of hub extensions.

## What matters for §7

1. **P3CRID** (Algorithms 19(5):347, 2026) is a 2026 smart-home threat model that names Home
   Assistant integrations as an attack vector and cites [5]; for integration code taken from GitHub its
   only mitigation is that the owner reviews the code. It supports the gap sentence with a source
   inside the window.
2. **TAPShield** (Moazen et al., IEEE Euro S&P 2025, pp. 60–77) protects apps on Node-RED and IFTTT
   with Intel SGX and language-level sandboxes, and its abstract reports "compatibility trade-offs" on
   real-world apps. It is not Home Assistant, so the first half of §7's sentence stands. Whether it
   meets the second half ("none measures the compatibility cost of confining extensions that already
   exist") depends on what that compatibility evaluation is. **Full text needed** (IEEE Xplore,
   university access).
3. **Outside the window, found by following TAPShield back:** SandTrap (Ahmadpanah, Hedin, Balliu,
   Olsson and Sabelfeld, USENIX Security 2021) confines **unmodified** third-party Node-RED nodes at
   run time with per-node policies (module, API, value and context levels) in a self-hosted hub, and
   reports under 100 ms of load and trigger overhead per node. Its evaluation is 10 benign and 10
   malicious cases per platform, not a compatibility measurement over a corpus, so the sentence
   survives; but SandTrap is the closest prior design to this project's and **§7 does not cite it**.
   It is a miss of the narrative review, not a result of this search, and is reported as such.

## Owed

- Younes: Google Scholar S1 by hand (date, hit count, first 50 results) → rows with source `scholar`.
- Younes: TAPShield's full text through the library; then its row is settled A or B.
- Younes: review every A and B (R0003, R0057, R0226, R0497) and the 20 exclusions in
  `review_sample.csv` (seed 20261015); disagreements recorded in that file, not erased.
- Then: §7.1's one or two sentences with these counts; SandTrap (and TAPShield) placed in §7's text
  where the comparison with this project's design is made.
