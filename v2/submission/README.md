# Submission draft

**First rough draft, 2026-09-08.** Written against the programme template evidenced by the two
capstone outlines in `.claude/Outlines.txt`, following the mapping in
`notes/rewrite_plan_outline_mapping.md`.

**This is a draft, not a submission.** Read `notes/rewrite_plan_outline_mapping.md` §5 before
editing: the dated corrections and the pre-registered predictions in the working report are
load-bearing, and this draft preserves them in condensed form rather than dropping them.

## Files

| File | § | Source |
|---|---|---|
| `00_front_matter.md` | — | Condensed from `report/00_front_matter.md` |
| `01_introduction.md` | 1 | Ch 1 §1.1–1.3 |
| `02_problem_statement.md` | 2 | Ch 1 §1.4–1.10 |
| `03_project_specification.md` | 3 | Ch 3 + Ch 1 §1.6; verdicts from Ch 7 §7.5 |
| `04_steeple.md` | 4 | **New writing** |
| `05_engineering_standards.md` | 5 | Ch 4 §4.1 + **new** |
| `06_logic_model.md` | 6 | **New writing**, sourced from Ch 7 §7.6 and `01_PLAN.md` |
| `07_literature_review.md` | 7 | Ch 2 entire |
| `08_methodology_and_design.md` | 8 | Ch 4 entire + Ch 7 §7.1 |
| `09_system_architecture.md` | 9 | Ch 5 + Ch 6 |
| `10_feasibility.md` | 10 | **New framing** of existing experiments |
| `11_data_presentation.md` | 11 | Ch 7 §7.1–7.11, §7.12.1, §7.23.1 |
| `12_results.md` | 12 | Ch 7 results + Ch 8 §8.2–8.5 |
| `13_learning_strategies.md` | 13 | **New writing**, sourced from Ch 8 §8.4 and `STATE.md` |
| `14_future_work.md` | 14 | Ch 8 §8.7 + `STATE.md`'s realistic-scenario section |
| `15_conclusion.md` | 15 | Ch 8 §8.2, §8.8, §8.9 |
| `16_references.md` | — | Copied unchanged — 28 sources, 28/28 resolving |
| `17_appendices.md` | A–F | **Stubs.** Content to be lifted verbatim from the working report |

## Known gaps in this draft

1. **Four appendices are stubs.** The tables exist in `report/` and need lifting, not writing.
2. **Nine figures are marked `[TO DRAW]`.** This is the largest remaining block of work and it
   *adds* pages rather than cutting them.
3. **Three citations are flagged `[To verify]`** in §4.5 and §5.2.1 — the Cyber Resilience Act and
   the ISO/IEC 27001 clause identifiers. Both are currently argued from principle.
4. **Every number here traces to the working report**, but this draft has had **no read-through
   pass** of its own. The working report needed three, and each found something.

## Building the Word document

    python3 build_docx.py            # -> capstone_report_draft.docx

Typography is set in one place at the top of `build_docx.py`: body **Times New Roman
12 pt**, headings **14 pt bold**, tables 10 pt, block quotes 11 pt, code in Courier New.
The title-page title is 18 pt — the only size not derived from the two the brief names.

**Generated, not hand-maintained.** Edit the markdown and re-run; a `.docx` edited
directly will be overwritten and its changes lost. On opening in Word, right-click the
contents page and choose *Update Field* to populate it — the heading structure is already
there, so it builds itself.
