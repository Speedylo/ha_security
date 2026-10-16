# F61 in the submission — draft for Younes's review (2026-10-16)

Written while the final rerun is still running. Step 3's Pi half has not finished, so the outcome
clause carries a placeholder: [PI RESULT]. Nothing below is in `submission/` yet.

## 1. Appendix F, new row after F60

| F61 | Final rerun | Minor | The two fault-injection scripts, and the end-to-end script's supervisor, were not updated when F57 made an approval mandatory, so every fault case stopped at its first registration. From F57's fix to the final rerun, no fault case ran against the current code | Fixed in the scripts under their own tag; no framework code changed. The fault cases were rerun at that tag: 11 of 11 criteria held on the laptop, [PI RESULT] on the reference device |

## 2. Appendix F, the closing paragraph (changed words in bold)

Of the **61** findings, one is Critical, 14 Major, 5 between Minor and Major, **37** Minor, 3 notes and
1 a request to re-measure. F01–F53 come from the verification campaign, F54–F56 from the functional
retest made after the cut-off, F57–F60 from checking Section 9 against the code and from the fixes
that followed, **and F61 from the final rerun**. One remains open (F18), one is retained as a residual
risk (F11), and one is carried as a stated limitation (F53).

## 3. §8.6, a new closing paragraph after "…so the numbers in Section 12 come from one version of the code."

The final rerun found one further defect, and it lay in the verification itself rather than in the
framework. When F57 made an approval mandatory before any sandbox could start, every script that
starts one was meant to record that approval first, as a household's administrator would. The two
fault-injection scripts were missed, so at the final tag each of their cases stopped at the first
start, refused by the very check F57 had added (finding F61). No fix after F57 reran the faults,
so for six days the most recent fault results were measured on code from before the approval
existed. The scripts were corrected under their own tag, with a prediction note committed first, and only the
fault step was rerun from it; the failed attempt is kept beside the result. The lesson is a
property of regression testing rather than of this project: a regression run checks the files a fix
touches, so a script that depends on a changed rule without being changed itself drops out of view
until everything is run again. That is the case for one full rerun at the end, and here it was the
rerun that found the gap.

## 4. Counts elsewhere that follow from F61

- `00_front_matter.md` line 61: **F01–F60** → **F01–F61**.
- `03_project_specification.md` line 98 (D7): "a log of 60 findings" → "61 findings".
- §8.6 second paragraph: "The repository holds 36 such notes" — F61's prediction note adds one.
  The exact figure comes from step 13 (`verify/prereg.py`) rather than from counting by hand.

## Points for Younes to decide

1. **Severity: Minor.** The framework behaved as specified, and nothing the household relies on
   changed. The gap in the record (six days with no fault case run against the current code) is
   what makes it worth a row. Major instead, if the gap in the record should weigh more.
2. **One finding or two.** `verify/phase2_l23.sh` also `cd`s into the old frozen tree
   (`~/r2exp/verify/v2`) rather than the checkout it belongs to: run as is, it would have tested that
   tree. This is the same defect as F19 in `suites_all.sh`, recurring in a second script. The draft
   folds only the approval gap into F61. The path could be F62, a clause in F61, or a note under F19.
