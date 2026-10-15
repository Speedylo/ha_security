# Documented literature search, December 2024 – October 2026: protocol

**Written 2026-10-14, before any search is run. Never revised after the first search; a change of plan
gets a dated amendment at the end.**

## 1. Why

§7's central claim is an absence: *no published work builds or evaluates runtime confinement of Home
Assistant's community integrations, and none measures the compatibility cost of confining extensions
that already exist.* The review behind §7 is narrative. For January 2019 – November 2024 the claim
leans on Thingnes and Meland's systematic review [21] (713 papers screened), which found the gap and
named it as future research. **Nothing covers December 2024 onwards**, the period in which similar work
is most likely to have appeared. This search covers that window with a documented, repeatable
procedure, so that §7.1 can state it with counts.

It is not a full systematic review: one database protocol, one primary screener, no quality appraisal
of included studies. §7.1 will say exactly that.

## 2. Question and window

**Question.** Has any work published or posted since 2024-12-01 (a) proposed, built or evaluated a
mechanism that restricts the run-time authority of third-party code (plug-ins, integrations, apps)
executing on a smart-home hub or gateway, or (b) measured what such code uses of its platform, or what
it costs in compatibility to confine it?

**Window.** Publication date 2024-12-01 to the date of the search (recorded per query).

## 3. Sources

| Source | How | Why |
|---|---|---|
| OpenAlex | API, scripted; raw JSON saved | Broadest open index (journals, proceedings, arXiv); reachable from here (checked 2026-10-14) |
| Semantic Scholar | API, scripted, one request every few seconds (it returned HTTP 429 on 2026-10-14) | Second index with different coverage, and its citation graph |
| arXiv | API, scripted | Preprints, where the newest work appears first (did not answer on 2026-10-14; retry) |
| Forward citations | OpenAlex `cites:` filter for [9], [18], [20], [21] since 2024-12-01 | The strongest check: new work on this problem almost certainly cites at least one of them |
| Google Scholar | **Decision for Younes** (§8) | No API; results vary by person and day, so it cannot be reproduced |

## 4. Search strings

Each string runs in every scripted source, adapted only to each API's syntax. The exact query sent is
saved beside its results.

- **S1 — Home Assistant directly:** `"Home Assistant"` AND (integration OR plugin OR extension OR
  "custom component") AND (sandbox OR isolation OR confinement OR permission OR "least privilege" OR
  "access control").
- **S2 — hubs and gateways in general:** ("smart home" OR "home automation") AND (hub OR gateway OR
  platform) AND (plugin OR extension OR "third-party" OR app) AND (sandbox OR isolation OR confinement
  OR "least privilege" OR permission).
- **S3 — other self-hosted hubs:** (openHAB OR "Node-RED" OR Homey OR Hubitat OR Domoticz OR ioBroker)
  AND (sandbox OR isolation OR permission OR "least privilege").
- **S4 — the measurement half:** ("smart home" OR "Home Assistant" OR "IoT platform") AND (plugin OR
  integration OR extension) AND ("API usage" OR overprivilege OR "compatibility").

## 5. Screening

1. **De-duplicate** across sources by DOI, then by normalised title.
2. **Title and abstract**, against the inclusion criterion of §2 and these exclusions: device firmware;
   network-only anomaly or intrusion detection; vendor-cloud application platforms *unless* the work
   confines existing applications without changing them; not in English; outside the window.
3. **Full text** for every record that passes 2. A record whose full text cannot be obtained is kept,
   marked, and judged on its abstract.
4. **Classify** each record that passes 3:
   - **A — closes the gap:** builds or evaluates run-time confinement of Home Assistant integrations, or
     measures the compatibility cost of confining existing extensions. §7's claim must then change.
   - **B — adjacent:** the same problem on another hub, or Home Assistant work that is diagnostic,
     network-layer or a threat model. Cited in §7 where it changes what §7 says.
   - **C — not relevant** after full reading, with the reason.

Every decision is a row in `screening.csv` (id, source, title, year, venue, DOI, stage reached,
decision, reason). Claude screens first; **Younes reviews every A and B, and a random sample of 20
exclusions** (seed recorded), as a partial second reviewer. Disagreements are recorded, not erased.

## 6. Prediction (registered now)

- **A: zero.** Basis: nothing surfaced in the narrative searches up to September 2026, and [21]'s
  future-work paragraph suggests that the direction was open at the end of 2024.
- **B: between zero and five**, most of them threat models, network-layer work or other platforms.
- **Forward citations of [9], [18], [20], [21] since 2024-12-01: fewer than 30 in total.**

If an A appears, §7's gap sentence, §7.6's contributions and the abstract change, and contribution 2's
novelty is restated against it; contributions 1 and 3 are checked against it separately.

## 7. Records and reporting

- `experiments/lit_search_2026/`: `search.py` (the queries, the APIs, the date), `raw/` (one JSON file per
  query per source), `screening.csv`, `summary.md` with counts at each stage (records found,
  after de-duplication, after title and abstract, after full text, A/B/C).
- **In §7.1:** one or two sentences stating the window, the sources, the counts and the outcome, and
  that it is a documented search rather than a systematic review. Any B that changes the argument goes
  into the text of §7.4–§7.6.
- Credential scan before pushing, as always (the API calls use no key unless Younes supplies one).

## 8. Decisions for Younes before running

1. **Google Scholar.** (a) Younes runs S1–S4 by hand and records the date, the hit count and the first
   50 results of each; or (b) it is omitted, and §7.1 says why (not reproducible). Recommendation: (a)
   for S1 only, the Home Assistant string, since that is where an A would be.
2. **Semantic Scholar API key.** A free key avoids the rate limit; without one, the script waits between
   requests, which is slower but works.
3. **Second reviewer.** The partial check in §5 (every A and B, and 20 random exclusions) is the
   recommendation. A full second screening of every record is stronger, but costs Younes several hours.

**Estimated time:** script and runs about 2 hours; screening 1–3 hours, depending on how many records
survive de-duplication; Younes's checks about an hour; the §7.1 text 30 minutes.

## 9. Amendment 2026-10-15 — decisions taken, before any search has run

1. **Google Scholar:** option (a) for S1 only. Younes runs S1 by hand and records the date, the hit
   count and the first 50 results; those enter `screening.csv` with source `scholar`.
2. **Semantic Scholar:** no API key; the script waits between requests and retries on HTTP 429.
3. **Second reviewer:** the partial check of §5 (every A and B, and 20 random exclusions, seed
   recorded).

**Reference numbers.** The references were renumbered on 2026-10-15. The forward-citation seeds of §3,
written as [9], [18], [20], [21], are now [5] (Corno and Mannella 2022, threat model), [15] (Corno and
Mannella 2023, gateway MUD), [33] (Mannella's 2024 thesis) and [25] (Thingnes and Meland 2025). [25]
was itself published inside the window; it is the seed, not a result, and is excluded from the counts.
A seed that OpenAlex does not index is recorded as such, not replaced.
