# Where the rebuild stands

**Last updated:** 2026-09-02 · **Read this first when resuming.**

**Where it stands in one line:** **Chapters 1–5 complete, Chapter 6 drafted §6.1–§6.14, Chapter 7
opened with its methodology pre-registered and its first result in.** The framework exists and
runs on the Pi 5; ten measurements were run rather than argued. **The baseline arm has landed and
it is the strongest result the project has: the confined and unconfined arms fail on the same six
integrations, for the same reasons — the import-level compatibility cost of confinement is zero
of 37.** 84% was never a fact about confinement; it is the fraction of the corpus that loads on
2026.8.3 at all. Chapter 6 corrected Chapter 5 four times and itself twice; Chapter 7 has now
corrected two of its own pre-registered predictions. **Still unbuilt**: scope item 2 (mediated
egress, F2/S4) — see "Next session".

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
| `experiments/unstrip/` | ✅ **Pi 5, 2026-08-25.** Un-stripping toward `http`: **46% → 70%** import-level compatibility for **+75.9 MB PSS** per sandbox (budget 44 → 18 on that harness, ~26 → ~14 translated). Two findings — `http` needs an auth manager (**0.1 MB**, takes the cascade 0/11 → 10/11) and a fresh netns's loopback is DOWN. Feeds §6.12 |
| `experiments/compat/` | ✅ **Pi 5, 2026-08-25, three profiles.** 37 community integrations by install count, each in its own sandbox, source untouched. **46% import clean with all entity platforms** against the minimal instance; 57% once their declared components are supplied. §5.6.5's second G3 trigger **fires, qualified** — and `http` alone blocks 10 of the 16 component failures. Third run added the per-integration `declared` profile: **57% at +9.0 MB**, and the blanket profile's lead over it is *entirely* package spillover from `stream`. Feeds §6.11.3 and §6.13 |
| `experiments/base_component/` | ✅ **Pi 5, 2026-08-25.** The measurement §5.6.5 deferred to Chapter 6. The base component **can** be dropped — 46.6 MB per sandbox, budget 17 → **26** (1.53×, **not** the 2× §5.6.5 predicted). Two controls: both arm orders, and a 0.1 MB replication of §5.6.3's marginal figure. It also found a defect in §5.6.3's own recipe — see below. Feeds §6.3 |
| `experiments/cgroup_placement/` | ✅ **Pi 5, 2026-08-25.** Four placement mechanisms × two positions, unprivileged. **Corrects §5.7.4:** `clone3(CLONE_INTO_CGROUP)` fails with the same `EACCES` as migration, so what binds is *where the supervisor runs*, not when it places the sandbox. Feeds §6.4.1 |
| **`framework/confine/`** | ✅ **The artifact, as far as it goes, 2026-08-25.** `cgroup.py`, `namespaces.py`, `preflight.py`, `sandbox.py`, `enter.py`, `spawn.py`, `selftest.py` — standard library plus `ctypes`, no dependencies, no override flag. **Preflight: 8/8 on the Pi. Self-test: passes** — uid 0 inside mapped to 1000 outside, one visible process, `lo` only, `secrets.yaml`/`.storage`/the other integration all **absent**. Plus `seccomp.py` — 29 calls denied, verified by behaviour on both architectures. **All three of §5.7.3's primitives are built and measured.** Plus `channel.py`, `mediator.py` and `selftest_channel.py` — **identity is the socket, demonstrated with two sandboxes both claiming to be the same integration**. Plus `manifest.py` and `selftest_policy.py` — validation, S5's asymmetry, resolve-then-pin, clause pointers. Plus `describe.py` (the F4 surface, discharging T13's unplaced half) and `audit.py` (three-part identity, hash chain **and** keyed MAC chain, failing independently). **Eight self-tests, all passing on the Pi** — including `selftest_adversary.py`: 37 attempts, 21 blocked, 9 **empty** (succeeded and found nothing), 6 denied, 1 permitted, neither canary reached. Described by §6.4.2, §6.4.4–§6.4.6 and §6.5–§6.8 |
| `report/07_evaluation.md` | 🔵 **§7.1–§7.11 written 2026-09-02 *before* any result, and dated so; §7.12 is the first result.** Criteria for **all 20 requirements** fixed in advance (§7.5), five predictions recorded (§7.6), falsifiers stated (§7.7), inherited obligations consolidated (§7.8), validity threats named (§7.9). **Two rows are ⛔ blocked — F2 and S4 — because egress does not exist**, named in the criteria table rather than buried in a limitations section. §7.12 scores P1 and P2 as **wrong** rather than revising them |
| `experiments/compat/results/compat_baseline.json` | ✅ **Pi 5, 2026-09-02. The baseline arm.** 37 against a full, unconfined HA — same release, host, interpreter, corpus, and the *same* `inspect()` function, shared not copied. **31/37 — 84%, identical to confined, same six failures, same reasons.** `failures(design) = 0`. Baseline loads a median of **52** components; the sandbox sets up **2** |
| `framework/confine/baseline_runtime.py` | ✅ The unconfined arm. `--profile baseline` in `compat.py`. Bias deliberately resolved toward the baseline throughout |
| `report/06_implementation.md` | 🔵 **§6.1–§6.14 drafted 2026-08-25; one scope item still unbuilt.** The bridge is built, the corpus has been run four ways, and **Gate G3 has its recommendation**: `declared` + core package set, **31/37 — 84% — at +19.1 MB**, strictly dominating every other profile measured. What is *not* built is §5.8.2's scope item 2 — mediated egress, F2 and S4 — recorded in §6.11.1 as "◐ Half. Egress does not exist." Section plan, the §6.13–§6.14 reasoning and the viva answers in `notes/ch6_working_notes.md` |
| `experiments/host_isolation_probe/` | ✅ **Pi 5, 2026-08-24; re-run 2026-08-25.** Namespaces (unprivileged), seccomp and cgroup v2 all present. `memory` was absent on the stock install; after the boot change it is present **and the cap is verified to bite, unprivileged**. Feeds §5.7.4 |

## Next session — start here

**The one-line score.** §5.15.6 said the design's central claim is empirical and Chapter 6 is
where it stops being an argument. The security half is **measured**. The compatibility half is now
**demonstrated but not evidenced** — an unmodified integration runs, publishes and is confined,
and the population it was drawn from is one. §6.11.1 scores it as half rather than reporting a
percentage that would hide which half is missing.

**§5.8.5's cut-order conflict is moot (§6.11.4).** The actuator path is built and measured, so
there is nothing left to cut that would save time. G3 is now a question about coverage alone.

**Read this paragraph first if nothing else.** Chapters 1–5 are complete; Chapter 6 is drafted
§6.1–§6.14 and its artifact runs; Gate G3 has an answer that is not close. **Two things are
open, and only one of them is a decision.**

- ~~**Not a decision — just do it.** The baseline arm.~~ ✅ **Done 2026-09-02, and the answer is
  zero.** The design costs nothing in import-level compatibility on this corpus. What replaces it
  as the cheap-and-load-bearing item is S8's paired baseline.
- **A decision, and it is Younes's.** §5.8.2's scope item 2 — mediated egress, F2 and S4 — has no
  implementation, and T11's control is therefore undemonstrated. Build it and Chapter 6's derived
  scope is complete; defer it and Chapter 7 evaluates a design with a quarter of its declared
  scope unbuilt. **Recommendation: build it**, because a requirements table that does not match
  the artifact is exactly what an auditor-by-profession reads for, and there is roughly six weeks
  of slack against `01_PLAN.md`. **The argument against** is the standing instruction to prefer
  code that can be personally owned and defended over code volume — if the proxy would arrive
  undefendable, deferring it and saying so plainly is the better thesis. The prior spike has an
  egress broker (`RESULTS_2026-08-14_egress_broker.md`) to cite as feasibility; under
  `00_METHOD.md` §5 it is **not** retyped.

**⚠ This repository has no remote.** `git remote -v` is empty; everything lives on this machine
and the Pi. Six chapters and 5,118 lines of framework exist in exactly one place.

Chapter 6 has now corrected Chapter 5 four times (§6.3.2, §6.4.1, §6.6.6, §6.11.4) and itself
twice (§6.13 on §6.12.4, §6.14 on §6.13.4). Every correction came from running a measurement
rather than re-reading the argument. **Two successive predictions bracketed the truth from
opposite sides** — §6.12.4 over-predicted, §6.13.4 under-predicted — which is what
`00_METHOD.md` §2's evidence rule looks like when it is working.

| # | Task | Notes |
|---|---|---|
| ~~**1**~~ | ~~**The baseline arm**~~ | ✅ **Done 2026-09-02.** Zero. See §7.12 |
| **1** | **S8's and S3's paired baselines** | §7.5 makes them criteria: the 2021 file-theft pattern must **succeed** unconfined and be blocked confined, and S3 needs a paired baseline quantifying what is readable without the framework. The baseline arm supplies the instance but not the attack. This is now the cheapest high-value item and it is the project's single strongest security result |
| **2** | **Then the egress proxy — and this is still Chapter 6** | §5.8.2 scope item 2's second half: per-integration outbound network with T11's resolve-then-pin **at connection time**. Closes F2, S4 and T11. See the decision paragraph above |
| **3** | **Then PSS as a function of what is declared** | `experiments/unstrip/scale.py --components http,websocket_api` etc. The blanket profile costs 130.4 MB; an integration declaring nothing costs 54.5 MB. Measuring two or three points gives the *expected* budget over the corpus's real declaration distribution — and §6.13 now supplies that distribution: twelve of the 37 declare no components at all, and the median declaration is two |
| **4** | **Then the uniform-sample corpus** | The 37 are head-weighted by install count. A uniform sample answers "what most integrations do" rather than "what most installations run"; `figures/fetch_hacs_corpus.py` already takes the corpus and only the selection changes |
| **5** | **Then Chapter 7** | Seven obligations are already recorded for it below. The two most likely to bite: mediation latency at realistic sandbox counts (two clients moved p99 **85%**; the budget is ~26), and whether `fsync`-per-decision is affordable, since §5.11.3's ordering guarantee is only real if the record is durable before the action |

**✅ Gate G3 has a recommendation, and it is no longer close (§6.14, 2026-08-25).**

| Profile | Clean | Median peak | Premium | Disk |
|---|---|---|---|---|
| `minimal` | 17/37 — 46% | 100.6 MB | — | — |
| `declared` | 21/37 — 57% | 109.6 MB | +9.0 MB | per integration |
| `unstripped` blanket ten | 26/37 — 70% | 132.8 MB | +32.2 MB | 449 MB |
| **`declared` + core packages** | **31/37 — 84%** | **119.7 MB** | **+19.1 MB** | 641 MB |

- **The last row strictly dominates the blanket profile** — every integration the blanket profile
  passes, plus five more, for 13.1 MB *less* per sandbox. No trade to weigh.
- **"What a stock installation has" is computed, not asserted.** `core_requirements()` takes the
  `default_config` dependency closure (57 components) and the union of their declared requirements
  (39 packages), from the platform's source. `--print-core-requirements`.
- **Six failures remain and only three are the design's.** `aiofiles` ×3; `eufy_security` is
  broken on 2026.8.3 itself (`SOURCE_TYPE_GPS` removed from `device_tracker`); `hacs` and `spook`
  are corpus artifacts. **31/34 — 91%** of what the corpus delivered in a loadable state.
- **Home Assistant's own `package_constraints.txt` corroborates §6.13.3**: `# aiofiles keeps
  getting downgraded by custom components`. Upstream pinned defensively rather than requiring a
  declaration. **8% of the corpus still imports a package nothing would supply**, down from 16%.
- **The cost is stated in §6.14.5 and Chapter 8 owes it**: the sandbox holds 641 MB of code no
  integration declared. Cheap per sandbox and shared, and these are *libraries, not capabilities*
  — but it does weaken §6.8.1's third identity component, and 57% is the version that keeps that
  property intact. That is what 27 points cost.

**⚠ §6.12.4's prediction failed, and the failure is the better result (§6.13, 2026-08-25).**
The per-integration `declared` profile — auth wired, only the components an integration's own
manifest asks for — was predicted to reach 70–76%. It reaches **57%**, over *exactly the same
twenty-one integrations* as the earlier arm that ran with auth unwired. Wiring auth changed eleven
failure reasons and moved the corpus figure by zero.

- **The budget half of the prediction held.** +9.0 MB median over the minimal instance, against
  the blanket profile's +32.2 MB. Twelve of the 37 declare no components and are charged nothing; the median declaration is two.
- **The blanket profile's entire lead is dependency spillover, not components.** Six integrations
  pass under it and fail under `declared`, and all six fail on a missing *package* — `numpy`
  (`browser_mod`, `dwd_weather`, `llmvision`, `webrtc`) or `turbojpeg` (`dreame_vacuum`,
  `powercalc`). Both are requirements of `stream`, which none of the six declares and none needs.
  **70% = 57% earned + 16 points borrowed.**
- **It bounds Chapter 5's central premise with a number. 16% of this corpus imports at least one
  package its manifest never names.** "The declaration always already exists" survives — those six
  still declare components, platforms and config flow truthfully — but for packages it is
  *incomplete*, and Chapter 8 owes that rather than letting 57% stand as though nothing were.
- Chapter 5 was **not** edited; §6.12.4 carries a pointer to §6.13.

**✅ The base component is dropped (2026-08-25, `experiments/base_component/`).**

- **It can go.** Both probes load, the same entities are published, and the only loss is the
  `homeassistant` domain's thirteen services — which are cross-integration by nature and the
  design routes through the mediator anyway. The sandbox's service registry is then *empty*,
  which makes §5.6.2's claim literally true.
- **But §5.6.5's "roughly doubles" was wrong.** 46.6 MB per sandbox, budget 17 → 26, a factor
  of **1.53**. The prediction came from subtracting single-process figures — the arithmetic
  §5.6.3 warns against, four paragraphs earlier in the same chapter. **Chapter 5 was not
  edited to be right**; §5.6.5 and §5.8.1 now carry a pointer to §6.3.2 instead.
- **Compatibility cost, bounded:** 8 of 144 community integrations (5.6%) call a
  `homeassistant.*` service with a literal domain; 13 (9.0%) import the component. Lower bounds.

**⚠ The more valuable finding was accidental, and Chapter 7 depends on it.** §5.6.3's
`build_minimal_hass` reaches the running state with `set_state(CoreState.running)`, which never
fires `EVENT_HOMEASSISTANT_START`. `async_at_start` branches on `hass.is_running`, so this
*splits* deferred callbacks rather than dropping them: those registered before the flag (the
helper layer's own — **state restoration among them**) are lost permanently; those registered
after fire immediately, mid-assembly, instead of at start. **The fix is `await
hass.async_start()` called last**, after every component is set up — starting earlier also
repairs restoration and is the wrong fix. The defect was silent: no exception, no log line,
just a sensor reporting the wrong number. **Chapter 7 must check any compatibility failure
against the minimal instance before charging it to the design.**

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

**⚠ A finding from building the mount namespace, and it is a cost of the design's best idea
(§6.4.5).** Three separate defects came up and all three presented as an *absence* — a swallowed
write to the wrong descriptor, a `/tmp` mounted over a declared path, and a test expecting the
configuration root to be gone when it is legitimately a skeleton. **§5.6.2's structural denial
uses absence to mean "not granted", so any bug producing an absence is indistinguishable from
the framework working.** Responses in code, not prose: declared paths are bound last, and every
one is verified to exist before the sandbox is allowed to run. **Chapter 7 consequence:** an
integration that cannot find a file it declared is not evidence that confinement broke it until
the grant is shown to have arrived.

**⚠ §5.7.4's cgroup rule was wrong, and §6.4.1 corrects it (2026-08-25).** The *finding* —
migration refused with `EACCES` because the common ancestor is root-owned — stands. The *rule*
inferred from it in the same paragraph, that the sandbox must therefore be placed in its cgroup
at creation, does not: `clone3(CLONE_INTO_CGROUP)` fails with the identical `EACCES` from the
identical position, because the kernel checks the common ancestor either way.

- **What binds is the supervisor's own position.** It must run inside the cgroup subtree
  systemd delegates to its user — a systemd **user unit**. An ssh session lands in
  `user-1000.slice/session-N.scope`, outside it, and from there *nothing* works.
- **`clone3` is not needed, so the supervisor stays in Python.** Migration works from the right
  position. The child writes its own pid immediately before `exec`, which closes the uncapped
  window without C.
- **The trap:** `mkdir` succeeds from the wrong position. Everything looks right and only
  placement fails — so the supervisor must test placement at startup and refuse under N3.
- Chapter 5 was **not** edited to be right; §5.7.4 carries a pointer to §6.4.1, and
  `experiments/host_isolation_probe/README.md` is marked superseded on that one paragraph.

**⚠ Four obligations are outstanding — three from §5.14's traceability check, one added by
§6.3.3. They are cheap now and expensive in November.**

| Owed by | What | Why |
|---|---|---|
| ~~Ch. 6~~ | ~~A surface where the user encounters the declaration~~ | ✅ **Discharged 2026-08-25 in §6.7** — `confine/describe.py`, four states, denials shown at the same weight as grants |
| ~~Ch. 7~~ | ~~Never repeat §4.10's "filesystem isolation *to declared resources*"~~ | ❌ **Withdrawn 2026-08-25 (§6.6.6).** The obligation rested on §5.14.4's claim that "nothing about the filesystem is declared", which contradicts §5.10.3 and §5.10.5. §4.10's phrase is accurate |
| **Ch. 7** | State S9's boot-time precondition when evaluating it | The Pi's `memory` cgroup controller is disabled by Pi OS (§5.7.4). Testing on a machine where that was quietly fixed, without saying so, is the dishonest version |
| **Ch. 7** | Measure what `resources.memory_mb` costs a *legitimate* integration | §6.9.4. cgroup v2 charges page cache to the cgroup, so the memory limit bounds file reading too. An integration processing a large local dataset is indistinguishable, to this control, from one searching for secrets |
| **Ch. 8** | The `aiofiles` finding, and the objection it answers | §6.14.4. 8% of the corpus imports a package its manifest never names, and `homeassistant/package_constraints.txt` says upstream knows: *"# aiofiles keeps getting downgraded by custom components"*. **This is corroboration of the contribution claim, not a defect** — it is why "ask the author to declare it" is an assumption the evidence contradicts, and why 84% is worth what it is worth *because nothing was asked of anyone*. Long form and the viva answer in `notes/ch6_working_notes.md` |
| **Ch. 8** | Record that the strongest control produces no audit trail | §6.9.4. An OOM kill leaves a corpse and no record of what was attempted — the audit trail is weakest exactly where the control is strongest, and the cgroup has no `EPERM` to offer |
| **Ch. 7** | Decide whether `fsync` per decision is affordable | §6.8.3. The ordering §5.11.3 requires is only real if the record is durable before the action, and that costs far more than the 2.4 µs decision. §6.5.3's figures do **not** include it. The alternative is a bounded window of loss |
| **Ch. 7** | Negative cases must assert on **why** something was refused, not that it was | §6.6.5. A default-deny system produces the safe answer for almost any mistake, so a passing negative test is weak evidence by construction — three path-rejection cases were passing through the wrong rule entirely |
| **Ch. 7** | Measure mediation latency at realistic sandbox counts | §6.5.3. Two sandboxes moved the median 19% and p99 **85%** — queueing, not work. The budget is 26 sandboxes (§6.3.2), and two clients say nothing about twenty-six |
| **Ch. 7** | Check every compatibility failure against the minimal instance **before** charging it to the design | §6.3.3. The `async_at_start` defect broke state restoration silently — no exception, no log line. Left in, it would have been measured as the cost of confinement |

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
