# Decision — rebuilding the impact scale, and holding the standards set at two

**Decided:** 2026-08-22 · Not part of the report. · **Affects:** Ch. 4 §4.4, §4.7, §4.9,
§4.10.1, §4.12. · **Applied in:** `report/04_threat_model.md`; the pre-revision chapter is
in git history at `ca44ecd`.

## What triggered it

A challenge to two individual ratings: T15's likelihood (3) and T16's impact (3). Both were
wrong, but checking them exposed something larger than two cells.

**T15.** The anchors give 4 for "documented in this ecosystem, **or requires no attacker
skill**", 3 for "documented in comparable ecosystems", 2 for "technically available, no
documented occurrence". T15's justification note read "Same-user processes readable via
`/proc`" — a statement of *capability*, which is the anchor for **2**. So 3 was the one
value the note supported least. The rating is right at **4**, via the no-skill clause:
reading `/proc/<pid>/environ` for a same-uid process is a one-line file read.

Note that T15 is *not* documented in this ecosystem. The 2021 disclosures were directory
traversal, already banked as T14's justification. Extending them to process-table
disclosure is an inference, not an occurrence, and the evidence rule (`00_METHOD.md` §2)
says not to.

**T16.** The threat reads "rendering the gateway unresponsive" — *total* loss of function.
Level 2 says "partial loss of function", level 3 says "disclosure of occupancy or
behavioural patterns". Neither describes it. T16 had nowhere legitimate to sit.

## The real defect: the scale had no ladder for two-thirds of the harm types

Levels 5, 4 and 3 were all confidentiality or physical-access harms. Availability appeared
exactly once, at level 2. Auditing the assets of §4.4 against the scale:

| Asset | Rung before |
|---|---|
| A1 physical control | 5 ✓ |
| A2 occupancy | 3 ✓ |
| A3 credentials | 4 ✓ |
| A4 camera | 4 ✓ |
| A5 platform availability | **none above 2** |
| A6 other integrations' state (integrity) | **none** — level 2's text is disclosure-flavoured |
| A7 the audit record | **none** — no rung for loss of attribution |
| A8 home network | 4 by stretch — "credentials beyond the home" is not a LAN pivot |

Consequence: **four threats were rated against level text that did not describe them** —
T07, T10, T16, T18. Same root cause as T15 and T16. The numbers were mostly defensible
judgement; the anchors were missing.

## The fix

**Value the assets, then derive the ladder from the valuation.** §4.4 previously listed
A1–A8 with a "why it matters" column but never *ordered* them, while §4.7 independently
asserted an ordering. That is the same judgement made twice, in two places, with nothing
connecting them. The revised §4.4 states the valuation; §4.7's scale follows from it, and
every asset must be reachable on the ladder — which is what makes the completeness check
above repeatable rather than a one-off.

Three columns per level (confidentiality / integrity and control / availability), rated at
the highest level any column matches.

**Rejected: score C, I and A separately per threat, CVSS-style.** It avoids asserting that
"credentials leak" and "gateway frozen overnight" are commensurable — but it destroys the
single ordering that drives treatment priority, and §4.7 already warns that multiplying
ordinals is not arithmetic. Doing that three times across eighteen threats is worse, not
better. One risk owner, one ladder.

**Two conventions now stated that were previously implicit:**

- **Worst credible case.** The existing ratings already worked this way — T14 at impact 4
  presumes credentials are in fact stored — but nowhere said so.
- **Reversibility is the axis that makes harm types comparable.** §4.4 already reasoned this
  way ("irreversible in effect", "irreversible once disclosed") without the scale encoding
  it. It is what justifies placing an outage below an exfiltration despite the outage
  feeling more dramatic: confidentiality harm is permanent, availability harm is usually
  recovered.

Also added, needing no citation: **the risk owner is named.** §4.7's appetite statement was
already written on the homeowner's behalf without ever saying whose appetite it was.

## Rating changes and their consequences

| Threat | Before | After | Why |
|---|---|---|---|
| T15 | I4 × L3 = 12 High | I4 × **L4** = 16 High | No attacker skill required; band unchanged |
| T16 | I3 × L3 = 9 Medium | **I4** × L3 = 12 High | Total loss of an unattended platform; **band changes** |

Anchor-only fixes, no number moved: T07 (note rewritten — recoverable, since the owning
integration's next update overwrites), T10 and T18 (both now have level text that describes
them).

Knock-on effects, all applied in the revised chapter:

- §4.9's evaluation paragraph: four Critical and **twelve** High, two Medium.
- §4.10.1's derivation of **S9 is strengthened** — the requirement the method generated now
  traces to a High risk rather than a Medium one.
- §4.12 records the review as dated, per ISO 31000 §6.6, rather than the cells being
  silently edited.

## The standards decision: stay at two

**ISO 31000 for process, STRIDE for identification. Nothing further.**

The temptation was real — the gap was in impact criteria, and there are standards that
address exactly that. Reasons for holding:

1. **The gap was structural, not bibliographic.** The scale was incomplete because it was
   never checked against the asset list. Importing a generic published scale would not have
   found that, and a scale calibrated to a private dwelling is not something a generic
   standard supplies — no published ladder has a rung for "defeat of a life-safety function
   in a house".
2. **Standards-piling reads as credential-stacking.** Three or four frameworks named in one
   chapter invites the reader to check whether each is *used* or merely *cited*. This
   advisor audits for a living and is exactly the reader who can tell.
3. **The coursework justification would break.** `01_PLAN.md` defends 31000 and STRIDE as
   "both from coursework, so defensible from teaching rather than citation". A standard
   known only by reputation does not qualify, and citing one unread is the thing already
   refused over Tyche's authorship (`ch2_working_notes.md`).

### Considered and not taken

- **ISO/IEC 27005** (information security risk management; the natural companion to 31000,
  and it does give guidance on consequence criteria). Blocked by the paywall plus the
  evidence rule. **Revisit only if institutional library access turns out to exist** — if it
  does, the value is real, because the advisor's register is the 27000 family. Until then,
  a derived scale beats an unread citation.
- **NIST SP 800-30 Rev. 1** — free, publicly downloadable, contains qualitative impact and
  likelihood scales. A genuine fallback if a published exemplar is ever wanted. Not taken:
  less resonant for an ISO-oriented reader, and it would still be an *import* where a scale
  derived from §4.4 is stronger.
- **ISO/IEC 27001** — dropped at Younes' instruction, 2026-08-22. Recorded only because the
  one idea worth keeping from it needed no citation and has been kept: naming the risk
  owner. Its Annex A control set remains a possible *completeness cross-check* for
  Chapter 5's controls, which is a different chapter and a different question.

## Weaknesses to concede if pressed

- **The three-column scale still asserts commensurability.** Placing "credentials beyond the
  home" and "total loss of an unattended platform" both at level 4 is a judgement.
  Reversibility is the stated justification for it, not a proof.
- **T16's impact depends on the installation profile.** A gateway with no life-safety
  automation is a 3; one running the alarm is arguably a 5. It is rated 4 on the modal case,
  with the worst case stated. An assessor may reasonably place it elsewhere.
- **The re-rating was prompted by challenge, not by the process.** Honest framing: §4.12 is
  the clause that exists for this, the review is dated, and a register that never changed
  would be the less believable artefact. But it was found by someone reading the table, not
  by a scheduled review, and saying so is cheaper than being asked.

## Anticipated question

*"You changed two ratings after the fact — how do I know the register is not fitted to the
conclusion?"* The changes are dated, recorded in §4.12, and both moved risk **upward**,
which is the opposite direction from fitting a model to a favourable result. One of them
strengthened a requirement (S9) rather than excusing the absence of one.
