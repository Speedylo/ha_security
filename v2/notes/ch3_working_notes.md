# Chapter 3 — working notes

**Written:** 2026-08-21. Not part of the report.

## The discipline that shaped the chapter

Every requirement had to fill a row in the §3.8 traceability matrix or be cut. This is worth
keeping, because the requirements I *wanted* to write from experience — resource limits,
rate limiting, restart survival, entity registry parity — could not be traced to anything in
Chapters 1 or 2 and so are not here.

That is not a claim they are unimportant. It means **the first two chapters do not yet
justify them**, and the honest options are to earn them in Chapter 4 (where the threat model
may raise availability as a security property) or to leave them out. Smuggling them in now
would break the chain the whole rebuild exists to establish.

Watch for this specifically: **cgroups / resource exhaustion has no requirement here.** If
Chapter 4's threat model identifies denial of service as in scope, a requirement appears
then, derived from the threat model, and that is the correct order. If it does not, resource
limits are out of scope and the report should say so.

## S1 is the chapter's load-bearing requirement

Corno & Mannella's garbage-collector demonstration eliminates every in-process design in one
step, on published experimental evidence rather than assertion. It forces:

- enforcement outside the integration's process,
- the credential held away from the integration (S2),
- and therefore a boundary that has to be crossed by *something*, which is the whole design
  problem of Chapter 5.

If challenged on why the design is not simply "a wrapper around `hass`", the answer is one
citation and one code listing. Do not paraphrase it — quote their code.

## Requirements that came from prior work's *limitations*

C3, S1, S4 and S5 all derive from what the closest prior work could not do, rather than from
Chapter 1's problem statement. This is the return on reading Corno & Mannella and Tyche
properly instead of distinguishing them at arm's length, and it is worth saying in the viva
if asked what the literature review contributed beyond positioning.

- **C3** (no reliance on author cooperation) ← their own acknowledgement that snippets can be
  altered by whoever controls the source.
- **S4** (per-integration egress attribution) ← their consolidated gateway-level MUD file
  giving every plug-in the union of all declarations.
- **S5** (risk-asymmetric granularity) ← Tyche.

## Deliberate omissions and soft spots

- **F4 is weaker than it looks.** Requiring that the manifest be *presentable* is easy;
  whether users act on disclosures is a large human-factors literature (Felt et al. on
  Android permissions would be the entry point) and is excluded in §3.7. An examiner may
  press on whether a control users ignore is a control at all. Prepared answer: the
  mechanism's value does not depend on the user reading the manifest, because enforcement is
  automatic — visibility is additive, not load-bearing.
- **N1 asserts no performance threshold.** Deliberate: inventing a number now ("under 50 ms")
  and then meeting it is circular. Reporting measured figures against a baseline is honest.
  Risk: an examiner may want a stated acceptability criterion. If pressed, the defensible
  framing is that the criterion is comparative, not absolute.
- **S7's stated limit** (a local log cannot be authoritative against whoever controls the
  machine) is real and should be repeated in Chapter 4 rather than buried here.
- **No requirement covers the update path**, though §1.6 identified it as a coverage gap in
  community review. Confinement applies to whatever version is running, so this may be
  adequately handled — but check in Chapter 4 whether a malicious *update* raises anything
  the current requirements miss.

## Open questions this chapter deliberately did not answer

1. **Who authors the manifest?** C3 says enforcement cannot assume the author is honest, but
   it does not say who writes the declaration. Candidates: the author (visible but
   self-serving), the user (informed but unqualified), derived by static analysis (objective
   but incomplete), or community-curated. This is a Chapter 5 decision and it will be asked
   about early — §1.10's "declared" is doing quiet work here.
2. **How does an unmodified integration run outside the process it expects?** The hardest
   engineering question in the project, deferred to Chapter 5 on purpose so that Chapter 4
   can constrain the answer.
