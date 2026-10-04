# Where the project stands — a plain-English overview

> **Out of date on results since 2026-10-03.** This overview predates §7.30–§7.35: T12 measured, three
> more real integrations and the defects they found, a credentialed integration, the durable audit log
> wired everywhere, and the footprint re-runs. Its explanations of how the system works still hold. For
> where the project is now, read the top of `STATE.md` and `notes/remaining_work_20261003.md`.
>
> **And since 2026-10-04 (§7.36):** the push loop exists, so "No push loop" below and the one partial
> requirement are closed at the stand-in platform; all 20 requirements are now met. Building it found
> that the mediator had recorded each action *after* carrying it out, from 2026-08-25 to 2026-10-04,
> so the audit log's "record before act" promise held only in its own self-test. Fixed the same day.
> The same day (§7.37) the mediator was put in front of a **real** Home Assistant: confined entities
> now have registry identity there and survive restarts. Commands from it into a sandbox remain.

**Written 2026-09-06.** This is the orientation document: what the project is, how it works, what
has been proven and what has not. `STATE.md` is the working resume point with all the detail;
this is the version you can hold in your head.

---

## 1. The problem

Home Assistant is the most-used open-source home automation platform — **669,743 active
installations**. Its usefulness comes from *integrations*: third-party plug-ins that connect it to
a brand of light bulb, a solar inverter, an energy market, a vacuum cleaner. Most are written by
hobbyists and installed through a community store called HACS.

**Every one of them runs inside Home Assistant's own process, with the full authority of Home
Assistant itself.**

That means an integration you installed to read your electricity prices can, with no special
effort and nothing stopping it:

- read `secrets.yaml` — every password and API token in your home
- reach into another integration's live objects in memory and read *its* credentials
- call any service on any device — unlock a door, disarm an alarm
- see every entity in the house, including presence sensors that say whether you are home
- reach anything on your local network

None of this requires an exploit. It is the normal capability of any integration, because there
is no boundary between them. The platform's own documentation for creating an integration
specifies no permission model, no scoping rule and no caller check.

This is not theoretical. In 2021 a set of Home Assistant integrations were disclosed as
vulnerable to exactly this class of file theft, and published academic work demonstrates an
integration walking the garbage collector to reach another integration's live secrets.

---

## 2. The goal, stated honestly

**The objective:** build confinement for these integrations that requires *no change to the
integration* and *no change to Home Assistant*, and measure what it costs.

The "no change" part is the whole difficulty and the whole point. There are **4,220 distinct
community integrations**, written by people who owe you nothing and will not rewrite their code for
your security model. A solution that requires them to cooperate is a solution that does not deploy.

The scale is worth having in mind: **56.6%** of Home Assistant installations run HACS, and a HACS
installation runs a mean of **4.02** community integrations. But the distribution is extreme —
**3,095 of the 4,220 have fewer than 100 installs**, and the median integration has **20**. That
split is why the project measures two different corpora rather than one (see §5 below).

### What the contribution is — and what it is not

Two claims were considered and **dropped as false** early on, and they must never reappear:

| Tempting claim | Why it is false |
|---|---|
| ~~"Nobody has identified this problem"~~ | Corno & Mannella threat-modelled extensible home gateways with a Home Assistant use case in 2022 |
| ~~"Manifest-declared permissions are novel"~~ | Barth et al. settled that in 2010 |

**What is left is stronger because it is defensible:** nobody has *built and evaluated* confinement
for these integrations, and **nobody has measured what confining pre-existing, unmodifiable
extensions costs in compatibility.**

There is even a published request for exactly this. Thingnes & Meland's systematic review calls in
its future-work section for *"a proof-of-concept implementation for Home Assistant … evaluated
based on the threat model introduced by Corno and Mannella."* That is this project. **The
direction is not a personal preference — it is a documented gap someone else asked to be filled.**

---

## 3. How it works — the architecture

### The central idea

**Every integration already tells you what it needs, and nobody uses that information for
anything.** Three independent findings, one shape:

| Where | What already exists | What it is currently spent on |
|---|---|---|
| Prior work | a plug-in's declared "scope" | prose in the documentation |
| Home Assistant's source | `is_built_in` — which code is third-party | the wording of a log line |
| Integration manifests | `iot_class` — whether it reaches the cloud, declared by **83%** | a discovery heuristic |

**The contribution is not inventing the declaration. It is making one load-bearing.** That also
kills the obvious objection before it is raised: authors are not being asked to do something new,
just a more precise version of something most already do unprompted.

### The five moving parts

**1. A sandbox.** Each integration runs in its own isolated process using standard Linux
facilities — namespaces (its own view of the filesystem, network and process list), seccomp (29
system calls refused outright) and cgroups (hard caps on memory, processes, CPU and disk space).
All of it **unprivileged**: no root, no setuid, no daemon.

**2. A real, stripped Home Assistant inside the sandbox.** This is the decision that makes
"unmodified" possible. Rather than faking the platform's API, the sandbox runs a genuine but
minimal Home Assistant. The integration imports what it always imports and cannot tell the
difference.

**3. A manifest.** A small permissions block declaring what the integration may reach — which
entities, which services, which network hosts, what resources. **Default-deny**: anything not
declared is refused.

**4. A mediator.** A separate process holding the real credentials and the real Home Assistant.
The sandbox can only ask; the mediator decides, acts with its *own* authority, and returns a
result. The integration never holds a credential.

**5. An audit log.** Every decision recorded with a three-part identity of the code that asked
(source, manifest, dependencies — hashed separately *and* together), chained twice: a hash chain
anyone can verify, and a keyed MAC chain an attacker who cannot read the mediator's memory cannot
forge.

### The two ideas worth being able to say aloud

**Identity is the socket, not a field in the message.** The supervisor creates the communication
channel *before* the sandbox exists, so an integration cannot claim to be another one — its
identity is which pipe the request arrived on. Demonstrated with two sandboxes both insisting
they were the same integration.

**Most of the manifest is enforced structurally, not by checking.** An integration cannot ask to
read `secrets.yaml` and be refused — **the file is not in its filesystem at all, so there is
nothing to ask.** This is why the design is both fast and safe by default: the strongest
protections cost nothing at runtime because no check happens.

---

## 4. Requirements and scope

### 20 requirements, every one traceable to a source

Nothing was invented from experience. A requirement that cannot name where it came from does not
belong — that rule removed several I wanted to write.

| Group | Count | What they cover |
|---|---|---|
| **C1–C4** Constraints | 4 | Integrations run unmodified; Home Assistant runs unmodified; a hostile manifest cannot widen authority; it runs on a Raspberry Pi 5 |
| **F1–F4** Functional | 4 | Publish sensors; reach a declared network host; every decision names the clause that decided it; the user can see what was declared |
| **S1–S9** Security | 9 | Enforcement outside the integration's process; credentials held away from it; entity visibility; cross-integration denial; risk-asymmetric granularity; default-deny; tamper-evident audit; file isolation; resource bounds |
| **N1–N3** Non-functional | 3 | Latency; report import-level and executed results separately; refuse to start rather than degrade silently |

S9 is worth noting: it was **added by the threat model**, not by the requirements chapter — Chapter
4 generated a requirement Chapter 3 had no basis to write. Chapter 7 later did the same thing again
and generated a residual risk (R7) Chapter 4 could not have written.

### The threat model

**18 threats**, identified with STRIDE, structured on ISO 31000, diagrammed in OWASP Threat Dragon.
**7 residual risks** — things explicitly accepted rather than solved.

### Scope — what was deliberately built and what was deliberately not

Built: **sensors, mediated network egress across two integrations, and one `lock` service path.**

The lock path matters disproportionately: it is the only thing that verifies S5 (you may declare
`lock.lock` without being granted `lock.unlock`) and it demonstrates a control for the joint-highest
risk in the register. Cutting it would have been cheap and wrong.

---

## 5. What has been measured

Everything runs on the real target hardware — a **Raspberry Pi 5, 4 GB**, against **Home Assistant
2026.8.3**, Python 3.14.

### The headline result

> **Confined and unconfined arms fail on the *same* integrations, for the *same* reasons.**
> The import-level compatibility cost of confinement is **zero**. Measured twice, on two corpora
> that share only 5% of their members.

| Corpus | What it answers | Confined | Unconfined | Cost of the design |
|---|---|---|---|---|
| 37 most-installed | what most *installations* run | **84%** | **84%** | **0** |
| 40 randomly drawn | what most *integrations* do | **92%** | **92%** | **0** |

The 84% is **not** a fact about confinement. It is the fraction of the corpus that loads on Home
Assistant 2026.8.3 at all. Six failures: three integrations import a package their own manifest
never declares, one is broken on 2026.8.3 itself, two are packaging artifacts. **Not one is caused
by the sandbox.**

The paired baseline is what makes this a result rather than a number. It has stopped **three**
misattributions that would each have charged the design more than it deserved.

### The rest of the evidence

| Area | What was measured | Result |
|---|---|---|
| **Attack resistance** | 38 attacks, run confined *and* unconfined | Unconfined: both canary secrets stolen, 11 attacks returned data. Confined: **0 of 2**, nothing reached |
| **The published gc attack** | a real victim integration holding a live token | Unconfined the adversary reaches it **7 ways**; confined it finds nothing — while the same token is *confirmed live* in the mediator |
| **Entity visibility** | a 36-entity home, 20 disclosing presence | Unconfined **36/36** and all presence; confined **1/36**, every undeclared probe denied with a clause |
| **Speed** | one mediated request | **31.5 µs**; capacity ~11,000× realistic demand before the audit write, **63×** after it |
| **Durability** | `fsync` on every decision | 3.67 ms — expensive, and affordable |
| **Memory** | per-sandbox footprint | ~120 MB; **26 sandboxes** fit in 60% of a 4 GB Pi |
| **Resource caps** | each verified by a sandbox *exceeding* it | 25% CPU cap holds at 25.1%; `ENOSPC` at the disk cap; OOM-kill at the memory cap |
| **Network** | what integrations actually do, measured before building | 96% of DNS goes through a path the original design would not have seen — **the design's enforcement point was in the wrong place**, corrected before any code was written |
| **Real integration, real API** | `nordpool` through the mediated path | Same price confined as unconfined, in the same minute; clause removed → denied |
| **Unmodified (C1)** | 75 integration trees hashed before and after | **0 changed, 0 diff lines** |

**19 self-test suites pass on the Pi.**

### The intellectual result — this is what makes it a dissertation and not a project

**Six of eight predictions registered in advance were wrong. None was revised after the fact.**

Across the whole project, **every correction has been to a sentence next to a measurement, never
to a measurement** — with two exceptions, and both were found by building something adversarial or
running something real, not by reading code:

1. A hostile integration could have granted itself extra network reach by writing one key into a
   request it already composed. Found by writing the attack.
2. **No real integration could create an HTTP client inside the sandbox at all.** The helper the
   platform tells authors to call builds its DNS resolver by joining a multicast group, which a
   fresh network namespace cannot do. The egress design had been unusable for the 41% of the
   corpus it exists to serve — **behind eighteen passing test suites** — because every earlier
   test subject was written by the same person who wrote the sandbox.

**That second one is the most important methodological finding in the project.** Five different
mechanisms catch errors here — a paired baseline, two instruments bounding each other, self-tests,
recomputation from raw data, and running unmodified real code. Only the last found a defect that
made the design unusable for its target population. The reason is structural: **the other four are
all written out of the same assumptions as the thing they test.**

---

## 6. What has NOT been tested — read this before the supervisor meeting

This is the honest half, and it is where the remaining work is.

### The big one

> **The mediator acts on an in-memory stand-in, not a live Home Assistant.**

The integration inside the sandbox runs *genuine* Home Assistant 2026.8.3. But on the far side of
the mediator — the part that would actually turn on your light — there is a simplified stand-in
written for the tests. **A real Home Assistant component has never been built.** This is the
largest limitation in the report and the report says so.

### The others

| Not tested | What it means |
|---|---|
| **The durable audit log ran in 1 experiment out of ~8** | Everything else recorded to an in-memory list that dies with the process. The mechanism is built and proven in isolation — but the one time it ran for real it produced **three defects in a single session** |
| **Only 5 integrations executed end-to-end** | 77 were tested at *import*. Actually running them is capped at 11 of 37, because 26 need a real vendor credential before setup completes |
| **Only 1 integration against a real API** | `nordpool` — the corpus's only member needing a network but no credential |
| **No push loop** | Subscriptions are verified at the decision layer only. Nothing streams live state changes yet |
| **UDP not exercised in a real sandbox** | The relay is built and unit-tested; never spawned in real namespaces |
| **2 of 3 network stacks not spawned confined** | And the one that *was* spawned turned out to break — so "the others are presumably fine" is exactly the reasoning that was wrong once |
| **T12 has no evidence at all** | The only threat in either register with none, and the report points at it |
| **Disk I/O bandwidth is not bounded** | The kernel controller exists but is not delegated to unprivileged users. Stated as a residual risk (R7) rather than hidden |

### The pattern worth noticing

Two separate components — the egress path and the audit log — passed every test their own author
wrote, and broke the first time real work went through them. **Two instances is a pattern**, and it
is the argument that the next work should be *running the whole thing for real*, not adding more
tests written from the same assumptions.

---

## 7. Where we are today

| | |
|---|---|
| **The idea** | Settled and defensible; the gap is documented in published work |
| **The architecture** | Complete — all four re-openable design decisions settled, two of them **against** the first attempt's answer |
| **The artifact** | Built and running on the Pi. 19 self-test suites pass |
| **The measurements** | Complete. All 20 requirements carry a verdict: **19 met, 1 partial** (entity subscriptions, which need the push loop) |
| **The write-up** | All 8 chapters drafted, plus front matter and a 28-source bibliography |
| **Quality control** | Three full read-through passes done. 18 findings, **not one of them a measured figure** |
| **Blocked on** | The programme handbook — 4 fields on the title page, and what the AI-use declaration must say |

### What is genuinely left

1. **The realistic-scenario validation** — a real Home Assistant component, real integrations at
   volume, actually executed rather than imported, with the durable audit log engaged throughout.
   **This is the piece that would turn the strongest claim in the report from a claim about a
   mediator's decisions into a claim about a running system.**
2. **The push loop** — the largest missing feature; would close the one partial requirement.
3. **T12's measurement** — hours of work on the only threat with no evidence.
4. **A consolidation rewrite** — the report is honest but hard to read: corrections are stacked in
   layers and Chapter 7 alone is 198 KB. Backlogged deliberately, not patched piecemeal.
5. **Defence preparation.**

### How to think about the timeline

The summer work established **feasibility**: the idea is sound, the architecture holds, it runs on
the target hardware, and the compatibility cost is measurably zero. That was the risky part and it
is now settled.

**What it does not yet establish is that the whole system works end to end in a real house.** The
mediator's far side is a stand-in; the audit log has barely run; five integrations have actually
executed. That is real, substantial, interesting work — and by the project's own evidence
(two components that broke the first time real code hit them) it is the work most likely to find
something rather than merely confirm something.
