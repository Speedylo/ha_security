# 6. Logic Model Framework

## 6.1 Target population

**Primary: households running Home Assistant with community integrations installed.** The
telemetry gives the size and shape of this population directly: **379,326 installations run HACS
(56.6% of all reporting installations)**, and each runs a mean of **4.02** community integrations.
These are the parties who own the assets, carry the consequences, and are currently assigned the
risk without any means of acting on it.

**Secondary: community integration authors** — 4,220 of them, overwhelmingly single-author
volunteer projects with a median of 20 installs. They are a target population rather than a
stakeholder to satisfy, because the design's central constraint is that **it must impose no work
on them**. An author who does nothing gets a manifest with no permissions clause, which under
default-deny means their integration is confined to what it can do without any grant.

**Tertiary: the Home Assistant project.** Not an adopter of this artifact, but the eventual owner
of any durable fix — and the audience for the single upstream ask in §15.2.

## 6.2 Underlying assumptions

Eight assumptions were **registered as predictions before the corresponding measurement was run**,
in a committed file, so they could be scored rather than remembered. **Six were wrong.**

| | Assumption | Outcome |
|---|---|---|
| P1 | Confinement's import-level compatibility cost is at or near zero | ✅ Held — measured 0, twice |
| P2 | A zero measured on one corpus holds on a near-independent sample | ✅ Held |
| P3 | A package the platform pins defensively must therefore be installed | ✗ Wrong — it is not |
| P4 | The mediator degrades in the tail before the median | ✗ Wrong — it saturates and degrades in both |
| P5 | cgroup v2's page-cache charging will kill a legitimate large-file reader | ✗ Wrong — page cache is reclaimable |
| P6 | The ecosystem's long tail imports worse than its head | ✗ **Wrong in sign** — the tail imports eight points better |
| P7 | Per-integration declared components beat a blanket profile | ✅ Held |
| P8 | Wiring the auth manager raises the compatibility figure | ✗ Wrong in both halves — it moved the figure by zero |

**The pattern is the finding, not the count.** The two assumptions that held were the two *about
the design*. Every wrong one was an assumption about what the ecosystem or the kernel would do.
**The design behaved as designed; the world did not behave as assumed** — and that is only
available as a statement because the predictions were on the record before the numbers were.

Three further assumptions underpin the work and are **not** falsifiable within it, so they are
stated as limits: that the kernel's namespace and cgroup implementations are sound; that an
integration's declared `manifest.json` is a meaningful starting point for a permissions clause;
and that a household is willing to accept a bounded, declared integration in place of an
unbounded, silent one.

## 6.3 Resources and challenges

### 6.3.1 Resources

| Resource | What it provided |
|---|---|
| **Raspberry Pi 5, 4 GB, Pi OS trixie** | The target device. Every measurement in §12 was taken on it, unprivileged and without root |
| **Home Assistant 2026.8.3 source, pinned** | The platform under test, unmodified. Pinning a commit is what makes any compatibility figure reproducible |
| **The HACS index** | Two reproducible corpora — 37 integrations by install count, 40 drawn uniformly with a recorded seed |
| **Home Assistant's published telemetry** | Every ecosystem figure in §1 and §6.1 |
| **Four primary papers, read in full** | The threat model this work is evaluated against, the MUD architecture, the consolidating thesis, and the systematic review that names this project as an open direction |
| **Python standard library and `ctypes`** | The entire framework. No third-party dependency, deliberately: a confinement tool that pulls a dependency tree has enlarged the attack surface it exists to reduce |

### 6.3.2 Challenges

| Challenge | How it was met, or not |
|---|---|
| **The extensions cannot be changed** | Confinement is imposed from outside by a supervisor; the integration's source is never touched, and this is now counted rather than argued |
| **The platform cannot be changed** | Enforcement lives in a mediator beside the platform, not in it. Cost: the mediator must hold an unscoped credential, which is a retained residual risk with an upstream owner |
| **The published attack defeats every in-process design** | Resolved by architecture rather than by defence: the sandbox is a different process, so the attack runs perfectly and finds nothing |
| **26 of 37 corpus integrations need a credential before setup completes** | **Not met.** It caps the executed-end-to-end population at 11 and it binds any confinement scheme equally. It is why N2's second number is a named set of five and not a rate |
| **The platform moves underneath the design** | Partially met. One release, one host, one architecture. The first measured instance of a platform helper breaking the design arrived in the last week of measurement |
| **A test written by the author of the thing tested** | **This is the project's central methodological finding** and §13 is about it |

## 6.4 Activities

The work was organised in five stages with gates between them, and the gates were used: two of
four architectural decisions **diverged** from the first pass when re-examined against evidence.

| | Stage | Activity |
|---|---|---|
| 1 | **Problem and literature** | Primary sources only; four key papers read in full; the gap stated as a falsifiable absence |
| 2 | **Requirements and threats, in that order** | 19 requirements each traced to a finding; then the threat model, which generated a 20th |
| 3 | **Architecture** | Four decisions, each with candidates, a measurement where one was available, and a recorded divergence where the first pass had been wrong |
| 4 | **Implementation** | The framework, 19 self-test suites, and an adversary built to attack it |
| 5 | **Evaluation** | Paired arms throughout; predictions registered before measurement; three whole-report read-through passes |

**The ordering is itself an activity.** The threat model was written *before* the architecture, so
the controls answer threats enumerated independently of them. Written the other way round, a
threat model becomes a justification for decisions already taken.

## 6.5 Outputs

- A confinement framework with **19 passing self-test suites** on the target hardware.
- **Two reproducible corpora** of real community integrations, with manifests permitting redraw.
- A **paired measurement harness** computing compatibility identically in both arms from one
  shared function — so a drift of one platform name could not flatter either side.
- An **adversarial integration** covering the 2021 pattern, the published `gc` attack, credential
  recovery, and absent, over-broad and mismatched manifests.
- A **threat model** of 18 threats and 7 residual risks, mapped to the closest published model.
- A **measured compatibility result** against an unconfined baseline: the number nobody else has.

## 6.6 Outcomes

### 6.6.1 Short-term — achieved and measured

The published attack that forced the architecture was **reproduced and defeated** against a live
credential; the 2021 file-theft pattern **succeeds unconfined and recovers nothing confined**; and
the import-level compatibility cost of confinement across 77 integrations is **zero**, twice, on
corpora sharing 5% of their members.

### 6.6.2 Intermediate — plausible, and each with a named blocker

That the framework runs a realistic household's worth of integrations end to end rather than five;
that the mediator acts on a live Home Assistant rather than a stand-in; and that the manifest is
generated by static analysis rather than written. Each is priced in §14, and none needs a research
result — they need engineering time.

### 6.6.3 Long-term — the outcome that is not this project's to deliver

**Enforcement inside the platform's own loader.** This report states plainly that a capability
check inside Home Assistant would be the better design on every axis except deployability, and
that this project's most durable contribution to it may be the *evidence* such a proposal needs:
what confinement costs in compatibility, what the declaration should express, and which threats it
closes. Those answers do not depend on the architecture that produced them.
