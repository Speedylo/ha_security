# §12 Results and Interpretation — plan for approval

**Written 2026-10-08.** Budget 3,500 words, about 10 pages (`rewrite_plan_outline_mapping.md` §0).
Style: third person, each paragraph topic sentence → evidence → analysis → link, IEEE citations
integrated (§0's style paragraph). The topic sentences below are drafts of the real ones; the prose is
written only after this plan is approved.

## The organising decision

The budget table named four axes (compatibility, security, performance, verification). The report
itself already frames its claim more precisely, and §12 should follow that frame: one claim
("unmodified, pre-existing integrations can be confined at a cost worth paying"), three assertions
(A effective, B compatible, C affordable), each with a falsifier fixed before any measurement, and a
fourth falsifier about the evaluation itself. Security is therefore A, compatibility B, performance C,
and the verification campaign is the answer to the fourth falsifier. Each subsection opens by quoting
its falsifier and closes by saying whether it fired. This keeps §12 answerable to §11's method and
lets §15 conclude by referring to four verdicts instead of restating evidence.

Every figure below is quoted as it stands at tag `verify-2026-10-tests`. Timing figures use the
median of five passes with the range across passes (`final_f45_stats.txt`). The history of a
correction appears only where the correction is itself the result, as in §12.4.

## Opening (≈150 words)

> This section tests the project's central claim against four falsifiers that were recorded before
> any measurement was made.

States the claim, the three assertions and the fourth falsifier, then the reading rule: every security
and compatibility result is a difference between a confined and an unconfined arm on the same host and
release. Links to §12.1.

## 12.1 Assertion A — confinement is effective (≈850 words)

**Table 12.1 — Each attack, unconfined against confined.**

| Attack | Unconfined | Confined |
|---|---|---|
| Garbage-collector walk to a live credential [Corno & Mannella] | reached it 7 ways | 8,942 objects, all its own; the same token live in the mediator, 7 references deep |
| 2021 file-theft canaries | 2 of 2 recovered | 0 of 2 (`FileNotFoundError`) |
| Another process's environment | leaked | empty |
| Undeclared entity states (occupancy and presence) | 36 of 36 (20 of 20) | 1 of 36 (0 of 20) |

Paragraph topic sentences:
1. *Confinement removed every capability the published attacks depend on, and each removal is measured
   against an unconfined arm rather than asserted.* Evidence: Table 12.1. Analysis: without the
   unconfined arm, an absence is indistinguishable from a broken test. Link: the first row matters most.
2. *The garbage-collector technique published by Corno and Mannella [n] is the result the architecture
   was designed to defeat.* Evidence: seven paths unconfined; none confined while the credential is
   confirmed live in the mediator. Analysis: this result rules out every in-process design, which is
   why the sandbox boundary exists at all.
3. *Against the project's own threat register, sixteen of nineteen threats are demonstrated, six of
   them against an unconfined arm.* Evidence: one partial (T16), two retained by a decision recorded
   in advance; against the external register, eight of Corno and Mannella's eleven mapped, five
   cleanly. Analysis: no aggregate "threats controlled" figure is reported, by the rule set in §11.
   Full register in Appendix C.
4. *The security result is bounded by who attacked the framework.* Evidence: every adversary was
   written by the author; the independent adversary planned for verification step 4.6 was not run.
   Analysis: A is therefore shown against published techniques, and suggested, not shown, against an
   unknown attacker. Link to B.

**Figure:** none here. A threat-status figure would duplicate Appendix C; the table carries the result.

## 12.2 Assertion B — confinement is compatible (≈1,000 words)

**Figure 12.1 — Import-level compatibility, confined and unconfined, on both corpora** (grouped bars
by sandbox profile, head-weighted corpus of 37 and uniform corpus of 40, the two arms side by side).
Shows 84% = 84% and 92% = 92%. Generated from source in `figures/`, as Figures 4.1 and 5.1 are.

**Table 12.2 — The thirteen integrations executed end to end** (name, how it reaches its service
— cloud API, LAN device, datagram, OAuth — HTTP stack, result in each arm). Thirteen per the corrected
abstract (finding F01); the names are taken from §7.17, §7.27, §7.31, §7.34 and §7.40–§7.42 when
written.

Paragraph topic sentences:
1. *Confinement costs nothing in import-level compatibility on either corpus.* Evidence: Figure 12.1;
   identical failure sets, four of six error strings identical byte for byte; 77 measurements across 75
   integrations. Analysis: 84% describes the corpus and the platform release, not confinement; the
   result is the difference, and the difference is zero.
2. *An integration that imports has not yet been shown to work, so thirteen were executed end to end.*
   Evidence: Table 12.2; all thirteen load and behave the same in both arms. Analysis: a named set, not
   a rate, because 26 of 37 integrations need a credential before setup can finish, and the
   unconfined arm meets the same wall.
3. *Running real integrations exposed defects that purpose-built test subjects had concealed.*
   Evidence: the mDNS failure in `async_get_clientsession` (the sample paragraph Younes approved);
   `powercalc`'s apparent cost traced to a fault in the test instance, not to confinement. Analysis:
   a test subject is evidence only for the code paths it exercises.
4. *The corpus's need for the network splits evenly, and the two halves need different capabilities.*
   Evidence: 30 of 37 (81%) declare network access; 41% reach cloud services, 41% reach devices on
   the home network, the second behind a separate explicit permission. Analysis: the egress proxy made
   41% workable directly, not 81%; this is a property of the design, not a defect. Link to cost.

## 12.3 Assertion C — confinement is affordable (≈700 words)

**Table 12.3 — Cost of confinement on the Raspberry Pi 5 (4 GB)**, median of five passes and range:

| Quantity | Median | Range across passes | Compared with |
|---|---|---|---|
| Mediation latency, one sandbox | 43.0 µs | 41.2–43.4 µs | — |
| Mediation latency, 26 sandboxes | ≈800 µs | 794–814 µs | — |
| Durable audit record (`fsync`) | 3.67 ms | 3.62–3.69 ms | — |
| Mediator capacity, audit write included | 269 decisions/s | — | demand 4.33 req/s → 62× headroom |
| Memory, marginal per sandbox | 124 MB | 122–134 MB | — |
| Sandbox budget on the device | 26 | — | mean 4.02 integrations per installation |
| One delivered state change (mediator) | 10.9 µs | 11.3–11.5 µs | — |
| A change in Home Assistant to the sandbox | 0.71 ms | 0.71–0.93 ms | — |
| A user's command to the integration | 11–16 ms | 11.1–15.7 ms | — |
| Flood start to cut-off | 0.81 s | 0.807–0.818 s | — |

(Exact rows and wording re-derived from `final_f45_stats.txt` at writing; the two figures stated as
ranges are F43 and F44.)

**Figure 12.2 — Mediation latency against the number of sandboxes**: median with p99 whisker per count,
throughput on a second panel, flat from 2 to 26 sandboxes.

**Figure 12.3 — Memory budget on the 4 GB device**: per-sandbox memory stacked to the 26-sandbox
budget, with the 4.02-integration mean marked.

Paragraph topic sentences:
1. *The mediator handles sixty-two times the realistic demand, and the durable audit write, not the
   mediation itself, sets that limit.* Evidence: 3.67 ms against 43 µs; 269 decisions/s against
   4.33 req/s. Analysis: comfortably but finitely clear of demand.
2. *Latency grows with the number of sandboxes because the mediator serves them in turn, and it remains
   below a millisecond at the full budget.* Evidence: Figure 12.2. Analysis: the 43 µs figure replaces
   the 31.5 µs first published; the increase was traced to two features the design needs (descriptor
   passing for egress, the push loop), so the figure was corrected, not the code.
3. *Memory allows twenty-six sandboxes on the reference device, about six times the mean number of
   community integrations an installation runs.* Evidence: Figure 12.3. Analysis: the mean is the only
   statistic the public telemetry supports; installations in the tail may exceed it.
4. *The paths a household experiences are measured in milliseconds.* Evidence: push 0.71 ms, command
   11–16 ms, flood cut-off 0.81 s. Analysis: C holds for push delivery as well as request/response;
   a busy home's real rate of change remains unmeasured. Link to §12.4.

## 12.4 The evaluation tested against itself (≈650 words)

**Table 12.4 — What each verification method found** (method, findings, the most serious, outcome):
re-measurement (F17: latency), re-derivation of every headline number (F23: a figure with no source),
fault injection (F28–F31: a full disk, a supervisor killed), security review (F34 Critical: the
sandbox shared the supervisor's terminal; F33: malformed requests crashed the mediator), mutation
testing (M16, M18c, M31 survived until tests were added), acceptance by hand (F42). All resolved except
F18.

**Figure 12.4 — The claim register** (153 claims: 119 verified, 27 qualified, 5 argued, 2 withdrawn),
a single horizontal bar, with findings by severity beside it (1 Critical, 12 Major, the rest Minor or
notes, counts re-derived from the findings log at writing).

Paragraph topic sentences:
1. *The fourth falsifier concerned the evaluation, and it fired twice before the verification campaign
   began.* Evidence: requirement C1 reported as verified before any count existed; the security
   scoring §11 promised was missing until a read-through found it. Analysis: both were found by
   reading the report as one document, not by the tests.
2. *Before the engineering cut-off, every claim in the report was registered with a pass criterion
   fixed before it was re-run.* Evidence: Figure 12.4. Analysis: 27 claims hold only in a narrower form
   and 2 were withdrawn; the report states them in that form.
3. *The campaign found fifty-three findings, one of them critical, and none overturned A, B or C.*
   Evidence: Table 12.4. Analysis: the critical finding was an isolation defect fixed in code and
   retested; the latency correction changed a number, not a verdict.
4. *A test suite that cannot fail is not evidence, and deliberate defects showed where the suites
   could not fail.* Evidence: 40 mutants of the cut-off code, 39 detected, one equivalent; three
   survived first and each produced a new test. Link to §13, where this becomes a lesson.

## 12.5 Interpretation (≈300 words)

> *The central claim holds within stated bounds: confinement defeats the published attacks, costs
> nothing in import-level compatibility on two corpora, and leaves the mediator sixty-two times clear of
> realistic demand.*

States the bounds in one paragraph each (import level against a named executed set; a purpose-built
adversary; the mean as the only demand statistic) and hands the limits to §14.

## What leaves §12, compared with the 2026-09-08 draft

| Draft section | Goes to |
|---|---|
| 12.4 C1 counted | §3 verdict table and Appendix B |
| 12.6 "The result that arrived last" | Folded into 12.2, paragraph 3 |
| 12.7 What was not done | §14 Future work |
| 12.8 A measurement that did not resolve | Appendix D note, one sentence |
| 12.9 The predictions, scored | §6.2 Underlying assumptions |
| 12.10 The finding nobody was looking for (50 components loaded for nothing) | §14, one paragraph |

## To check while writing

1. §8.4.2 says every correction was to a sentence, never to a measurement. F17 corrected a measured
   figure (the code changed after it was measured). The claim must be restated before §12.4 or §13 uses it.
2. The citation numbers: Corno and Mannella, the 2021 disclosure, the HA developer documentation for
   `async_get_clientsession`. Assigned when the IEEE list is rebuilt.
3. Table 12.2's thirteen names, and whether all thirteen ran in both arms.
4. Appendix F's contents follow Table 12.4 and Figure 12.4, so it is written in the same week.

## Progress

- **2026-10-08: §12 opening and §12.1 written** (`submission/12_results.md`; the old draft's §12.2–12.10
  stay below a marker until rebuilt). §12.1 is about 1,070 words of prose plus Table 12.1, over the
  850 budgeted; the overrun is recovered from §12.5 or by a cut at the read-through.
  Facts checked against §7.13.2–3, §7.14.2, §7.15.3, §7.26.3–4, §7.44.4 (F38's restatement),
  §7.45.6 and §7.45.10; Corno and Mannella's technique against §2.4.1's quotation of [9].
- **Owed by §11, because §12 relies on it:** the three assertions and their falsifiers, the paired
  design, and the rule that no aggregate "threats controlled" figure is reported.
- **2026-10-08: §12.2 written** (about 1,000 words of prose, Tables 12.2 and 12.3). Table numbers shift
  by one from the plan: 12.2 is the headline compatibility table, 12.3 the thirteen, so §12.3's cost
  table is 12.4 and §12.4's methods table 12.5. Facts checked against §7.12.2, §7.23.2, §7.27,
  §7.31.5–6, §7.34.1, §7.40.3, §7.41.4, §7.42.2, §8.2.2 and the abstract. **New reference [32]:**
  Home Assistant Developer Docs, Integration Quality Scale rule "The integration dependency supports
  passing in a websession", https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/inject-websession
  (opened 2026-10-08; recommends `async_get_clientsession(hass)`). Add it when the IEEE list is rebuilt.
  Plan's "all thirteen behave the same in both arms" was too strong and is not used: all thirteen load
  confined; cloud outputs matched (three identical, two within a live value's movement).
- **2026-10-08, Younes's review of §12.2:** the date for the home-network TCP path removed ("built later
  in the project"). Table 12.3 rebuilt one row per integration (what it does, what the run exercised,
  result), because the first version reported the five platform-only integrations as "load", which is
  import-level evidence. Stated in the text: nine of thirteen produced a checkable value; `watchman`,
  `adaptive_lighting`, `powercalc` show setup and publication only; `scheduler` setup only (§7.17.2–3,
  §7.31.6). Rule for the rest of §12: an end-to-end claim says what was exercised, not only that it loaded.
- **2026-10-08: §12.3 written** (about 825 words of prose, Table 12.4). The budget is a range by
  component count (§7.35.3: 43 / 26 / 17 sandboxes for none / `http`+`websocket_api` / all ten in 60% of
  the device's memory; capacities use the Pi's actual MemTotal, so 0.6 × 4,096 MB does not reproduce them
  exactly), not the single 26 in the plan. Five-pass ranges from `final_f45_stats.txt`. Figures 12.2 and
  12.3 not drawn (Younes: no figures now). Facts checked against §5.6.3, §5.8.1, §6.3.2, §7.19.3, §7.35,
  §7.36, §7.44.4, §7.45.1, F43, F44.
- **2026-10-08: §12.4 written** (about 690 words of prose, Table 12.5). Findings recounted from the log:
  53 = 1 Critical (F34), 12 Major (F11 F17 F18 F21 F23 F28 F30 F32 F33 F36 F42 F45: six report statements,
  four failure behaviours, two reproducibility), 4 Minor-to-Major (F03 F08 F31 F35), 32 Minor, 3 Notes
  (F12 F51 F53), 1 Re-measure (F05). §8.4.2's "never a measurement" restated in the text (F17, F23), which
  closes check item 1. Figure 12.4 (register bar) not drawn: the counts are in prose.
- **2026-10-08: §12.5 written; §12 complete in draft.** About 3,950 words of prose against 3,500, plus
  Tables 12.1–12.5; the ~450-word overrun is cut at the week-6 read-through. §12.5 states that the
  evaluation's falsifier fired twice during development and that the campaign found six further wrong or
  unsupported statements (consistent with §12.4). The old 2026-09-08 draft stays below the marker as a
  record until §3, §6 and §14 have absorbed what it held; then it is deleted.

**Owed (2026-10-15, Younes):** once the old 2026-09-08 text below line 134 of `12_results.md` is
removed, §12 may gain contribution 1's precise numbers (report §7.33 table: config_entries 94.4/92.5,
services 64.6/37.5, bus 48.6/17.5, states 41.0/35.0, others' services 22.2/12.5; own entry 90% vs all
entries 22.5%), pointing back to §9.3's paragraph.

**2026-10-15: old 2026-09-08 tail deleted; contribution 1's numbers added (Younes).**
- Tail's destinations confirmed: 12.4 → §3 C1 row; 12.6 → §12.2; 12.7 → §14; 12.9 → §6.2.
  12.8 (non-monotonic depth series) superseded: resolved 2026-10-03 (56.5/92.3/111.6/135.6 MB, §10, §12.3).
  12.10 ("52 components vs 2") dropped: pre-rerun figure, not rechecked (as in §4), and its argument for a
  check inside the loader contradicts §9. 12.2.2's profile decision dropped as design history.
- New Table 12.4 (API surface, 144 most-installed vs 40 random; report §7.33 /
  `figures/api_surface_uniform.json`) at the end of §12.2, with one paragraph pointing to §9.3.
  Tables renumbered: costs 12.4 → 12.5, verification 12.5 → 12.6 (Appendix B's two references updated).
- Stale in approved §12.2's closing paragraph, fixed as §12.5 was: "thirteen …, nine of which produced
  checkable values" → "each of which produced a value checked against its own code".
- §12 now ~4,280 prose words vs 3,500 (trim at week 6).
