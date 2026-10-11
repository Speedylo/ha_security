# 8. Methodology and Capstone Design

## 8.1 The method, and three rules it is written under

The project follows an engineering research method: requirements traced to evidence, a threat model written before the design, a design chosen against alternatives, an implementation, and a paired evaluation that runs each integration with and without confinement. The results in Section 12 can only be read correctly if three rules that governed this method are known, because each rule constrains what a result is allowed to mean.

The first rule is that every requirement traces to a finding, or it is cut. A requirement that arrives from intuition about what a sandbox ought to do is how scope inflates, and how a design comes to answer questions that the problem never posed. Section 8.4 shows the rule producing a requirement rather than only removing them.

The second rule is that the threat model is written before the architecture. Placed between the requirements and the design, the threat model enumerates threats independently of the controls that later answer them, in the order ISO 31000 prescribes, where risks are assessed before they are treated [25]. Written afterwards, a threat model could only check the controls that already exist, and the threats that no control answers would be the ones least likely to be found.

The third rule is that a prediction is committed before the measurement it predicts, and that text later found wrong is corrected with a dated note rather than rewritten. A reader can then check what was believed before a number arrived, not only what is believed after it. Of the first eight predictions the project registered, six were wrong and none was revised, a record that Section 13 treats as a result in its own right. The same rule governs the verification described in Section 8.6, so the threat model and the evidence that tests it were both fixed before the outcomes that could have shaped them.

## 8.2 Threat model: framework, scope and owner

The threat model follows ISO 31000 for the risk-management process [25] and uses STRIDE to identify threats, applied to each trust boundary in turn [26]. ISO 31000 does not prescribe a technique for identifying risks [25], so the two are complementary: the standard fixes the process from context to treatment, and STRIDE fills the one step the standard leaves open. The process begins by fixing its context, which here means what is in scope and whose risk is being managed.

The system in scope is a self-hosted Home Assistant installation extended by third-party integrations, together with the assets those integrations can reach. The risk owner is the householder who lives with it: the party that owns the assets and bears the consequences, but has no security function and no means of responding to an incident. Every rating in the model is calibrated to that owner, and would differ for an organisation with a security team.

Three sources of threat are out of scope: a compromised platform, a hostile local network, and physical access. The platform's maintainers are trusted, because if the platform itself is hostile no control at the level of an integration can help. This exclusion has a consequence that the design inherits directly. Since F57, an administrator of the house's Home Assistant can approve a grant from the Repairs panel (Section 9.3), so a compromised administrator account could approve a wider grant than intended. That case belongs to the compromised platform excluded here, which is why Section 9.8 records it as a limit of the architecture rather than as a threat this model treats.

## 8.3 Assets, actors and trust boundaries

The assets an integration can reach range from the physical control of the home to the audit record that makes any other loss attributable, and Table 8.1 lists them. Reversibility is the axis that makes them comparable. A disclosure cannot be undone, whereas availability is normally recovered, which is why the model rates an outage below an exfiltration of similar apparent severity, and it applies that judgement consistently.

**Table 8.1 — Assets**

| ID | Asset | Why it matters |
|---|---|---|
| A1 | Physical control of the dwelling: locks, alarms, garage doors | Life safety and property; irreversible in effect |
| A2 | Occupancy and behavioural data | Enables burglary; irreversible once disclosed |
| A3 | Stored credentials | Lateral compromise beyond the home |
| A4 | Camera and media streams | Intimate privacy harm |
| A5 | Platform availability | Automations include alarms and heating |
| A6 | Other integrations' state and secrets | Reachable in-process, as demonstrated |
| A7 | The audit record | Its integrity decides whether any other loss can be attributed |
| A8 | The home network | A pivot target reachable from the gateway |

The actors in Table 8.2 differ in how strongly their threat is evidenced, and the model states that difference rather than levelling it. A remote attacker exploiting a vulnerable integration (AC3) is the only actor documented in this ecosystem, through eight integrations disclosed in 2021 with unauthenticated flaws [4], [6]. A co-resident compromised integration (AC4) is the only one with a demonstrated technique: Corno and Mannella reached another integration's live objects by walking Python's garbage collector [9]. A malicious author (AC1) is the most severe actor and the least evidenced, and is stated as such rather than inflated.

**Table 8.2 — Actors**

| ID | Actor | Evidence for plausibility |
|---|---|---|
| AC1 | Malicious integration author | No documented Home Assistant case; the capability is trivially available |
| AC2 | Compromised honest author | XZ Utils: a contributor took part in maintenance for 2.6 years, then inserted a backdoor [8] |
| AC3 | Remote attacker via a vulnerable integration | Documented in this ecosystem: 2021, eight integrations, unauthenticated [4], [6] |
| AC4 | Co-resident compromised integration | Demonstrated: the garbage-collector technique [9] |
| AC5 | The user | Not an adversary, but a source of risk through action |
| AC6 | Platform maintainers | Trusted; out of scope |

Six trust boundaries separate these actors from the assets, and in today's Home Assistant four of the six do not exist. Figure 8.1 shows why. The integration and the platform share one operating-system process and one Python interpreter, so the boundaries between an integration and the mediating component (TB1), the network (TB3), the host (TB5) and other integrations (TB6) have no point anywhere in the running system at which they could be enforced. The two that exist, the platform's API surface (TB2) and the distribution channel (TB4), constrain an integration's structure but not its behaviour.

![Figure 8.1](../figures/fig_4_1_current_state.svg)

**Figure 8.1 — Home Assistant as it stands, with the six trust boundaries overlaid.** Everything within the heavy border shares one process; the four boundaries marked ABSENT have no enforcement point. The gap between TB1 and TB2 is where a mediating component would stand, and today nothing does. Drawn with OWASP Threat Dragon [27] from one source, so the model and the figure cannot drift.

The confined design instantiates the four missing boundaries, and Figure 8.2 draws it on the same canvas so that the difference between the two figures carries the argument. Five flows present in Figure 8.1 are absent from Figure 8.2, and none of them is refused by a check: the stores they read are not in the sandbox's view, and the integrations no longer share a process, so there is no request to make. TB2 is narrowed rather than closed. The mediator connects as an ordinary Home Assistant user, so it holds no administrative function but can still operate every device. One flow is new: no grant reaches a sandbox until a person has approved exactly what was shown.

![Figure 8.2](../figures/fig_8_2_confined.svg)

**Figure 8.2 — The confined design, on Figure 8.1's canvas.** Each integration runs in its own sandbox and reaches the platform only through the mediator. TB1, TB3, TB5 and TB6 now exist, and TB5 and TB6 are crossed by no flow at all; TB4 is unchanged and TB2 is narrowed (residual risk R3). Flow A is the approval (Section 9.3).

## 8.4 Risks, treatment, and a requirement the model generated

Applying STRIDE to each boundary identified eighteen threats, and their concentration is the model's main finding. Four are Critical and twelve High, and all four Critical threats share a single cause, the shared process, as the summary in Table 8.3 shows. The full register, with every rating and its justification, is in Appendix C.

**Table 8.3 — Threat summary (inherent risk)**

| ID | Threat | Inherent |
|---|---|---|
| T01 | Integration bypasses mediation by acting on in-process objects | 25 Critical |
| T03 | Integration modifies the mediating component or its policy in memory | 25 Critical |
| T05 | Integration induces an undeclared service call, as a confused deputy | 25 Critical |
| T04 | Integration recovers the platform credential held by the mediator | 20 Critical |
| T02, T06, T08–T10, T12–T18 | Spoofing, disclosure, tampering, denial of service and repudiation across TB2–TB6 | 12–16 High |
| T07, T11 | Cross-integration state corruption; DNS rebinding to an internal address | 8 Medium |

The likelihood of T01, T03 and T05 is rated 5, almost certain, meaning that the event occurs by default in normal operation. The rating is not an exaggeration. An integration that calls `lock.unlock` today exploits nothing, so the register records ordinary platform behaviour as Critical risk. Since one architectural decision governs most of the risk, treating that decision is worth more than treating any number of individual threats, and that is the choice Section 9 describes.

The treatments overwhelmingly change consequence rather than likelihood: they bound what an integration's code can do, which complements the ecosystem's existing control on what may be listed, a structural review before an integration enters the default catalogue [5]. Each treatment maps to a requirement from Section 3, and one requirement did not exist until the model produced it. Section 3 contained no requirement on resource exhaustion, because neither the problem statement nor the literature justified one and the first rule forbade inventing it. T16, an integration exhausting CPU, memory or disk, supplied the justification: availability is a security property when automations include alarms and heating, and the closest published model treats a gateway's "resource saturation up to a frozen state" as a threat [9]. Requirement S9, that the framework shall bound an integration's consumption of CPU, memory and disk, was therefore derived from an identified threat, at the point in the process where ISO 31000 places it [25].

## 8.5 Residual risks

Seven risks remain after treatment, and each is stated with the reason it is retained, because a residual risk that is not written down has been ignored rather than accepted. Table 8.4 lists them.

**Table 8.4 — Residual risks**

| | Risk | Residual | Why retained |
|---|---|---|---|
| R1 | The over-declaring manifest | High | Structural: a manifest bounds an integration to its declaration but cannot make the declaration minimal. Barth et al. found that 76% of the browser extensions they studied used unnecessarily powerful APIs [12]. Authority becomes visible and bounded instead of silent and total |
| R2 | Abuse of legitimately declared authority | High, structural | An integration that declares `lock.unlock` may unlock the door at 03:00; preventing that needs contextual integrity, a different mechanism with its own usability costs |
| R3 | The mediator's credential still reaches every device | High, narrowed | The mediator runs as an ordinary user (F45): it can no longer create users, change the configuration or install integrations, but it can operate every device, because the platform's per-domain policy cannot be configured through a supported interface |
| R4 | A local audit log cannot be authoritative against whoever controls the machine | Medium | Hash chaining gives tamper evidence, not tamper proofing, and says nothing about events never recorded |
| R5 | Exfiltration through a declared host | High | Structural: destination control cannot become content control without inspecting payloads, which is itself a privacy problem, and TLS makes the data visible only to its two endpoints [47] |
| R6 | The user is not equipped to evaluate a declaration | Medium | Out of scope: enforcement does not depend on the user reading the manifest |
| R7 | Input and output bandwidth is unbounded | Medium | Inherited: systemd delegates only the `cpu`, `memory` and `pids` controllers to a user's service manager [48], so the unprivileged supervisor cannot apply the `io` controller |

R3 changed during verification, and the change illustrates the third rule at work. The model originally stated that Home Assistant issues no scoped token, so the mediator had to hold full authority. Checked against the platform's own release, that was wrong: a token carries its user's permissions, and an entity policy by domain is enforced. The mediator had held an administrator's token only because this project's bridge admitted no one else (finding F45). It now runs as an ordinary user, which removes every administrative function from its reach. The risk stays High because the locks of A1 are still reachable, but its reason is now narrower and exact: the platform's per-domain policy exists, yet no supported interface creates one.

No Critical residual risk remains, and four High residual risks do, each structural and each stated. The appetite declared for this owner accepts High residual risk only where it is structural and openly stated, so the design satisfies the appetite under that clause, and the result should be read that way rather than as a clean one.

## 8.6 How the claims were verified

Before the engineering cut-off, every claim in the report was entered in a register with the evidence behind it, the commit on which it was measured and a pass criterion fixed before any rerun. The register holds 153 claims: 119 verified by a test or measurement, 27 qualified, five argued rather than measured, and two withdrawn. The tier decides the wording used later, so that verified claims "show", qualified claims "suggest", and argued claims are presented as argument.

Each measurement and each fix was preceded by a prediction note committed to the repository before the run. The repository holds 34 such notes, and a script checks that each note was committed before its first result and that no prediction line was changed afterwards. A prediction that fails is reported as failed. When the first fix for F57's approval screen was regressed, for instance, the start that followed an approval crashed; the failure is recorded in the note, and the correction carries its own tag.

A suite that passes shows that the code does what the suite checks, but not that the suite checks what the report claims. Mutation testing narrows that gap [46]. Each security-relevant check in the framework was removed or inverted by a hand-written mutant, one per enforcement point, and a mutant counts as killed when at least one suite fails with it applied. There are 53 such mutants; every one was killed when it was introduced or last rerun, except one that is equivalent to the original code on the reference interpreter. Automated mutation of the mediator and the manifest parser was considered and not run, a decision Section 14 records.

Faults around the framework were injected as well, because the suites test misbehaving integrations far more than failing surroundings. Nine faults, from a sandbox dying mid-message to the wall clock jumping an hour, were each run against a criterion fixed beforehand; five held as designed, and four exposed defects that were fixed and retested. Finally, the reproduction instructions were followed from a fresh clone of the repository. Following them on a freshly imaged device remains open (finding F18), because no spare memory card was available. These methods tested the code frozen at the cut-off; the code that changed after it needed a rule of its own.

The writing of this report turned up defects that had to be fixed after the cut-off. Each such fix received its own prediction note, a test shown to fail before it, its own tag and a regression run of the suites, and every one is listed in Appendix F. One full rerun of every measurement, mutant, suite and fault follows the last fix, at the final tag, so the numbers in Section 12 come from one version of the code.

## 8.7 What the method does not establish

The method has three limits that bound how far its results reach. First, no independent adversary attacked the framework. The plan included one, and it was dropped because the framework was built with AI assistance, so neither the author nor the assistant would have been independent of the assumptions that built it. The security results therefore rest on attacks the project wrote itself, and a security review that found a sandbox escape missed by every suite (F34) is the strongest evidence that attacks the builders did not imagine exist. Second, STRIDE is oriented to boundaries and is weaker on threats that arise from combining individually permitted actions; R2 is the clearest case, and it is retained rather than solved. Third, the ratings are judgements: likelihood is anchored on documented occurrence and impact on the asset valuation, so both can be argued with rather than merely disputed, and the ordering of the risks is more robust than their values. Within these limits, Section 9 describes the architecture that the treatments produced, and Section 12 measures it.
