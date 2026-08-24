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
| `report/05_architecture.md` | 🔶 §5.1–§5.11 drafted; §5.12 next. **All four G2 decisions settled** (two confirmed, two diverged) and **§3.9's open question 1 — who authors the manifest — closed in §5.9** |
| `figures/api_surface.py`, `fetch_hacs_corpus.py` | ✅ **2026-08-24.** The API surface re-derived by `ast` parsing over two corpora — 1,458 shipped and 144 community integrations, zero parse failures. Write-up in `notes/ch5_evidence_api_surface.md`; corpus reproducible from `hacs_corpus_manifest.json` |
| `experiments/r2_footprint/` | ✅ **Pi 5, 2026-08-24.** R2's premise holds and it fits: minimal HA builds without `bootstrap`, an ordinary integration runs against it, 176 MB first sandbox / 136 MB marginal / ~17 in 60% of 4 GB. Feeds §5.6.3 |
| `experiments/mediation_latency/` | ✅ **Pi 5, 2026-08-24.** One mediated request over the channel: **30.0 µs** median, p99 33.9 µs; ~33k req/s. Floor only — excludes manifest check and audit write. Feeds §5.11.4 |
| `experiments/host_isolation_probe/` | ✅ **Pi 5, 2026-08-24.** Namespaces (unprivileged), seccomp and cgroup v2 all present; **`memory` controller absent** — Pi OS ships `cgroup_disable=memory`, so S9 needs a boot change. Feeds §5.7.4 |

## Next session, in order

*(Steps 1 and 2 of the previous list — get the source, re-derive the coupling — were done
on 2026-08-24. What follows is what remains.)*

**1. Review Figure 4.1** (`figures/fig_4_1_current_state.svg`) — drawn 2026-08-24 and
already inserted into §4.6 with its caption, so Chapter 4 is closed unless the figure is
wrong. Open the `.json` in Threat Dragon if it needs adjusting by hand, but put anything
worth keeping into the generator script.

**2. Chapter 5 is under way** — `report/05_architecture.md`, §5.1–§5.11 drafted. **§5.12 (identity and
the audit record) is next**; the plan is in
`notes/ch5_working_notes.md`.

**Gate G2 fired twice** — see the table below for all four outcomes. The compatibility
divergence (§5.6) was approved by Younes on 2026-08-24 **with an explicit fallback to R1 if
implementation refutes it**, written into §5.6.5 with trigger conditions and tied to G3.

**⚠ One conflict is open and deliberately unresolved.** `01_PLAN.md` §6 says the actuator PoC
is cut first if G3 fires. §5.8.2 derived scope from Chapter 3's verification column and found
that cutting the actuator leaves **S5 unverifiable** and T05 — the register's joint-highest
risk — with no demonstrated control. The plan's cut list predates the scope derivation.
Recommendation in `notes/ch5_working_notes.md`: cut coverage-widening first instead. **This is
Younes's call at G3**, and `01_PLAN.md` has deliberately not been edited.

**3. ~~Re-derive the API-surface measurement~~ — done 2026-08-24.**
`notes/ch5_evidence_api_surface.md`; scripts and results in `figures/`. Two corpora parsed
with `ast` under Python 3.14, zero parse failures: 1,458 shipped integrations and the top 144
community ones by install count. **The headline is that the population changes the answer** —
community integrations use every handle 1.5–4.7× more than shipped ones, so core-only results
do not transfer. §7 of that note lists the six things §5.10 takes from it.

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

**Gate G2 is closed: all four re-openable decisions are settled, two confirmed and two
diverged**, all in Chapter 5. A rebuild that could only ever have confirmed would have been
theatre (`00_METHOD.md` §3); two divergences out of four is the evidence it was not.

| # | Decision | Outcome | Where |
|---|---|---|---|
| 1 | Platform | Home Assistant — **confirmed, but weakly**: a chain that begins there tends to end there, and the section says so | §5.4 |
| 2 | Compatibility strategy | **DIVERGED** — R2 (real stripped HA in the sandbox), not the first pass's proxy shim | §5.6 |
| 3 | Isolation primitive | namespaces + seccomp + cgroup v2 — **confirmed, and strongly**: reached via S4, S9 and a measured budget the first pass did not have | §5.7 |
| 4 | Implemented scope | **DIVERGED** — sensors + mediated egress across two integrations + one `lock` service path, not the first pass's polling sensors only | §5.8 |

## The three things most worth remembering

1. **The declaration always already exists, and is never load-bearing.** Three independent
   findings, one shape — and this is the sharpest statement of the contribution available.
   Reuse it in Chapter 5's opening, Chapter 8 and the proposal.

   | Where | Information that exists | What it is spent on |
   |---|---|---|
   | §2.4.1 Corno & Mannella | a plug-in's "scope" | prose in the documentation |
   | `ch5_evidence_ha_coupling.md` §5 | `is_built_in` — which code is third-party | the wording of a log line |
   | §5.9.1 | `iot_class` — whether it reaches the cloud, declared by **83%** | a HomeKit discovery heuristic |

   **The contribution is not inventing the declaration; it is making one load-bearing.** The
   83% also kills the feasibility objection before it is raised: authors are not being asked
   for a new behaviour, but for a more precise version of one most already perform unprompted.

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
