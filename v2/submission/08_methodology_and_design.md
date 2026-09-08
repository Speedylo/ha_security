# 8. Methodology and Capstone Design

## 8.1 The method, and one rule it is written under

The project's method is ordinary engineering research — requirements traced to evidence, a threat
model before the design, a design justified against candidates, an implementation, and a paired
evaluation. Three rules were adopted at the start and are worth stating, because the results in
§12 are only interpretable if the reader knows them.

**Rule 1 — Every requirement traces to a finding, or it is cut.** Requirements that arrive from
intuition about what a sandbox ought to do are how scope inflates and how a design ends up
answering questions nobody asked.

**Rule 2 — The threat model is written before the architecture.** Placing it between requirements
and design means the controls answer threats enumerated independently of them. Written the other
way round, a threat model becomes post-hoc justification for a design that was going to be built
anyway, which is a recognisable failure mode and one an assessor is entitled to look for.

**Rule 3 — Predictions are registered before measurements, and superseded text is not edited to be
right.** Where a later section corrects an earlier one, the earlier text stands and gains a
forward pointer. This is deliberate: a reader can check what was believed *before* the number
arrived rather than only what is believed after. Six of eight registered predictions were wrong
and none was revised, and §13.1 argues that record is itself a result.

## 8.2 Threat model: framework and scope

**ISO 31000** [25] supplies the risk-management process; **STRIDE** [26] fills the identification
slot ISO 31000 deliberately leaves open, applied per trust boundary. §5.1 states how each clause is
discharged.

**In scope:** a self-hosted Home Assistant installation extended by third-party integrations,
together with the assets those integrations can reach. **The risk owner is the occupying
householder** — the party that owns the assets, carries the consequences, and has neither a
security function nor an incident-response capability. Naming them matters, because every
judgement in the model is calibrated to that owner and would be different for an organisation.

**Out of scope:** threats originating from a compromised platform, a hostile LAN, or physical
access. Platform maintainers are **trusted**: if the platform is hostile, no integration-level
control helps.

## 8.3 Assets and actors

**Table 8.1 — Assets**

| ID | Asset | Why it matters |
|---|---|---|
| A1 | **Physical control of the dwelling** — locks, alarms, garage doors | Life-safety and property; irreversible in effect |
| A2 | **Occupancy and behavioural data** | Enables physical burglary; irreversible once disclosed |
| A3 | **Stored credentials** | Lateral compromise beyond the home |
| A4 | **Camera and media streams** | Intimate privacy harm |
| A5 | **Platform availability** | Automations include alarms and heating |
| A6 | **Other integrations' state and secrets** | Reachable in-process, demonstrated |
| A7 | **The audit record** | Meta-asset: its integrity determines whether any other loss is attributable |
| A8 | **The home network** | Pivot target reachable from the gateway |

**Reversibility is the axis that makes these commensurable.** Disclosure is permanent;
availability is normally recovered. That is what justifies rating an outage below an exfiltration
of comparable drama, and it is applied consistently.

**Table 8.2 — Actors**

| ID | Actor | Evidence for plausibility |
|---|---|---|
| AC1 | Malicious integration author | No documented Home Assistant case; the capability is trivially available |
| AC2 | Compromised honest author | XZ Utils: two years of trust-building, then a backdoor [8] |
| AC3 | Remote attacker via a vulnerable integration | **Documented in this ecosystem** — 2021, eight integrations, unauthenticated [4][6] |
| AC4 | Co-resident compromised integration | **Demonstrated** — the garbage-collector technique [9] |
| AC5 | The user | Not an adversary, but a source of risk through action |
| AC6 | Platform maintainers | **Trusted**; out of scope |

AC3 is the only actor with documented realisation *in this ecosystem*, and AC4 the only one with a
demonstrated technique. **AC1 is the most severe and the least evidenced, and is stated as such
rather than inflated.**

## 8.4 Trust boundaries — and the finding is that four of six do not exist

| ID | Boundary | Status today |
|---|---|---|
| TB1 | Integration ↔ mediating component | **Absent.** Integration and platform share a process |
| TB2 | Mediating component ↔ Home Assistant | Exists as the platform's API surface; unscoped and unauthenticated per integration |
| TB3 | Integration ↔ external network | **Absent.** Unrestricted outbound |
| TB4 | Author and channel ↔ the user's machine | Exists procedurally; verifies structure not behaviour |
| TB5 | Integration ↔ host OS, filesystem, process table | **Absent.** Integration holds the platform's OS privileges |
| TB6 | Integration ↔ other integrations | **Absent.** Demonstrated crossable |

> **Figure 8.1 — [TO DRAW]** Home Assistant as it stands today, with the six trust boundaries
> overlaid; four of the six do not exist. Everything within the heavy border shares one
> operating-system process and one Python interpreter, so the boundaries marked ABSENT have no
> enforcement point anywhere in the running system. TB1 and TB2 are drawn as two curves with an
> empty gap between them: **that gap is where a mediating component would stand, and today nothing
> does.** Drawn with OWASP Threat Dragon [27]; the model and the rendering are generated from one
> source so they cannot drift.

**Three of the four missing boundaries are missing for one reason**, visible in the figure as a
single enclosure: the integration and the platform occupy the same process, so there is no
location at which any of the three could be enforced. This is why the register below finds four
Critical risks sharing a single cause, and why no combination of controls placed *inside* that
enclosure can address them.

## 8.5 Risk identification and evaluation

Eighteen threats, identified by applying STRIDE to each boundary. The full register with ratings
and justifications is **Appendix C**; the summary and the concentration it reveals are here.

| ID | Threat | Inherent |
|---|---|---|
| T01 | Integration bypasses mediation by acting on in-process objects | **25 Critical** |
| T03 | Integration modifies the mediating component or its policy in memory | **25 Critical** |
| T05 | Integration induces an undeclared service call — a confused deputy | **25 Critical** |
| T04 | Integration recovers the platform credential held by the mediator | **20 Critical** |
| T02, T06, T08, T09, T10, T12–T18 | Spoofing, disclosure, tampering, DoS and repudiation across TB2–TB6 | 12–16 High |
| T07, T11 | Cross-integration state corruption; DNS rebinding to an internal address | 8 Medium |

**Four Critical and twelve High inherent risks, and the Critical ones share a single cause.** That
concentration is the finding: **one architectural decision governs the majority of the risk**, and
treating it is worth more than treating any number of individual threats.

**A note on the likelihood ratings of T01, T03 and T05.** Their likelihood is 5 — *almost certain*,
meaning "occurs by default in normal operation". This is not hyperbole. An integration calling
`lock.unlock` today is not exploiting anything. **The register records ordinary platform behaviour
as Critical risk**, which is exactly what §2 argued and what an assessment of this system should
surface.

## 8.6 Treatment, and a requirement the threat model generated

Treatments are overwhelmingly **change consequence** — bounding what code can do — which is the
deliberate complement to the ecosystem's existing likelihood controls. Each treatment maps to a
requirement from §3.6; the full mapping is in Appendix C.

One outcome is worth reporting on its own, because it is evidence the ordering in §8.1 works.
**§3.6 contained no requirement addressing resource exhaustion**, because nothing in the problem
statement or the literature justified one and Rule 1 forbade inventing it. T16 — an integration
exhausting CPU, memory or disk — supplied the justification: availability is a security property,
automations include alarms and heating, and the closest published model treats gateway "resource
saturation up to a frozen state" as an explicit threat.

> **S9 — The framework shall bound an integration's consumption of CPU, memory and disk.**
> *Derived from T16, by this chapter.* *Verification:* an integration deliberately exhausting each
> resource is shown not to render the gateway unresponsive.

**The requirement was derived from an identified threat rather than from an implementer's
instinct, and it arrived at the point in the process where ISO 31000 says it should.**

## 8.7 Residual risks

Seven risks remain after treatment, each stated with why it is retained — because a residual risk
that is not written down has been ignored rather than accepted.

| | Risk | Residual | Why retained |
|---|---|---|---|
| **R1** | The over-declaring manifest | High | **Structural.** The browser precedent has the identical limit after fifteen years. Authority becomes *visible* and *bounded*, replacing a silent-full-trust default |
| **R2** | Abuse of legitimately declared authority | High, structural | An integration that declares `lock.unlock` may unlock the door at 03:00. Addressing it requires contextual integrity, a different mechanism with its own usability costs |
| **R3** | The mediator holds an unscoped credential | High | **An upstream platform limitation, not a design flaw here.** Home Assistant issues no read-only or per-domain token, so the mediator must hold full authority to mediate at all. §15.2 is the ask |
| **R4** | A local audit log cannot be authoritative against whoever controls the machine | Medium | Hash-chaining gives tamper-*evidence*, not tamper-proofing, and says nothing about events never recorded: **integrity is not completeness** |
| **R5** | Exfiltration through a declared host | High | **Structural.** Destination control cannot become content control without payload inspection, which is a privacy problem in itself and defeated by TLS |
| **R6** | The user is not equipped to evaluate a declaration | Medium | Out of scope, and honestly so. Enforcement does not depend on the user reading the manifest |
| **R7** | I/O bandwidth is unbounded | Medium | **Inherited.** cgroup v2's `io` controller is present on the host and *not delegated* to a user manager, so an unprivileged supervisor cannot enforce it at any effort |

**Summary against appetite.** No residual Critical risk remains. **Four residual High risks
remain, each structural and each stated.** The appetite declared that High residual risk is
acceptable only where it is structural and openly stated; this satisfies it only under that
clause, **and that should be said plainly rather than presented as a clean result.**

**R7 could not have been written when this model was drafted.** It was measured during the
evaluation, from a property of the host rather than of the design — which is the second occasion
in this project of a later stage generating something an earlier one had no basis to write, and
the reason "new threats surface from the evaluation itself" is a standing review trigger.

## 8.8 Relationship to the closest published model

Corno and Mannella's model [9] enumerates eleven threats across confidentiality, integrity,
availability, authentication, authorisation and non-repudiation. §12.5 scores this system against
**both** registers, so the security result is comparable against an existing published model
rather than against criteria invented here — the framing the independent systematic review [21]
proposed.

One difference is the sharpest available statement of what this project contributes. **Their
notion of *scope* is defined by documentation; this project makes it enforceable.** Their model
states that a plug-in's scope is "the set of variables, files, or resources that the plug-in can
legitimately access", and that "to legitimately access a resource, the plug-in documentation has
to include its possible use". Every one of their threats is defined relative to that scope. **The
closest published threat model therefore presupposes a notion of scope that has no
machine-readable representation and no enforcement mechanism.** The manifest of §9.4 is that same
notion of scope, made explicit, machine-checkable and enforced at runtime — which is why their
model can be used to evaluate this system directly, and why their model motivates it.

## 8.9 Limits of the threat model

- **It models threats originating from an integration.** Others are excluded by scope, not because
  they are unimportant.
- **The ratings are judgements.** Likelihood is anchored on documented occurrence and impact on the
  asset valuation, so both axes can be argued against rather than merely disputed. **The ordering
  is more robust than the values.**
- **A threat model enumerates what its author thought of.** This is not a hedge but the central
  methodological point: testing demonstrates the absence of *known* failures, never the absence of
  failures.
- **STRIDE is boundary-oriented** and is weaker on threats arising from the composition of
  individually permitted actions. R2 is the clearest example, and it is retained rather than
  solved.
