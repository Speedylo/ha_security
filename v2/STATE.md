# Where the rebuild stands

**Last updated:** 2026-08-25 · **Read this first when resuming.**

**Where it stands in one line:** Chapters 1–5 drafted — Chapter 5 complete at §5.15 of 15,
Gate G2 closed with two divergences, and four measurements run on the Pi 5 and the corpora
rather than argued — see `experiments/` and `figures/`.

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
| `figures/fig_5_1_confined.py` | ✅ **2026-08-25.** Figure 5.1 — a *copy* of the Ch. 4 script with every surviving element at its Figure 4.1 coordinates, so the two read as one before-and-after. Asserts on each run that the figure still says what §5.14 claims: six boundaries none absent, TB2/TB4 unchanged, the five removed flows still absent, and nothing crossing TB5 or TB6 |
| `figures/ecosystem_scale.py` | ✅ Regenerates every number in Ch. 1 |
| `refs/` | ✅ Four PDFs obtained and read (Corno & Mannella ×2, Thingnes & Meland, Mannella thesis) |
| **HA source on the machine** | ✅ `~/ha-src/core`, pinned to **2026.8.3** (`759e465`, 2026-08-21), shallow clone. **Outside the capstone repo on purpose** — never committed, never confused with the frozen spike |
| `notes/ch5_evidence_ha_coupling.md` | ✅ Written 2026-08-24 — the in-process coupling re-derived from source. **Discharges item 1 of `00_METHOD.md` §2** |
| `notes/ch5_12_audit_explained.md` | ✅ §5.12 from first principles — what a hash is, why the manifest is part of identity, unreachable vs tamper-evident, and six self-test questions |
| `notes/ch5_evidence_ha_coupling_explained.md` | ✅ The same finding from first principles, for defending it aloud — what `import` really does, why `hass` is everything, a 30-second version, and six self-test questions |
| `report/05_architecture.md` | ✅ **Complete.** §5.1–§5.15 drafted and read end to end 2026-08-25 (eight fixes; see `notes/ch5_working_notes.md`). **All four G2 decisions settled** (two confirmed, two diverged), **§3.9's open question 1 closed in §5.9**, and **§1.6's defence-in-depth promise discharged in §5.13** |
| `figures/api_surface.py`, `fetch_hacs_corpus.py` | ✅ **2026-08-24.** The API surface re-derived by `ast` parsing over two corpora — 1,458 shipped and 144 community integrations, zero parse failures. Write-up in `notes/ch5_evidence_api_surface.md`; corpus reproducible from `hacs_corpus_manifest.json` |
| `experiments/r2_footprint/` | ✅ **Pi 5, 2026-08-24.** R2's premise holds and it fits: minimal HA builds without `bootstrap`, an ordinary integration runs against it, 176 MB first sandbox / 136 MB marginal / ~17 in 60% of 4 GB. Feeds §5.6.3 |
| `experiments/mediation_latency/` | ✅ **Pi 5, 2026-08-24.** One mediated request over the channel: **30.0 µs** median, p99 33.9 µs; ~33k req/s. Floor only — excludes manifest check and audit write. Feeds §5.11.4 |
| `experiments/host_isolation_probe/` | ✅ **Pi 5, 2026-08-24; re-run 2026-08-25.** Namespaces (unprivileged), seccomp and cgroup v2 all present. `memory` was absent on the stock install; after the boot change it is present **and the cap is verified to bite, unprivileged**. Feeds §5.7.4 |

## Next session — start here

**Chapters 1–5 are complete.** Chapter 5 was read end to end on 2026-08-25 and its eight fixes
applied. **Chapter 6 is next**, and its first task is already fixed by §5.6.5.

| # | Task | Notes |
|---|---|---|
| **1** | **Ch. 6 — measure whether the sandbox needs the base `homeassistant` component** | **60 MB of the 176 MB.** Dropping it roughly doubles the ~17-sandbox budget and largely dissolves §5.8.1's third qualification |
| 2 | Then the rest of Chapter 6 | The spike is cited as prior feasibility work, then reconciled with the design Ch. 5 produced |

**✅ S9 is now verified on the Pi (2026-08-25).** The blocker is cleared and the result is
stronger than "the controller is present":

- The cause was sharper than §5.7.4 first recorded — `cgroup_disable=memory` is *prepended by
  the Pi 5 firmware* and is **not in `/boot/firmware/cmdline.txt` at all**, so the original
  "remove it" advice could not be followed. `cgroup_enable=memory cgroup_memory=1` was
  **appended** to that file (backup at `cmdline.txt.bak-20260825-124406`) and the Pi rebooted.
- **The cap bites, unprivileged.** 192 MB against a 64 MB cap is OOM-killed; the same
  allocation uncapped succeeds. Both as uid 1000. This is what makes S9 and the
  unprivileged-supervisor finding compatible rather than in tension.
- **A third finding came out of it, owed to Chapter 6.** An unprivileged process cannot create
  a cgroup and then migrate an existing process into it — that needs write access to the
  root-owned common ancestor. **The sandbox must be placed in its cgroup at creation**, not
  confined afterwards. §5.7.4 notes that this is the third mechanism to land on the same rule:
  construction precedes execution, or the property is not available at all.
- `probe.sh` now tests the cap for *effect*, not presence, and prints the applicable boot
  instruction for whichever case the host is in.

**⚠ §5.14's traceability check generated three obligations. They are cheap now and expensive
in November.**

| Owed by | What | Why |
|---|---|---|
| **Ch. 6** | A surface where the user encounters the declaration | T13's control has two halves; "enforcement bounded to the declaration" is placed thoroughly and **"declaration made visible" is placed nowhere in Ch. 5**. Bounded by §3.7 — a surface is owed, not evidence anyone reads it |
| **Ch. 7** | Never repeat §4.10's phrase "filesystem isolation *to declared resources*" | §5.10.2 removed the filesystem clause entirely. The design is stricter than the control, but the phrase now misdescribes the artifact |
| **Ch. 7** | State S9's boot-time precondition when evaluating it | The Pi's `memory` cgroup controller is disabled by Pi OS (§5.7.4). Testing on a machine where that was quietly fixed, without saying so, is the dishonest version |

**Then Chapter 6 (implementation).** Its first task is fixed by §5.6.5: measure whether the
sandbox needs the platform's base `homeassistant` component. That is **60 MB of the 176 MB**,
and dropping it roughly doubles the ~17-sandbox budget.

**⚠ One conflict is open and deliberately unresolved.** `01_PLAN.md` §6 says the actuator PoC
is cut first if G3 fires. §5.8.2 derived scope from Chapter 3's verification column and found
that cutting the actuator leaves **S5 unverifiable** and T05 — the register's joint-highest
risk — with no demonstrated control. The plan's cut list predates the scope derivation.
Recommendation in `notes/ch5_working_notes.md`: cut coverage-widening first instead. **This is
Younes's call at G3**, and `01_PLAN.md` has deliberately not been edited.

**Owed before Chapter 7 reports coverage:** the API-surface measurement was run on the top 144
community integrations *by install count*. That describes what most installations run, not
what most integrations do. A uniform sample answers the second question and
`figures/fetch_hacs_corpus.py` already takes the corpus — only the selection changes.

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

## Chapter 5 — what it settled

**Settled.** Every constraint Chapters 3 and 4 handed to Chapter 5 now has a home:

| Carried in | Answered in | How |
|---|---|---|
| **S1** — enforcement outside the integration's context | §5.3 | L3: a mediator in a separate process. L1/L2/L4 eliminated |
| **S2** — mediator holds the credential | §5.11.3 | The mediator acts only with its own credential, at step 5 of 5 |
| **T02** — per-integration identity on every request | §5.11.2 | **Identity is the socket**, not a field. The supervisor creates the pair before the sandbox exists |
| **T11** — resolve-then-pin | §5.10.5, §5.11.1 | The mediator resolves; the same principle is applied to filesystem paths |
| **T12** — re-check declaration per version | §5.9.6, §5.12.2 | The manifest binds to a content hash; identity is recomputed per sandbox construction |
| **S5 / Tyche** — risk-asymmetric granularity | §5.10.4 | **No wildcard in `services.call`.** Patterns allowed for entities, never for services |
| **S9** — resource limits | §5.10.6, §5.7.4 | cgroup v2; and the framework refuses to start when the memory controller is missing |
| **S7 identity** — name + content hash | §5.12.1 | Extended to a **three-part tuple** — source, manifest, dependencies — hashed separately *and* together |
| **§1.9** — relocation without scoping | §5.2 | **Discharged.** Authority is *positional*, so moving code moves authority unless the new position confers less |
| **§3.9 Q1** — who authors the manifest | §5.9 | Plural provenance, ordered, default-deny. The file's location is the provenance signal |
| **§3.9 Q2** — how unmodified code runs elsewhere | §5.6 | R2: a real stripped platform in the sandbox. **G2 divergence** |
| **§5.1 item 5** — traceability in the other direction | §5.14 | **Discharged.** All 18 Ch. 4 controls placed; **four rows differ from what §4.10 assumed**, and the check was run control-to-threat as well |
| **§5.3's promise on L2** | §5.15.2 | **Discharged**, and conceded: L2 is the better design on every axis but deployability. C2 is the axis this project is answerable for |
| **§1.6** — defence in depth | §5.13 | **Discharged.** Six layers named, honestly counted as **three** independent ones plus a detective record; every layer this work adds is on the impact side |

**Still owed by Chapter 5.**

Nothing. Every constraint Chapters 1–4 handed to Chapter 5 has a home, and §5.15.6 records
where the chapter leaves the work: the design's central claim is empirical, and Chapter 6 is
where it stops being an argument.

**Two framings to reuse, both stronger than when they were first written:**

1. **The declaration always already exists and is never load-bearing** — now three findings
   (see below), not one borrowed line.
2. **Most of the manifest is enforced structurally, not by checking.** An integration cannot
   ask to read `secrets.yaml` and be refused; the file is not in its mount namespace, so
   there is nothing to ask. §5.6.2, §5.10.2 and §5.11.1 are the same idea in three places, and
   it is what makes both the performance and the default-deny arguments work.

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
