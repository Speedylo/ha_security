# §8 and §11 week-6 read-through — 2026-10-16

Checked against the final rerun, Appendix C and Appendix F. Nothing in the submission changes until Younes
chooses.

## §11: no changes needed

- Table 11.2: kernel 6.12.47 (`+rpt-rpi-2712`, rerun logs), Home Assistant on Python 3.14.7, framework on
  3.13.5, unprivileged throughout.
- Table 11.3: medians 16,294 and 48, 998,478 against 46,979 (≈ 21.3, "twenty-one times"), 18 of 37 and 26 of
  40. The head-weighted median and total were restated in an earlier session (STATE, Table 11.3 row) and
  recompute covers the rest; nothing in the rerun touches them.
- 39 attack attempts, 26 of 37 needing credentials, the five-pass/ten-pass wording: consistent with §12 as
  revised today.

## §8: the numbers hold; two statements need fixing

Checked: 153 / 119 / 27 / 5 / 2; 38 notes; 53 mutants; nine faults (five held, four fixed: F28–F31); "six
days" (F57's fix 2026-10-10 to the rerun 2026-10-16); the 18 threats = 5 Critical + 12 High + 1 Medium (Table
8.3 and Appendix C).

**C4. Eighteen threats in §8.4, nineteen in §12.1, and the body never says why.** Appendix C explains it: T19,
the refusal flood, was created by T18's treatment (a durable record per decision), so it is rated against the
design and not counted among the eighteen. A reader going from §8 to §12 meets 18 and then 19 with no link
between them. Proposed: one sentence at the end of §8.4's first paragraph:

> A nineteenth, T19, arose from the design itself, because writing a durable record for every decision lets a
> flood of refused requests exhaust the mediator; it is rated against the design rather than the platform, and
> Appendix C gives both.

**C5. §8.5 uses "structural" in two senses, and with both together the counts don't add up.** The first
paragraph says "Four are structural, in that no confinement of an integration could remove them". By the
table those are R1, R2, R4 and R5, and R4 is Medium. The closing paragraph says "four High residual risks do,
each structural". The four High risks are R1, R2, R3 and R5, so R3, which the first sense excluded, is now
called structural. Appendix C defines the appetite's "structural" as "no available control addresses it", and
R3 meets that definition, since the platform offers no supported interface. Proposed, for the closing
paragraph's first sentence:

> No Critical residual risk remains, and four High residual risks do, R1, R2, R3 and R5, each stated and none
> with an available control.

The appetite sentence after it then reads correctly as it stands.

**O5. An outside reader.** §8.2 says "Since F57, an administrator…". A finding number stands in for the event.
Proposed: "Since the approval step added after finding F57, an administrator…".

## Trim candidates (deferred with §12's)

- §8.6's F61 paragraph runs to about 260 words. The regression lesson and the three stale-path scripts could
  go in two sentences, with the detail left to Appendix F (≈ 100 words).
