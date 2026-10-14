# §7 Literature Review — plan and decisions (2026-10-14)

Budget 1,400 words, 4 pp. Skill loaded before drafting. Rebuilt from `report/02_literature_and_gap.md`
(4,238 words), using the 2026-09-08 draft (1,834) only as a skeleton.

**Structure.** 7.1 scope and method (narrative review, its limits); 7.2 browser extensions [12];
7.3 smart-home application platforms [13]–[17] with Table 7.1 (assumptions); 7.4 extensible hubs:
Corno and Mannella [9], the MUD architecture [18], [19], the thesis [20], the systematic review [21],
GitHub Security Lab [22]; 7.5 supply chain [23], [8] and measurement as method [24]; 7.6 the gap and
the three contributions; threats to validity folded into 7.1 and the end of 7.6.

**Changed against the working report and the old draft:**
- Table 7.1's "existing permission model: none" for Home Assistant is wrong after F45. Now: a model for
  users of its interfaces, which in-process code bypasses [52] (as §2.3 states).
- The comparison with Corno and Mannella's eleven threats (moved out of §8 on 2026-10-11) is one
  paragraph in 7.4 pointing to Table C.5, with its result: eight of eleven mapped, five without
  qualification, and the three unmapped are availability consequences this design does not touch.
- The RFC [11] is not repeated: §2.3 carries it.
- Contribution 1 is stated over both corpora (the uniform re-run of 2026-10-03, working report §7.33).
- "third-party" → "community" (decided 2026-10-14).

**Decisions / flags for Younes:**
1. **Contribution 1 has no results anywhere in the rewritten submission.** §12 reports compatibility,
   security, cost and verification; §9 states the design without the API-surface figures that justify
   the schema (states read by 41.0% of head integrations, `config.path` by 33.3%, all four granularity
   decisions holding on the uniform 40). Either §9 gains a short paragraph (where the schema is
   justified), or §12 gains a sub-section, or the contribution is restated as part of contribution 2.
   Recommendation: two or three sentences in §9.3, where the schema's decisions are made, since the
   figures were used as design evidence rather than as a result.
2. The Thingnes and Meland quotation is kept, because it is the strongest independent evidence that the
   gap is real and it names the evaluation framing the project adopted.
