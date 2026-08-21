# Chapter 3 — Requirements

## 3.1 How these requirements were derived

Chapters 1 and 2 established a problem and an absence. This chapter converts them into
requirements, under one discipline: **every requirement must trace to a finding in Chapter 1
or 2, or it does not belong here.** Requirements that arrive from intuition about what a
sandbox ought to do are how scope inflates and how a design ends up answering questions
nobody asked. §3.8 gives the traceability matrix, and any requirement that cannot fill a row
in it has been removed.

A second discipline: each requirement states **how it will be verified**. A requirement that
cannot be tested is a preference. The verification column is what Chapter 7's evaluation
plan is built from, and writing it now — before any implementation exists — is what keeps
the evaluation from being fitted to whatever the implementation turns out to do.

Requirements use **shall** for mandatory and **should** for desirable-but-sacrificeable, and
are grouped as constraints (C), functional (F), security (S) and non-functional (N).

## 3.2 Stakeholders

Four parties have standing, and their interests do not coincide.

| Stakeholder | Interest | Consequence for requirements |
|---|---|---|
| **The user** | Runs the hub, owns the assets, carries the risk (§1.8) | Must be able to see and bound what an integration may do, without reading code |
| **The integration author** | Wants their integration to work; usually honest, occasionally not (§1.5) | Must not be required to change their code or cooperate (C1, C3) |
| **The platform project** | Maintains Home Assistant; cannot underwrite third-party code (§1.8) | Must not require changes to Home Assistant core (C2) |
| **The attacker** | Malicious author, or an adversary who compromises an honest one (§1.5) | Enforcement must not depend on the integration behaving (S2) |

The user is the party this work serves, because they are the one currently assigned risk
without means (§1.8).

## 3.3 Constraints

These are not choices. They are properties of the situation, and they eliminate most of the
designs that prior work used (Table 2.1).

**C1 — Integrations shall run unmodified.**
No change to integration source may be required. *Derivation:* §2.2 — Chrome could require
developers to migrate because it was a new platform; Home Assistant cannot, with 4,220
existing integrations written by volunteers (§1.3). Table 2.1 records this as the row where
every prior smart-home mechanism's assumption fails.
*Verification:* the compatibility evaluation reports integrations run with **zero** source
lines changed, counted mechanically.

**C2 — Home Assistant core shall not be modified.**
The design must be deployable as an addition to a stock installation. *Derivation:* §1.8 and
Table 2.1 — the platform is community-maintained and this work has no authority to change
it; a solution requiring a core patch is a proposal, not a deployable control.
*Verification:* the framework is demonstrated against an unmodified, official Home Assistant
release, with the version recorded.

**C3 — Enforcement shall not presuppose the author's cooperation or honesty.**
*Derivation:* §2.4.2 — the MUD architecture requires developers to write declarations, and
its authors acknowledge that "anyone accessing the integrations source code could alter it",
proposing developer allow-lists as mitigation. §1.5 establishes that the author may be
malicious or compromised. A control that assumes a well-behaved author is a likelihood
control (§1.6), and the missing control is one on impact.
*Verification:* the adversarial evaluation includes an integration whose declared manifest is
absent, over-broad, and deliberately mismatched to its behaviour.

**C4 — The design shall run on self-hosted, resource-constrained hardware.**
*Derivation:* §1.1, Table 2.1 — Home Assistant is self-hosted, commonly on single-board
computers. A design requiring a vendor cloud is inapplicable by construction.
*Verification:* measured on a Raspberry Pi-class device, reporting per-integration memory
and added latency.

## 3.4 Functional requirements

**F1 — Integrations shall be able to publish entities and states into Home Assistant.**
Publishing state is what an integration is *for*; a framework that confines an integration
into uselessness has not solved the problem. *Derivation:* §1.2, §1.2.1 — an integration is
what connects a device or service to the entity model, and no add-on can do that job in its
place.
*Verification:* entities published by a confined integration are present in Home Assistant
and behave as native entities under the measures used in Chapter 7.

**F2 — Integrations shall be able to reach declared external network endpoints.**
*Derivation:* §1.7, Table 1.2 — integrations exist largely to contact device and cloud APIs.
Egress is a required capability, not a deniable one, which is why a blanket network denial
is not an available design.
*Verification:* an integration polling a declared remote API completes successfully while
confined.

**F3 — An integration's required authority shall be expressed in a declarative manifest.**
The manifest is the security contract: the unit that is written, shown to the user, and
enforced. *Derivation:* §1.10 — the missing mechanism is a way for authority to be
"declared, enforced and audited"; §2.2 — the manifest model is established practice in
browsers.
*Verification:* the manifest schema is specified in Chapter 5 and every enforcement decision
in the evaluation is attributable to a manifest clause.

**F4 — The declared authority shall be presentable to the user before installation.**
*Derivation:* §1.8 — the user "cannot see what an integration intends to access before
installing it". Visibility is half of what is missing; enforcement alone would leave the
user informed of nothing.
*Verification:* demonstrated by rendering the manifest of each evaluated integration in
human-readable form. **Note:** this requirement concerns *availability* of the information,
not user comprehension; whether users act correctly on such disclosures is a
human-factors question outside this project's scope (§3.7).

## 3.5 Security requirements

**S1 — Enforcement shall occur outside the integration's own execution context.**
*Derivation:* §2.4.1, decisively. Corno and Mannella demonstrate an integration walking the
Python garbage collector to obtain another integration's live object and read and modify its
private state. Any permission layer implemented as an in-process wrapper is therefore
reachable and defeatable by the code it purports to constrain — including any credential it
holds. This single finding eliminates the entire class of in-process designs.
*Verification:* an adversarial test attempts the published garbage-collector technique and
attempts to locate the mediating component and its credential from within the sandbox.

**S2 — The sandbox shall not hold a credential granting unmediated platform access.**
*Derivation:* §1.7 and §2.4.1 — if the confined code holds a token that Home Assistant
honours, it can bypass mediation entirely and the manifest becomes decorative. The mediating
component holds the credential; the integration holds none.
*Verification:* adversarial tests attempt to recover a platform credential from the sandbox's
environment, filesystem, process table and memory.

**S3 — Mediation shall cover reads and subscriptions, not only writes.**
*Derivation:* §1.7, Table 1.2 — the first row of the authority table is *entity states*, and
its consequence is occupancy, presence, sleep patterns and absence from home. A design
mediating only state changes would leave surveillance untouched, which is the majority of the
privacy harm.
*Verification:* a confined integration attempting to read and to subscribe to undeclared
entities is denied, with a paired baseline measuring what is readable without the framework.

**S4 — Egress shall be attributable and enforceable per integration.**
*Derivation:* §2.4.2 — the closest prior work consolidates all plug-ins' declarations into
one gateway-level profile enforced by a firewall that sees a single host, so the effective
policy for any plug-in becomes the union of every plug-in's declarations. Per-integration
attribution is precisely what that design cannot provide, and it is where this project
differs.
*Verification:* an integration is denied a host declared only by a *different* integration.

**S5 — The manifest's granularity shall distinguish operations of asymmetric risk.**
*Derivation:* §2.3 — Tyche's observation that physical operations are risk-asymmetric:
`lock.unlock` is not the inverse of `lock.lock` in risk terms, yet a domain-granular
permission grants both. Granularity is a security property of the manifest, not a formatting
decision.
*Verification:* a manifest permitting a lock operation is shown not to permit its
risk-asymmetric counterpart.

**S6 — Enforcement shall default to denial.**
Anything not declared is refused. *Derivation:* §1.10 — the objective is to bound authority,
and an allow-by-default policy bounds nothing; §3.3 C3 — an absent or malformed manifest must
fail safe, since a malicious author may simply omit it.
*Verification:* an integration with no manifest, and one with an unparseable manifest, are
both denied all mediated capability.

**S7 — Every enforcement decision shall be recorded in a tamper-evident log.**
*Derivation:* §1.8 — the user "cannot detect afterwards what it accessed"; §2.4.3 — Thingnes
and Meland report that extensions "are free to perform actions without being authenticated,
reducing the ability to audit logs and locate malicious extensions". Attribution is the
missing property, not merely logging.
*Verification:* decisions appear in the log with the integration's identity; modification,
deletion or reordering of records is shown to be detectable. **Stated limit:** tamper-*evidence*
is not tamper-proofing, and a local log cannot be authoritative against an adversary who
controls the machine (§3.7).

**S8 — Filesystem and process isolation shall confine the integration to declared resources.**
*Derivation:* §1.7 — the filesystem row of Table 1.2, stated by the platform itself: an
integration can read "any file that is accessible by the Home Assistant process… includ[ing]
any credential that you might have stored". This is the capability exercised in the 2021
disclosures (§1.5).
*Verification:* the 2021 file-theft pattern is reproduced against a baseline installation and
shown to be blocked under the framework.

## 3.6 Non-functional requirements

**N1 — Overhead shall be small enough not to change how the platform is used.**
Mediation adds a boundary crossing to every operation. *Derivation:* C4 — on a
resource-constrained host, a control that halves the number of integrations a user can run
will not be adopted, and an unadopted control protects nobody.
*Verification:* added latency per state update, memory per confined integration, and maximum
concurrent confined integrations, all measured on the target hardware and reported against
an unconfined baseline. No threshold is asserted in advance; the figures are reported and
discussed.

**N2 — Compatibility cost shall be measured and reported, not asserted.**
*Derivation:* §2.8, contribution 3 — no prior work reports what fraction of real, unmodified
extensions still function under confinement, and this is the contribution nobody else has
data for. It is therefore a requirement on the *evaluation*, not only on the artifact.
*Verification:* Chapter 7 reports the number of real integrations executed end-to-end under
confinement, separately from any count of integrations that merely import successfully —
the two shall never be conflated, since import success is an upper bound on compatibility
and not a compatibility claim.

**N3 — The framework should degrade to a stated failure mode rather than silently.**
*Derivation:* §1.6 — the user's exposure today is invisible; a framework that fails open and
silently would reproduce that property while implying protection.
*Verification:* behaviour on mediator unavailability is specified and tested.

## 3.7 Non-goals

Stated explicitly, because an unstated scope boundary reads as an oversight, and because
several of these will be asked about.

| Non-goal | Why excluded |
|---|---|
| **Add-ons** | Already isolated as containers (§1.2.1). The problem is specific to in-process integrations. |
| **Determining whether an integration is malicious** | This project bounds authority; it does not classify intent. Detection is a likelihood control, which the ecosystem already has in community review (§1.6). |
| **Preventing abuse of legitimately declared authority** | A lock integration that declares `lock.unlock` and then unlocks the door at 03:00 is acting inside its declaration. Manifest confinement structurally cannot prevent this; it is a **residual risk** carried into Chapter 4, not a defect to be engineered away. The browser-extension precedent (§2.2) has the same limit. |
| **Guaranteeing the manifest is minimal or honest** | An author declares what they choose (C3). The mechanism converts *invisible* authority into *declared, bounded and audited* authority. That is the entire claim, and it is smaller than "the manifest makes integrations safe". |
| **Supply-chain integrity** | Signing, provenance and update integrity are likelihood controls addressed by an existing literature (§2.5). Complementary, not in scope. |
| **Multi-user access control** | Home Assistant "assumes every user is trusted" (§1.8). Changing that is a platform-level concern (C2). |
| **User comprehension of disclosures** | F4 requires the information be available. Whether users understand and act on permission disclosures is a human-factors research question with its own literature. |

## 3.8 Traceability

Every requirement, and where it comes from. A row that could not be filled meant the
requirement was cut.

| Req | Source | Nature of source |
|---|---|---|
| C1 | §2.2 (Barth et al.); Table 2.1 | Prior work's assumption that fails here |
| C2 | §1.8; Table 2.1 | Platform's stated position |
| C3 | §2.4.2 (authors' own acknowledgement); §1.5 | Limitation of closest prior work |
| C4 | §1.1; Table 2.1 | Property of the deployment |
| F1 | §1.2, §1.2.1 | Platform architecture |
| F2 | §1.7, Table 1.2 | Capability required for function |
| F3 | §1.10; §2.2 | The stated missing mechanism |
| F4 | §1.8 | User cannot see intent before install |
| S1 | §2.4.1 (demonstrated GC attack) | Published experimental result |
| S2 | §1.7; §2.4.1 | Architecture + published result |
| S3 | §1.7, Table 1.2 row 1 | Authority analysis |
| S4 | §2.4.2 (consolidation limitation) | Limitation of closest prior work |
| S5 | §2.3 (Tyche) | Published design principle |
| S6 | §1.10; C3 | Objective + adversarial assumption |
| S7 | §1.8; §2.4.3 (SLR) | User gap + independent review |
| S8 | §1.7; §1.5 (2021 disclosures) | Platform's own impact statement |
| N1 | C4 | Deployment constraint |
| N2 | §2.8 contribution 3 | Research contribution |
| N3 | §1.6 | Invisibility is the current failure |

Two observations from the matrix itself. First, **four requirements (C3, S1, S4, S5) derive
from limitations or findings in prior work rather than from the problem statement** — which
is the practical return on Chapter 2 having read the closest work carefully rather than
distinguishing it at arm's length. Second, **S1 is the highest-leverage requirement in the
chapter**: it eliminates every in-process design on the strength of one published
experiment, and it is what forces the architecture of Chapter 5.

## 3.9 What this chapter fixes, and what it leaves open

Fixed: the design must place enforcement outside the integration's process (S1), hold the
credential away from it (S2), mediate reads as well as writes (S3), attribute egress per
integration (S4), default to denial (S6), and be measurable on modest hardware (C4, N1) —
all without touching either the integration (C1) or the platform (C2).

Left open, deliberately, for Chapter 5: *how* an unmodified integration can execute outside
the process it was written to run inside; what the manifest's schema and granularity are in
detail (S5 constrains but does not specify it); who authors the manifest, given C3; and what
the mediating component's interface looks like.

Chapter 4 comes first. The threat model determines which of these open choices are
security-relevant and which are merely engineering, and a set of controls chosen before the
threats are enumerated will read as post-hoc justification for a design that was going to be
built anyway. The order is the argument.
