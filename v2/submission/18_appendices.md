# Appendices

## Appendix A — Open-source repository and artifact index

| | |
|---|---|
| Framework | `v2/framework/confine/` — standard library plus `ctypes`, no third-party dependencies, no override flag |
| Self-tests | **35 suites**, all passing on the test hardware. `selftest.py` and `selftest_*.py` in the same directory; `experiments/selftests/suites_all.sh` runs them |
| Experiments | `v2/experiments/` — each with its script, its raw result file and a readable write-up |
| Figures | `v2/figures/` — each figure and its threat model generated from one source, so they cannot drift |
| Corpora | `hacs_corpus_manifest.json` — both corpora, redrawable; the uniform draw records its seed (20260902) |
| Working notes | `v2/notes/` — decision records, evidence write-ups and the pre-registered predictions |
| Test hardware | Raspberry Pi 5, 4 GB, Raspberry Pi OS trixie. **Every measurement in this report was taken on it** |
| Version | Tag `final-2026-11`, at which every measurement, mutant, suite and fault was rerun on 1 November 2026; results in `v2/experiments/verify/results/final2_20261101/`. The first full rerun, at tag `final-2026-10` on 16 October 2026, is kept in `final_20261016/` |
| Full appendices | `v2/notes/appendices_full_20261110/`: the full compatibility results, the 35 self-test suites, the manifest schema, the requirements' derivations and criteria, the 71 findings one per line, and the architecture's detail, cut from this report for length |
| Reproduction | `v2/REPRODUCE.md`, followed from a fresh clone; following it on a freshly imaged device is still open (F18) |

The repository is public at https://github.com/Speedylo/ha_security.

---

## Appendix B — Requirements register

This appendix gives the verdict on each requirement of Table 3.2, with its evidence. The criteria were fixed on 2 September 2026, before the evaluation ran, and the last column records how a verdict changed after that, because a register that showed only final verdicts would hide the cases in which verification overturned an earlier one. In every such case the criterion stayed as written and the verdict moved. Where each requirement comes from, and its criterion in full, are kept in the repository (Appendix A).

**Table B.1 — Verdicts, evidence and history**

| ID | Verdict | Evidence | How the verdict changed |
|---|---|---|---|
| C1 | Met | Every source tree hashed before and after its run, in both arms of both corpora and again at both final reruns: no source changed, no line differed | Argued until 6 September 2026: the report had described a difference check that did not exist, and the check was then built and run |
| C2 | Met | Every arm ran on the unmodified release 2026.8.3, recorded in each result file (Section 11) | — |
| C3 | Met | Absent, over-broad and mismatched manifests each handled as specified; the over-broad one is honoured, and that residual is stated as R1 (Section 8.4, Table C.5) | — |
| C4 | Met | Every performance figure measured on the Raspberry Pi 5 (Table 12.4) | — |
| F1 | Met | A confined integration's fifteen sensors are registry entities in a live Home Assistant instance, keep their names and survive a restart (Appendix F.2) | Bounded to a stand-in platform until 4 October 2026, when the same entities were published into a live instance |
| F2 | Met | Real integrations polled their own live services confined and matched the unconfined arm's output, across three HTTP libraries and one authenticated service (Table 12.3) | Could not be tested when the criteria were frozen, because egress had not been built; met on 3 September 2026, first by purpose-built integrations and then by a real one |
| F3 | Met | Seven mismatched behaviours produced seven refusals naming seven distinct clauses; the suite checks that a refusal without a clause cannot be built | Qualified on 6 October 2026: seven code paths could build a refusal with no clause, though none appeared in any record (finding F03), and they were fixed |
| F4 | Met | The grant renders in plain language with denials at equal weight, in the terminal and on the approval screen | Strengthened later: an approval is now bound to the grant shown (F57, F60) |
| S1 | Met, paired | The heap walk reached a live credential through 7 objects unconfined and through none of 8,942 objects confined (Table 12.1) | — |
| S2 | Met, paired | Other processes, whose environment can hold credentials, were visible unconfined and not confined (Table 12.1); the adversary suite recovered no platform credential from the sandbox's file system, process table or memory | — |
| S3 | Met, paired | Reads: 36 of 36 entity states unconfined, 1 of 36 (the declared one) confined. Subscriptions: 3 of 3 undeclared changes delivered unconfined and 0 of 3 confined, both on the same platform release (Table 12.1; Appendix C, Table C.4) | Partial until 4 October 2026, because no mechanism yet delivered state changes to a sandbox; the subscription half was paired against an unconfined arm on 13 October 2026 |
| S4 | Met | Two integrations running at once were each denied the host declared only by the other, as the mediator's own record shows | Could not be tested when the criteria were frozen; met on 3 September 2026 |
| S5 | Met | A manifest declaring `lock.lock` does not permit `lock.unlock`, and `lock.*` is rejected when the manifest is parsed | — |
| S6 | Met | Absent and unparseable manifests each denied all mediated capability, each refusal naming its rule | — |
| S7 | Met | Modification, deletion and reordering each detected, the two chains failing independently; every harness that decides writes the durable log | Twice qualified: the identity was recorded only inside the suite until 3 October 2026, and a full disk or a restart could break the chain until 6 October (F28, F31) |
| S8 | Met, paired | The 2021 pattern recovered 2 of 2 planted secrets unconfined and 0 of 2 confined; the file does not exist inside the sandbox (Table 12.1) | Qualified on 6 October 2026: each sandbox shared the supervisor's terminal, a route out that no file-theft test exercised (F34), since fixed; host paths remain readable without file contents (F11, residual) |
| S9 | Met, narrowed | Memory exhaustion ended by the kernel, process creation refused at the cap, a 25% processor cap held at 25.1%, writing refused at the disk quota (Appendix C, T16) | Narrowed on evidence: "disk" means space, not I/O bandwidth, because the device's service manager does not delegate that control to an unprivileged user (systemd, n.d.) |
| N1 | Met | Memory, latency and capacity reported against the unconfined arm, with no threshold (Table 12.4) | — |
| N2 | Met by reporting | Import-level results for 75 integrations and end-to-end results for 15 are reported separately and never combined (Tables 12.2 and 12.3) | — |
| N3 | Met | The framework refuses to start without the memory controller or from the wrong control-group position, and fails closed when the mediator stops (Section 9; `selftest_supervise`) | Strengthened during verification: a killed supervisor once left its sandbox running without a mediator (F30), and a sandbox did not restart when the platform returned (F29); both fixed |

All twenty requirements are met, eighteen as stated and two in a narrower form. S9 was narrowed by the evidence, and N2 is met by the way results are reported rather than by a measured rate. The history column also bears on how far the verdicts can be trusted. Eleven of the twenty rows changed after the criteria were frozen, and in four of them (C1, F3, S7, S8) verification found that a verdict had claimed more than the code supported. In each of those four, the code or the check was corrected and the criterion was left as written, so no verdict was restored by weakening the test it had failed.

---

## Appendix C — Threat register

This appendix gives the full register that Section 8 summarises. It follows ISO 31000's process (International Organization for Standardization, 2018): criteria fixed first, threats identified with STRIDE (Shostack, 2014) at each of the six trust boundaries, each threat rated before treatment, then treated, then scored against the running system. Table C.6 maps the register onto Corno and Mannella's (2022) eleven threats, so that the result can be checked against a model this project did not write.

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

Inherent risk is rated against Home Assistant as it stands, with no requirement of Section 3 implemented. The CM column gives the corresponding threat in Corno and Mannella's (2022) model.

**Table C.3 — Threats identified, by trust boundary, with inherent risk**

| ID | STRIDE | Threat | CM | Impact | Likelihood | Inherent |
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
| T07 | Tampering | Writes state for entities it does not own, corrupting another integration's data and triggering the automations that act on it | T3, T4 | 5 | 4 | 20 Critical |
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

Eighteen threats were identified against the platform as it stands: five Critical, twelve High and one Medium, and all five Critical threats share one cause, the shared process. T19 has no rating against the platform, because it does not exist there. The treatment of T18 created it: a durable record per decision makes each refusal cost the mediator about 3.7 ms of shared time, and a flood of refusals happened by accident during the evaluation. It is rated against the design before its control and is not counted among the eighteen.

T07's impact is rated through the platform's automations rather than through the data it corrupts. A state trigger in Home Assistant fires on any change to its entity's state, and the context passed to the automation records the user who caused the change, if any, but not the integration that wrote it (`triggers/state.py` and `Context` in `core.py`, release 2026.8.3). An integration that writes `home` to a householder's presence entity therefore causes any automation that disarms the alarm or unlocks the door on arrival to do so, without itself calling the service that T05's control checks. The worst outcome consistent with the actor model is physical access to the dwelling (A1), level 5. The owning integration's next update does not lower that rating, for two reasons. Presence, door and lock entities report only when something changes, so a forged value can stand for hours, and an automation that has already acted is not reversed when the state is corrected. An earlier rating of 2, Minor, rested on that correction and was raised for these reasons.

### C.3 Treatment and verdicts

Figure C.1 draws the confined design on the canvas of Figure 8.1, so that the difference between the two shows what the treatments change: the four absent boundaries now exist, and the flows that reached the shared memory, the stored credentials, any file and the other integration have no counterpart.

![Figure C.1](../figures/fig_8_2_confined.svg)

**Figure C.1**
*The confined design, on the canvas of Figure 8.1*

*Note.* Each integration runs in its own sandbox and reaches the platform only through the mediator. All six boundaries now exist; TB4 is unchanged and TB2 is narrowed (residual risk R3). Flow (m) is the approval.

Every treatment but two changes consequence rather than likelihood, bounding what the code can do. The verdicts are not aggregated into a single figure, for the reason Section 11 gives. *Paired* means the threat was also shown to succeed against the unconfined arm on the same host and platform release.

**Table C.4 — Treatment, requirement and verdict**

| ID | Control | Req. | Verdict and evidence |
|---|---|---|---|
| T01 | Run the integration outside the platform's process | S1 | Demonstrated, paired: the heap walk reaches a credential through 7 objects unconfined, and only the attacker's own 8,942 objects confined |
| T02 | Identity taken from the channel, on every request | S1, S7 | Demonstrated: a request claiming to come from another integration is decided under its sender's own grant, and refused |
| T03 | Mediator outside the integration's address space | S1 | Demonstrated; cannot be paired, because unconfined there is no mediator to tamper with |
| T04 | Credential held only by the mediator | S2 | Demonstrated, paired: the sandbox's sweep finds no credential while the same token is live in the mediator |
| T05 | Service calls checked against the manifest, deny by default | F3, S5, S6 | Demonstrated: `lock.unlock` refused under a grant of `lock.lock`; `lock.*` rejected when the manifest is parsed |
| T06 | Reads and subscriptions both mediated | S3 | Demonstrated, paired: reads 36 of 36 unconfined, 1 of 36 confined; undeclared changes delivered 3 of 3 unconfined and 0 of 3 confined on the same host and release, and 3 of 3 with the filter bypassed |
| T07 | Writes only to declared entities | F3, S6 | Demonstrated |
| T08 | Network access per integration, by declared host | S4 | Demonstrated: two concurrent integrations, each refused the host only the other declared |
| T09 | Retained (R5) | — | Retained: the mediator controls the destination and never sees content |
| T10 | Private destinations refused unless separately granted | S4 | Demonstrated, and the granted path measured with a real integration against a simulated device |
| T11 | Destination checked on the resolved address, not the name | S4 | Demonstrated: the host clause satisfied, the connection refused on its address |
| T12 | Each start confined by the manifest and code it starts with; a changed grant needs a new approval | F3, S6 | Demonstrated: a changed manifest bounds the next start and is reported before it takes effect |
| T13 | Retained in part (R1, R2): the declaration is shown and approved, and enforcement is bounded to it | F4 | Retained: an over-broad grant is honoured once approved; the ceiling it cannot raise is measured |
| T14 | Filesystem view limited to the integration's own directories | S8 | Demonstrated, paired: canary secrets 2 of 2 unconfined, 0 of 2 confined; the path does not exist |
| T15 | Process table limited to the sandbox | S8 | Demonstrated, paired: other processes visible unconfined, none confined |
| T16 | Resource limits from the manifest | S9 | Partial: memory, processor time, processes and disk space bounded, each shown by a sandbox exceeding it; I/O bandwidth not bounded (R7); the persistent data folder checked against the disk bound only at start |
| T17 | Separate processes, so no shared heap | S1 | Demonstrated, paired, by the same heap walk as T01 |
| T18 | Attributed, tamper-evident record written before the action | S7 | Demonstrated, bounded by R4: modification, deletion and reordering each detected by both chains independently |
| T19 | Refusals counted per integration; past 100 in 10 s, one record, and the integration stopped until a person restarts it, never with more authority | S7, S9 | Demonstrated: cut off within 0.81 s after exactly 100 recorded refusals, while a second sandbox continued to be served |

Sixteen of the nineteen threats are demonstrated, six of them paired; one is partial and two are retained by decisions made before the evaluation. All five Critical inherent threats are among those demonstrated, which is the register's most important result, because one control, the separate process, answers the cause they share.

### C.4 Residual risks

The seven residual risks, R1 to R7, are given with their ratings and the reason each is retained in Table C.5. Section 8.4 discusses the four that remain High.

**Table C.5**
*Residual risks*

| | Risk | Residual | Why retained |
|---|---|---|---|
| R1 | The over-declaring manifest | High | Structural: a manifest bounds an integration to its declaration but cannot make the declaration minimal. Barth et al. found that 76% of the browser extensions they studied used unnecessarily powerful APIs (Barth et al., 2010). Authority becomes visible and bounded instead of silent and total |
| R2 | Abuse of legitimately declared authority | High, structural | An integration that declares `lock.unlock` may unlock the door at 03:00; preventing that needs contextual integrity, a different mechanism with its own usability costs |
| R3 | The mediator's credential still reaches every device | High, narrowed | The mediator runs as an ordinary user (F45): it can no longer create users, change the configuration or install integrations, but it can operate every device, because the platform's per-entity policy cannot be configured through a supported interface |
| R4 | A local audit log cannot be authoritative against whoever controls the machine | Medium | Hash chaining gives tamper evidence, not tamper proofing, and says nothing about events never recorded |
| R5 | Exfiltration through a declared host | High | Structural: destination control cannot become content control without inspecting payloads, which is itself a privacy problem, and TLS makes the data visible only to its two endpoints (Rescorla, 2018) |
| R6 | The user is not equipped to evaluate a declaration | Medium | Out of scope: enforcement does not depend on the user reading the manifest |
| R7 | Input and output bandwidth is unbounded | Medium | Inherited: systemd delegates only the `cpu`, `memory` and `pids` controllers to a user's service manager (systemd, n.d.), so the unprivileged supervisor cannot apply the `io` controller |

R3 changed during verification. The model originally stated that Home Assistant issues no scoped token, so the mediator had to hold full authority. Checked against the platform's own release, that was wrong: a token carries its user's permissions, and an entity policy, by domain or by entity, is enforced. The mediator had held an administrator's token only because this project's bridge admitted no one else (finding F45). It now runs as an ordinary user, which removes every administrative function from its reach. The risk stays High because the locks of A1 are still reachable, but its reason is now narrower and exact: the platform's per-entity policy exists, yet no supported interface creates one.

One further residual sits within T14 and was found by measurement. The sandbox's filesystem binds the interpreter and its libraries at their host paths, so a confined integration can read the host's directory layout along those paths, including a user's name where the runtime is installed under a home directory. It cannot read any content outside its grant. Its likelihood is 5, because the exposure follows from the construction, and its impact 1, since a name and directory names give no capability and disclose no reading, so it is rated 5, Medium, and retained. The remedy is a deployment step, installation under a neutral path. Rated at impact 2 it would be High, and the appetite would then require the remedy.

T07's treatment also leaves a residual, and it falls within R2. Confinement stops an integration writing to entities it has not declared, but it cannot make the values it writes to its own entities true. An integration that publishes its own presence sensor can report a householder at home, and an automation the householder has built on that sensor will act on the report. The control bounds which entities an integration can forge, not whether its readings are honest, so this is the abuse of legitimately declared authority that R2 names, and it is retained with R2 as High and structural.

### C.5 The register against an external model

**Table C.6 — Corno and Mannella's (2022) eleven threats, scored through Table C.3's CM column**

| CM | Their threat | Mapped from | Verdict |
|---|---|---|---|
| T1 | Confidentiality: data used outside its scope | T04, T06, T14, T15, T17 | Demonstrated, all five paired |
| T2 | Data spread outside its scope | T08, T09 | Split: T08 demonstrated, T09 retained, because destination is controlled and content is not |
| T3 | Integrity: device state altered | T05, T07, T10 | Demonstrated |
| T4 | Integrity: private data altered | T07, T17 | Demonstrated |
| T5 | Availability: delay | — | Not mapped |
| T6 | Availability: partial loss | — | Not mapped |
| T7 | Availability: complete loss, including "resource saturation up to a frozen state" | T16, T19 | Partial: T19 demonstrated, T16 partial |
| T8 | Availability: physical damage | — | Not mapped; out of reach of any software control on the gateway |
| T9 | Authentication: impersonation | T02, T11 | Demonstrated |
| T10 | Authorisation: escalation | T01, T03, T05, T13 | Demonstrated, except T13, retained |
| T11 | Non-repudiation: anonymous action | T18 | Demonstrated, bounded by R4 |

Eight of the eleven are mapped, five without qualification. The two registers differ in both directions: theirs reaches consequences this design does not touch, delay, partial loss and physical damage, while this register separates the update channel (TB4) and the host (TB5) into boundaries that a gateway-level model folds together. T16's control plausibly reaches T5 and T6 as well, since a gateway being exhausted is delayed and partially lost before it is lost entirely, but the register maps T16 only to T7, and the table reports that mapping as it stands.

---

### C.6 What an integration can reach today

Table C.7 gives the authority that Section 2.1 summarises, with the source for each row. The last column separates what is deduced from how the platform loads an integration from what has been shown in practice, because the two carry different weight as evidence.

**Table C.7**
*Authority held by any community integration in Home Assistant 2026.8.3*

| Asset | Reach | Consequence of abuse | Basis |
|---|---|---|---|
| Entity states | Every entity in the installation | Occupancy, presence, sleep patterns, absence from home | Deduced from the loading model (Home Assistant, n.d.-g) |
| Service calls | Any service, including unlocking a door and disarming an alarm | Physical access to the dwelling | Deduced from the loading model (Home Assistant, n.d.-g); the platform's per-user check lets through a call that carries no user (Home Assistant, 2026) |
| Stored credentials | Any file the process can read, including stored secrets | Compromise of every linked cloud account | Deduced from the loading model; shown for flawed integrations in 2021, where the platform noted that the exposed files include stored credentials (Home Assistant, 2021a) |
| File system | Whatever the process's user can read | Configuration, history database, tokens | Deduced from the loading model; shown for flawed integrations in 2021 (Home Assistant, 2021a) |
| Network | Unrestricted outbound access and the home network | Exfiltration; a foothold inside the home | Deduced from the loading model (Home Assistant, n.d.-g) |
| Web endpoints | Can add its own HTTP endpoints to the platform's web server, with the login check switched off | An unauthenticated way into the home | Reported for an integration shipped with the platform (CVE-2023-27482) (elttam, 2023) |
| Other integrations' live objects | Any object in the shared interpreter | Theft or alteration of another integration's secrets | Demonstrated experimentally (Corno & Mannella, 2022) |

## Appendix D — Verification findings and the claim register

This appendix records the outcome of the verification campaign that Section 12.4 summarises. During development, every claim in the project's working report was registered with its evidence and a pass criterion fixed before the claim was re-tested, and every measurement was repeated on fixed versions of the code. Table D.1 gives the register's outcome, and the paragraph after it summarises the 71 findings the project recorded. The findings one per line, the full register and the detailed log, with the evidence for each entry, are in the repository (Appendix A).

**Table D.1 — Claim register outcome by tier**

| Tier | What it holds | Rows | Verified | Qualified | Argued | Withdrawn |
|---|---|---|---|---|---|---|
| A | The abstract, the 20 requirements, the 19 threat verdicts, the 11 verdicts against the published threat model, the central claim and the contributions | 91 | 72 | 15 | 4 | 0 |
| B | One row per measurement, each with its criterion kind declared before re-running | 30 | 24 | 5 | 0 | 1 |
| C | The remaining claims in the text, as 16 mechanism groups and 16 single claims | 32 | 23 | 7 | 1 | 1 |
| | **Total** | **153** | **119** | **27** | **5** | **2** |

A claim is *Verified* when it held as stated on the frozen code, *Qualified* when it holds only in a narrower form, which the report now states, *Argued* when it rests on reasoning rather than measurement, and *Withdrawn* when the evidence did not support it.

Of the 71 findings, one is Critical, 17 Major, 5 between Minor and Major, 44 Minor, 3 notes and 1 a request to re-measure. F01–F53 come from the verification campaign, F54–F56 from a functional retest, F57–F60 from checking Section 9 against the code and from the fixes that followed, F61 and F62 from the first final rerun, F63 from writing the manifest schema, and F64–F71 from extending the end-to-end runs and the bridge. One remains open (F18), one is retained as a residual risk (F11), and two are carried as stated limitations (F53, F63).

---
