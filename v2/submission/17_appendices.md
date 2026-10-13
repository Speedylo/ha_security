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

This appendix gives the full register that Section 8 summarises. It follows ISO 31000's process [25]: criteria fixed first, threats identified with STRIDE [26] at each of the six trust boundaries, each threat rated before treatment, then treated, then scored against the running system. Table C.5 maps the register onto Corno and Mannella's eleven threats [9], so that the result can be checked against a model this project did not write.

### C.1 Risk criteria

The scales are ordinal, not cardinal. They order risks for treatment, and the product of two ordinal scales is not a quantity, so the bands below are labels for priority rather than measurements. The risk owner is the occupying householder, who has neither a security function nor any capacity to respond to an incident, and every rating is calibrated to that owner. A threat is rated on the worst outcome consistent with the actor model, and at the highest impact level that any of the three harm types in Table C.1 matches.

**Table C.1 — Impact (asset identifiers as in Table 8.1)**

| | Level | Confidentiality | Integrity and control | Availability |
|---|---|---|---|---|
| 5 | Severe | — | Physical access to the dwelling by a state change (A1) | A life-safety function defeated: alarm, smoke or CO response, heating in freezing conditions (A5 with A1) |
| 4 | Major | Credentials compromised beyond the home (A3); camera or media access (A4) | Reach into other devices on the home network (A8) | Total loss of the platform while unattended (A5) |
| 3 | Moderate | Occupancy or behaviour disclosed (A2) | Undetected corruption of another integration's data (A6) | Loss of attribution: harm that cannot be traced to its source (A7) |
| 2 | Minor | Individual non-sensitive readings disclosed | Corruption that is detected, or overwritten by the owning integration's next update (A6) | Partial or transient loss of function |
| 1 | Negligible | No meaningful loss | | |

**Table C.2 — Likelihood, and the evaluation bands**

| | Level | Anchor |
|---|---|---|
| 5 | Almost certain | Occurs by default in normal operation |
| 4 | Likely | Documented in this ecosystem, or requires no attacker skill |
| 3 | Possible | Documented in comparable ecosystems |
| 2 | Unlikely | Technically available, no documented occurrence |
| 1 | Rare | Requires capability inconsistent with the actor model |

Bands: Low 1–4, Medium 5–9, High 10–16, Critical 17–25. **Appetite:** no residual Critical risk is acceptable, and a residual High risk is acceptable only where it is structural, meaning that no available control addresses it, and is stated openly to the user.

### C.2 Threats and inherent risk

Inherent risk is rated against Home Assistant as it stands, with no requirement of Section 3 implemented. The CM column gives the corresponding threat in Corno and Mannella's model [9].

**Table C.3 — Threats identified, by trust boundary, with inherent risk**

| ID | STRIDE | Threat | CM | I | L | Inherent |
|---|---|---|---|---|---|---|
| | | **TB1 — integration and mediating component** | | | | |
| T01 | Elevation | Bypasses mediation by acting directly on the platform's in-process objects | T10 | 5 | 5 | 25 Critical |
| T02 | Spoofing | Presents itself as another integration to obtain that integration's authority | T9 | 4 | 4 | 16 High |
| T03 | Tampering | Modifies the mediating component or its policy in memory | T10 | 5 | 5 | 25 Critical |
| T04 | Disclosure | Recovers the platform credential held by the mediator | T1 | 5 | 4 | 20 Critical |
| T19 | Denial of service | Floods the mediator with refused requests, each a durable record, exhausting the decision capacity all sandboxes share and the disk | T7 | 3 | 4 | 12 High, against the design |
| | | **TB2 — mediating component and Home Assistant** | | | | |
| T05 | Elevation | Induces the mediator to make an undeclared service call, as a confused deputy | T3, T10 | 5 | 5 | 25 Critical |
| T06 | Disclosure | Reads undeclared entity states, or subscribes to a stream of the whole installation | T1 | 3 | 5 | 15 High |
| T07 | Tampering | Writes state for entities it does not own, corrupting another integration's data | T4 | 2 | 4 | 8 Medium |
| | | **TB3 — integration and external network** | | | | |
| T08 | Disclosure | Sends data to an undeclared host | T2 | 4 | 4 | 16 High |
| T09 | Disclosure | Sends data through a declared host: content, not destination | T2 | 4 | 3 | 12 High |
| T10 | Elevation | Reaches other devices on the home network, or services on the gateway's loopback | T3 | 4 | 3 | 12 High |
| T11 | Spoofing | Uses a declared host name that resolves, at request time, to an internal address | T9 | 4 | 2 | 8 Medium |
| | | **TB4 — author and channel, and the user's machine** | | | | |
| T12 | Tampering | A malicious update arrives through the authorised update path to an integration already trusted | — | 5 | 3 | 15 High |
| T13 | Spoofing | The declaration misrepresents behaviour: over-declared, or absent | T10 | 4 | 4 | 16 High |
| | | **TB5 — integration and host operating system** | | | | |
| T14 | Disclosure | Reads files outside its resources: `secrets.yaml`, the state database, tokens | T1 | 4 | 4 | 16 High |
| T15 | Disclosure | Reads another process's memory, environment or command line through the process table | T1 | 4 | 4 | 16 High |
| T16 | Denial of service | Exhausts processor, memory or disk, making the gateway unresponsive | T7 | 4 | 3 | 12 High |
| | | **TB6 — integration and other integrations** | | | | |
| T17 | Disclosure, tampering | Reads or alters another integration's live objects and secrets | T1, T4 | 4 | 4 | 16 High |
| T18 | Repudiation | Acts without attribution, so no record identifies which integration acted | T11 | 3 | 5 | 15 High |

Eighteen threats were identified against the platform as it stands: four Critical, twelve High and two Medium, and all four Critical threats share one cause, the shared process. T19 has no rating against the platform, because it does not exist there. The treatment of T18 created it: a durable record per decision makes each refusal cost the mediator about 3.7 ms of shared time, and a flood of refusals happened by accident during the evaluation. It is rated against the design before its control and is not counted among the eighteen.

### C.3 Treatment and verdicts

Every treatment but two changes consequence rather than likelihood, bounding what the code can do. The verdicts are not aggregated into a single figure, for the reason Section 11 gives. *Paired* means the threat was also shown to succeed against the unconfined arm on the same host and platform release.

**Table C.4 — Treatment, requirement and verdict**

| ID | Control | Req. | Verdict and evidence |
|---|---|---|---|
| T01 | Run the integration outside the platform's process | S1 | Demonstrated, paired: the heap walk reaches a credential through 7 objects unconfined, and only the attacker's own 8,942 objects confined |
| T02 | Identity taken from the channel, on every request | S1, S7 | Demonstrated: a request claiming to come from another integration is decided under its sender's own grant, and refused |
| T03 | Mediator outside the integration's address space | S1 | Demonstrated; cannot be paired, because unconfined there is no mediator to tamper with |
| T04 | Credential held only by the mediator | S2 | Demonstrated, paired: the sandbox's sweep finds no credential while the same token is live in the mediator |
| T05 | Service calls checked against the manifest, deny by default | F3, S5, S6 | Demonstrated: `lock.unlock` refused under a grant of `lock.lock`; `lock.*` rejected when the manifest is parsed |
| T06 | Reads and subscriptions both mediated | S3 | Demonstrated, paired: reads 36 of 36 unconfined, 1 of 36 confined; undeclared changes delivered 4 of 4 unconfined, 0 of 3 confined |
| T07 | Writes only to declared entities | F3, S6 | Demonstrated |
| T08 | Network access per integration, by declared host | S4 | Demonstrated: two concurrent integrations, each refused the host only the other declared |
| T09 | Retained (R5) | — | Retained: the mediator controls the destination and never sees content |
| T10 | Private destinations refused unless separately granted | S4 | Demonstrated, and the granted path measured with a real integration against a simulated device |
| T11 | Destination checked on the resolved address, not the name | S4 | Demonstrated: the host clause satisfied, the connection refused on its address |
| T12 | Each start confined by the manifest and code it starts with; a changed grant needs a new approval | F3, S6 | Demonstrated: a changed manifest bounds the next start and is reported before it takes effect |
| T13 | Retained in part (R1, R2): the declaration is shown and approved, and enforcement is bounded to it | F4 | Retained: an over-broad grant is honoured once approved; the ceiling it cannot raise is measured |
| T14 | Filesystem view limited to the integration's own directories | S8 | Demonstrated, paired: canary secrets 2 of 2 unconfined, 0 of 2 confined; the path does not exist |
| T15 | Process table limited to the sandbox | S8 | Demonstrated, paired: another process's environment read unconfined, nothing to read confined |
| T16 | Resource limits from the manifest | S9 | Partial: memory, processor time, processes and disk space bounded, each shown by a sandbox exceeding it; I/O bandwidth not bounded (R7); the persistent data folder checked against the disk bound only at start |
| T17 | Separate processes, so no shared heap | S1 | Demonstrated, paired, by the same heap walk as T01 |
| T18 | Attributed, tamper-evident record written before the action | S7 | Demonstrated, bounded by R4: modification, deletion and reordering each detected by both chains independently |
| T19 | Refusals counted per integration; past 100 in 10 s, one record, and the integration stopped until a person restarts it, never with more authority | S7, S9 | Demonstrated: cut off within 0.81 s after exactly 100 recorded refusals, while a second sandbox continued to be served |

Sixteen of the nineteen threats are demonstrated, six of them paired; one is partial and two are retained by decisions made before the evaluation. All four Critical inherent threats are among those demonstrated, which is the register's most important result, because one control, the separate process, answers the cause they share.

### C.4 Residual risks

The seven residual risks, R1 to R7, are given with their ratings and the reason each is retained in Table 8.4. One further residual sits within T14 and was found by measurement. The sandbox's filesystem binds the interpreter and its libraries at their host paths, so a confined integration can read the host's directory layout along those paths, including a user's name where the runtime is installed under a home directory. It cannot read any content outside its grant. Its likelihood is 5, because the exposure follows from the construction, and its impact 1, since a name and directory names give no capability and disclose no reading, so it is rated 5, Medium, and retained. The remedy is a deployment step, installation under a neutral path. Rated at impact 2 it would be High, and the appetite would then require the remedy.

### C.5 The register against an external model

**Table C.5 — Corno and Mannella's eleven threats [9], scored through Table C.3's CM column**

| CM | Their threat | Mapped from | Verdict |
|---|---|---|---|
| T1 | Confidentiality: data used outside its scope | T04, T06, T14, T15, T17 | Demonstrated, all five paired |
| T2 | Data spread outside its scope | T08, T09 | Split: T08 demonstrated, T09 retained, because destination is controlled and content is not |
| T3 | Integrity: device state altered | T05, T10 | Demonstrated |
| T4 | Integrity: private data altered | T07, T17 | Demonstrated |
| T5 | Availability: delay | — | Not mapped |
| T6 | Availability: partial loss | — | Not mapped |
| T7 | Availability: complete loss, including "resource saturation up to a frozen state" | T16, T19 | Partial: T19 demonstrated, T16 partial |
| T8 | Availability: physical damage | — | Not mapped; out of reach of any software control on the gateway |
| T9 | Authentication: impersonation | T02, T11 | Demonstrated |
| T10 | Authorisation: escalation | T01, T03, T05, T13 | Demonstrated, except T13, retained |
| T11 | Non-repudiation: anonymous action | T18 | Demonstrated, bounded by R4 |

Eight of the eleven are mapped, five without qualification. The two registers differ in both directions: theirs reaches consequences this design does not touch, delay, partial loss and physical damage, while this register separates the update channel (TB4) and the host (TB5) into boundaries that a gateway-level model folds together. Neither register contains the other, and reporting only this project's own would have been the more favourable choice. T16's control plausibly reaches T5 and T6 as well, since a gateway being exhausted is delayed and partially lost before it is lost entirely, but the register maps T16 only to T7, and the table reports that mapping as it stands.

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
| F57 | Writing Section 9 | Major | No approval was required before a sandbox started: a derived manifest was used unconfirmed, an author-declared one unseen, and an update that widened its own grant received it | Fixed in code after the cut-off, with a test that failed first: a sandbox registers only if an approval matches its current code and its loaded grant. A refused start is shown to the household as a Repairs issue, from which an administrator can read the permissions and allow them |
| F58 | Writing Section 9 | Minor–Major | Internet egress accepted the shared address space 100.64.0.0/10, used by carrier-grade NAT and Tailscale, so a granted name resolving into it would have been connected to | Fixed in code after the cut-off, with a test that failed first |
| F59 | Writing Section 9 | Minor | A restarted integration lost everything it had stored, its configuration entry and any login token included, because every start received a fresh data directory | Fixed in code after the cut-off, with a test that failed first: only Home Assistant's own data store is kept between starts, held to a size limit, and the directory the code is loaded from is still fresh at every start |
| F60 | Building the approval screen (F57) | Minor | The command-line rendering did not warn that a derived grant had widened since its approval, because the file holding it is not part of the integration's identity | Fixed in code after the cut-off, with a test that failed first: the warning compares the approved grant itself |

Of the 60 findings, one is Critical, 14 Major, 5 between Minor and Major, 36 Minor, 3 notes and 1 a request to re-measure. F01–F53 come from the verification campaign, F54–F56 from the functional retest made after the cut-off, and F57–F60 from checking Section 9 against the code and from the fixes that followed. One remains open (F18), one is retained as a residual risk (F11), and one is carried as a stated limitation (F53).

---

## Appendix G — Manifest schema

*[To be lifted: the full JSON schema for the `permissions` block, the eight top-level capabilities
and ten declarable clauses beneath them, the parse-time rejection rules, and the clause-pointer
format that makes every enforcement decision attributable.]*
