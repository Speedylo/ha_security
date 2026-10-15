# Appendices

## Appendix A — Open-source repository and artifact index

| | |
|---|---|
| Framework | `v2/framework/confine/` — standard library plus `ctypes`, no third-party dependencies, no override flag |
| Self-tests | **29 suites**, all passing on the test hardware (Appendix E). `selftest.py` and `selftest_*.py` in the same directory; `experiments/selftests/suites_all.sh` runs them |
| Experiments | `v2/experiments/` — each with its script, its raw result file and a readable write-up |
| Figures | `v2/figures/` — each figure and its threat model generated from one source, so they cannot drift |
| Corpora | `hacs_corpus_manifest.json` — both corpora, redrawable; the uniform draw records its seed (20260902) |
| Working notes | `v2/notes/` — decision records, evidence write-ups and the pre-registered predictions |
| Test hardware | Raspberry Pi 5, 4 GB, Raspberry Pi OS trixie. **Every measurement in this report was taken on it** |

*[Repository URL and access statement to be supplied on submission.]*

---

## Appendix B — Requirements register

This appendix gives the full register that Table 3.2 summarises. Its purpose is to let a reader check each verdict against a criterion that was fixed before the evidence existed, so it is presented in two parts: what each requirement demands and how it was to be judged (Table B.1), and what the evaluation found (Table B.2).

Each requirement was traced to a source in the problem statement or the literature, and a requirement with no source was cut rather than kept. The criteria in Table B.1 are quoted as they were frozen on 2 September 2026, before the evaluation ran, with one exception: S9 entered when the threat model identified resource exhaustion (threat T16, Appendix C), and its criterion was fixed then, before its measurement. Four requirements (C3, S1, S4, S5) derive from a limitation or a result in prior work rather than from the platform, which reflects how closely the design follows the work it extends.

**Table B.1 — Requirements, derivation and criteria fixed in advance**

| ID | The framework shall… | Derivation | Criterion: the requirement passes if… |
|---|---|---|---|
| C1 | Run integrations with their code unmodified | Browser extension models could require authors to adopt a new permission model because the platform was new [14]; Home Assistant has thousands of existing integrations [1] written against an interface that presumes full authority | Every integration in the compatibility runs shows a zero-line difference against its fetched original, counted mechanically after the run |
| C2 | Require no change to Home Assistant | The platform leaves community code to its users' risk [3], and the project has no authority over the platform | Every arm runs against an unmodified official Home Assistant release, with the version recorded in the result file |
| C3 | Not depend on the author's cooperation or honesty | The closest prior work relies on truthful declarations by plug-in developers, and its authors acknowledge that anyone with access to the source could alter it [15] | The adversarial run includes an absent manifest, an over-broad manifest and one deliberately mismatched to behaviour, and all three are handled by the manifest's precedence rules |
| C4 | Run on self-hosted, resource-constrained hardware | A property of the deployment: Home Assistant is commonly installed on single-board computers | Every performance figure is produced on the Raspberry Pi 5, reporting per-integration memory and added latency |
| F1 | Let a confined integration publish entities and states | Connecting a device or service to the entity model is what an integration is for, and an add-on cannot do it in its place [2], [12] | A confined integration's entities are present in Home Assistant and behave as native entities under the measures used in the evaluation |
| F2 | Let a confined integration reach declared network endpoints | Integrations exist largely to contact device and cloud services, so network access cannot simply be denied | An integration polling a declared remote service completes successfully while confined |
| F3 | Express authority in a declarative manifest | The missing mechanism is a way for authority to be declared, enforced and audited, and the manifest is established practice in browsers [14] | Every enforcement decision in the evaluation names the manifest clause that produced it, and a decision with no attributable clause is shown to be unconstructible |
| F4 | Show declared authority before it is granted | Users cannot see what an integration will access before installing it, because nothing in the installation path shows it (Section 2) | The manifest of each evaluated integration renders in human-readable form, with denials shown at the same weight as grants |
| S1 | Enforce outside the integration's process | Corno and Mannella showed one integration reaching another's live object through Python's garbage collector [5], so any in-process permission layer is reachable by the code it constrains | The published garbage-collector technique, attempted from inside the sandbox, reaches no platform object, and the mediator and its credential cannot be located from within |
| S2 | Keep every platform credential out of the sandbox | If the confined code holds a token the platform honours, it can bypass mediation and the manifest becomes decorative [5] | No platform credential is recoverable from the sandbox's environment, file system, process table or memory |
| S3 | Mediate reads and subscriptions, not only writes | Entity states reveal occupancy, presence and absence from home, so mediating only state changes would leave surveillance untouched | A confined integration is denied both a read and a subscription to undeclared entities, each refusal naming its clause, against a paired unconfined baseline measuring what is readable without the framework |
| S4 | Attribute and enforce network access per integration | The closest prior work merges every plug-in's declarations into one gateway profile, so each plug-in's effective policy becomes the union of all of them [15] | An integration is denied a host declared only by a different integration |
| S5 | Separate operations of unequal risk | Physical operations are asymmetric in risk, and a permission granted per domain grants both directions [38] | A manifest permitting `lock.lock` is shown not to permit `lock.unlock`, and the refusal is structural rather than a check |
| S6 | Deny by default | An allow-by-default policy bounds nothing, and a malicious author may simply omit the manifest (C3) | An integration with no manifest and one with an unparseable manifest are each denied all mediated capability, each refusal naming its rule |
| S7 | Record every decision in a tamper-evident log | Users cannot detect afterwards what an integration accessed, and a systematic review found that unauthenticated extensions reduce the ability to audit logs and locate malicious ones [25] | Decisions appear in the log bearing the integration's three-part identity, and modification, deletion and reordering are each detected independently by a hash chain and a keyed chain |
| S8 | Isolate files and processes | The platform states that an integration can read any file the Home Assistant process can, including stored credentials, which is what the 2021 disclosures exploited [3], [7] | The 2021 file-theft pattern succeeds against an unconfined baseline installation and is blocked under the framework, on the same host and release |
| S9 | Bound processor, memory and disk use | No source in the problem statement or literature; added when the threat model rated resource exhaustion (T16) | An integration deliberately exhausting processor, memory and disk in turn does not make the gateway unresponsive, demonstrated without administrator privileges, with the boot-time precondition stated |
| N1 | Report overhead against an unconfined baseline | On a constrained device, a control that halves the number of integrations a user can run will not be adopted (C4) | Added latency, per-integration memory and the maximum number of concurrent integrations are reported against an unconfined baseline on the target hardware; no threshold is set in advance |
| N2 | Report compatibility as measured, not asserted | No prior work reports what fraction of Home Assistant's real, unmodified integrations still work under confinement | "Imports clean" and "executed end to end" are reported as two separate numbers, never combined, with the first labelled an upper bound wherever it appears |
| N3 | Fail in a stated way | The user's exposure today is invisible, and a framework that failed open and silently would reproduce that while implying protection | Behaviour when the mediator is unavailable is specified in advance and tested, and the framework refuses rather than degrades silently, including when the supervisor is in the wrong position in the control-group tree |

The verdicts in Table B.2 cite the evidence in the body of the report or in the other appendices. The last column records how a verdict changed after the criteria were frozen, because a register that showed only final verdicts would hide the cases in which verification overturned an earlier one. In every such case the criterion stayed as written and the verdict moved.

**Table B.2 — Verdicts, evidence and history**

| ID | Verdict | Evidence | How the verdict changed |
|---|---|---|---|
| C1 | Met | 75 source trees hashed before and after the runs: no source changed, no line differed (Appendix D) | Argued until 6 September 2026: the report had described a difference check that did not exist, and the check was then built and run |
| C2 | Met | Every arm ran on the unmodified release 2026.8.3, recorded in each result file (Section 11) | — |
| C3 | Met | Absent, over-broad and mismatched manifests each handled as specified; the over-broad one is honoured, and that residual is stated as R1 (Section 8, Table 8.4) | — |
| C4 | Met | Every performance figure measured on the Raspberry Pi 5 (Table 12.5) | — |
| F1 | Met | A confined integration's fifteen sensors are registry entities in a live Home Assistant instance, keep their names and survive a restart (Table 12.3) | Bounded to a stand-in platform until 4 October 2026, when the same entities were published into a live instance |
| F2 | Met | Real integrations polled their own live services confined and matched the unconfined arm's output, across three HTTP libraries and one authenticated service (Table 12.3) | Could not be tested when the criteria were frozen, because egress had not been built; met on 3 September 2026, first by purpose-built integrations and then by a real one |
| F3 | Met | Seven mismatched behaviours produced seven refusals naming seven distinct clauses; the suite checks that a refusal without a clause cannot be built (Appendix E) | Qualified on 6 October 2026: seven code paths could build a refusal with no clause, though none appeared in any record (F03, Appendix F), and they were fixed |
| F4 | Met | The grant renders in plain language with denials at equal weight, in the terminal and on the approval screen (Appendix E) | Strengthened after the cut-off: an approval is now bound to the grant shown (F57, F60) |
| S1 | Met, paired | The heap walk reached a live credential through 7 objects unconfined and through none of 8,942 objects confined (Table 12.1) | — |
| S2 | Met, paired | Another process's environment leaked unconfined and was empty confined (Table 12.1); the adversary suite recovered no platform credential from the sandbox's file system, process table or memory (Appendix E) | — |
| S3 | Met, paired | Reads: 36 of 36 entity states unconfined, 1 of 36 (the declared one) confined. Subscriptions: 3 of 3 undeclared changes delivered unconfined and 0 of 3 confined, both on the same platform release (Table 12.1; Appendix C, Table C.4) | Partial until 4 October 2026, because no mechanism yet delivered state changes to a sandbox; the subscription half was paired against an unconfined arm on 13 October 2026 |
| S4 | Met | Two integrations running at once were each denied the host declared only by the other, as the mediator's own record shows (Appendix E) | Could not be tested when the criteria were frozen; met on 3 September 2026 |
| S5 | Met | A manifest declaring `lock.lock` does not permit `lock.unlock`, and `lock.*` is rejected when the manifest is parsed (Appendix E) | — |
| S6 | Met | Absent and unparseable manifests each denied all mediated capability, each refusal naming its rule (Appendix E) | — |
| S7 | Met | Modification, deletion and reordering each detected, the two chains failing independently; every harness that decides writes the durable log (Appendix E) | Twice qualified: the identity was recorded only inside the suite until 3 October 2026, and a full disk or a restart could break the chain until 6 October (F28, F31) |
| S8 | Met, paired | The 2021 pattern recovered 2 of 2 planted secrets unconfined and 0 of 2 confined; the file does not exist inside the sandbox (Table 12.1) | Qualified on 6 October 2026: each sandbox shared the supervisor's terminal, a route out that no file-theft test exercised (F34), since fixed; host paths remain readable without file contents (F11, residual) |
| S9 | Met, narrowed | Memory exhaustion ended by the kernel, process creation refused at the cap, a 25% processor cap held at 25.1%, writing refused at the disk quota (Appendix C, T16) | Narrowed on evidence: "disk" means space, not I/O bandwidth, because the device's service manager does not delegate that control to an unprivileged user [16] |
| N1 | Met | Memory, latency and capacity reported against the unconfined arm, with no threshold (Table 12.5) | — |
| N2 | Met by reporting | Import-level results for 75 integrations and end-to-end results for 13 are reported separately and never combined (Tables 12.2 and 12.3) | — |
| N3 | Met | The framework refuses to start without the memory controller or from the wrong control-group position, and fails closed when the mediator stops (Section 9; Appendix E, `selftest_supervise`) | Strengthened during verification: a killed supervisor once left its sandbox running without a mediator (F30), and a sandbox did not restart when the platform returned (F29); both fixed |

All twenty requirements are met, eighteen as stated and two in a narrower form. S9 was narrowed by the evidence, and N2 is met by the way results are reported rather than by a measured rate. The history column also bears on how far the verdicts can be trusted. Eleven of the twenty rows changed after the criteria were frozen, and in four of them (C1, F3, S7, S8) verification found that a verdict had claimed more than the code supported. In each of those four, the code or the check was corrected and the criterion was left as written, so no verdict was restored by weakening the test it had failed.

---

## Appendix C — Threat register

This appendix gives the full register that Section 8 summarises. It follows ISO 31000's process [20]: criteria fixed first, threats identified with STRIDE [21] at each of the six trust boundaries, each threat rated before treatment, then treated, then scored against the running system. Table C.5 maps the register onto Corno and Mannella's eleven threats [5], so that the result can be checked against a model this project did not write.

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

Inherent risk is rated against Home Assistant as it stands, with no requirement of Section 3 implemented. The CM column gives the corresponding threat in Corno and Mannella's model [5].

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
| T15 | Process table limited to the sandbox | S8 | Demonstrated, paired: another process's environment read unconfined, nothing to read confined |
| T16 | Resource limits from the manifest | S9 | Partial: memory, processor time, processes and disk space bounded, each shown by a sandbox exceeding it; I/O bandwidth not bounded (R7); the persistent data folder checked against the disk bound only at start |
| T17 | Separate processes, so no shared heap | S1 | Demonstrated, paired, by the same heap walk as T01 |
| T18 | Attributed, tamper-evident record written before the action | S7 | Demonstrated, bounded by R4: modification, deletion and reordering each detected by both chains independently |
| T19 | Refusals counted per integration; past 100 in 10 s, one record, and the integration stopped until a person restarts it, never with more authority | S7, S9 | Demonstrated: cut off within 0.81 s after exactly 100 recorded refusals, while a second sandbox continued to be served |

Sixteen of the nineteen threats are demonstrated, six of them paired; one is partial and two are retained by decisions made before the evaluation. All five Critical inherent threats are among those demonstrated, which is the register's most important result, because one control, the separate process, answers the cause they share.

### C.4 Residual risks

The seven residual risks, R1 to R7, are given with their ratings and the reason each is retained in Table 8.4. One further residual sits within T14 and was found by measurement. The sandbox's filesystem binds the interpreter and its libraries at their host paths, so a confined integration can read the host's directory layout along those paths, including a user's name where the runtime is installed under a home directory. It cannot read any content outside its grant. Its likelihood is 5, because the exposure follows from the construction, and its impact 1, since a name and directory names give no capability and disclose no reading, so it is rated 5, Medium, and retained. The remedy is a deployment step, installation under a neutral path. Rated at impact 2 it would be High, and the appetite would then require the remedy.

T07's treatment also leaves a residual, and it falls within R2. Confinement stops an integration writing to entities it has not declared, but it cannot make the values it writes to its own entities true. An integration that publishes its own presence sensor can report a householder at home, and an automation the householder has built on that sensor will act on the report. The control bounds which entities an integration can forge, not whether its readings are honest, so this is the abuse of legitimately declared authority that R2 names, and it is retained with R2 as High and structural.

### C.5 The register against an external model

**Table C.5 — Corno and Mannella's eleven threats [5], scored through Table C.3's CM column**

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

## Appendix D — Full compatibility results

This appendix lists every integration measured at the import level, in both arms, so that a reader can check the central compatibility result of Section 12.2 row by row rather than accept its zero on trust. The result rests on a comparison of two columns: if confinement caused a failure, some integration would pass in the unconfined column and fail in the confined one. No row in either table does so.

Each integration was placed on a ladder of outcomes, from worst to best. *Not found* means the platform could not locate the integration; *import failed* means its main module could not be imported; *platform import failed* means the module imported but at least one of its entity platforms did not; and *platforms clean* means the module and every entity platform it declares imported. The ladder measures whether code loads, not whether it works, which is why Section 12.2 reports the thirteen integrations executed end to end separately and never combines the two figures. The unconfined arm imported each integration into a full Home Assistant instance; the confined arm imported it inside a sandbox with only the components it declares. Both arms ran on release 2026.8.3 on the Raspberry Pi 5. The results below are from the re-run of 3 October 2026, made after the platform instance used by every runtime was corrected; each corpus produced the same outcomes as in its first run.

The two corpora are drawn differently and share only `bermuda` and `browser_mod`, so 77 measurements cover 75 distinct integrations. The head-weighted corpus takes the most-installed integrations; 40 repositories were requested and 39 fetched, and two pairs of them install under the same domain (`govee` and `solarman`), leaving 37 integrations. The uniform corpus is a random draw of 40 from the whole community catalogue with a recorded seed (20260902). Installation counts are those recorded in each corpus manifest from Home Assistant's analytics [1], where 0 means that no installation reported the integration. Both manifests pin each integration to the commit whose files match the measured copy byte for byte (finding F21, Appendix F).

**Table D.1 — Head-weighted corpus (37 integrations), by installations**

| Integration | Installations | Unconfined | Confined |
|---|---|---|---|
| `hacs` | 379,326 | Import failed | Import failed |
| `sonoff` | 43,799 | Platforms clean | Platforms clean |
| `localtuya` | 32,222 | Platforms clean | Platforms clean |
| `alexa_media` | 29,308 | Platforms clean | Platforms clean |
| `spook` | 27,331 | Not found | Not found |
| `webrtc` | 26,804 | Platforms clean | Platforms clean |
| `frigate` | 26,484 | Platforms clean | Platforms clean |
| `browser_mod` | 26,109 | Platforms clean | Platforms clean |
| `alarmo` | 25,370 | Platforms clean | Platforms clean |
| `waste_collection_schedule` | 23,336 | Platforms clean | Platforms clean |
| `meross_lan` | 22,628 | Platforms clean | Platforms clean |
| `xiaomi_miot` | 21,657 | Platforms clean | Platforms clean |
| `scheduler` | 21,557 | Platforms clean | Platforms clean |
| `bambu_lab` | 19,980 | Import failed | Import failed |
| `nodered` | 18,180 | Platforms clean | Platforms clean |
| `xiaomi_home` | 18,084 | Platforms clean | Platforms clean |
| `watchman` | 17,956 | Platforms clean | Platforms clean |
| `adaptive_lighting` | 16,550 | Platforms clean | Platforms clean |
| `tapo_control` | 16,294 | Import failed | Import failed |
| `dreame_vacuum` | 14,793 | Platforms clean | Platforms clean |
| `battery_notes` | 14,405 | Platforms clean | Platforms clean |
| `powercalc` | 13,777 | Platforms clean | Platforms clean |
| `midea_ac_lan` | 12,605 | Platforms clean | Platforms clean |
| `solcast_solar` | 11,444 | Platforms clean | Platforms clean |
| `govee` | 10,230 | Platforms clean | Platforms clean |
| `smartthinq_sensors` | 10,016 | Platforms clean | Platforms clean |
| `homematicip_local` | 9,947 | Platforms clean | Platforms clean |
| `octopus_energy` | 9,820 | Platforms clean | Platforms clean |
| `solarman` | 9,690 | Platforms clean | Platforms clean |
| `eufy_security` | 9,683 | Platform import failed | Platform import failed |
| `dwd_weather` | 9,598 | Platforms clean | Platforms clean |
| `bermuda` | 9,385 | Import failed | Import failed |
| `nordpool` | 8,253 | Platforms clean | Platforms clean |
| `pirateweather` | 8,220 | Platforms clean | Platforms clean |
| `thermal_comfort` | 7,955 | Platforms clean | Platforms clean |
| `llmvision` | 7,866 | Platforms clean | Platforms clean |
| `ble_monitor` | 7,816 | Platforms clean | Platforms clean |

**Table D.2 — Uniform corpus (40 integrations), by installations**

| Integration | Installations | Unconfined | Confined |
|---|---|---|---|
| `browser_mod` | 26,109 | Platforms clean | Platforms clean |
| `bermuda` | 9,385 | Import failed | Import failed |
| `zendure_ha` | 3,746 | Platforms clean | Platforms clean |
| `network_scanner` | 2,700 | Platforms clean | Platforms clean |
| `apsystems_ecu_reader` | 815 | Platforms clean | Platforms clean |
| `polleninformation` | 695 | Platforms clean | Platforms clean |
| `solis_modbus` | 576 | Platforms clean | Platforms clean |
| `localtuya_rc` | 438 | Platforms clean | Platforms clean |
| `pronote` | 353 | Platforms clean | Platforms clean |
| `irrigationprogram` | 343 | Platforms clean | Platforms clean |
| `enphase_ev` | 302 | Platforms clean | Platforms clean |
| `oekofen_pellematic_compact` | 231 | Platforms clean | Platforms clean |
| `sessy` | 215 | Platforms clean | Platforms clean |
| `trakt_tv` | 215 | Platforms clean | Platforms clean |
| `nature_remo` | 181 | Platforms clean | Platforms clean |
| `qolsys_panel` | 163 | Platforms clean | Platforms clean |
| `saj_esolar_air` | 159 | Platforms clean | Platforms clean |
| `tvoverlay_ui` | 112 | Platforms clean | Platforms clean |
| `kamstrup_403` | 73 | Platforms clean | Platforms clean |
| `sonyavr` | 48 | Platforms clean | Platforms clean |
| `lifesmart` | 47 | Platforms clean | Platforms clean |
| `lightwave2` | 38 | Platform import failed | Platform import failed |
| `tasmota_mielhvac` | 13 | Platforms clean | Platforms clean |
| `ocado` | 8 | Platforms clean | Platforms clean |
| `skybellgen` | 8 | Platforms clean | Platforms clean |
| `regensburg_transport` | 5 | Platforms clean | Platforms clean |
| `honor_x3` | 1 | Platforms clean | Platforms clean |
| `alarm_clocks` | 0 | Platforms clean | Platforms clean |
| `als_sundance_marin` | 0 | Platforms clean | Platforms clean |
| `circuitsetup_energy_analyzer` | 0 | Platforms clean | Platforms clean |
| `ecobot` | 0 | Platforms clean | Platforms clean |
| `enki` | 0 | Platforms clean | Platforms clean |
| `ha_insights` | 0 | Platforms clean | Platforms clean |
| `kroki` | 0 | Platforms clean | Platforms clean |
| `next_rocket_launch` | 0 | Platform import failed | Platform import failed |
| `nuki_otp` | 0 | Platforms clean | Platforms clean |
| `smhi_brandrisk` | 0 | Platforms clean | Platforms clean |
| `trmnl_webhook_push` | 0 | Platforms clean | Platforms clean |
| `vacation_mode` | 0 | Platforms clean | Platforms clean |
| `warema_wms` | 0 | Platforms clean | Platforms clean |

The failures are the same in both arms, and so are their messages. Table D.3 gives each one with its cause. Every cause lies in the integration, the corpus or the platform release, and none in confinement. Three integrations import a package, `aiofiles`, that they do not declare and that no component of the default configuration installs, so they fail wherever that package is absent. Two use constants that Home Assistant has since removed. The remaining failures concern how one integration ships its interface and how another is laid out in its repository.

**Table D.3 — The nine failing measurements, identical in both arms**

| Integration | Corpus | Outcome | Message, both arms | Cause |
|---|---|---|---|---|
| `bambu_lab`, `tapo_control` | Head | Import failed | `ModuleNotFoundError: No module named 'aiofiles'` | An undeclared dependency |
| `bermuda` | Both | Import failed | `ModuleNotFoundError: No module named 'aiofiles'` | An undeclared dependency |
| `eufy_security` | Head | Platform import failed | `ImportError: cannot import name 'SOURCE_TYPE_GPS' from 'homeassistant.components.device_tracker'` | A constant removed from the platform |
| `lightwave2` | Uniform | Platform import failed | `ImportError: cannot import name 'COLOR_MODE_BRIGHTNESS' from 'homeassistant.components.light'` | A constant removed from the platform |
| `next_rocket_launch` | Uniform | Platform import failed | `ImportError: Exception importing custom_components.next_rocket_launch.sensor` | Inside the integration's sensor module |
| `hacs` | Head | Import failed | `ModuleNotFoundError: No module named 'custom_components.hacs.hacs_frontend'` | The interface is bundled when a release is built and is absent from a source checkout |
| `spook` | Head | Not found | `IntegrationNotFound: Integration 'spook' not found.` | The repository's directory layout |

One further measurement tested whether a fuller instance would rescue a failure in the confined arm. The harness re-ran `hacs` with every component it declares set up, and it failed with the same message, which confirms that the missing module belongs to the integration's packaging rather than to the components the sandbox omits.

The same runs also carried the count behind C1. Every source tree was hashed before and after its run, in all four runs, and no source file changed and no line differed. That count was first made on the head-weighted pair in September (75 trees across the two arms, Appendix B) and was extended to the uniform pair by this re-run.

---

## Appendix E — Self-test suites

The self-test suites are the evidence on which most verdicts in Appendix B rest, and each was written against a claim stated in the design before the suite existed. A suite is one of the 29 test programs that the suite runner executes: the base sandbox test and 28 suites, each named for what it checks. They were last run in full at the final fix of the writing phase (tag `fix-2026-10-f59`), twice on the Raspberry Pi 5, and all 29 passed both times. The count of checks in Table E.1 is the number of lines a suite marks as passed in its log; three suites report a paired comparison instead, because their result is a difference between two arms rather than a list of checks. Section 12.4 reports how the suites were themselves tested, by deliberate defects introduced into the code that some suite had to detect.

**Table E.1 — The 29 suites, grouped by what they protect**

| Suite | What it asserts | Checks passed |
|---|---|---|
| *Isolation and the published attacks* | | |
| `selftest` (base) | A sandbox built beside a secrets file, the platform's configuration store and a second integration's source sees only its own directory; the other files are absent rather than refused | 19 |
| `selftest_adversary` | A hostile integration inside a sandbox makes 39 attacks and one permitted control request; neither planted secret reaches it, and the durable record matches the decisions made | 43 |
| `selftest_adversary_baseline` | The same attacks with no sandbox: both planted secrets recovered and 11 attacks returning data, so the confined arm's result is a comparison | Paired: 2 of 2 secrets recovered |
| `selftest_gc` | The garbage-collector heap walk [5] reaches a live credential unconfined and nothing confined, while the same credential stays live in the mediator | Paired: 7 objects against 0 of 8,942 |
| `selftest_reads` | What an integration can see of a furnished home, confined and unconfined | Paired: 36 of 36 entities against 1 of 36 |
| `selftest_resources` | Each of the four resource bounds holds when a sandbox tries to exceed it, and a limit that cannot be enforced is refused rather than ignored | 15 |
| `selftest_flood` | An integration that keeps requesting what it may not have is stopped after a fixed number of refusals and is not restarted with more authority | 36 |
| *Policy, identity and the record* | | |
| `selftest_policy` | `lock.lock` does not grant `lock.unlock`; paths into the configuration root are rejected when the manifest is parsed; no manifest grants nothing; every decision names its clause | 33 |
| `selftest_c3` | An over-broad manifest is honoured, as the residual risk R1 states, and behaviour mismatched to the manifest is refused, each refusal naming a distinct clause | 17 |
| `selftest_channel` | Two sandboxes both claiming the same identity are each recorded under their true identity, which comes from the channel and not from the message | 11 |
| `selftest_audit` | Identity has three components, including the dependency versions installed; modification, deletion and reordering of records are detected by two chains that fail independently; the record is written before the action | 42 |
| `selftest_integrity` | The counter behind C1 gives the known answer on trees changed in known ways, and does not count the bytecode caches that a clean run leaves | 15 |
| `selftest_t12` | An update is checked against its own declaration, so a malicious update cannot inherit the grants of the version before it | 33 |
| `selftest_approval` | A sandbox starts only under a grant a person has approved, bound to the integration's identity and to the grant that was shown | 14 |
| `selftest_describe` | Every state an integration can be in has a plain-language rendering, with denials shown at the same weight as grants | 16 |
| *Network access* | | |
| `selftest_socket_pinning` | A connected TCP socket cannot be redirected; a connected UDP socket can, which is why datagrams are relayed rather than handed over | 6 |
| `selftest_fdpass` | A connected socket crosses into the sandbox intact, and four ways a hostile sender could abuse the passing are refused | 12 |
| `selftest_egress` | A declared host is reached, an undeclared one refused with its clause, a host declared by another integration refused, and a name resolving to a private address refused | 23 |
| `selftest_egress_shim` | Unmodified HTTP client libraries reach a declared host, and the sandbox never holds the host's real address | 7 |
| `selftest_egress_sandboxed` | Two real integrations in real namespaces poll their own hosts at once, and each is refused the other's | 18 |
| `selftest_local_tcp` | A declared port on a home-network device is reached, and undeclared ports and addresses are refused | 17 |
| `selftest_udp` | Datagrams reach declared ports through the relay, device discovery works, and the sandbox never holds a socket able to broadcast | 21 |
| `selftest_netshape` | The instrument that records an integration's network behaviour reports what a deliberately provoked behaviour should produce | 13 |
| *The platform, the supervisor and the user interface* | | |
| `selftest_bridge` | An unmodified integration in a sandbox publishes an entity, reads a declared one, finds an undeclared one absent, and has its service calls reach their targets | 14 |
| `selftest_push` | A state change reaches a sandbox only when its subscription was granted | 28 |
| `selftest_real_platform` | The mediator, acting as a non-administrator user, publishes into and acts on a live Home Assistant instance | 52 |
| `selftest_ws` | The mediator's WebSocket client reproduces the protocol specification's own example values | 9 |
| `selftest_supervise` | The supervisor stops a flooding sandbox, restarts one from the Repairs panel, restarts one when the platform returns, clears a dead supervisor's sandbox, and does not restart one that exited by itself | 50 |
| `selftest_keep` | What an integration stores survives a restart, within its disk bound, and nothing it could run from does | 14 |

Two suites deserve attention from a reader scanning the table, because each records a case in which an assumption failed. The first, `selftest_socket_pinning`, passes when something surprising is true. The network design originally assumed that a connected UDP socket, like a connected TCP socket, could not be redirected to another address; the suite found that it can, the design was changed to relay datagrams, and the suite now passes only while redirection works. A future kernel that pinned UDP sockets would therefore fail the suite and prompt a review, rather than leave a design resting silently on a changed fact. The second, `selftest_netshape`, exists because an instrument once misled the project. The first version of the network recorder reported 23 of 37 integrations attempting to reach the network, and that number reflected what the recorder attributed to the integration rather than what the integration did. Since then the recorder has been tested against behaviours whose answers are known in advance before any of its output is trusted.

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
