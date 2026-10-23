# AI-use log: corrections to AI output

This log records each time AI output (Claude Code, Anthropic, Claude Opus model) was wrong, overclaimed, or was
rejected or changed by Younes, and how the problem was caught. It is the source for the final report's
AI Use Disclosure appendix, the AI-use log the syllabus requires, and each deliverable's AI Evidence Box.
New entries are added as they happen. Entries marked *rebuilt* were reconstructed later from `STATE.md`,
`notes/` and git history, not logged at the time.

**Skills** refers to the AIAC skills: S1 literacy (failure modes), S2 technical, S3 application (when and how
to use AI and check it), S4 ethics, S5 communication and disclosure.

| # | Date | Deliverable | What the AI produced | What was wrong | Caught by / how | Correction | Skills |
|---|---|---|---|---|---|---|---|
| 1 | 2026-10-15 *rebuilt* | Report §9.3 | "38 integrations declare permissions" | It counted the head corpus's `manifest.json` files, not the integrations that declare permissions | Number-check read-through flagged it (Q1); re-measured on the Pi | 0 of 75; §9.3 corrected (`f53e2ed`) | S1 |
| 2 | 2026-10-16 *rebuilt* | Report §12 | Findings counted to F56; 40 deliberate defects | Stale counts left after later findings (true: 62, later 63; 53 defects) | Week-6 number check of §12 (`notes/s12_readthrough_20261016.md`, C1, C2) | Text and Table 12.6 corrected | S1 |
| 3 | 2026-10-16 *rebuilt* | Verification code | Fault-injection scripts | Never updated when approval became mandatory (F57), so every case stopped at its first start; for six days the latest fault results came from code that predated the approval step | The final full rerun (step 3) | Fixed under `fix-2026-10-f61`, prediction note first; recorded as F61 | S1, S3 |
| 4 | 2026-10-15 *rebuilt* | Literature search | Five records classed B (adjacent) | Four did not bear on the gap | Younes's review of every A/B row (`experiments/lit_search_2026/review_younes.md`) | Only P3CRID kept as B | S1, S3 |
| 5 | 2026-10-15 *rebuilt* | Report §3, §7, App B, contribution 3 | Claims narrowed to fit TAPShield's abstract | A change resting on a source whose full text was never read | Younes's review | Rolled back to the approved text; TAPShield excluded | S1, S4 |
| 6 | 2026-10-15 *rebuilt* | Literature search | Title screen: 590 of 642 excluded by Claude | Not an error found, but a risk: the AI alone excluded on titles | Protocol control: Younes checked a random sample of 20 exclusions (seed 20261015) and agreed with all 20 | None needed; the limit is stated in the protocol | S3 |
| 7 | 2026-10-23 | Planning | "Diary 2 was due Oct 13 and is 10 days late" | Took the syllabus's dates as authoritative; they are often wrong | Younes | Dates now come from Younes; recorded in memory | S1 |
| 8 | 2026-10-23 | Diary 2 | Recommended the Development-based template | Had not checked which box Diary 1 ticked (research-based) | Younes | Research-based template used | S1 |
| 9 | 2026-10-23 | Diary 2 §7 | "credential scan before every push to the public repository" | The repository is private | Claude's own check before showing the draft | "push to GitHub" | S1 |
| 10 | 2026-10-23 | Diary 2 AI Evidence Box | "I reviewed every screening decision" | Overclaim about the human's own verification: Younes reviewed the B rows and 20 random exclusions, not the 590 title exclusions | Younes asked why only 52 of 642 were screened | Rewritten to the actual review scope; §3 now states the title stage (590) | S1, S5 |
| 11 | 2026-10-23 | Planning (S2) | Warned against an agent answering at the defence | Assumed the answers would be presented as Younes's; he meant an openly labelled agent, a practice already used in the School of Business Administration | Younes | Plan kept, on condition that SSE and the supervisor confirm | S4, S5 |

## Open

- P3CRID: `experiments/lit_search_2026/summary.md` says it supports §7's gap sentence, but the submission
  does not cite it. Raised 2026-10-23; Younes to decide.
