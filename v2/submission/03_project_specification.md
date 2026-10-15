# 3. Project Specification

This section fixes what the project set out to build and how each part was to be judged. Every requirement was traced to a finding in the problem statement or the literature and stated with its test before any code existed, so that the evaluation could not be fitted to the implementation afterwards.

## 3.1 Objective

The objective is to design, build and evaluate a mechanism through which the authority of a Home Assistant community integration is declared, enforced at run time and recorded, without modifying the integration's code or the platform and without relying on the honesty of the integration's author. Because no published work reports what fraction of real, unmodified extensions still function once confined, the objective has a second, research half: to measure what confinement costs in compatibility, memory and latency against an unconfined baseline, on hardware typical of self-hosted installations.

## 3.2 Scope

The project addresses community integrations: Python packages that Home Assistant loads into its own process, installed through HACS, the community catalogue [6], onto a self-hosted installation on one machine. Integrations are in scope because they share the platform's process and therefore all of its authority, whereas add-ons already run as separate containers [12]. Table 3.1 lists what was excluded and why.

**Table 3.1 — Exclusions**

| Excluded | Reason |
|---|---|
| Add-ons | Already isolated as containers [12], which shows that the platform accepts process isolation where its architecture allows it |
| Deciding whether an integration is malicious | The project bounds authority; it does not classify intent |
| Misuse of declared authority | An integration granted `lock.unlock` that unlocks the door at night acts within its grant, so this is a residual risk rather than a defect |
| A minimal or honest manifest | An author declares what they choose; the mechanism makes authority visible, bounded and recorded, which is a smaller claim than making integrations safe |
| Supply-chain integrity | Whether code can be trusted is a complementary question with its own literature [13] |
| Multi-user access control | The platform "assumes every user is trusted" [9], and changing that requires changing the platform |
| Whether users understand disclosures | A human-factors question; the project requires only that the grant be shown |

Four parties have a stake in what an installed integration can do. The user owns the devices and carries the risk, and must be able to see and bound what an integration may do without reading its code. The author wants the integration to work and should not have to change it. The platform project cannot underwrite community code, whose users "install them at their own risk" [3]. The attacker, a malicious author or one who has taken over an honest author's repository [8], is the party on whose behaviour enforcement must not depend. These interests produce the constraints.

## 3.3 Constraints

Four constraints are properties of the situation rather than choices, and together they rule out most mechanisms that prior work used.

**C1 — Integrations shall run with their code unmodified.** Chrome could require extension authors to adopt a new permission model because the platform was new [14]. Home Assistant cannot, because 4,220 custom integrations report through its telemetry [1], written by volunteers against an interface that presumes full authority. "Unmodified" refers to the code. Confinement additionally requires a permissions manifest per integration, which the framework accepts from the author or supplied with the installation; no existing integration carries one, so every manifest in the evaluation was written by hand by the project, and producing manifests at scale is unmeasured.

**C2 — Home Assistant shall not be modified.** The project has no authority over the platform, so a mechanism needing a platform change would be a proposal rather than a control a household could deploy.

**C3 — Enforcement shall not presuppose the author's cooperation or honesty.** The closest prior work relies on plug-in developers to write truthful declarations, and its authors acknowledge that "anyone accessing the integrations source code could alter it" [15]. A malicious author declares whatever serves the attack, so the framework must hold an integration to its declaration whatever its behaviour, and grant nothing when the declaration is absent.

**C4 — The design shall run on self-hosted, resource-constrained hardware.** Home Assistant is commonly installed on single-board computers, so every measurement was taken on a Raspberry Pi 5 with 4 GB of memory, without root privileges except for one boot-time change that enables the kernel's memory controller.

C1 and C3 together define the central difficulty: confinement must be imposed on code written on the assumption that it has none, by a party that is neither the code's author nor the platform's maintainer. The requirements state what that confinement must achieve.

## 3.4 Requirements

Fifteen further requirements, functional (F), security (S) and non-functional (N), were derived in the same way as the constraints. A sixteenth entered later, and its origin is evidence that the method worked: S9, a bound on resource consumption, had no basis in the problem statement or the literature and was added only when the threat model identified resource exhaustion as a threat. Table 3.2 summarises all twenty with their verdicts; Appendix B gives each one's derivation, criterion and evidence.

**Table 3.2 — Requirements and verdicts**

| | The framework shall… | Verdict |
|---|---|---|
| C1 | Run integrations with their code unmodified | Met: 75 source trees compared before and after the runs, no change |
| C2 | Require no change to Home Assistant | Met: every arm ran on the unmodified release 2026.8.3 |
| C3 | Not depend on the author's cooperation | Met: absent, over-broad and mismatched manifests each handled as specified |
| C4 | Run on resource-constrained hardware | Met: every measurement on the Raspberry Pi 5 |
| F1 | Let a confined integration publish entities | Met, including into a live Home Assistant instance |
| F2 | Let a confined integration reach declared network endpoints | Met by real integrations against their live services |
| F3 | Express authority in a declarative manifest | Met: every decision names the clause that produced it |
| F4 | Show declared authority before it is granted | Met: grants and denials rendered in plain language, at equal weight |
| S1 | Enforce outside the integration's process | Met, paired: the heap-walk attack reaches a credential unconfined and nothing confined |
| S2 | Keep every platform credential out of the sandbox | Met, paired |
| S3 | Mediate reads and subscriptions, not only writes | Met, paired: 36 of 36 entity states readable unconfined, 1 of 36 confined |
| S4 | Attribute and enforce network access per integration | Met: each of two concurrent integrations denied the other's host |
| S5 | Separate operations of unequal risk | Met: a grant of `lock.lock` does not permit `lock.unlock` |
| S6 | Deny by default | Met: an absent or unparseable manifest grants nothing |
| S7 | Record every decision in a tamper-evident log | Met: modification, deletion and reordering each detected |
| S8 | Isolate files and processes | Met, paired: the 2021 file-theft pattern recovers 2 of 2 secrets unconfined and 0 of 2 confined |
| S9 | Bound processor, memory and disk use | Met against narrowed wording: disk space, not I/O bandwidth |
| N1 | Report overhead against an unconfined baseline | Met: memory, latency and capacity reported |
| N2 | Report compatibility as measured, not asserted | Met by reporting: import-level for 75 integrations, end to end for 13, never combined |
| N3 | Fail in a stated way | Met: refuses to start without its preconditions and fails closed when the mediator stops |

All twenty requirements are met, two in a narrowed form. S9 was narrowed on evidence, because the device's service manager does not delegate control of I/O bandwidth to an unprivileged user [16]. N2 is met by how results are reported rather than by a rate, since most integrations need an account before they can run end to end. Some verdicts changed during verification, S3 being met only once state changes could be pushed to a sandbox, and Appendix B keeps that history. The design that meets these requirements has seven features.

## 3.5 Key features

Each feature names, in brackets, the requirements it answers.

1. **A permissions manifest** with eight clauses: seven grant capability (entity reads, subscriptions and writes; service calls; events; network access; files; enumeration of configuration entries; HTTP routes) and one bounds resources. Anything not declared is denied (F3, S5, S6).
2. **One sandbox per integration**, built from seven Linux namespaces [17], a seccomp filter [18] and a cgroup v2 slice bounding memory, processor time, processes and disk space [19] (S8, S9).
3. **A real but minimal Home Assistant runtime inside each sandbox**, so that the integration's unmodified code runs against the platform's genuine helpers while seeing only the state and services it was granted (C1, C2).
4. **An out-of-process mediator** that runs as an ordinary, non-administrator Home Assistant user, holds the only credential, and decides every request crossing each sandbox's single channel; identity is a property of the channel, not a claim in the message (S1, S2, S3).
5. **An egress broker** that resolves a declared host name itself and connects to the address it resolved, with the home network behind a separate permission (F2, S4).
6. **A tamper-evident audit log**, hash-chained and keyed, written before the action it records and naming the integration's identity and the deciding clause (F3, S7).
7. **Approval and recovery in the Home Assistant interface**: the grant shown in plain language, an approval bound to the integration's identity and to the grant shown, and Repairs issues that explain a stopped integration and never widen its permissions except through an action labelled as an approval (F4, N3).

## 3.6 Deliverables

Table 3.3 lists the framework and the evidence needed to check its claims.

**Table 3.3 — Deliverables**

| | Deliverable |
|---|---|
| D1 | The confinement framework: supervisor, sandbox and mediator, the supervisor and mediator using only Python's standard library |
| D2 | A Home Assistant integration that brings approvals and Repairs into the user interface |
| D3 | Twenty-nine self-test suites, and 53 hand-written mutants that test the suites |
| D4 | Two pinned corpora of real community integrations, 37 by install count and 40 drawn uniformly, and a harness that runs each one confined and unconfined |
| D5 | An adversarial suite reproducing the published attacks against the platform |
| D6 | A threat model of nineteen threats and seven residual risks, following ISO 31000 [20] with STRIDE [21] |
| D7 | A verification record: predictions committed before each run, a register of 153 claims, a log of 60 findings |
| D8 | A reproduction guide, and this report |

## 3.7 Expected outcome

The expected outcome was stated as a claim that the evaluation could refute: unmodified integrations can be confined at a cost worth paying. The claim divides into three assertions, that confinement defeats the published attacks that motivated it, that it leaves integrations able to run, and that a reference device can afford it, and each assertion received a falsifier before anything was measured. Every result is reported as a difference between a confined and an unconfined arm on the same host and platform release, because only that difference separates the cost of the design from the cost of the platform and the corpus. Section 11 sets out how those measurements were made.
