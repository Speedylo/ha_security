# Where the rebuild stands

**Last updated:** 2026-08-24, end of session · **Read this first when resuming.**

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
| `report/04_threat_model.md` | ✅ **Complete.** 18 threats, 6 residual risks; impact scale rebuilt 2026-08-22 (`notes/decision_impact_scale_and_standards.md`); §4.6 figure drawn and inserted 2026-08-24 |
| `figures/fig_4_1_current_state.py` | ✅ Generates the Threat Dragon model **and** the rendered figure from one source, so they cannot drift. Spec and as-built departures in `notes/ch4_figure_4_1_spec.md` |
| `figures/ecosystem_scale.py` | ✅ Regenerates every number in Ch. 1 |
| `refs/` | ✅ Four PDFs obtained and read (Corno & Mannella ×2, Thingnes & Meland, Mannella thesis) |
| **HA source on the machine** | ✅ `~/ha-src/core`, pinned to **2026.8.3** (`759e465`, 2026-08-21), shallow clone. **Outside the capstone repo on purpose** — never committed, never confused with the frozen spike |
| `notes/ch5_evidence_ha_coupling.md` | ✅ Written 2026-08-24 — the in-process coupling re-derived from source. **Discharges item 1 of `00_METHOD.md` §2** |
| `notes/ch5_evidence_ha_coupling_explained.md` | ✅ The same finding from first principles, for defending it aloud — what `import` really does, why `hass` is everything, a 30-second version, and six self-test questions |

## Next session, in order

*(Steps 1 and 2 of the previous list — get the source, re-derive the coupling — were done
on 2026-08-24. What follows is what remains.)*

**1. Review Figure 4.1** (`figures/fig_4_1_current_state.svg`) — drawn 2026-08-24 and
already inserted into §4.6 with its caption, so Chapter 4 is closed unless the figure is
wrong. Open the `.json` in Threat Dragon if it needs adjusting by hand, but put anything
worth keeping into the generator script.

**2. Chapter 5 is under way** — `report/05_architecture.md`, §5.1–§5.6 drafted. **§5.7 (the
isolation primitive) is next**; the section plan and the questions each section owes are in
`notes/ch5_working_notes.md`.

**Gate G2 has fired once, on the compatibility decision.** The first pass built a proxy shim
(R1); this pass reaches R2 — a real, stripped Home Assistant inside the sandbox, with only
permitted effects forwarded. Two measurements taken in this pass drive it: 91% of the 1,482
shipped integrations import the helper layer while **2** write state directly on `hass`; and
on the Pi 5 a sandbox costs 176 MB, each additional one 136 MB, against a threshold of 809 MB
fixed before the run. Younes confirmed the decision on 2026-08-24 **with an explicit fallback
to R1 if implementation refutes it** — written into §5.6.5 with its trigger conditions and
tied to Gate G3.

**3. Re-derive the API-surface measurement**, when §5.10 needs it. Which of the nine handles
in `notes/ch5_evidence_ha_coupling.md` §4 must be mediated, which can be denied outright, and
which are used so rarely that denial is free, is an empirical question and the manifest's
granularity depends on the answer. The spike measured it across 3,105 repos; under the
evidence rule that result is private knowledge until re-derived in this pass. The §5.6.1
measurement is the template — same method, run over community integrations rather than
shipped ones, which Chapter 7 owes anyway.

---

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
   the answer. **Now specified, not yet answered:** `notes/ch5_evidence_ha_coupling.md` §4
   tabulates the nine handles reachable from the `hass` object, and any design must present
   that surface or modify the integration — which C3's compatibility constraint forbids.
   The coupling is one ordinary `importlib.import_module` call (`loader.py:1091` at HA
   2026.8.3), which is also why authority here is *positional* rather than granted, and
   therefore why relocation without scoping changes nothing — the §1.9 discharge.

**One finding worth using in Ch. 5's opening.** Home Assistant *does* distinguish custom
code from built-in — `Integration.is_built_in` — and every one of its consumers is
presentational: a warning banner, a quality-scale label, log wording, an issue-tracker URL,
a deprecation severity. The flag is never consulted on the load path or at either dispatch
site. The platform knows which code is untrusted and uses that knowledge to phrase a
warning. It pairs exactly with Corno & Mannella's scope-that-lives-only-in-prose.

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
- **Dates and the advisor email are parked** at the user's instruction (2026-08-21), and
  the email is **not blocking** — it will not cancel the project, so it is status if asked
  and never a flag raised unprompted (confirmed 2026-08-22). The stage dates in
  `01_PLAN.md` are stale and should not drive decisions until unparked; Stages 0–1 landed
  roughly three weeks early, so a cheap re-fit is owed whenever the parking lifts.
