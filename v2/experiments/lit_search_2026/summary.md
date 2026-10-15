# Documented literature search, 2024-12-01 to 2026-10-15 — results

Protocol: `notes/lit_search_2025_2026_protocol.md` (§9 decisions, §10 field amendment). Searches run
2026-10-15 18:49–18:50 UTC by `search.py`; raw responses in `raw/` (gzipped); decisions in
`decisions.py`, applied to `screening.csv`. Full texts read are kept locally in `fulltext/`, not
committed.

## Counts

| Stage | Records |
|---|---|
| Found, all sources (OpenAlex 641 incl. 496 full-text S1 sweep and 11 forward citations; Semantic Scholar 76; arXiv 4; Google Scholar 37 entries on four saved pages) | 758 |
| After de-duplication (DOI, then normalised title; the seed [25] removed) | 642 |
| Excluded on title | 590 |
| Screened on abstract (Scholar records on its snippet) | 52 |
| Excluded on abstract or full text (C) | 47 |
| **B — adjacent** | **5** (TAPShield on its abstract) |
| **A — closes the gap** | **0** |

Full text was read for R0003, R0048, R0226, R0261. It could not be obtained (publisher blocks,
paywall) for R0057, R0231, R0281, R0497, R0611; those were judged on their abstracts, as §5.3 allows.
**Google Scholar (S1, by hand, §9.1):** run by Younes 2026-10-15 19:19, range 2024–2026, the query as
written in §4; Scholar estimated "about 116 results" but displayed 37 entries over four pages (10, 10, 7,
10). Page 4 was reached by paging, with nothing clicked; it repeated seven of page 3's entries and added
three, and on a later attempt the same page came back empty (Younes, 2026-10-15). Scholar's paging is not
stable, which is why the protocol records this source as not reproducible, 30 of them distinct. 14 were already in the
set and 16 were new; one new record is B (R0639). Parsed by `scholar_parse.py` into `raw/scholar_S1.json.gz`;
the saved pages are kept in `scholar/`. Scholar's estimate is not a count of retrievable records.

## Against the prediction (§6)

- **A: zero** — holds, with TAPShield (R0497) judged on its abstract; see below.
- **B: zero to five** — holds: P3CRID (R0226), SHERLOC (R0057), the ESPHome/MQTT analysis (R0003),
  the protocol-security thesis from Scholar (R0639), and TAPShield (R0497).
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
   exist") depends on what that compatibility evaluation is, and its full text could not be obtained.
   It is classed B on the abstract, and §7's sentence is narrowed to Home Assistant's integrations so
   that it holds either way (Younes, 2026-10-15).
3. **Outside the window, found by following TAPShield back:** SandTrap (Ahmadpanah, Hedin, Balliu,
   Olsson and Sabelfeld, USENIX Security 2021) confines **unmodified** third-party Node-RED nodes at
   run time with per-node policies (module, API, value and context levels) in a self-hosted hub, and
   reports under 100 ms of load and trigger overhead per node. Its evaluation is 10 benign and 10
   malicious cases per platform, not a compatibility measurement over a corpus, so the sentence
   survives; but SandTrap is the closest prior design to this project's and **§7 does not cite it**.
   It is a miss of the narrative review, not a result of this search, and is reported as such.

## Owed

- TAPShield's full text could not be obtained (paywall; no institutional access; no repository copy).
  Younes decided 2026-10-15: B on the abstract, and §7's sentence narrowed so that it holds whatever
  TAPShield's compatibility evaluation measured.
- Younes: review every A and B (R0003, R0057, R0226, R0497, R0639) and the 20 exclusions in
  `review_sample.csv` (seed 20261015); disagreements recorded in that file, not erased.
- Done 2026-10-15: §7.1 gains one sentence (window, registered protocol, 642 records, none confining
  Home Assistant's integrations); §7.6's gap sentence is narrowed to Home Assistant and contributions 2
  and 3 name SandTrap as [42]. TAPShield and P3CRID are not cited (Younes declined the paragraphs).
