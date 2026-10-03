# Where the rebuild stands

**Last updated 2026-10-03. Resume from the T-table directly below — it is the only live plan in this
file.** Everything after it is history, newest first: earlier resume points are kept as record and
are superseded, not live. Deadlines are deliberately out of scope for now (Younes, 2026-10-03).

**Proposal track, 2026-09-17.** The programme's EGR 4402 *Capstone Project Proposal* template arrived (`CSC_Capstone_Project_Proposal_Template-1.docx`) and must be filled and submitted. Content lives in `proposal/proposal.md`; `python3 proposal/build_proposal.py` fills the template into `proposal/capstone_proposal.docx`. **It is written prospectively, as if the work began 31 Aug 2026** (Younes's instruction) — the timeline is an estimate on that assumption, and success-criteria targets are set as pre-registered thresholds, not as the measured results. Still owed from Younes: student ID, supervisor, submission date.

**Technical work before report polish — Younes's decision, 2026-10-01.** Everything engineering
finishes first; the submission rewrite (figures, appendices, read-through) comes last. This reverses
the earlier ordering, where figures were first *because* they were on the submission path. The list,
in the order agreed:

| | Do this | Cost | Why |
|---|---|---|---|
| ~~**T1**~~ | ~~**T12's measurement**~~ | ~~hours~~ | ✅ **Done 2026-10-01 — §7.30. `selftest_t12.py`, 29 checks, all passing; suite count 19 → 20.** Every mechanism already existed and three said T12 in their own comments, so the gap was one of *reporting*, like §7.26.1. **Two things came out of it that were not on the list.** `Identity.manifest` says *the manifest changed*, not *the grant changed* — a version bump alone moves it, found by mutating the suite (§7.30.3) — and the design has **no re-check trigger of its own**, because no mediator outlives a respawn; the re-check happens because a spawn builds a fresh policy (§7.30.2, §7.30.4), and §8.7 item 14 now carries that. **Then a third thing, found by Younes asking how a GitHub manifest change reaches a house (§7.30.6): the user-facing half of T12 — the banner saying the code changed since you approved it — had no caller able to compute it, because nothing stored an approved identity to compare against. Fixed the same day**: `AuditLog.approval()`, `audit.last_identity()`, and a `describe` CLI that computes the flags itself. It also exposed that the banner's single message asserted the permissions had not changed, which is false when both components move — three messages now. **§7.30 missed it because the suite held both identities in local variables, which no installation does.** **The 19-vs-20 suite question below is resolved and the report was right**: the count is the exact glob `selftest_*.py`, which excludes `selftest.py`. Fourth time a recount of mine was wrong. Original entry: The only threat in either register with no evidence, and §7.26.5 tells the examiner exactly where it is. Every mechanism exists: `Identity` already hashes the manifest separately from the source *for this purpose*. Six assertions — set up under v1, change the manifest, re-spawn, and show (a) `Identity.manifest` moved while `Identity.source` did not, (b) the request v1 permitted is denied with a clause pointer into v2, (c) `describe.py` shows the v2 surface *before* it takes effect, (d) the durable log carries both identities |
| **T2** | **Two or three more real integrations end-to-end**, three arms, via `endtoend_egress.py` | a session | **The real-integration path is n=1.** §7.27 is one integration and it found the most important defect in the project, behind 18 passing suites. §8.4.2's lesson — real unmodified code finds what the paired baseline, two instruments, self-tests and recomputation cannot — **has been applied exactly once**. 11 credential-free candidates exist; the harness is already parameterised by corpus |
| **T3** | **One credentialed integration, end-to-end, with a real account** | half a day | **26 of 37 ask for an API key, token, password, username, host or email, and none has ever completed setup with a valid credential in either arm.** The 11-of-37 ceiling is sound and an unconfined baseline hits it identically — but *no account exists* is a choice, not a wall. Untested as a result: a **successful authenticated** round trip from inside a sandbox (nordpool's API is public, so the one real success carries no auth header), the config entry persisting a secret in the stripped instance, **re-auth/token refresh — which happens at a different phase than setup**, so egress demand appears where nothing has looked, and the audit log telling a 401 from a denial. **Note for the viva: S2/T04/R3's credential is the *platform* token the mediator holds, not an integration's own remote API key — and S2 is already tested by `gc_attack`. No account is needed to defend S2** |
| **T4** | **Wire `AuditLog` into the other harnesses** | small | Instantiated in three places only; everything else records to `mediator.audit` — in-memory, no chain, no MAC, no `fsync`, dies with the process. **The one time the durable log ran for real it produced three defects in a session** (§7.27.6). §8.7 still has no row for it |
| **T5** | **Re-run `figures/api_surface.py` on the uniform corpus** (§8.7 #6) | one run | Closes the half of contribution 1 (§2.8) that §7.23 left undelivered |
| **T6** | **Re-run the 20 suites on the Pi** | a session | Untouched since 2026-09-06; the report asserts they pass |

**Then** the report: figures (~8, each generated from source with an assertion that it still says what
the prose claims), appendices B–F (all *lift verbatim* — and until they exist the compression has
**deleted** evidence rather than relocated it; Appendix D is what lets an examiner check the
zero-compatibility-cost claim), the submission draft's **first** read-through, the three `[To verify]`
citations, and the four handbook-blocked title-page fields.

~~**Open question, ten minutes:**~~ ✅ **Resolved 2026-10-01, and the report was right.** The count
is the exact glob **`selftest_*.py`** — the pattern the front matter's artifact index states — which
excludes `selftest.py`, the framework's own base self-test, recorded separately in `01_PLAN.md`. 19
was correct on 2026-09-06 and the count is **20** from today. **Fourth occasion on which a recount of
mine was wrong and the report right**, after §8.5's declared-component counts, §7.13's adversary
outcomes and pass 3's blocked count. The rule holds: a disagreeing recount is a question until the
counted field is confirmed.

---

*History from here down. The block below was the resume point on 2026-09-08 and is superseded by the
T-table above.*

**The front matter has now been read through too — 2026-09-08, five findings, all fixed, and again
none of them a measured figure.** It was the one piece of prose no Stage 5 pass had covered, and its
own *Outstanding* section said so. Three findings were in the **abstract**, which is the newest prose
in the report: mediation latency was quoted as §5.11.4's **30 µs floor** in a sentence whose other two
figures are §7.20.1's, where the corrected figure is **31.5 µs** — §7.23.1's two-populations mistake
in miniature, one sentence mixing a Chapter 5 floor with Chapter 7's corrected measurements;
*"two lines fixed it"* described a fix that is a flag bit plus a route added by `SIOCADDRT`, which
§7.27.3 itself calls two *steps*; and the closing sentence said every correction had been to a
sentence next to a measurement **in the paragraph immediately after describing a correction to the
artifact**, so the two exceptions now travel with the claim. Outside the abstract: the Tables section
stated **149** unnumbered in one sentence and **152** in the next — `toc.py` checked the second and
not the first, so the unchecked statement is the one that drifted, and **the check now covers both,
verified by making it stale** — and the abbreviations table still said **six** residual risks where
§4.11 gained R7 on 2026-09-04. Also fixed: the title-page date range stopped at 4 September, and
**`v2/notes/` had no row in the artifact index** although the chapters point into it 24 times, which
is the general case of the one instance pass 1 caught (§5.6.1's reconciliation living only in a note).

**Stage 5 pass 3 — five findings, all five fixed, and none of them a measured figure.** The sixth
consecutive pass where that has held. Targets were §7.19–§7.25's prose (which neither earlier pass
read) and every claim of the form *X is verified/counted/measured*. **F3 is the one worth being
able to say aloud**: the head corpus requests 40 repositories and measures **37 integrations**,
because three domains — `scheduler`, `govee`, `solarman` — are each claimed by *two different
repositories*, and a domain is one slot on disk. §7.23.1's install figures were computed over the
39 fetched *repositories* while the rows beneath them were over the 37 *integrations*, so one
column described two populations; restated, the median rises to 16,294 and the total falls to
998,478 and the reach ratio goes 22× → 21×. **No conclusion moved.** The reproducibility half is
sharper: which repo won each collision is not recoverable from the manifest, and `govee`'s two
candidates differ 5 vs 46 Python files — the same weakness §7.29.2 records from the other side.
Also: §7.24.7's table listed 11 of 12 (`solarman` absent, and it was the member selected to test
assumption 1); §7.21.3 said *five* mis-pointed obligations where ten of eleven point at a
methodology section; §7.26.4 cited an IPv4-mapped address the run never produced; and the
adversary suite's 37→38 transition was never stated. **Once again a recount of mine was wrong and
the report was right** (the 21-vs-20 blocked count) — third occasion across passes 2 and 3.

**A consolidation backlog now exists: `notes/rewrite_consolidation_backlog.md`.** Younes's
instruction, 2026-09-06: the report will later be rewritten to consolidate sections and simplify
the prose. Five structural items are recorded there rather than patched — the correction stacks
are several layers deep, one number has five statements, the obligations register lives in three
places, §7.5's snapshots are redundant now that it has a verdict column, and Chapter 7 at 198 KB
is read as one document only by its own read-through sections. **These are not defects and should
not be fixed piecemeal.**

**What the 2026-09-06 session did, in one line:** built and ran **the C1 count** — task 1 below,
§8.7 #4, the highest-value hour left — and it passes: **75 tree comparisons across both arms, zero
source changes, zero diff lines** (§7.29). C1 goes from *argued* back to *counted* and §7.5's row
is ✅. **Two things came out of it that were not on the list.** The check could not be built as
§8.7 priced it — hashing *at fetch* is impossible for a corpus whose manifest pins `HEAD` and
records no content hash, so the count covers a run and not the project's history (§7.29.2); and the
first version of the instrument **reported a clean zero because it compared the baseline tree
against itself**, which is §6.4.5's failure mode for the fourth time, caught by a self-test written
for it (§7.29.3). Suite count is now **19**. Nothing else changed; no measurement was re-run except
the two compatibility arms, which returned **31/37 — 84% and the same six failures**, unchanged.

**What the 2026-09-04 session did, in one line:** fixed Chapter 8's known defect, wrote the front
matter and a single 28-source bibliography where two colliding schemes had been, and ran **two
Stage 5 read-through passes that found twelve things — none of them a measured figure, and one of
them serious**: §7.4.1 and §8.3 both claimed C1 was *"verified mechanically"* and **that
verification does not exist** (§7.28). C1 is downgraded from *counted* to *argued*, and running the
check is an hour and the first thing on the list above.

**Changed 2026-09-04.** Three things: the Chapter 8 defect recorded below was fixed (§8.7 gains a row
for building the real Home Assistant component, now #2 of twelve), and **task 6 is done** — front
matter, abstract and a single consolidated bibliography now exist. **Only Stage 5 remains.** Details
in *What the 2026-09-04 pass changed*, below; the bibliography was not the clerical job it looked
like and found four uncited sources, one of them Chapter 4's entire method. **Third: a realistic-
scenario validation is now recorded as the next engineering work** — real HA, real integrations at
volume, executed rather than imported, with the durable audit log actually engaged. See *The
realistic-scenario validation*, below. It is not on the critical path to submission; it is what
would make the strongest claim in the report a claim about a running system rather than about a
mediator's decisions.

**Where it stands in one line:** **Chapters 1–8 are written.** All twenty requirements in §7.5
carry a verdict, 18/18 self-test suites pass on the Pi, and the framework runs. The strongest
result remains the paired baseline: confined and unconfined arms fail on the *same* integrations
for the *same* reasons, so **the import-level compatibility cost of confinement is zero** — twice,
on two corpora sharing 5% of their members. 84% was never a fact about confinement; it is the
fraction of the corpus that loads on 2026.8.3 at all.

**What the project has learned about itself, and the reason to trust the rest.** Chapter 6
corrected Chapter 5 four times and itself twice; Chapter 7 corrected Chapter 6 five times and
itself across two read-throughs; **six of eight pre-registered predictions were wrong and none was
revised.** Across all of it, *every* correction has been to a sentence next to a measurement and
none to a measurement — with **two exceptions, both defects in the artifact, and both found by
building something adversarial or real rather than by reading code**:

1. `EgressBroker.open` trusted `allow_private` from the sandbox's own request — a hostile
   integration could have granted itself T10's non-public reach by writing one key into a message
   it already composed. Found by writing the attack case; fixed and regression-tested (§7.26.2).
2. **No real integration could construct an HTTP client inside the sandbox at all.**
   `async_get_clientsession(hass)` — what the platform tells authors to call — builds its DNS
   resolver by instantiating Zeroconf, which joins the mDNS group, and a fresh netns `lo` has no
   `IFF_MULTICAST`. The egress design had therefore been unusable for the 41% of the corpus it
   exists to serve, **behind eighteen passing suites**, because every earlier subject was written
   by the author of the sandbox and used a bare `aiohttp.ClientSession()`. Found on 2026-09-03 by
   running one real community integration; fixed in two measured steps (§7.27).

**That second one is the single most important methodological result in the project** and §8.4.2
states it: a paired baseline, two instruments, a self-test and recomputation each catch a class of
error — and *running unmodified real code* finds what none of the four were looking for, because
the other four are all written out of the same assumptions.

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
| `report/04_threat_model.md` | ✅ **Complete.** 18 threats, **7** residual risks (R7 added against §4.11 by Stage 5 pass 1); impact scale rebuilt 2026-08-22 (`notes/decision_impact_scale_and_standards.md`); §4.6 figure drawn and inserted 2026-08-24 |
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
| `report/00_front_matter.md` | ✅ **2026-09-04; read through 2026-09-08 (five findings, all fixed — see below).** Title page, abstract, declaration/AI-use content, contents, figures, abbreviations, artifact index, *Outstanding*. Title: *Confining Unmodified Third-Party Integrations in Home Assistant — A Declared-Authority Architecture and Its Measured Cost*. **Four title-page fields stay placeholders**, blocked on the same unresolved input as every date in `01_PLAN.md` §9.6 |
| `report/09_references.md` | ✅ **2026-09-04.** One bibliography, **28 sources**, numbered by first appearance across the whole report. Ch. 1, 2 and 5 remapped onto it; per-chapter lists replaced by a pointer. Three bibliographic details flagged unverified at the foot of the file |
| `report/toc.py` | ✅ **2026-09-04.** Generates the contents page and figure list into the front matter between markers, and **asserts the counts its prose states** (now 242 third-level headings; 155 tables, 3 numbered and 152 not) so they cannot drift. `--check` exits non-zero when stale — verified by making it stale. **2026-09-08: it checked the unnumbered count in one of the two sentences that state it, and the unchecked one had drifted to 149. Both are checked now** |
| `report/07_evaluation.md` | ✅ **Complete, §7.1–§7.27.** §7.1–§7.11 written 2026-09-02 *before* any result and dated so; §7.12–§7.25 written one result at a time; **§7.26 is the read-through** (it found that §7.2 promised a scoring against two threat registers that the results half never performed — both now done, 13/18 threats demonstrated and 8/11 of the external register mapped); **§7.27 is the real-integration arm**. All 20 §7.5 rows carry a verdict |
| `report/08_conclusions.md` | ✅ **Written 2026-09-03.** *Conclusions, Limitations and Future Work*, ~42k chars. Answers the claim against §7.7's pre-fixed falsifiers (**the fourth falsifier — the one about the evaluation — fired**, §8.2.4); closes §2.8's three contributions; §8.4 the 6-of-8 scorecard and the five mechanisms; §8.5 the 52-vs-2 finding; §8.6 twelve artifact limits and six evaluation limits; §8.7 eleven future-work items priced; §8.8 the single upstream ask (R3). **Known gap: §8.7 has no row for building the real HA component** — fix next session |
| `framework/confine/endtoend_egress.py` | ✅ **2026-09-03, §7.27.** Three arms on `nordpool` — unconfined / confined+declared / confined+clause-removed. The third is what makes the second evidence: a leaked namespace would produce arm B's result exactly. **11/11.** Destination evidence comes from the mediator's *durable* log, not `mediator.audit` |
| `experiments/end_to_end/results/pi5_nordpool_egress.json` | ✅ **Pi 5, 2026-09-03.** `0.026` confined and unconfined **in the same minute**; 3 grants logged as `dataportal-api.nordpoolgroup.com:443`, both chains verifying; clause removed → 3 denials and `unavailable`. `nordpool_egress.md` beside it is the readable write-up |
| `framework/confine/selftest_c3.py` | ✅ **2026-09-02, §7.16.1.** C3's two uncovered shapes, and the ceiling table that makes R1's "structural" claim checkable |
| `experiments/gc_attack/` | ✅ **Pi 5, 2026-09-02, §7.15. S1's baseline half — and the realism fix.** §6.9's confined gc sweep was near-tautological (its process held no other secret). Here a **real victim integration** holds a live token: unconfined the adversary reaches it **7 ways** (`CloudClient.attr`, `hass.data`, module); confined it finds nothing while the same token is **confirmed live in the mediator's process** (7 refs). The confirmation is what makes "found nothing" a result rather than an absence |
| `experiments/entity_visibility/` | ✅ **Pi 5, 2026-09-02, §7.14. S3 paired.** One 36-entity home, 20 disclosing presence. Unconfined **36/36** and **20/20** presence, plus every change to others' entities; confined **1/36**, every undeclared probe absent and denied with a clause. Subscription half verified at the **decision layer only** — no push loop exists (§6.11.2) |
| `experiments/adversary_baseline/` | ✅ **Pi 5, 2026-09-02. S8's pairing, §7.13.** The same hostile payload with and without the sandbox — `ATTACKS` imported, not copied. **Three corrections to §6.9**: the `/dev/zero` misattribution (stands), the counts 21/9 → **20/10** (stands), and one *withdrawn* — S9's evidence was never invalid; the hardened harness had briefly stopped telling a kernel kill from its own timeout. S9 gained a second, better demonstration anyway: **allocate** memory rather than read files. Harness finding: `PTRACE_TRACEME` succeeds unconfined and wedges the process on the next signal, which is why the suite was only ever fragile in the arm nobody had run |
| `experiments/compat/results/compat_baseline.json` | ✅ **Pi 5, 2026-09-02. The baseline arm.** 37 against a full, unconfined HA — same release, host, interpreter, corpus, and the *same* `inspect()` function, shared not copied. **31/37 — 84%, identical to confined, same six failures, same reasons.** `failures(design) = 0`. Baseline loads a median of **52** components; the sandbox sets up **2** |
| **`framework/confine/integrity.py`** | ✅ **2026-09-06, §7.29. The C1 count.** Hashes an integration's tree before and after a run and classifies what moved. **Reuses `audit.Identity`** — §5.12.1's three-part tuple, already built to answer *did this code change* for T12 — rather than defining a second hash, so the report has one mechanism in two places. Wired into **both arms** of `compat.py`, so C1 is counted as a side effect of any future compatibility run. `selftest_integrity` **15/15**. `sha256_file` promoted from private in `audit.py`; `selftest_audit` unaffected |
| `experiments/compat/results/c1_*.json` | ✅ **Pi 5, 2026-09-06.** Both arms re-run with the check wired in. **Baseline 37 trees, confined 38, `source_changed: 0`, `total_diff_lines: 0`, `lines_unknown: 0`.** Each row carries its own `integrity` record, not just the totals. Compatibility unchanged at **31/37 — 84%** in both arms, same six failures |
| `framework/confine/baseline_runtime.py` | ✅ The unconfined arm. `--profile baseline` in `compat.py`. Bias deliberately resolved toward the baseline throughout |
| `report/06_implementation.md` | ✅ **Complete as written, §6.1–§6.14, 2026-08-25.** Its one unbuilt scope item was built and reported in Chapter 7 (§7.25, §7.27); **the chapter is deliberately not edited to be right** — §6.11.1 still reads "Egress does not exist" because that was true when it was written, which is the same rule applied to §5.6.5 and §5.7.4. Original note follows. **§6.1–§6.14 drafted 2026-08-25; one scope item still unbuilt.** The bridge is built, the corpus has been run four ways, and **Gate G3 has its recommendation**: `declared` + core package set, **31/37 — 84% — at +19.1 MB**, strictly dominating every other profile measured. What is *not* built is §5.8.2's scope item 2 — mediated egress, F2 and S4 — recorded in §6.11.1 as "◐ Half. Egress does not exist." Section plan, the §6.13–§6.14 reasoning and the viva answers in `notes/ch6_working_notes.md` |
| `experiments/egress_shape/` | ✅ **Pi 5, 2026-09-03, §7.24. What the proxy must do, measured before it is built.** Twelve head-corpus integrations, unconfined with real network, driven through their own config flows. **Three of §5.10.3's assumptions fail**: resolution is 96% `aiodns` not `getaddrinfo` (3,073 vs 120, uniform 93–97%); ports 8123/6445/20086 as well as 443; UDP is real. Inbound is not needed. Three network stacks (aiohttp, urllib3, raw), TLS via both `wrap_bio` and `wrap_socket`, all verified. **It also answers §7.18's "no observational method can answer this"** — that binds *how much*, not *what shape*, because a flow validates a credential by making the call. Instrument is `framework/confine/netshape.py`, 13/13 self-test on both architectures, paired with `strace`, which bounds its blind spot at 74–87% of kernel egress |
| `experiments/host_isolation_probe/` | ✅ **Pi 5, 2026-08-24; re-run 2026-08-25.** Namespaces (unprivileged), seccomp and cgroup v2 all present. `memory` was absent on the stock install; after the boot change it is present **and the cap is verified to bite, unprivileged**. Feeds §5.7.4 |

## Next session — start here

**Superseded 2026-10-03: the live plan is the T-table at the top of this file.** What this section
held on 2026-09-06 — C1, pass 3, the handbook lookup, defence prep — is either done or recorded there.
The pass-3 method below is kept because it is the recipe for the submission draft's first read-through.

### How to run pass 3, since two passes have now taught the method

1. **Grep for completion claims before reading.** `verified|counted|measured|demonstrated|confirmed`
   next to a requirement ID. C1 hid because §7.4.1 stated it as fact, and **§7.8's obligations table
   can only be swept for promises** — a promise can be checked against the section it names, a false
   statement of completion names nothing.
2. **Check every load-bearing claim against the artifact, not against another section.** Both of
   pass 2's real findings came from `grep`ping `framework/` for a mechanism the prose described.
3. **Recompute from the result files, and expect to be wrong.** Twice in pass 2 the recount was
   wrong and the report was right — §8.5's counts and §7.13's outcomes. **A disagreement is a
   question, not a finding, until the field being counted is confirmed.**
4. **The mechanical sweeps are cheap and already written**: `python3 report/toc.py --check`, plus
   the reference and section-reference checks in the pass-1 commit message (`3636b16`).

### Optional measurements, ranked — none blocks submission

Taken from §8.7's list, which is ordered by what each would settle. **§7.27 reordered that list
after it was written**, which is what evidence is supposed to do to a plan.

| | Work | Cost | Why |
|---|---|---|---|
| ~~**T12's measurement**~~ (§8.7 #5) — ✅ **done 2026-10-01, §7.30; now T1** | Set an integration up, change its manifest, spawn it again; show the second run is bounded by the second declaration and that `describe.py` shows the change before it takes effect | **Hours** | **The best value per hour on the list.** T12 is the only threat in *either* register with no evidence at all, and §7.26.5 says so in the report — so an examiner will find it because we told them where it is |
| **Re-run `api_surface.py` on the uniform corpus** (§8.7 #6) | One run of an existing script over an already-fetched corpus | **One run** | Contribution 1 (§2.8) is half delivered: §7.23 answered the uniform question for *compatibility* and never for the API surface, so §7.8's obligation row was discharged for one of two |
| **The other two network stacks, confined** (§8.7 #7) | `urllib3`/`requests` and a raw socket, spawned in real namespaces | Days; may need recorded fixtures | Promoted from nowhere to sixth by §7.27. The one stack actually spawned turned out to break, so "the other two are presumably fine" is exactly the reasoning that was wrong once |
| **The push loop** (§8.7 #1) | Build it | Days | Largest missing piece, but it is *building* not testing. Unblocks S3's subscription half and the only latency path that could consume §7.20.1's 63× margin |
| **The real Home Assistant component** (§8.7 #2) | Build it — the spike has ~250 lines that load nothing from any integration, reusable under `00_METHOD.md` §5 | Days | §8.6.3's limit #2, and the one the 2026-09-04 fix added to §8.7. What it settles is entity **identity**: the states API publishes without a registry row, and §5.6.1 measured **83%** of the corpus publishing by the path that creates one. The *finding* is private knowledge under §2 and would have to be re-measured, not cited |

### ⚠ The realistic-scenario validation — agreed 2026-09-04, and it is one measurement, not four

**Younes's instruction: the solution needs testing again in a realistic scenario.** The report's
future-work list prices the pieces separately (§8.7 #2, #10, and the compatibility corpus work) and
that framing understates them, because **what has never happened is all of them at once**. The
value is in the composition: each part alone is already priced; together they are the first run in
which nothing on the critical path is a stand-in.

| Part | Where it stands today |
|---|---|
| **A real Home Assistant** | ⛔ **Never.** The mediator's step 5 acts on `platform.py`'s in-memory stand-in — §8.6.3's limit #2, §8.7 #2. The integration inside the sandbox runs *genuine* HA 2026.8.3; the platform on the far side of the mediator does not exist |
| **Real integrations** | ✅ Partly. 77 unmodified community integrations at **import**; **5** executed end to end (3 published confined, 4/5 unconfined); **1** — `nordpool` — against a real API over the mediated path |
| **A large sample, executed** | ⛔ **n=5.** The ceiling is 11 of 37, because 26 need a credential before any config flow completes (§7.17.1), so this needs recorded fixtures or a cooperating vendor set — §8.7 #8 calls that "a different project's measurement" and it is the honest framing |
| **The logging mechanism, engaged** | ⚠ **One run of about eight.** `AuditLog` is instantiated in exactly two places in the codebase: its own self-test and `endtoend_egress.py` (§7.27). Every other experiment records to `mediator.audit`, an **in-memory list** — it carries op/allowed/clause so F3 holds and the measurements are sound, but it has no hash chain, no MAC, no `fsync`, and it dies with the process |

**The logging half is the one with no home in the report, and it is the sharpest of the four.**
The mechanism is built and its properties are demonstrated — `selftest_audit` is 15/15, both chains
fail independently, tamper/delete/reorder all detected, and durability is measured at **3,670.7 µs
median with `fsync` against 61.8 µs without**. What is *not* demonstrated is the mechanism running
under the evaluation. **And the one time it did run for real, it produced three defects in a single
session** (§7.27.6): the log was created inside a directory the harness deletes, so the run reported
*no decisions at all*; the destination evidence was read from `mediator.audit`, which does not carry
the request, so every destination read `None`; and `audit.py` itself recorded an egress target as
host **without port**, so the log could not tell a grant of 443 from one of 6445 on the same host.

**This is §7.27's lesson arriving a second time, on a different component.** A thing exercised only
by tests its own author wrote passes; it breaks the first time real work goes through it. Two
instances is a pattern, and it is the argument for this validation being *the* next engineering
work rather than one of eleven ranked items.

**Cheapest first move, and it is not the big run:** wire `AuditLog` into the other experiment
harnesses. It is a small change to code that already exists, no new measurement, and on the
evidence above it is likelier to find something than to confirm something.

**Two things the report does not currently say**, and a decision is owed on whether it should:
§8.6.4's evaluation limits do **not** state that the durable log was engaged in one run of eight,
and §8.7 has no row for it. Left unrecorded, the report reads as though the audit mechanism was
exercised throughout the evaluation.

**Not obtainable, and stated rather than owed:** the adversary is purpose-built and exercises the
*pattern* of the 2021 disclosures rather than the eight disclosed integrations at their vulnerable
versions — those versions are not in the corpus (§7.13.6).

### What the 2026-09-04 pass changed

**Bookkeeping only. No measurement was re-run, no figure moved, and no claim changed.** Two things
were repaired and one further defect was found while repairing them.

1. ✅ **Chapter 8's known defect is fixed.** §8.7 had no future-work row for building the real Home
   Assistant component, even though §8.6.3 names "the mediator acts on a stand-in, not a live Home
   Assistant" as limit #2 — *the largest limitation in the report had no entry in its own
   future-work list*. §8.7 now carries it as **#2 of twelve**, priced in days, and the row states
   what it settles: **identity, not realism**. §8.6.3's limit #2 gains the reciprocal pointer, so
   the limitation and its price now name each other in both directions.
2. ⚠ **Found while fixing it: §8.7's cross-references into §8.6.3 were off by one.** The
   derived-manifest row settles §8.6.3's *item 13*, and said "item 12". Almost certainly because
   §7.27 inserted the mDNS limit at 12 after §8.7 was drafted. **Fixed — and it is a Stage 5 result
   arriving early**: the two rows that point at §8.6.3 by number and happened to still be right
   (items 5 and 7) were checked, so all three now resolve.
3. ✅ **This file's own tables were stale, and are repointed.** The obligations table below still
   listed as outstanding several things Chapter 7 discharged; the header said "seven chapters" in
   one row and "eight" in another; §8.7 was described as ten items. All corrected against the
   report rather than against memory.

4. ✅ **Task 6 is done, and the bibliography was not the clerical job it looked like.** It found
   four things, and the third is the one to be able to say aloud:
   - **Chapters 1 and 2 carried independent `[n]` schemes that collided.** `[3]` was the 2021
     disclosure in Ch. 1 and FlowFence in Ch. 2. Unified by first appearance, 28 sources.
   - **Chapter 5 was citing Chapter 1's private numbering** — §5.13's D0 row carried `[3][5][10]`,
     which resolved only against a list in another chapter. The collision had already reached a
     third chapter and nothing had noticed.
   - **Chapter 4's own method was uncited.** The chapter follows **ISO 31000** clause by clause and
     names the clause it discharges in every section heading, identifies risk with **STRIDE**, and
     draws Figure 4.1 with **OWASP Threat Dragon** — and none of the three had a bibliography entry
     anywhere in the report. **RFC 1918** is normative for what `is_public` refuses and was also
     unlisted. All four now carry an inline marker at first use, as [25]–[28].
   - **One listed source was never cited** (Ch. 2's old `[15]`, Mannella's PhD Day summary). Removed
     rather than carried, with the removal recorded in `09_references.md` rather than done silently.
   - **The count was wrong.** This file and `01_PLAN.md` §9.6 both said 18 references. It is 28.

**The pattern is worth noticing before Stage 5 starts.** Every one of these is a *pointer* that
stopped matching what it points at, and none is a claim that was wrong. That is exactly the failure
mode a single-voice read-through exists to catch — and it is now **four** passes over this project's
prose that have each found something real (§7.26 twice, the §8.7 fix, the bibliography). The
bibliography is the sharpest of the four, because the uncited standards are not a formatting defect:
an examiner reading §4.1 is told the chapter's whole method comes from two frameworks the report
never cites.

### ✅ Stage 5, pass 1 (2026-09-04) — eleven findings, all eleven now fixed

Chapters 1–6 and 8 were read in full; Chapter 7's headline figures were re-verified against the raw
result files; every cross-reference was swept mechanically. **Eleven findings, all eleven fixed** — five
unambiguous ones in `3636b16` (three prose-form citations in Ch. 4 still on the old numbering,
§4.14's correction spliced through the paragraph it corrects, §5.10.3's schema table broken in half
by a blockquote, Ch. 7's eight references to a non-existent Chapter 9, and the front matter's false
claim that no table is numbered), and the six below, each of which needed a judgement call. **The
first is the one that mattered.**

| # | Finding | What was done |
|---|---|---|
| **1** | **§7.4 says "Every one appears in §7.5 with a verdict" and §7.5's third column is headed *Verdict source*.** Seventeen of twenty rows carry a section pointer — `Security`, `Performance`, `All arms` — not a verdict. Only F2, S4 and S9 were updated in place, and §7.5's own note calls those "this table's **one deliberate exception**". §8.2.4 repeats the claim while answering the falsifier about the evaluation's honesty | ✅ **§7.5 gains a fourth column carrying all twenty verdicts**, each with its evidence pointer. The Criterion column is verbatim as frozen 2026-09-02 and the Verdict-source column is untouched; the new column is the reconstruction, and a dated note at §7.5 says so. §7.4's sentence now carries a pointer recording that it was not true until this pass. **No verdict is new** — every one was recoverable from the chapter; what was missing was the column that collects them |
| **2** | **§7.18.1 says "the second is the one Chapter 8 owes" and Chapter 8 does not carry it.** The owed finding is that the corpus's network need splits **41% cloud-facing / 41% local-facing**, that these are different capabilities, and that building the proxy therefore makes 41% workable and puts the other 41% behind `allow_private` — a flag the user must read differently (T10). §7.18.1 says in its own words that nothing in Chapters 1–7 had stated this | ✅ **Delivered as a paragraph closing §8.2.2.** 30 of 37 (81%) declare a network need; it splits 41% cloud-facing / 41% local-facing, and the second half sits behind `allow_private` — the flag §7.26.2 caught being read from the sandbox's own request. **Building the proxy made 41% workable, not 81%** |
| **3** | **§7.22.2 contains an unfilled placeholder**: *"I/O bandwidth is a live T16 vector… **R‑numbered residual risk**, and Chapter 8 owes it a row."* Chapter 8 §8.6.3 #4 then says **§4.11** owes the row, and §4.11 never gains one | ✅ **Entered as R7 against §4.11**, as a dated addition with §4.11's original text left as written. Rated **Medium, inherited** — the `io` controller is present and not delegated, so an unprivileged supervisor cannot enforce it at any effort. **The symmetry is worth keeping: §4.10.1 is Chapter 4 generating a requirement Chapter 3 could not have written; R7 is Chapter 7 generating a residual risk Chapter 4 could not have written**, and §4.12 already listed that as a review trigger. §8.6.3 #4 and §8.6.1 updated |
| **4** | **The report states two sizes for the same population.** §5.6.1 and §5.9.1 say *n = 1,482* shipped integrations; §8.3 says *1,458*. Both are correct — 1,482 directories, 1,458 containing Python — **but the reconciliation exists only in `notes/ch5_evidence_api_surface.md`, which is not submitted** | ✅ **Reconciled in the report at both ends** — §5.6.1 carries the explanation (1,482 directories; the `ast` parser skips 24 holding no `.py` file) and §8.3 carries a pointer to it |
| **5** | **§5.10.7's worked example: "Nine of the ten capabilities are denied by their absence."** The example grants two of the ten leaf clauses (`entities.read`, `network.egress`), so eight are denied. Reads as off by one | ✅ **Corrected to eight of ten, with the correction recorded rather than applied silently**, and the two granularities named: §5.10.3's *eight* are the top-level capabilities `manifest.py` enforces, the *ten* are the declarable clauses beneath them. Checkable from the JSON four lines above it, which is why a read-through catches it and a self-test cannot |
| **6** | **§3.8 says "Every requirement, and where it comes from" and lists nineteen.** S9 is added by §4.10.1 and §7.5 tests twenty. §4.10.1 explains itself well, but §3.8 has no forward pointer — the only superseded claim in the report without one | ✅ **§3.8 gains the forward pointer to §4.10.1**, stating why S9 is absent — §3.1's traceability discipline forbade inventing it — rather than adding a row Chapter 3 had no basis to write |

**What the pass did *not* find is worth as much as what it did.** No measured figure disagreed with
the raw result files. `failures(design) = 0` recomputes from all four arms; §6.14's four G3 profiles
recompute to 17/21/26/31 exactly; §8.5's 52-vs-2 and 53-vs-0 recompute, including the 18-and-26
`dependencies == []` counts that §7.26.6 had already reconciled against the 12 that count
`setup_components`. **Eleven findings, none of them a number** — the fifth consecutive pass over
this project's prose where that has been true, and §8.4.2's claim now has one more instance behind
it than the chapter states.

### ⚠ Stage 5, pass 2 (2026-09-04) — one finding, and it is the most serious in the report

Pass 2 read **Chapter 7's prose**, which pass 1 had only verified numerically. One finding, and it
is worth more than pass 1's eleven put together.

**C1's verification does not exist.** §7.4.1 says *"C1 is verified mechanically, not asserted. Zero
source lines changed, counted by diffing each integration's tree against the fetched original after
the run"*, and §8.3 repeated it. **Nothing in `framework/`, `figures/` or `experiments/` hashes or
diffs an integration's tree against an original.** No result file carries the field; no results
section reports the count. C1 underwrites the word the report's title rests on.

**What is true instead is two lines of the harness, and it is asymmetric:**

| | Confined arm | Baseline arm |
|---|---|---|
| Source that runs | a copy — `shutil.copytree` (`compat.py:264`) | **the fetched tree itself**, by path (`compat.py:393`) |
| Can it be modified? | **No** — `sandbox.py:218` mounts the copy read-only | **Yes** — full authority, in-process, no mount |
| Diffed? | no | no |

So the confined arm is *stronger* than the criterion asked for — structurally incapable rather than
observed innocent — and **the baseline arm has nothing at all**, which is the arm every
compatibility figure is measured against. **And the check as described would not have tested what
it claims**: the confined run operates on a copy, so diffing the *original* afterwards compares a
tree nothing touched.

**C1 is downgraded from *counted* to *argued*, not withdrawn.** No modification has ever been
observed and `copytree` performs no transformation. §7.28 is the new section, §7.5's row states it,
**§8.2.4's answer to the fourth falsifier is corrected rather than quietly fixed** — it had said
"nothing was reported as passed that was not demonstrated" — and **§8.7 #4 prices the repair at an
hour**: hash each tree at fetch, re-hash the copy before the confined run and the tree after the
baseline run, report mismatches. Until that runs, C1 rests on reading two lines of the harness.

**Why four earlier sweeps missed it, and this is the transferable part.** §7.21.3 caught five
obligations "discharged" in a methodology section by checking each against the results section it
named. **C1 was never entered in §7.8's obligations table at all**, because §7.4.1 stated it as an
accomplished fact rather than as something owed. *A promise can be swept for; a false statement of
completion cannot.* §7.8 now carries that observation and the pointer to §7.21.3 it lacked.

**Two recounts I ran against the raw data during this pass were wrong and the report was right** —
§8.5's declared-component counts (I counted `setup_components`, the field §7.26.6 had already
distinguished) and §7.13's adversary outcomes (I counted the run's own summary line as an extra
row). **Across two passes: twelve findings, not one of them a measured figure, and two occasions
where the checker was wrong and the measurement was not.**

### The standing risk, unchanged since 21 August

**Programme deadlines for proposal / mid-report / final / defence are unknown**, and it is
§9.7's top-ranked risk. Every schedule figure in `01_PLAN.md` §9.6 assumes end-of-November
submission. The handbook route needs nobody's reply. This is the only input that makes the
remaining plan mean anything.

### Repository

**✅ Remote:** `git@github.com:Speedylo/ha_security.git`, **private**. `main` tracks
`origin/main`. `.ha_token`, `spike/.ha_config/`, the HACS cache and the telemetry snapshot stay
ignored, and no tracked file carries a credential. **If this is ever made public, remove
`v2/refs/*.pdf` first** — four third-party papers, fine to store privately and not to
redistribute.

### The task table

| # | Task | Notes |
|---|---|---|
| ~~**1**~~ | ~~**The baseline arm**~~ | ✅ **Done 2026-09-02.** Zero. See §7.12 |
| ~~**1**~~ | ~~**S8's paired baseline**~~ | ✅ **Done 2026-09-02, §7.13.** Unconfined: **canaries 2/2**, 11 attacks returned data, 5 traversals worked. Confined: **0/2**. `open("../../secrets.yaml")` returns the credential unconfined and `FileNotFoundError` confined. **The pairing also cut against the design** — `/etc/shadow`, `127.0.0.1:8123` and `example.invalid` fail in *both* arms and are not this framework's controls, which is what a single arm would have miscredited |
| ~~**1**~~ | ~~**S3's paired baseline**~~ | ✅ **Done 2026-09-02, §7.14** |
| ~~**1**~~ | ~~**S1's gc baseline**~~ | ✅ **Done 2026-09-02, §7.15** — the realism fix Younes asked for |
| ~~**1**~~ | ~~**C3 + re-verify S5/S7/F4/N3**~~ | ✅ **Done 2026-09-02, §7.16.** `selftest_c3` adds over-broad and mismatched. **Over-broad is honoured — R1, and the section says so** — but the *ceiling* it cannot raise contains exactly what Ch. 4 rated Critical: `lock.unlock`, `secrets.yaml`, cross-domain reach, all rejected at **parse** time. Mismatched: 7 behaviours, 7 denials, 7 distinct clauses. **All eight self-tests pass.** 15 of 20 requirements now discharged |
| ~~**1**~~ | ~~**Phase B — executed end-to-end**~~ | ✅ **Done 2026-09-02, §7.17.** **3 of 5 loaded and published**; §6.11.1's population of one becomes three. `thermal_comfort` is the round trip: two declared entities mirrored in, **15 derived sensors published out**, dew point physically correct. **The ceiling is 11 not 37** — 26 of 37 need a credential before any flow completes, and an unconfined baseline meets the same wall. **The baseline arm ran the same day and overturned half of it (§7.17.5): unconfined 4/5, so confinement's cost is exactly one — `powercalc`, on an undeclared component.** `scheduler` fails in **both** arms (unconfined: a frame-helper `RuntimeError`, broken on 2026.8.3 like `eufy_security`), so **the multicast finding is withdrawn as evidence that confinement costs compatibility** — and with it the inference that §9.5's egress decision should turn on discovery. Second time in Ch. 7 a baseline has corrected an attribution made without one |
| ~~**1**~~ | ~~**Phase C — performance at scale**~~ | ✅ **Done 2026-09-02, §7.19–§7.20.** Latency to 26 sandboxes (**P4 wrong** — saturation at ~4 clients, not tail queueing; N1 unaffected at 0.009% utilisation), `fsync` at **3.67 ms** with 63× headroom, and **P5 falsified** — page cache is reclaimable, so S9 bounds *retention*, not reading. PSS-by-declaration attempted and **did not resolve** (§7.20.3): non-monotonic at three sandboxes per point, no curve drawn |
| ~~**1**~~ | ~~**Wire `resources` to enforcement**~~ | ✅ **Done 2026-09-02, §7.22.** `ResourceLimits` is now the one type the manifest and the cgroup share, and `create` has no signature that accepts a limit and drops it. `cpu.max` wired; `disk_mb` added and applied as the private `/tmp`'s tmpfs `size=`; values validated at parse time; `compat.py`/`endtoend.py` take the bound from the integration's own clause. `selftest_resources.py` — **13/13**, each bound checked by a sandbox exceeding it (25% CPU cap holds at 25.1%, `ENOSPC` at `disk_mb`). All twelve pre-existing suites still pass. **S9 is ✅ against narrowed wording**: the `io` controller is *not delegated to a user manager*, so disk means space and not I/O bandwidth — §6.4.1's present-but-not-permitted distinction found a second time. F2 and S4 are now the only failing rows |
| ~~**2**~~ | ~~**The egress proxy**~~ | ✅ **Built and evaluated, 2026-09-03.** §5.8.2 scope item 2. Closes F2, S4 and T11 — the last ⛔ rows in §7.5, now both ✅ Met (§7.25). Design in `notes/decision_network_capability.md`, corrected against §7.24's measurement before any code existed: **both resolution seams** (`getaddrinfo` and `aiodns`), the `network.egress` clause now carries a **port**, a **UDP relay** for the 20% of the corpus that needs it (`udp_demand.md`), inbound **not built** (tested as unneeded). `channel.py` carries fd-passing (`selftest_fdpass`, 12/12); `egress.py` is the mediator-side broker with resolve-then-pin structural by construction; `egress_shim.py` is the sandbox side, at both seams; `udp_relay.py` serves synchronous datagram integrations and names the asyncio-`DatagramProtocol` quarter it does not (4 of 15, owed to Ch. 8). `selftest_egress_sandboxed.py` spawns **two real confined sandboxes concurrently** against real internet hosts — F2 and S4 evaluated in genuine namespaces, not as function calls, 17/17 stable across three runs. **One security bug found and fixed en route**: `EgressBroker.open` trusted `allow_private` from the sandbox's own request — a hostile integration could have granted itself T10's reach by writing one key into its request. Caught, fixed, regression-tested before evaluation ran. **18/18 self-tests pass on the Pi.** All twenty §7.5 requirements now carry a verdict |
| ~~**3**~~ | ~~**The uniform-sample corpus**~~ | ✅ **Done 2026-09-02, §7.23.** Seed 20260902, 40/40 fetched, both arms. **92% confined and 92% unconfined, identical failure sets — `failures(design) = 0` a second time**, on a corpus sharing only 2 of 40 members with the head. Predictions were committed *before* the draw (`notes/ch7_uniform_prediction.md`, commit ddff314): **P7 right, P6 wrong in sign** (the tail is *better* and cheaper — it declares median 0 components against the head's 1), **P8 wrong in both halves**. §7.9's external-validity threat is discharged, and all eight of §7.10's scheduled items are now complete or conditional |
| ~~**4**~~ | ~~**Chapter 7's read-through**~~ | ✅ **Done 2026-09-03, §7.26.** The chapter was read as one document for the first time and it found two substantive gaps, both of the same kind — things the chapter promised or possessed and did not report. **(1) §7.2 committed the security axis to being scored twice**, against Ch. 4's eighteen threats and against the closest published model's eleven, *"so that the result is comparable against an existing published model"* — and **neither scoring existed**. The results half is organised by §7.5's requirements, so closing out §7.10's schedule gave no signal that a *reporting* obligation was open. Both are now performed from evidence the chapter already held: **13 demonstrated (5 paired), 2 partial, 2 retained, 1 never evaluated**; **8 of the published model's 11 mapped, 5 clean**. **(2) §7.5 predicted that building the proxy would give T08, T10 and T11 demonstrated controls; §7.25 closed F2/S4 and scored none of them** — `selftest_egress` holds a real DNS-rebinding demonstration (the manifest permits the *name*, the broker refuses the *resolved address*) that no section reported. Also found: **T12 is the only threat in either register neither demonstrated nor declared unevaluable**, and **§4.14 states one divergence from the published model where there are three** (their T5 and T6 are unmapped too — §4.14 gains a pointer). Five smaller corrections (§7.26.6), the sharpest being **the one that looked like the report's first disagreement between measurements and is not**: twelve-of-37 against eighteen-of-37 declaring no components — recomputed from the results files, both correct, counting *set up* against *declared*. **No measured figure in the chapter was wrong.** |
| ~~**5**~~ | ~~**Chapter 8**~~ | ✅ **Written 2026-09-03**, `report/08_conclusions.md` — *Conclusions, Limitations and Future Work*, ~40k chars. Refuses to re-list §3.7/§4.11/§5.15/§7.9/§7.11 and answers the three questions no earlier chapter can. **§8.2 answers the claim against §7.7's falsifiers fixed in advance** — A, B and C all hold; **the fourth falsifier, on the evaluation rather than the artifact, fired**, and §8.2.4 reports it. **§8.3 closes §2.8's three contributions**, including the honest gap: the API-surface measurement was never re-run on the uniform corpus, so contribution 1 is half-delivered. **§8.4** — 6-of-8 predictions wrong, and the two that held were the two *about the design*; plus the methodological result now stated with its **explanation and four transferable mechanisms**. **§8.5** the 52-vs-2 / 53-vs-0 finding. **§8.6** twelve artifact limits, six evaluation limits, structural and inherited kept separate. **§8.7 future work priced and ordered** — ten items as written, **twelve after the 2026-09-04 fix**; cheapest first-value is still *one run of an existing script*. **§8.8** the single upstream ask (R3), now measured rather than reasoned about |
| ~~**4b**~~ | ~~**Real integration, confined, against a real API**~~ | ✅ **Done 2026-09-03, §7.27.** Not scheduled — run because §7.25.5 said in its own words that a real integration against a real API was a different measurement it did not substitute for. `nordpool` is the corpus's only member that both needs a network and configures without a credential (26 of 37 cannot). Three arms: unconfined / confined+declared / confined+clause removed, the third being what makes the second evidence. **The first run failed, and that is the result**: `async_get_clientsession(hass)` — what the platform tells an author to call — builds its resolver by instantiating Zeroconf, which joins the mDNS group, and a fresh netns `lo` has no `IFF_MULTICAST`. **A real integration could not construct an HTTP client inside the sandbox at all**, so the egress design had been unusable for the 41% it was built to serve, behind a suite that all passed. §7.25's subject used a bare `aiohttp.ClientSession()` and skipped the very helper that breaks it. Fixed in two measured steps (`IFF_MULTICAST`, then a `224.0.0.0/4` route to `lo` — zeroconf joins via `INADDR_ANY` and the kernel picks the interface from the routing table); the grant is **vacuous**, the route's device is `lo`. Result: **0.026, the same price confined as unconfined, in the same minute**, 3 grants logged as `dataportal-api.nordpoolgroup.com:443` with both chains verifying; clause removed → 3 denials and `unavailable`. **11/11.** Also re-establishes §7.17.5's withdrawn finding on exactly the evidence it specified, and fixes `audit.py` recording an egress target as host without port. **18/18 suites re-run after both changes.** |
| ~~**6**~~ | ~~**Front matter, abstract, bibliography**~~ | ✅ **Done 2026-09-04.** Title page, abstract (three paragraphs against §8.9), declaration and AI-use content, generated contents page, figure list, abbreviations, artifact index and an *Outstanding* section. **The bibliography was not clerical**: Ch. 1 and Ch. 2 carried independent `[n]` schemes that collided, Ch. 5 was citing Ch. 1's private numbering, ISO 31000 / STRIDE / OWASP Threat Dragon / RFC 1918 were cited by name and listed nowhere, and one listed source was never cited. **28 references, unified by first appearance; 28/28 resolve in both directions** |
| ~~**7**~~ | ~~**Stage 5**~~ | ✅ **Complete 2026-09-06. Three passes, eighteen findings, not one of them a measured figure.** Pass 1: Ch. 1–6 and 8 in full, Ch. 7 verified numerically — eleven findings. Pass 2: Ch. 7's prose — **one finding, the most serious in the report** (§7.28, C1). Pass 3: §7.19–§7.25's prose, the completion-claim sweep, and every headline recomputed from raw result files — **five findings, all fixed**, the sharpest being §7.23.1's two populations (F3). **Three times across passes 2 and 3 a recount of mine was wrong and the report was right**, which is the reason the method says a disagreement is a question until the field being counted is confirmed |

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

**✅ All obligations from §5.14's traceability check and from Chapters 5–6 are now discharged.**
This table said otherwise until 2026-09-04; Chapter 7 had closed them and this file was not
repointed. **Chapter 7 carries the authoritative register** — §7.8 lists eleven inherited
obligations, and **§7.21.3 is the correction that matters**: five of them had been marked
discharged "in §7.4.1" or "§7.4.3", which are *methodology* sections, and an obligation is not
discharged by a section that promises to discharge it. Read §7.21.3, not this table.

| Owed by | What | Where it was actually discharged |
|---|---|---|
| ~~Ch. 6~~ | ~~A surface where the user encounters the declaration~~ | ✅ **§6.7**, 2026-08-25 — `confine/describe.py`, four states, denials shown at the same weight as grants |
| ~~Ch. 7~~ | ~~Never repeat §4.10's "filesystem isolation *to declared resources*"~~ | ❌ **Withdrawn 2026-08-25 (§6.6.6).** The obligation rested on a §5.14.4 claim that contradicts §5.10.3; §4.10's phrase is accurate |
| ~~Ch. 7~~ | ~~State S9's boot-time precondition when evaluating it~~ | ✅ **§7.4.3, and honoured at §7.5's S9 row** — the Pi 5's firmware *prepends* `cgroup_disable=memory`, stated wherever S9 is evaluated |
| ~~Ch. 7~~ | ~~Measure what `resources.memory_mb` costs a *legitimate* integration~~ | ✅ **§7.20.2 — and the concern is withdrawn.** P5 falsified: page cache is reclaimable, so S9 bounds *retention*, not reading |
| ~~Ch. 8 / code~~ | ~~Wire `resources` to enforcement, and settle disk~~ | ✅ **§7.22.** `ResourceLimits` is the one type manifest and cgroup share; `cpu.max` wired, `disk_mb` applied as the private `/tmp`'s tmpfs `size=`; 13/13. **S9 narrowed on evidence**: `io` is not delegated to a user manager, so disk means space, not bandwidth (§8.6.3 #4) |
| ~~Ch. 8~~ | ~~Extend the derived-manifest analysis from packages to components~~ | ✅ **§8.7 #3**, priced. The component closure is the *easier* case — a name in the platform's own source, so exact rather than approximate |
| ~~Ch. 8~~ | ~~The `aiofiles` finding, and the objection it answers~~ | ✅ **§8.6.3 #13 and the paragraph beneath it** — three independent occasions, and `package_constraints.txt`'s own comment as corroboration rather than inference |
| ~~Ch. 8~~ | ~~Record that the strongest control produces no audit trail~~ | ✅ **§8.6.3 #6** — "the audit trail is weakest exactly where the control is strongest", named the sharpest form of R4 in the report |
| ~~Ch. 7~~ | ~~Decide whether `fsync` per decision is affordable~~ | ✅ **§7.20.1 — yes.** 3.67 ms, 63× headroom; `audit.py` already called it, so the question was never whether to pay |
| ~~Ch. 7~~ | ~~Negative cases must assert on **why**, not that~~ | ✅ **§7.4.2**, and exercised at §7.16 — mismatched cases give 7 behaviours, 7 denials, **7 distinct clauses** |
| ~~Ch. 7~~ | ~~Measure mediation latency at realistic sandbox counts~~ | ✅ **§7.19** to 26 sandboxes — and **P4 was wrong**: saturation at ~4 clients, not tail queueing |
| ~~Ch. 7~~ | ~~Check every compatibility failure against the minimal instance first~~ | ✅ **§7.17.4**, where **three of five were harness faults** — the obligation paid for itself |
| ~~Ch. 7~~ | ~~An absence is not evidence until the grant is shown to have arrived~~ | ✅ **§7.4.2** (§6.4.5's obligation, which this table had omitted entirely) |
| ~~Ch. 7~~ | ~~Re-run on a uniform corpus before reporting coverage~~ | ✅ **§7.23** — 40/40, both arms, 92%/92%. **Half-owed still**: for the API surface it was never re-run (§8.3, §8.7 #5) |
| ~~Ch. 7~~ | ~~N2: report imports-clean and executed-end-to-end separately, always~~ | ✅ **§7.12 and §7.17** |

**One is half-owed and the report says so**: the uniform-corpus re-run was performed for
*compatibility* and never for the *API surface*, so §2.8's contribution 1 is half-delivered. That
is §8.3's own admission and §8.7 #6's one-run item — the cheapest outstanding thing in the report.

**⚠ One conflict is open and deliberately unresolved.** `01_PLAN.md` §6 says the actuator PoC
is cut first if G3 fires. §5.8.2 derived scope from Chapter 3's verification column and found
that cutting the actuator leaves **S5 unverifiable** and T05 — the register's joint-highest
risk — with no demonstrated control. The plan's cut list predates the scope derivation.
Recommendation in `notes/ch5_working_notes.md`: cut coverage-widening first instead. **This is
Younes's call at G3**, and `01_PLAN.md` has deliberately not been edited.

**Still owed, and the cheapest thing in the report (§8.7 #6):** the API-surface measurement was
run on the top 144 community integrations *by install count*. That describes what most
installations run, not what most integrations do. §7.23 ran the uniform corpus for
**compatibility** and answered that question; **the API-surface parser was never re-run on it**, so
§2.8's contribution 1 stays half-delivered and §8.3 says so. The corpus is already fetched and
`figures/api_surface.py` already exists — only the selection changes. **One run.**

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

## The four things most worth remembering

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
   criteria invented here. **§7.2 promised that scoring on 2026-09-02 and §7.12–§7.25 never
   performed it** — the results half is organised by §7.5's requirements, so closing out the
   measurement schedule gave no signal that a *reporting* obligation was open. §7.26.4 performs
   it: **eight of their eleven mapped, five scoring cleanly**, and §4.14 states one divergence
   from their model where there are three. Do not repeat the earlier claim without §7.26.

4. **Running real code finds what nothing else does, and this is the project's own evidence
   for it.** Five mechanisms caught errors here — a paired baseline (three misattributions
   stopped, all of which would have charged the design *more* than it deserved), two
   instruments bounding each other, a self-test that passes when the surprising thing is true,
   recomputing a figure from its source rather than re-reading the sentence, and **running one
   unmodified real integration**. Only the last found a defect that made the egress design
   unusable for its target population, and it had sat behind eighteen passing suites (§7.27).
   The reason is structural and worth being able to say aloud: **the other four are all written
   out of the same assumptions as the thing they test.** §8.4.2 is the written form.

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
