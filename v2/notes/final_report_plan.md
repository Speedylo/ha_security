# Final report — plan (2026-11-04, due 2026-12-03)

## Decisions (Younes, 2026-11-04)

- **Structure:** the 16-section outline of `submission/` (past AUI finals: STEEPLE, standards, logic
  model, feasibility, learning strategies) **plus a new §13, AI use and evaluation**, grown from the interim's §6.
- **Format:** the interim's (Times New Roman, the template's styles, its front matter: conduct block,
  student statement, supervisor approval, acknowledgements, abstract + French résumé). **APA 7.**
- **Length:** body about **18,500 words**; appendices above the first 6,000 (lifted 2026-11-06).
- **The bridge extension (B1–B5, B4b) appears here only**; the interim stays at its 2026-10-27 build
  (12 of 37), so the final shows it as the work after the interim.

## Required by the syllabus

- One-page **AI Evidence Box** (tool, task, representative prompts, output, how checked, accepted /
  modified / rejected, ethical and reliability considerations).
- **AI Use Disclosure** appendix (tool and model, prompts, how output was used and modified).
- The **full AI-use log** (`notes/ai_use_log.md`, 40 rows on 2026-11-06).
- A description of the problem, approach, results and implications; supervisor's signature; one PDF,
  title in Title Case; similarity under 20%.

## Outline and word budget

| § | Section | Now | Budget | Main change |
|---|---|---|---|---|
| — | Abstract, Résumé, AI Evidence Box | 722 | 500 + 1 page | Current figures (the abstract's suite count: 35) |
| 1 | Introduction | 807 | 500 | |
| 2 | Problem statement | 1,061 | 600 | |
| 3 | Project specification | 1,988 | 1,000 | Verdicts at the frozen code |
| 4 | STEEPLE | 1,064 | 600 | |
| 5 | Engineering standards | 654 | 500 | |
| 6 | Logic model | 1,172 | 600 | |
| 7 | Literature review | 1,789 | 1,300 | From interim §4; |
| 8 | Methodology and design | 3,419 | 2,000 | Ethics from interim §5.5 |
| 9 | Architecture | 6,085 | 3,000 | The bridge: 29 kinds, confinement per kind |
| 10 | Feasibility | 991 | 500 | |
| 11 | Data presentation | 1,690 | 800 | |
| 12 | Results | 5,741 | 3,500 | Second rerun (`final2_20261101`); 36/37 by platform, 3 lose live video; fifteen vs real (A) 36/36; findings F01–F71 as a list; "26 of 37" credential count corrected; Table 7.5 keeps its figures |
| 13 | AI use and evaluation | interim 1,611 | 1,500 | New; first person |
| 14 | Learning strategies | 917 | 600 | |
| 15 | Future work | 1,213 | 600 | Live video, F18, solcast, the eight camera integrations run themselves |
| 16 | Conclusion | 631 | 400 | |
| App | Code/repository; AI Use Disclosure; full AI-use log; supporting tables | 15,988 | above 6,000, set at rewrite | |

## Method for every section (Younes, 2026-11-06)

Applies to all sections, **including those already approved** (§13, and the October drafts); the word budgets above are ceilings, not targets.

1. Read the matching section in at least two past reports (`~/capstone/.claude/*.pdf`).
2. Compare length, level of detail, what is mentioned and omitted, and readability; give Younes the gaps and the proposed shape.
3. Rework: one thread per subsection; figures and a worked example from real output; no finding codes or process accounting in the body; limits gathered in one place.
4. Move detail to an appendix, and keep the old text in `submission/before_final/`.
5. Check every number against its result file and every sentence for overclaiming before showing it.

§12 is the worked model. §13 has no past equivalent: compare it with the interim's §6 and the syllabus.

## Order of work

1. §13 and the AI appendices (Disclosure, log).
2. §12 Results, §9 Architecture, §8 Methodology (most new material).
3. The rest, front to back; abstract and résumé, then the AI Evidence Box as the last thing written (Younes, 2026-11-06).
4. References in APA 7 as each section is written; build in the template; Word render.
5. Number check (consistency + recompute), similarity check, supervisor's signature; `REPRODUCE.md` 29 → 35 suites.
   - Before it runs: `verify/recompute.py` and `verify/consistency.py` read `v2/report/` (the old working report), not `submission/`. Point them at `submission/` (`RECOMPUTE_REPORT` sets the folder) and move each lookup to the final file names (e.g. `07_evaluation.md` → `12_results.md`); settle `recompute.py`'s 34 suites against the summary's 35 at the same time.
   - `report/` and `proposal/` are untracked since `95bc730` (2026-11-08), so the check runs only on the laptop, where they and `submission/` are on disk; `REPRODUCE.md` says so.

Each section: academic-research-writer skill loaded, rewritten from the current `submission/` text,
every number checked against its result file, Younes reviews before the next one.

## Progress

- 2026-11-04: §13 drafted (`submission/13_ai_use_and_evaluation.md`; second rerun = Younes's idea; mutation wording confirmed (a)); AI Use Disclosure drafted (`submission/appendix_ai_use_disclosure.md`; "no other AI tool" confirmed by Younes); AI-use log appendix built (`submission/appendix_ai_use_log.md`: interim rows 1–30 + 31–39 in plain words). §13 APPROVED by Younes (2026-11-04); the Disclosure and log appendix await his read. Still owed: the one-page AI Evidence Box.
- 2026-11-06: AI Use Disclosure and AI-use log appendix APPROVED by Younes. Next: §12 (the Evidence Box is written last).
- 2026-11-06: §13.5 reworded and log row 40 added (Evidence Boxes in git history only); Younes approved. §12 started.
- 2026-11-06: §12 drafted, then reworked against the past reports (Younes): about 1,900 words, 4 tables, 2 figures (`figures/fig_12_1_states`, `fig_12_2_capacity`), one worked example, limits gathered in §12.5, no finding codes in the body. Detail moved to `submission/appendix_results_detail.md` (Appendix [R], about 3,100 words, not yet tidied: its old linking sentences remain). Earlier versions in `submission/before_final/`. APPROVED by Younes (2026-11-06). F64–F71 still to be added to App F, with ratings.
- 2026-11-08: §9 compared with r2 (Blokbustr §9, ~930 words, 1 figure, components + one data-flow walkthrough) and r1 (LucidLink 8.1.3, ~4,200, 12 figures, per-module flows); r4/r6 keep design inside Methodology. Younes chose ~2,500 words, three limits in a closing paragraph (§9.9), a light command as the worked example (§9.8). §9 rewritten: about 2,600 words with tables, 5 figures kept, 3 tables (decisions; clauses; the 29 bridge kinds by what the mediator checks), APA citations, no finding codes. Detail moved to `submission/appendix_architecture_detail.md` (Appendix [S], about 5,200 words: decisions, sandbox, manifest, mediator, services per kind from `COMMANDS`, egress, record, failure, the eleven limits with codes). Old text `before_final/09_system_architecture_20261108.md`. Final APA list started: `submission/references_apa.md` (Home Assistant n.d. letters re-lettered; §12's analytics citation now n.d.-c). AI-use log row 41. APPROVED by Younes (2026-11-08).
- 2026-11-08: §8 compared with r2 (~350), r1 (~1,000), r5 (~2,500), r6 (~3,400): past methodology = what was done and with what; none has a threat model. Younes: threat model stays (~1,300); Figure 8.2 → Appendix C as Figure C.1; new 8.5 at method level; no overlap with §13. §8 rewritten: about 2,170 words, Figure 8.1 + 2 tables; verification (old 8.6) dropped as [R].6 and §12.4 cover it with current numbers; ethics from interim §5.5 (seven live services now, five public, two accounts); bridge example and the independence reason left to §13. Figures 8.1/C.1 relabelled (community; flows (a)–(o); no codes or jargon), `1f9a4fd`. Appendix C: Figure C.1, residual Table C.5 + R3 note moved in, old C.5 → C.6 (lit review updated); front matter M01–M50 now points to §12.4. Appendix C still has IEEE citations: convert at the appendix rewrite. Old text `before_final/08_methodology_and_design_20261108.md`. After his read: Popper dropped from 8.1 (kept in §11), the third rule narrowed to the prediction records (the reports are rewritten, not corrected by dated note); Table 8.2 shows impact, likelihood and risk, with the scales and bands in the text; "engineering cut-off" and its date removed from 8.5. AI-use log row 42. APPROVED by Younes (2026-11-08).

## To see in practice before submission (Younes, 2026-11-08)

The report describes these, and Younes has not seen them himself; run them on the Pi with him before the final build, and adjust the text to what the screen actually shows:

- The approval in (A)'s Repairs panel: the plain-language account of a grant (§9.3), including what the integration cannot do and the not-declared-by-author mark.
- The *Allow and start* action (§9.3, §9.7): an approval recorded, and refused when the code or grant changed after the screen was opened.

## Decided 2026-11-06 (Younes)

- **Table 7.5 keeps the development figures.** The rerun's are all 3–5% higher, inside the rule set before it (restate only past 5%); the report says so.
- **The appendix budget of about 6,000 words is lifted.** The required Disclosure and log take 3,900 of it; the figure is set when the appendices are rewritten.
- **The interim gets no separate AI Evidence Box:** its §6 and Appendix B serve as the evidence of AI use. The final report keeps its one-page box.
