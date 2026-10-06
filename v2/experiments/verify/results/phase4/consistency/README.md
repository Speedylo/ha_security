# Verification 4.9 — the report agrees with itself (2026-10-06)

Criteria: `notes/integrity_consistency_prediction.md` §4.9, committed before the checks.

| Check | Result |
|---|---|
| `report/toc.py --check` | contents page current (`toc_check.txt`) |
| Every `§` reference resolves to a heading | 2,442 references, 0 unresolved; 10 point at `01_PLAN.md`, which is in the repository (`consistency.txt`) |
| Every `[n]` cited is in the bibliography, every entry cited | 29 entries, 0 problems |
| Control | a copy of the report with two bad `§` references, two citations of missing entries and one entry removed: all five caught |
| Stated counts | 25 suites and the base self-test; 19 threats (15 demonstrated, 2 partial, 2 retained); 20 requirement rows (C1–C4, F1–F4, S1–S9, N1–N3); 29 references: each matches its artefact |
| Shared figures, abstract and Chapters 7 and 8 | `verify/recompute.py`: 39/39 (`../review/recompute_after.txt`) |

**Finding F38.** T06's verdict reads ⚠ Partial because "the subscription half is a refusal without a
delivered stream". Its own row and the T1 row both say §7.36 closed that half on 2026-10-04, and S3,
the requirement T06 maps to, moved to ✅ Met. The count of 2026-10-05 (§7.44.4, §8.2.1) still
lists T06 as partial: 15 demonstrated and 2 partial. Restating T06 would make it 16 and 1. That
raises a security claim, so it is Younes's decision.

**The submission draft** (`v2/submission/`) is stale by design, and phase R rewrites it. It still
carries 31.5 µs (5 times), "77 integrations" (4), "eighteen threats" (3) and 272 decisions/s (2).
These are recorded here as input to phase R and were not corrected.
