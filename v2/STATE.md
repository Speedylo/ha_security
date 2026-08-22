# Where the rebuild stands

**Last updated:** 2026-08-21, end of session · **Read this first when resuming.**

Read alongside `00_METHOD.md` (ground rules — especially the evidence rule) and
`01_PLAN.md` (stage plan and gates). Chapter working notes in `notes/` carry the reasoning
that does not belong in the report, including anticipated viva questions.

---

## Done

| Artifact | State |
|---|---|
| `00_METHOD.md` | Ground rules, evidence rule, the ten things known privately and what each costs to re-derive |
| `01_PLAN.md` | Stage plan, three tracks, four gates |
| `report/01_problem_and_context.md` | ✅ Drafted, reviewed, revised |
| `report/02_literature_and_gap.md` | ✅ Drafted, reviewed, revised; all four key sources read in full |
| `report/03_requirements.md` | ✅ Drafted — 19 requirements + S9 added by Ch. 4 |
| `report/04_threat_model.md` | ✅ Drafted — 18 threats, 6 residual risks. **Outstanding:** the §4.6 boundary figure (`notes/decision_threat_model_diagrams.md`) |
| `figures/ecosystem_scale.py` | ✅ Regenerates every number in Ch. 1 |
| `refs/` | ✅ Four PDFs obtained and read (Corno & Mannella ×2, Thingnes & Meland, Mannella thesis) |

**Next: Chapter 5 — Architecture and design rationale.**

## Decisions taken, and their consequences

**Gate G1 fired (§`01_PLAN.md`).** Close prior art exists — Corno & Mannella threat-modelled
extensible gateways with a Home Assistant use case (SpliTech 2022). Two claims were dropped
as false and must never reappear:

- ~~"Nobody has identified this problem"~~ — they did, in 2022, on this platform.
- ~~"Manifest permissions for extensions are novel"~~ — Barth et al. settled that in 2010.

The contribution claim is now **constructive and empirical**: nobody has *built and
evaluated* confinement for these integrations, and nobody has measured what confining
pre-existing, unmodifiable extensions costs in compatibility. Weaker-sounding, far more
defensible. `notes/ch2_working_notes.md` has the full reasoning.

**Gate G2 (the four re-openable decisions) is still open** and belongs to Chapter 5.

## The three things most worth remembering

1. **Their threat model presupposes a scope it cannot enforce.** Corno & Mannella define a
   plug-in's scope as what "the plug-in documentation has to include", and all eleven of
   their threats are defined as acting *outside its scope*. The manifest is that notion made
   machine-readable and enforced. This is the sharpest available statement of the
   contribution — reuse it in Chapter 5's opening and in the proposal.

2. **The garbage-collector attack settles the architecture.** They demonstrate an integration
   walking `gc.get_objects()` to reach another integration's live object and read/modify its
   secrets. This eliminates every in-process design on published evidence, and forces S1
   (enforcement outside the integration's process) and S2 (credential held away from it).
   Quote their code, do not paraphrase it.

3. **Thingnes & Meland propose this project as future work.** Their systematic review's
   future-directions section calls for "a proof-of-concept implementation for Home Assistant
   … evaluated based on the threat model introduced by Corno and Mannella". Chapter 7 adopts
   that framing, so the security evaluation is measured against a published model rather than
   criteria invented here.

## Chapter 5 starts here

Chapters 3 and 4 constrain the design tightly. Carry these in:

- **S1** → enforcement outside the integration's process. Non-negotiable, published evidence.
- **S2** → the mediator holds the platform credential; the integration holds none.
- **T02** → per-integration *identity* on every mediated request. Do not assume one
  connection equals one integration; make the architecture carry identity explicitly.
- **T11** → resolve-then-pin the destination address. Checking hostnames is not enough.
- **T12** → confirm a new version's declaration is re-checked, not cached from install time.
- **S5 / Tyche** → granularity must separate risk-asymmetric operations; `lock.unlock` must
  not come free with `lock.lock`.
- **S9** → resource limits (added by Ch. 4 §4.10.1).
- **Paired figure** → Ch. 5 draws the same data-flow diagram as Ch. 4 §4.6, with TB1, TB3,
  TB5 and TB6 instantiated. Ch. 4 draws today, Ch. 5 draws the fix, and the delta is the
  argument. See `notes/decision_threat_model_diagrams.md`.
- **S7 identity** → an integration's identity in the audit log is its name *plus a content
  hash of the loaded source*. A design specification discharging S7, justified by T12 and
  A7 — not a new requirement. Decided 2026-08-22; the reasoning, the boundary it must not
  cross, and the trust-layer PoC that was refused are in
  `notes/decision_audit_identity_and_trust_layer.md`, which also carries three open
  questions Ch. 5 has to answer.

**Two questions Chapter 5 must answer and Chapter 3 deliberately left open:**

1. **Who authors the manifest?** C3 forbids assuming the author is honest, but does not say
   who writes the declaration. Candidates: the author (visible but self-serving), the user
   (informed but unqualified), static analysis (objective but incomplete), community
   curation. This will be asked early — §1.10's word "declared" is doing quiet work.
2. **How does an unmodified integration run outside the process it expects?** The hardest
   engineering question in the project, deferred on purpose so that Chapter 4 could constrain
   the answer.

Chapter 5 also owes two promises made earlier: the defence-in-depth framing (likelihood
control + impact control) promised in §1.6, and the §1.9 argument that relocation without
scoping does not constrain authority — which must be *discharged*, not repeated a third time.

## Standing constraints on how this work is done

- **The evidence rule** (`00_METHOD.md` §2). Everything learned in the first pass is private
  knowledge that stops me re-walking known traps; it is **not citable** until re-derived in
  this pass. If a chapter's argument only works because the answer was already known, the
  chapter is wrong.
- **Traceability** (`report/03_requirements.md` §3.1). A requirement that cannot name its
  source in Chapters 1–2 (or, now, Chapter 4) does not belong. This has already removed
  several requirements I wanted to write from experience.
- **Nothing outside `v2/` is edited.** The rest of `~/capstone` is the feasibility spike,
  cited as prior work in Chapter 6, not tidied.
- **Dates and the advisor email are parked** at the user's instruction (2026-08-21). The
  stage dates in `01_PLAN.md` are stale and should not drive decisions until unparked.
