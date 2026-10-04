# Backlog for the consolidation rewrite

Raised 2026-09-06 during Stage 5 pass 3. **These are not defects** — each is a place where the
report is *correct and hard to read*, and where the fix is structural rather than a correction.
Recorded here rather than patched, because patching them individually would add another layer of
the same kind. Younes's instruction: consolidate sections and simplify the writing in one pass
later.

## 1. The correction stacks are now several layers deep

The "leave it as written and add a dated pointer" convention (§6.4.1's, applied throughout) has
produced passages a reader has to unwind chronologically to extract the current claim. Worst
cases, in order:

| Where | Layers |
|---|---|
| §7.4.1's C1 paragraph | original claim → 2026-09-04 blockquote saying it is false → 2026-09-06 note inside that blockquote saying it is now true |
| §7.28 → §7.29 | a whole section reporting a defect, then a whole section reporting its repair, with §7.5's row carrying a third summary |
| §7.16.3 / §7.22.4 / §7.25.4 | three separate "where §7.5 now stands" snapshots, each superseded by the next |
| §7.21.4 | paragraph, then blockquote, then a second blockquote — item 7 and item 8 resolved on different days |

**The convention is right and should survive**: it is what makes the pre-registration checkable,
and §7.1's claim depends on it. What should change is *where the layers live*. Suggested shape —
each section states its current claim first, and the history moves to a clearly-marked
provenance note at the end of the section, or to a single "what this chapter corrected about
itself" appendix. The dates and the supersession must remain recoverable, because §8.4.2 is an
argument built on them.

## 2. One number, five statements: the adversary suite counts

`selftest_adversary`'s split is stated in §6.9 (21/9/6/1 over 37), §7.4.2 (quoting §6.9),
§7.13.4 (corrected to 20/10 over the same 37, and a 38th attack added without a new total),
§7.21.6 (the correction, tabulated) and §7.22.1 (21/6/10/1 over 38). **Every one is correct at
its date.** A reader tracking "how many attacks were blocked" meets three different answers and
must reconstruct the arithmetic themselves. Pass 3 added the missing reconciliation as a
sentence; the rewrite should give the suite **one canonical statement** with the history beneath it.

## 3. The obligations register lives in three places with one rule applied unevenly

§7.8 holds the eleven inherited obligations, §7.21.3 corrects where seven of them were
discharged, and `STATE.md` carries a third copy. §7.21.3 states a blanket rule — *an obligation
is not discharged by a section that promises to discharge it* — and applies it to seven of the
**ten** rows that point at a §7.4.x methodology section.

The three it does not touch are defensible and the report never says why: **§5.7.4/§6.4.1's
"state S9's boot precondition whenever S9 is evaluated", §6.6.5's "negative cases assert on why"
and §6.4.5's "an absence is not evidence" are *practices adopted as method*, not *measurements
owed a result*.** A practice genuinely is discharged by the methodology section that adopts it.
Pass 3 corrected the miscount; the rewrite should split the register into those two kinds and
state the rule once, which makes all ten rows resolve without an exception list.

## 4. §7.5's verdict column now carries the load three tables were sharing

§7.5 gained a fourth column in pass 1, and §7.16.3, §7.22.4 and §7.25.4 each still narrate a
snapshot of the same table. With the column in place the snapshots are redundant as *status* and
valuable only as *chronology*. Fold them into the provenance note of item 1.

## 5. Chapter 7 is 198 KB and is read as one document only by its own read-through sections

§7.26, §7.28 and §7.29 exist because nobody could hold the chapter in mind at once. That is a
symptom worth naming in the rewrite plan rather than a defect to fix in place. Splitting the
results half by *axis* (compatibility / security / performance) rather than by *date measured*
would let §7.5's four columns become the chapter's spine.

## 6. Added 2026-10-04: §7.36's pointers are another layer of the same kind

§7.36 added dated pointers in about twenty places across Chapters 5 to 8 and the abstract, listed
in `notes/w1_push_loop_prediction.md` §5. The worst stack is now the record-before-act ordering. §5.11.3 states it, §6.8.3 claims it
is implemented, §7.20.1 and §7.32 rely on it, and §7.36.1 shows it held for no operation that acts
from 2026-08-25 to 2026-10-04. In the rewrite it should be stated once, as it now holds, with the
window given in §7.36's provenance note rather than at each place that relied on it. The submission
draft in `submission/` carries none of this and must be rewritten from the report, not patched.

