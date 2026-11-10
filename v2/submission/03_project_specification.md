# 3. Project Specification

This section sets out what the project was to build and how each part was to be judged. Every requirement was stated with its test before any code existed, so that the evaluation could not later be fitted to the implementation.

## 3.1 Objective

The objective is to design, build and evaluate a mechanism through which the authority of a Home Assistant community integration is declared, enforced while it runs and recorded, without changing the integration's code or the platform, and without relying on the honesty of the integration's author. The objective has a second half, because no published work reports what fraction of real, unmodified extensions still work once confined: to measure what confinement costs in compatibility, memory and delay, against the same integrations run without it, on hardware typical of a self-hosted home.

## 3.2 Scope

The project addresses community integrations, the Python packages that a household installs through HACS, the community catalogue (HACS, n.d.), onto a self-hosted Home Assistant installation running on one machine. Integrations are in scope because they run inside the platform's own process and therefore hold all of its authority. Add-ons are not, because they already run as separate containers (Home Assistant, n.d.-a). Table 3.1 lists what else was excluded.

**Table 3.1**
*What the project excludes*

| Excluded | Reason |
|---|---|
| Deciding whether an integration is malicious | The project bounds what an integration can do; it does not judge intent |
| Misuse of a granted permission | An integration allowed to unlock the door that unlocks it at night acts within its grant, so this remains a stated risk |
| Whether the code can be trusted | Supply-chain integrity is a separate question with its own literature (Ladisa et al., 2023) |
| Several users with different rights | The platform "assumes every user is trusted and does not enforce user privileges" (Home Assistant, n.d.-f), and changing that means changing the platform |

## 3.3 Constraints

Four constraints follow from the situation rather than from choice, and together they rule out most of the mechanisms used in earlier work.

**C1: Integrations run with their code unmodified.** Browser vendors could require extension authors to adopt a new permission model because the extension platform was new (Barth et al., 2010). Home Assistant cannot, because 4,220 custom integrations already report through its analytics (Home Assistant, n.d.-d), written by volunteers for an interface that gives them full authority. "Unmodified" refers to the code. Confinement still needs a permissions manifest for each integration, and since none ships one today, every manifest in the evaluation was written by the project.

**C2: Home Assistant is not modified.** The project has no authority over the platform, so a mechanism that needed a platform change would be a proposal rather than a control that a household could install.

**C3: Enforcement does not depend on the author's cooperation or honesty.** The closest earlier work relies on developers to declare truthfully what their plug-ins need, and its authors acknowledge that anyone with access to the source could alter it (Corno & Mannella, 2023). A malicious author declares whatever serves the attack, so the framework must hold an integration to its declaration whatever the code does, and grant nothing when there is no declaration.

**C4: The design runs on modest home hardware.** Home Assistant is installed on hardware ranging from full computers down to small single-board computers such as the Raspberry Pi. A design that works only at the top of that range would exclude part of its users, so every measurement was taken on a Raspberry Pi 5 with 4 GB of memory, without administrator rights except for one setting made at boot.

C1 and C3 together define the central difficulty. Confinement has to be imposed on code written on the assumption that it has none, by a party that is neither the code's author nor the platform's maintainer.

## 3.4 Requirements

Twenty requirements state what that confinement must achieve: the four constraints, four functional requirements (F), nine security requirements (S) and three non-functional requirements (N). Table 3.2 gives each one with the test it had to pass, shortened from the criteria fixed on 2 September 2026, before the evaluation ran. Appendix B gives the full criteria, where each requirement comes from, and its verdict.

**Table 3.2**
*Requirements and how each was to be judged*

| | The framework shall… | It passes if… |
|---|---|---|
| C1 | Run integrations with their code unmodified | No integration's code differs from its downloaded original after a run |
| C2 | Require no change to Home Assistant | Every run uses an unmodified official release, recorded in its result file |
| C3 | Not depend on the author's cooperation | A missing, an over-broad and a deliberately misleading manifest are each handled as the rules specify |
| C4 | Run on modest home hardware | Every performance figure comes from the Raspberry Pi 5 |
| F1 | Let a confined integration publish its devices | A confined integration's devices appear in Home Assistant and behave as native ones |
| F2 | Let a confined integration reach the services it declared | An integration polling a declared online service succeeds while confined |
| F3 | Express authority in a manifest | Every decision names the manifest clause that produced it |
| F4 | Show declared authority before it is granted | Each manifest is shown in plain language, with what is refused shown as prominently as what is allowed |
| S1 | Enforce outside the integration's process | The published technique for reaching another integration's objects (Corno & Mannella, 2022) finds nothing of the platform from inside the sandbox |
| S2 | Keep every platform credential out of the sandbox | No credential can be recovered from the sandbox's environment, files, processes or memory |
| S3 | Control reading and watching devices, not only operating them | A confined integration can read and watch only the devices it declared, compared with what the same integration reads unconfined |
| S4 | Control network access per integration | An integration is refused a host that only another integration declared |
| S5 | Separate operations of unequal risk | Permission to lock a door does not permit unlocking it |
| S6 | Deny by default | An integration with no manifest, or one that cannot be read, is granted nothing |
| S7 | Record every decision in a tamper-evident log | Altering, deleting or reordering an entry is each detected |
| S8 | Isolate files and processes | The 2021 file-theft pattern (Home Assistant, 2021a) succeeds without the framework and fails with it, on the same device and release |
| S9 | Bound processor, memory and disk use | An integration exhausting each in turn does not make the home's Home Assistant unresponsive |
| N1 | Report overhead against an unconfined baseline | Added delay, memory per integration and the number that fit on the device are reported against the same integrations unconfined |
| N2 | Report compatibility as measured | "Loads" and "runs end to end" are reported as separate numbers, never combined |
| N3 | Fail in a stated way | When the mediator stops, the framework refuses rather than carries on silently |

S9 was not in the first list. It entered when the threat model identified resource exhaustion as a threat (Section 8.3), and its test was fixed then, before anything was measured.

## 3.5 Key features

The design that answers these requirements has seven features, each described in Section 9.

1. **A permissions manifest** for each integration, which states what the integration may read, operate and contact; anything not declared is refused (Section 9.3).
2. **One sandbox per integration**, built from Linux kernel isolation features, with limits on processor, memory and disk (Section 9.2).
3. **A real but empty Home Assistant runtime in each sandbox**, so that the unmodified code runs against the platform's genuine helpers but sees only what it was granted (Section 9.2).
4. **A mediator outside the sandbox**, the only process holding a credential to the household's Home Assistant, which decides every request (Section 9.4).
5. **A bridge integration** through which a confined integration's devices appear in the household's installation (Section 9.4).
6. **A network gate** that lets each integration reach only the hosts it declared (Section 9.5).
7. **A tamper-evident record and approval in the Home Assistant interface**: every decision is recorded, and nothing runs until the householder has approved its grant in plain language (Sections 9.3, 9.6 and 9.7).

## 3.6 Deliverables

Table 3.3 lists what the project delivers: the framework, and the evidence a reader needs to check its claims.

**Table 3.3**
*Deliverables*

| | Deliverable |
|---|---|
| D1 | The confinement framework (supervisor, sandbox, mediator), its supervisor and mediator written with Python's standard library only |
| D2 | The bridge integration, which brings confined devices, approvals and repair notices into the Home Assistant interface |
| D3 | 35 self-test suites, and 92 deliberately planted defects that test the suites |
| D4 | Two fixed samples of real community integrations, the 37 most installed and 40 drawn at random, and a harness that runs each one with and without confinement |
| D5 | A set of attacks by a hostile integration, reproducing the published techniques and the threats in the threat model |
| D6 | A threat model following ISO 31000 (International Organization for Standardization, 2018) with STRIDE (Shostack, 2014) |
| D7 | A verification record: predictions committed before each run, a register of 153 claims and a list of 71 findings |
| D8 | A guide to reproducing the results, and this report |

## 3.7 Expected outcome

The expected outcome was stated as a claim that the evaluation could prove wrong: unmodified integrations can be confined at a cost worth paying. The claim divides into three assertions. Confinement defeats the published attack techniques that motivated it; integrations still work inside it; and a home device can afford it. Each assertion was given, before anything was measured, a result that would refute it. Every result is reported as a difference between the same integration run with and without confinement, on the same device and platform release, because only that difference separates the cost of the design from the cost of the platform. Section 11 describes how those measurements were made.
