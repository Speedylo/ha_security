# Appendices

## Appendix A — Open-source repository and artifact index

| | |
|---|---|
| Framework | `v2/framework/confine/` — standard library plus `ctypes`, no third-party dependencies, no override flag |
| Self-tests | **19 suites**, all passing on the test hardware. `selftest_*.py` in the same directory |
| Experiments | `v2/experiments/` — each with its script, its raw result file and a readable write-up |
| Figures | `v2/figures/` — each figure and its threat model generated from one source, so they cannot drift |
| Corpora | `hacs_corpus_manifest.json` — both corpora, redrawable; the uniform draw records its seed (20260902) |
| Working notes | `v2/notes/` — decision records, evidence write-ups and the pre-registered predictions |
| Test hardware | Raspberry Pi 5, 4 GB, Raspberry Pi OS trixie. **Every measurement in this report was taken on it** |

*[Repository URL and access statement to be supplied on submission.]*

---

## Appendix B — Requirements register

*[To be lifted verbatim from the working report: all twenty requirements with their derivation, their
verification criterion as frozen before measurement, the verdict, and the evidence pointer for each.
This is the table §3.6 summarises.]*

**Structure of each row:** ID · statement · derivation (the §2 or §7 finding it traces to) ·
verification criterion · verdict · evidence.

---

## Appendix C — Threat register

*[To be lifted verbatim: eighteen threats T01–T18 with STRIDE category, trust boundary, impact,
likelihood, inherent rating, treatment option, the control applied, the requirement it maps to, and
the mapping to the closest published model. Followed by the seven residual risks R1–R7 with their
retention rationale and residual rating.]*

**Also to include:** the impact and likelihood scales, with the note that they are **ordinal, not
cardinal** — they order risks for treatment priority, and the product of two ordinal scales is not
a quantity and is not treated as one.

---

## Appendix D — Full compatibility results

*[To be lifted verbatim: for each of the 77 integrations across both corpora, in both arms — the
outcome on the ladder (not found → import failed → imports clean → platform import failed →
platforms clean), the error string where one occurred, the declared components and packages, and
the install count.]*

**The point of the appendix is the column comparison**: the confined and unconfined outcome for
each integration side by side, so a reader can verify the set difference is empty in both
directions rather than taking §12.2's zero on trust.

---

## Appendix E — Self-test suites

*[To be lifted: the 19 suites, what each asserts, and its pass count.]*

Two are worth flagging to a reader scanning the list. **One suite passes when a surprising thing is
true** — connected UDP sockets were assumed peer-pinned and are not, and the test passes when a
datagram is redirectable, so a future kernel change fails the suite rather than silently
invalidating the design's foundation. **One exists because an instrument lied**: the integrity
checker's first version reported a clean zero by comparing the baseline tree against itself, and
the self-test written for that failure mode is what caught it.

---

## Appendix F — Verification findings and the claim register

This appendix records the outcome of the verification campaign that §12.4 summarises. Before the engineering cut-off, every claim in the report was registered with its evidence and a pass criterion fixed before the claim was re-tested, and every measurement was repeated on one frozen version of the code. Table F.1 gives the register's outcome, and Table F.2 lists every finding the campaign recorded, one line each, so that a reader can check §12.4's counts against the findings themselves. The full register and the detailed log, with the evidence for each entry, are in the repository listed in Appendix A.

**Table F.1 — Claim register outcome by tier**

| Tier | What it holds | Rows | Verified | Qualified | Argued | Withdrawn |
|---|---|---|---|---|---|---|
| A | The abstract, the 20 requirements, the 19 threat verdicts, the 11 verdicts against the published threat model, the central claim and the contributions | 91 | 72 | 15 | 4 | 0 |
| B | One row per measurement, each with its criterion kind declared before re-running | 30 | 24 | 5 | 0 | 1 |
| C | The remaining claims in the text, as 16 mechanism groups and 16 single claims | 32 | 23 | 7 | 1 | 1 |
| | **Total** | **153** | **119** | **27** | **5** | **2** |

A claim is *Verified* when it held as stated on the frozen code, *Qualified* when it holds only in a narrower form, which the report now states, *Argued* when it rests on reasoning rather than measurement, and *Withdrawn* when the evidence did not support it.

**Table F.2 — Findings log.** The *method* column names the verification method that raised the finding; severities were assigned when each finding was recorded.

| ID | Method | Severity | Finding | Resolution |
|---|---|---|---|---|
| F01 | Claim register | Minor | The abstract counted ten integrations tested end to end; thirteen had been | Corrected to thirteen |
| F02 | Claim register | Minor | "Within a millisecond" held for the push path's median, not its worst case | Stated as the median (see F23) |
| F03 | Claim register | Minor to Major | Refusals without a manifest clause could be constructed, although none had been recorded | Fixed in code; every refusal now names its clause |
| F04 | Claim register | Minor | A row of the comparison with the published threat model predated threat T19 | Row updated |
| F05 | Claim register | Re-measure | The adversary pair and mediation latency had last been measured before later code changes | Re-measured in three passes; the adversary result held, the latency became F17 |
| F06 | Claim register | Minor | The tally of self-test suites stopped short of the number on disk | Tally corrected |
| F07 | Claim register | Minor | Nine results sections were named by no experiment's documentation | Every results section mapped to its experiment, checked by script |
| F08 | Claim register | Minor to Major | The audit identity hashed the declared dependency requirements rather than the installed versions | Fixed in code; the identity records resolved versions |
| F09 | Claim register | Minor | Three versions of the per-cycle mediation cost appeared in the text | All three explained against the current figure (0.43 ms) |
| F10 | Regression | Minor | A self-test check on the home directory passed only because the test's files lay outside it | Test rebuilt with a realistic layout and a control |
| F11 | Regression | Major | An integration could read the host paths of its mounts, revealing the user name and configuration location, though no file content | Retained as a residual risk, rated Medium, with a deployment requirement |
| F12 | Regression | Note | Baseline runs stopped publishing one of the platform's own entities | No claim rests on it; cause not established |
| F13 | Regression | Minor | Dependency installs were unpinned, so a re-run tested different versions | Installs resolve against a fixed date, recorded per run |
| F14 | Re-measurement | Minor | Result files did not record the command and options that produced them | A provenance record is written beside every result |
| F15 | Re-measurement | Minor | One dependency's share of network use moved outside its criterion (11% against 17 ± 5%) | Reported as a range; the design conclusion unchanged |
| F16 | Re-measurement | Minor | The sample behind the ecosystem figures was not kept, so could not be re-run | Sample rebuilt, pinned and shown equal to the original |
| F17 | Re-measurement | Major | Mediation latency was 43 µs on the frozen code, not the 31.5 µs published | Corrected; the increase traced to two features the design needs |
| F18 | Reproduction | Major | No guide existed for building the test environment from a clean checkout | Guide written and followed from a fresh clone; **open** until followed on a freshly imaged card |
| F19 | Reproduction | Minor | The suite runner tested a fixed directory rather than the checkout it was run from | Runner tests its own checkout and records the path |
| F20 | Reproduction | Minor | The code the report describes had not been pushed to the remote repository | Pushed after a credential scan |
| F21 | Reproduction | Major | Neither test corpus recorded the commits it was drawn at, so neither could be rebuilt | Both pinned by exact content match and rebuilt identically |
| F22 | Mutation | Minor | A mutant accepting a command's answer from any channel survived every suite | Test added; the mutant is killed |
| F23 | Re-derivation | Major | The push path's stated worst case (1.57 ms) matched no recorded run | Corrected to the recorded range, 1.49–2.91 ms |
| F24 | Re-derivation | Minor | "77 integrations" counted measurements; 75 distinct integrations were measured | Restated as 75 integrations, 77 measurements |
| F25 | Re-derivation | Minor | Suite counts mixed two counting conventions | One convention applied throughout |
| F26 | Re-derivation | Minor | One table gave two different throughput figures | Made consistent |
| F27 | Re-derivation | Minor | The count of integrations needing a credential had no committed script | Survey committed as a script that reproduces it |
| F28 | Fault injection | Major | A failed audit write on a full disk left every later record unverifiable | Fixed in code; tested on a real full disk |
| F29 | Fault injection | Minor | When the platform went away, the supervisor stopped and never restarted the integration | Fixed in code; the integration restarts when the platform returns |
| F30 | Fault injection | Major | A forcibly killed supervisor left its sandbox running without a mediator | Fixed in code; orphans end and are cleared on restart |
| F31 | Fault injection | Minor to Major | A restarted mediator broke the audit file's hash chain | Fixed in code; one audit file per start |
| F32 | Security review | Major | A manifest could raise its own resource bound, contrary to the stated design | Fixed in code; declarations can only tighten |
| F33 | Security review | Major | 26 kinds of malformed request could stop the mediator for every sandbox | Fixed in code; they become recorded refusals |
| F34 | Security review | **Critical** | Each sandbox shared the supervisor's terminal, through which it could have injected input; found by reading, not exploited | Fixed in code; each sandbox has its own session and no terminal |
| F35 | Security review | Minor to Major | Review of the fault-injection fixes found ten further defects | All ten fixed, eight with a test that failed first |
| F36 | Evidence integrity | Major | Version history could not show that the first baseline's criteria were written before its run | Claim qualified; all 19 later predictions shown to precede their results |
| F37 | Evidence integrity | Minor | The raw snapshot behind the ecosystem figures was not committed | Committed with its retrieval date |
| F38 | Document consistency | Minor | One threat was still counted as partly demonstrated after it had been closed | Restated as demonstrated |
| F39 | Negative controls | Minor | No test exercised the manifest's write check | Control added; fails under the matching mutant |
| F40 | Citation check | Minor | Two audit standards were cited as preferring to stop activity; both leave the choice open | Citation corrected |
| F41 | Citation check | Minor | Five bibliographic entries were incomplete or misnamed | All entries checked against their sources |
| F42 | Acceptance | Major | Restarting the platform from its own interface stopped it permanently | Fixed in code; the platform restarts in about 6 s |
| F43 | Re-measurement | Minor | Marginal memory per sandbox straddled its criterion across four runs | Reported as a range, 126–134 MB |
| F44 | Re-measurement | Minor | The command latency fell 27% below its stated figure | Reported as a range, 11–16 ms |
| F45 | Claim register | Major | The report said the platform had no restricted token; it has a permission model the mediator could use | Mediator moved to a non-administrator user; the risk re-rated |
| F46 | Regression | Minor | The push latency rose 31% in one run, within the run-to-run spread | Reported as a range, 0.5–0.9 ms |
| F47 | Mutation | Minor | A mutant letting any user designate itself the mediator survived every suite | Test added; the mutant is killed |
| F48 | Mutation | Minor | No suite exercised the supervisor, and the demonstration script reported success whatever happened | New suite; scripts now fail on a wrong value |
| F49 | Mutation | Minor | Security-relevant branches (the channel's bounds on hostile frames, among others) were executed by no suite | A check for each; 13 of 14 mutants killed, the 14th equivalent |
| F50 | Mutation | Minor | Three declarable operations were permitted and recorded but performed no action | Stated as designed and not built |
| F51 | Mutation | Note | Effects of the measuring instruments themselves, none a finding about the framework | Recorded |
| F52 | Mutation | Minor | A protocol-error record misstated the number of descriptors refused | Fixed in code |
| F53 | Mutation | Note | A command sent in the first second after a sandbox starts is recorded and has no effect | Stated as a limitation (§14) |
| F54 | Functional retest | Major | A confined service call lost a target given as a list, so the command reached the platform aimed at nothing, and no decision record named the device of any service call | Fixed in code after the cut-off, with a test that failed first |
| F55 | Functional retest | Minor | The unconfined arm was said to set up `default_config`, which fails there; the component the claim relied on loads through one of its dependencies | Wording corrected; the attribution stands |
| F56 | Functional retest | Minor | The unconfined arm could not start its web server beside the test instance (A), and reported only that the integration had not loaded | The arm now names the cause; unconfined runs are made with (A) stopped |
| F57 | Writing Section 9 | Major | No approval was required before a sandbox started: a derived manifest was used unconfirmed, an author-declared one unseen, and an update that widened its own grant received it | Fixed in code after the cut-off, with a test that failed first: a sandbox registers only if an approval matches its current code and its loaded grant |
| F58 | Writing Section 9 | Minor–Major | Internet egress accepted the shared address space 100.64.0.0/10, used by carrier-grade NAT and Tailscale, so a granted name resolving into it would have been connected to | Fixed in code after the cut-off, with a test that failed first |

Of the 58 findings, one is Critical, 14 Major, 5 between Minor and Major, 34 Minor, 3 notes and 1 a request to re-measure. F01–F53 come from the verification campaign, F54–F56 from the functional retest made after the cut-off, and F57–F58 from checking Section 9 against the code. One remains open (F18), one is retained as a residual risk (F11), and one is carried as a stated limitation (F53).

---

## Appendix G — Manifest schema

*[To be lifted: the full JSON schema for the `permissions` block, the eight top-level capabilities
and ten declarable clauses beneath them, the parse-time rejection rules, and the clause-pointer
format that makes every enforcement decision attributable.]*
