# §12 week-6 read-through — 2026-10-16

Every number in `submission/12_results.md` was checked against the final rerun
(`experiments/verify/results/final_20261016/`) and against Appendix F. Nothing is changed in the submission
until Younes chooses. Prose is 4,464 words against a budget of 3,500. Younes set no page limit, so the trims
below are for the reader's sake.

## Checked and correct

- Table 12.1: 7 live objects, 8,942 objects, 2/2 → 0/2, 36/36 → 1/36 (20/20 → 0/20). Step 6, both suite runs.
- Table 12.2 and the text: 31/37 and 37/40 in both arms, the same members and messages, 77 measurements of
  75 integrations. Step 5, exact.
- Table 12.3: as restated today (`fe897fa`).
- Table 12.4: equal to the committed JSONs in every field (step 12). 144 and 40.
- Table 12.5 and §12.3's arithmetic: 1/(3.67 ms + 43 µs) ≈ 269/s; 26 × 5 / 30 s = 4.33/s; 269 / 4.33 ≈ 62;
  3,670 / 43 ≈ 85; at 60% of 4,050 MB: 43 / 41 / 26 / 25 / 17; 17 / 4.02 ≈ 4.2 ("four times").
- §12.4: 4,864 malformed requests (step 4); 153 claims, 119 / 27 / 5 / 2; 39 headline figures; the campaign's
  53 findings (1 Critical, 12 Major, 4 Minor–Major, 32 Minor, 4 notes), consistent with Appendix F once
  F54–F62 are added (14, 5, 38, 4).

## Must fix: three statements the rest of the report contradicts

**C1. The findings stop at F56.** The paragraph after Table 12.6 counts 53 + 3 = 56 findings. Appendix F has 62,
and §12 never mentions F57–F62, although F57 (no approval before a sandbox started) is Major. Draft, to follow
"…two faults in the evaluation's own unconfined arm (F55, F56, Minor).":

> Checking Section 9 against the code added four more (F57–F60), the most serious that a sandbox could start
> without the user's approval (F57, Major), and the final rerun two (F61, F62, Minor), so Appendix F lists 62.

**C2. 40 deliberate defects, where every other section says 53.** §6, §8.6 and §13 all say 53, and the final
rerun ran 53 (52 killed, M25 equivalent). §12 still says 40 in two places:
- Table 12.6, mutation row, outcome: "Tests added; 39 of 40 defects caught, 1 equivalent" → "Tests added; 52 of
  53 defects caught at the final rerun, 1 equivalent".
- The paragraph after: "Each of the 40 deliberate defects" → "Each of the 53 deliberate defects".

**C3. §8.6 promises that "the numbers in Section 12 come from one version of the code", and Table 12.6 never
mentions the final rerun.** Even before today that sentence was not strictly true. The Figure column of
Table 12.5 has always given development figures, and the ranges now include the verification passes.
`adaptive_lighting`'s values and the retest's 42 of 45 also come from earlier runs. What is true is that the
rerun checked every one of these numbers at the final tag. Proposed:
- §8.6, last sentence → "One full rerun of every measurement, mutant, suite and fault follows the last fix, at
  the final tag, and every number in Section 12 was checked against it."
- Table 12.6, a new last row: | Final rerun at the submitted version | The fault-injection scripts lacked the
  approval F57 made mandatory (F61); one timing fell outside its band, faster than stated (F62) | F61 fixed and
  the faults rerun, 11 of 11; F62 reported as a range |

## For an outside reader

**O1. The phrase "five platform-only integrations" (the paragraph after Table 12.3's network discussion) is never
defined.** "the corrected platform instance" in the paragraph after Table 12.2 refers forward to it as well.
Suggestion: "the five integrations that need only the platform and no outside service (the first five rows of
Table 12.3)". The paragraph after Table 12.2 would then say "in a second run on a corrected test instance".

**O2. The defect paragraph gives "the 41% of the corpus it was built to serve" before 41% is introduced**, which
happens two paragraphs later. Suggestion: "did not work for the cloud-facing integrations it was built to serve".

**O3. "an earlier record of this project, which held that every correction had been to a sentence"** (the
paragraph after Table 12.6) refers to the working report, which an examiner has not read. Suggestion: delete
the three sentences from "The findings also qualify…" to "…restated accordingly." The two figure corrections
they mention are already F17 and F23 in Table 12.6.

**O4. The sentence about the final rerun added today sits between the F54 story and `watchman`.** Suggestion: move it
to just before the paragraph's last sentence, so the defect story and the `watchman` explanation stay
together.

## Trims (choose any; about 400 words in all)

| # | Where | What | ≈ words |
|---|---|---|---|
| T1 | §12 opening | Drop the sentence defining the two arms, since §11 defines them; keep "every result is a difference between a confined and an unconfined arm" | 40 |
| T2 | After Table 12.3 | The retest story: keep 42 of 45 and F54, and shorten the `scheduler` switch explanation to one clause | 70 |
| T3 | Zeroconf defect | Keep the mechanism in two sentences (the helper joins a multicast group; a new namespace has no multicast) and drop the resolver detail | 50 |
| T4 | Capacity paragraph | Drop "An earlier estimate that left out the audit write put the headroom at about 11,000 times; the figure quoted here includes it." | 25 |
| T5 | Push paragraph | Keep 0.50 ms, the 0.5–0.9 ms range, F46 and F62; drop the per-run medians, which App F has | 45 |
| T6 | After Table 12.6 | O3's deletion, and give the severity counts once ("1 Critical, 14 Major … see Appendix F") | 90 |
| T7 | §12.4 opening | Shorten the two-month story of "unmodified" to one sentence | 50 |
| T8 | Mutation paragraph | Keep the lesson and the flood example; drop the second test integration's description | 35 |

After C1–C3 (+~70 words) and all of T1–T8 (−~405), §12 would come to about 4,130 prose words.

## Seen elsewhere, for those sections' read-through

- §6 (`06_logic_model.md`, the outputs paragraph): "the record of 153 claims and 60 findings": Appendix F has 62.
