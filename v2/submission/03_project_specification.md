# 3. Project Specification

## 3.1 Objective

To design, build and evaluate a mechanism by which a Home Assistant community integration's
required authority is **declared, enforced at runtime and audited** — without modifying the
integration, without modifying Home Assistant, and without depending on the integration author's
cooperation or honesty — and to **measure what that confinement costs** in compatibility, memory
and latency against an unconfined baseline on representative hardware.

The objective is deliberately two-part. The mechanism is the engineering; the measurement is the
research, because no published work reports what fraction of real, unmodified extensions still
function once confinement is applied.

## 3.2 Scope

**In scope:** third-party *integrations* — Python modules loaded into the Home Assistant process
— installed through HACS onto a self-hosted installation on a single machine.

**Out of scope**, each for a stated reason:

| Non-goal | Why excluded |
|---|---|
| **Add-ons (apps)** | Already isolated as containers [3]. The problem is specific to in-process integrations, and the existence of add-ons shows the platform already accepts process isolation where its architecture permits it |
| **Determining whether an integration is malicious** | This project bounds authority; it does not classify intent. Detection is a likelihood control the ecosystem already has |
| **Preventing abuse of legitimately declared authority** | An integration that declares `lock.unlock` and then unlocks the door at 03:00 is acting inside its declaration. Confinement structurally cannot prevent this; it is a residual risk, not a defect |
| **Guaranteeing the manifest is minimal or honest** | An author declares what they choose. The mechanism converts *invisible* authority into *declared, bounded and audited* authority — a smaller claim than "the manifest makes integrations safe" |
| **Supply-chain integrity** | Signing and provenance are likelihood controls with their own literature. Complementary, not in scope |
| **Multi-user access control** | Home Assistant "assumes every user is trusted" [10]; changing that is a platform-level concern |
| **User comprehension of disclosures** | Whether users act correctly on permission prompts is a human-factors question with its own literature |

## 3.3 Key features

1. **A permissions clause in the manifest the integration already ships.** Eight declarable
   capabilities — entity reads, subscriptions and writes; service calls; event access; network
   egress; filesystem paths; config-entry enumeration; HTTP route registration — plus an optional
   resource clause. Anything not declared is denied.
2. **Per-integration Linux sandboxing.** Each integration runs in its own user, mount, PID,
   network, IPC and UTS namespaces, under a seccomp-BPF filter denying 29 syscalls, inside a
   cgroup v2 slice bounding memory, CPU, process count and disk space.
3. **A real but stripped Home Assistant inside the sandbox.** The integration imports the genuine
   helper layer and receives a genuine `hass` object — but a *local* one whose state machine and
   service registry start empty, so denial is structural rather than a check that must not be
   forgotten.
4. **An out-of-process mediator holding the platform credential.** Every permitted effect crosses
   one inherited Unix socket; identity is a property of the socket, not a claim in the message.
5. **A mediated egress broker** that resolves a declared hostname itself and pins the connection
   to the resolved address, so a name that resolves to an internal address at request time is
   refused.
6. **A tamper-evident audit log** — hash-chained and MAC-keyed — recording every decision, the
   clause that decided it, and the integration's three-part content identity, written *before*
   the action it records.
7. **A user-facing renderer** that prints an integration's declared authority in plain language
   before it is installed.

## 3.4 Deliverables

| | Deliverable | State |
|---|---|---|
| D1 | The confinement framework (`confine/`) — standard library plus `ctypes`, no third-party dependencies | Built |
| D2 | **19 self-test suites**, all passing on the target hardware | Built |
| D3 | Two reproducible corpora of real community integrations — 37 by install count, 40 drawn uniformly — with manifests | Built |
| D4 | A paired confined/unconfined measurement harness computing compatibility identically in both arms | Built |
| D5 | An adversarial integration exercising the 2021 file-theft pattern, the published garbage-collector attack, credential recovery, and absent/malformed/over-broad/mismatched manifests | Built |
| D6 | A threat model — 18 threats, 7 residual risks — under ISO 31000 with STRIDE | Built |
| D7 | This report, with every figure traceable to a named run and a raw result file | This document |

## 3.5 Constraints and challenges

These are properties of the situation rather than choices, and they eliminate most of the designs
prior work used.

**C1 — Integrations shall run unmodified.** 4,220 integrations already exist, written by
volunteers against an API that presumes full authority. *Verified:* source trees hashed before
and after every run — **75 tree comparisons, zero source changes, zero diff lines**.

**C2 — Home Assistant core shall not be modified.** A solution requiring a core patch is a
proposal, not a deployable control. *Verified:* every arm runs against an unmodified official
release, 2026.8.3.

**C3 — Enforcement shall not presuppose the author's cooperation or honesty.** The closest prior
work requires developers to write truthful declarations and its authors acknowledge the
declarations can be altered. *Verified:* the adversarial evaluation includes absent, over-broad
and deliberately mismatched manifests.

**C4 — The design shall run on self-hosted, resource-constrained hardware.** *Verified:* every
measurement in this report was taken on a **Raspberry Pi 5, 4 GB, Raspberry Pi OS trixie, kernel
6.12.47, Python 3.14.7, aarch64**, unprivileged and without root.

The **central challenge** follows from C1 and C3 together: the confinement must be imposed on
code that was written to assume it has none, by a party who is neither the code's author nor the
platform's maintainer. Everything difficult about this project descends from that sentence.

## 3.6 Requirements

Twenty requirements, each traced to a finding in §2 or §7 and each stating how it will be
verified. Requirements that could not be traced were cut. The full register, with derivations and
verdicts, is **Appendix B**; the summary is below.

| | Requirement | Verdict |
|---|---|---|
| **C1** | Integrations run unmodified | ✅ Counted — 75 trees, 0 changes |
| **C2** | Home Assistant core unmodified | ✅ |
| **C3** | No dependence on author cooperation | ✅ |
| **C4** | Runs on resource-constrained hardware | ✅ |
| **F1** | Integrations can publish entities and states | ✅ |
| **F2** | Integrations can reach declared network endpoints | ✅ |
| **F3** | Authority expressed in a declarative manifest | ✅ |
| **F4** | Declared authority presentable to the user before installation | ✅ |
| **S1** | Enforcement outside the integration's execution context | ✅ Paired |
| **S2** | Sandbox holds no credential granting unmediated access | ✅ Paired |
| **S3** | Mediation covers reads and subscriptions, not only writes | ◐ Partial — the push loop is not built |
| **S4** | Egress attributable and enforceable per integration | ✅ |
| **S5** | Manifest granularity distinguishes risk-asymmetric operations | ✅ |
| **S6** | Enforcement defaults to denial | ✅ |
| **S7** | Every decision recorded in a tamper-evident log | ✅ |
| **S8** | Filesystem and process isolation | ✅ Paired |
| **S9** | Resource limits bounded | ✅ Against narrowed wording — space, not I/O bandwidth |
| **N1** | Overhead small enough not to change how the platform is used | ✅ |
| **N2** | Compatibility cost measured and reported, not asserted | ◐ Partial — import-level for 77, end-to-end for 5 |
| **N3** | Degrades to a stated failure mode | ✅ |

**Nineteen met, one partial in two halves.** The two ◐ rows are the two the report is most
careful about, and §12.7 states them rather than a limitations section conceding them later.

## 3.7 Expected outcome

That an unmodified community integration can be confined and still work; that the published
attacks against this platform fail under confinement and succeed without it, measured on the same
host in the same session; and that **the compatibility cost of the design is separable from the
compatibility cost of the platform** — which requires an unconfined baseline, and is the reason
the evaluation is paired throughout.
