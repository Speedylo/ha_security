# Chapter 1 — working notes

**Written:** 2026-08-21. Not part of the report.

## Claims I deliberately did not make

**"Malicious integrations exist in the wild."** I have no evidence for this and did not
assert it. The 2021 disclosures are *vulnerabilities in honest integrations*, not
backdoors. §1.5 states this distinction explicitly rather than blurring it, because an
auditor will look for exactly that blur and finding it would discredit the whole chapter.

The argument is built so it does not need the malicious case: the mechanism of harm is
identical whether code turns hostile by intent or by exploitation, and only the *route*
differs. This is the chapter's most load-bearing move and the most likely thing to be
challenged. **Anticipated question:** "Isn't this a solution to a problem nobody has?"
**Answer:** the 2021 disclosure is a realised instance of the harm, the authority model is
demonstrable today, and a control that addresses both actors is not weakened by the
scarcity of one of them. Chapter 4 must carry both actors through the threat model
explicitly.

**"Nobody looks at the code."** Explicitly *not* claimed — §1.6 exists to prevent that
reading. Added 2026-08-21 after the first draft overstated §1.4's "no formal gate" into an
implied absence of any review at all. Integration source is public and the user base is
technical, so informal peer review is a genuine control and blatant malice would likely be
caught, especially in popular integrations.

The correction improves the argument rather than weakening it, and it is worth understanding
why: conceding the control forces the chapter to say precisely what it does *not* cover, and
that is where the project's actual justification lives. The framing that resulted —
**community review acts on likelihood, confinement acts on impact, neither substitutes for
the other** — is stronger than the original claim and is stated in risk-treatment vocabulary
this advisor uses professionally.

Three bounds are given, all evidenced rather than asserted: coverage collapses across the
long tail (median 20 installs, from Table 1.1); review is point-in-time while HACS updates
are continuous; and it is permeable to the non-obvious, evidenced *within this ecosystem* by
2021 — eight integrations, same flaw class, all public, found by a researcher rather than by
the community — and in general by XZ Utils.

**Do not inflate this into a claim that community review is ineffective.** It is the
mechanism doing most of the work today. The chapter's position is that it is a real control
with a measurable coverage envelope, and that the residual is what this project addresses.

**"HACS is negligent."** Not claimed, and I would resist it. §1.4 says the opposite —
reviewing 4,220 repositories is not something a volunteer project can undertake. The claim
is about what the *user reasonably infers* from a default store, not about HACS's conduct.
Keeping this generous is also tactically right: an argument that needs a villain is weaker
than one that follows from structure.

**A HACS "use at your own risk" disclaimer.** I searched for one and did not find it in
HACS's own documentation, so I cited the *platform's* disclaimer [3] instead, which is
explicit. Do not attribute the disclaimer to HACS without a source.

**CVE-2023-27482 as an integration attack.** It is not one — it is first-party code. Used
only to establish what code execution inside HA is worth, and labelled as such in §1.5.

## Numbers and their weaknesses

- All ecosystem figures come from `figures/ecosystem_scale.py` against HA's opt-in
  telemetry. Regenerate with `--refresh` before submission and re-date the chapter.
- **56.6% HACS penetration** is the headline. Opt-in bias plausibly inflates it, and the
  chapter says so. It is used only to support "widespread", which survives the bias.
- Median 20 installs / 3,095 under 100 installs: supports the "no external review" claim
  much more directly than the headline figure does, and is less bias-sensitive. If the
  56.6% figure is ever challenged successfully, the argument still stands on this one.
- The dashboard's 669,743 active-installation figure is rendered client-side and was
  transcribed by hand, not parsed. It is pinned in the script as a constant with its date.
  **Re-check before submission.**

## Rejected framings

- **Leading with the 2021 CVE.** Rejected: it makes the chapter a story about one bug that
  was fixed five years ago, inviting "so it's patched". Leading with the *architecture*
  and using 2021 as corroboration makes the problem structural and current.
- **Framing it as "HA is insecure".** Rejected: false, and antagonises a reader who knows
  the platform. The chapter's position is that HA's choices are reasonable for first-party
  code and that the gap appears only where the same mechanism carries third-party code.
- **Using the spike's own measurements** (API surface, probe results). Excluded by the
  evidence rule in `00_METHOD.md` — none of it has been earned in this pass yet. Chapter 1
  needs none of it, which is a good sign for the chapter.

## Open items for later chapters

- Ch. 2 must establish whether a manifest/capability mechanism exists for *this* platform,
  and must engage seriously with the Remote Integration Execution RFC [8] rather than
  dismissing it.
- Ch. 4 must carry both actors (malicious author; compromised honest author) explicitly.
- Ch. 4 owes a promise made in §1.6: **community review must appear in the threat model as
  an existing control**, with its coverage envelope, not be silently omitted because it is
  informal. Omitting it would make the residual-risk table overstate what the framework
  contributes.
- Ch. 5 owes the defence-in-depth framing (likelihood control + impact control) also
  promised in §1.6.
- Ch. 2 should engage with the "many eyes" claim as prior art rather than treating informal
  review as un-scholarly. There is a real literature on its limits, and XZ Utils [9] is the
  canonical modern counter-example.
- The §1.8 argument — that relocation without scoping does not constrain authority — is
  asserted here and *promised* to Chapter 5. It must actually be discharged there.
- §1.7's three-way framing (platform disclaims / channel does not inspect / user cannot
  act) is the spine of the whole report. If Chapter 2 finds a mechanism that closes any one
  of the three, the contribution claim changes. This is gate G1 in `01_PLAN.md`.
