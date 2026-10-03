<!--
Capstone project proposal — the content for the EGR 4402 proposal template.

Built into the template by build_proposal.py:
    python3 proposal/build_proposal.py   ->   proposal/capstone_proposal.docx

Conventions the build script relies on:
  * `# <key>` opens a section. Keys are the template's section numbers (2.1, 4.3 ...) plus
    `cover`, `type`, `5.2`, `9.1` and `refs`.
  * Prose sections: blank-line-separated paragraphs; lines starting `- ` are bullets.
  * Table sections: one markdown table. The header row is skipped (the template has its own).
    A cell containing only `=` keeps the template's text. `<br>` starts a new paragraph in a cell.
  * `**bold**` works everywhere. Citations are `[@key]`; they are numbered by first appearance
    and the reference list is generated from the `refs` section.

Written prospectively, as if the work began on 31 August 2026. The timeline is an estimate on
that assumption, not the schedule the project actually followed (Younes, 2026-09-17).
-->

# cover

| Field | Value |
|---|---|
| Project Title | Confining Unmodified Third-Party Integrations in Home Assistant: A Declared-Authority Architecture and Its Measured Cost |
| Student Name(s) | Younes Rahati |
| Student ID(s) | [ID] |
| Degree Program | B.S. in Computer Science |
| Supervisor | [Name] |
| Co-Supervisor / Client | Not applicable |
| Date of Submission | [Date] |

# type

Research-Based Project

# 1

Home Assistant is the largest open-source home-automation platform, with 669,743 reporting installations [@ha-analytics], of which 56.6% run community-written integrations installed through the Home Assistant Community Store (HACS) — a proportion computed for this proposal from the platform's published install counts [@ha-custom-integrations], as §2.2 sets out. Every such integration is imported into Home Assistant's own process and receives the platform's full authority: every entity, every service including `lock.unlock`, every stored credential and every network path. There is no permission model [@ha-devdocs], the store checks repository structure but never code behaviour [@hacs-include], and published work shows one integration can reach into another's live objects through the Python garbage collector [@corno2022].

This project will design, build and evaluate confinement for these integrations **without modifying the integrations or Home Assistant**. Each integration will run unmodified in its own Linux sandbox (namespaces, seccomp-BPF, cgroup v2) against a stripped Home Assistant instance, and will reach the real platform and the network only through an out-of-process mediator that enforces a permissions clause declared in the integration's existing manifest and records every decision in a tamper-evident log.

The expected contribution is empirical as well as constructive: prior work argues confinement is desirable, but no published work measures what fraction of real, unmodified extensions still function once it is applied. The evaluation will therefore be **paired** — confined against unconfined, on the same Raspberry Pi 5 and the same Home Assistant release — and will measure effectiveness against the published attacks, compatibility across two corpora of real community integrations, and cost in latency and memory, against success criteria and predictions fixed before measurement.

# 2.1

Home Assistant loads community-written integrations into its own process and grants each one unscoped authority over every entity, service, credential and network path available to the platform — including physical control of locks and alarms. Every control that exists today (the store's inclusion checklist, informal review of public source) acts on the *likelihood* that hostile or vulnerable code arrives. **Nothing bounds what that code can do once it is running.**

**Research question.** Can the authority of an unmodified Home Assistant community integration be declared, enforced at runtime and audited — without modifying the integration, without modifying Home Assistant, and without relying on the integration author's cooperation — and what does such confinement cost in compatibility, memory and latency on the hardware users actually run?

# 2.2

The exposure is widespread. Home Assistant publishes the per-integration install counts gathered by its opt-in telemetry as a machine-readable dataset [@ha-custom-integrations]. **The figures that follow are not quoted from that source but computed for this proposal** from a snapshot retrieved on 21 August 2026, by a script committed with the project so that every figure can be regenerated and re-dated rather than trusted.

That snapshot records 4,220 distinct custom integrations, of which HACS itself is the most installed at 379,326 — 56.6% of the 669,743 installations then reporting [@ha-analytics]. The remaining 4,219 integrations account for 1,524,971 installs between them, a mean of **4.02** per HACS-running installation. The distribution is long-tailed: the median integration has 20 installs and 3,095 of the 4,220 have fewer than 100 — single-author volunteer projects that informal review is least likely to reach.

Because analytics participation is opt-in, every one of these counts is a **lower bound** on the true population, and the bias is not neutral: installations that report are plausibly more engaged than average, and more engaged users are plausibly more likely to install third-party extensions. These figures should be read as a floor among installations that report, not as estimates of the whole population. The long-tail figures are the least sensitive to that bias and carry most of the argument: they establish that the majority of custom integrations serve a very small audience, which is precisely the population least likely to receive external review.

The exposure is also documented rather than hypothetical. In January 2021 Home Assistant disclosed a directory-traversal vulnerability class across HACS and several widely installed integrations, through which an attacker could read "any credential that you might have stored", in most cases without authentication [@ha-disclosure1][@ha-disclosure2]. The remediation blocked that vulnerability class but did not change what an integration is permitted to do. The platform's security policy places custom integrations outside its security programme [@ha-security], and a professional audit of the core platform explicitly declined to examine them, noting they "will have complete access to your Home Assistant installation" [@gh-securitylab]. Supply-chain compromises such as the XZ Utils backdoor [@xz] show that trusted, reviewed code can also turn hostile.

What makes this platform different from the general untrusted plug-in problem is the consequence: a compromised integration can unlock a front door through the platform's own legitimate control path. Home Assistant's own community is now discussing moving integrations out of the core process for reliability reasons [@ha-rfc-remote], which makes the question of what a relocated integration should be *permitted* to do timely.

# 2.3

- **Home Assistant users** — the 379,326 HACS-running installations, and in particular the householder who installs integrations and carries the risk without a security function or incident-response capability.
- **Other occupants of the home**, who are exposed to surveillance and physical-access risk from integrations they did not install and cannot read.
- **Community integration authors** — volunteers who would benefit from a way to state what their code needs, but who cannot be asked to rewrite existing code.
- **Home Assistant and HACS maintainers**, as the parties who could adopt the mechanism or the evidence it produces into the platform.
- **The smart-home security research community**, where a systematic review has named a proof-of-concept of exactly this kind as an open research direction [@thingnes2025].

# 2.4

**In scope:** third-party *integrations* (Python modules loaded into Home Assistant's process) installed through HACS onto a self-hosted installation on a single machine; declaring, enforcing and auditing their authority; measuring the cost of doing so.

**Out of scope:** add-ons, which already run as isolated containers [@ha-addons]; deciding whether an integration is malicious; preventing abuse of authority an integration has legitimately declared; guaranteeing that a manifest is minimal or honest; supply-chain integrity (signing, provenance); multi-user access control; and user comprehension of permission prompts.

**Constraints.** (C1) Integrations must run unmodified. (C2) Home Assistant core must not be modified — the work runs against one pinned official release, 2026.8.3. (C3) Enforcement must not depend on the integration author's cooperation or honesty. (C4) The design must run unprivileged on resource-constrained self-hosted hardware — a Raspberry Pi 5 with 4 GB of RAM. The project is also bounded by one semester, one developer and one test device, and by the fact that many integrations need a cloud account before they can be configured.

**Assumptions.** Unprivileged user namespaces, seccomp-BPF and cgroup v2 are available on Raspberry Pi OS (a short feasibility probe on the device before the semester supports this, and it will be re-verified in Phase 2); the platform maintainers are trusted; and threats from a hostile local network or physical access are excluded.

# 3

**Least privilege for extensions elsewhere.** Barth et al. analysed Firefox extensions, which then ran with the user's full privileges, and found 88% needed less than full privilege; the declared-manifest and privilege-separation architecture they proposed became standard in Chrome [@barth2010]. The idea at the centre of this project is therefore not new. What does not transfer is the route: Chrome could require developers to migrate to a new platform, and Home Assistant's volunteer authors cannot be required to do so.

**Smart-home platforms.** Fernandes et al. showed widespread overprivilege in Samsung SmartThings apps, including backdooring a door lock's PIN [@fernandes2016]. Follow-on mechanisms include FlowFence's declared data flows and sandboxed modules [@flowfence], ContexIoT's contextual runtime prompts [@contexiot], SmartAuth's reconciliation of an app's description with its behaviour [@smartauth], and Tyche's risk-based permissions, which observe that physical operations are risk-asymmetric — unlocking is not the inverse of locking [@tyche]. All of these assume a vendor-operated platform with an existing permission model and the power to mandate change. Home Assistant is self-hosted, runs integrations in-process, has no permission model, and cannot compel its authors.

**Extensible hubs — the closest work.** Corno and Mannella published the only threat model for plug-in-extensible smart-home gateways, validated on Home Assistant; their proof-of-concept integrations reach another integration's private state via the garbage collector, and they recommend that the gateway enforce controls and that plug-ins authenticate — without building such a mechanism [@corno2022]. Their follow-up adapts the Manufacturer Usage Description standard [@rfc8520] to gateways, merging developer-declared endpoints into one gateway-level policy enforced by a router firewall [@corno2023]. That enforcement cannot see in-process API calls, loses per-plug-in attribution when declarations are merged, depends on developer cooperation, and was validated on three integrations, two purpose-built. Mannella's thesis consolidates this line of work and does not propose runtime confinement [@mannella2024]. A 2025 systematic review lists "Insecure Extension Runtime" and "Insufficient Access Control" among eight challenges for extensible hubs and proposes a Home Assistant proof-of-concept evaluated against Corno and Mannella's threat model as future work [@thingnes2025].

**Supply chain and measurement.** Supply-chain research systematises how hostile code enters open-source ecosystems; its countermeasures all act on likelihood [@ladisa2023]. Li et al. measured API usage across 2,562 Model Context Protocol servers to motivate privilege management there [@li2025] — the measure-then-design method this project adopts. No equivalent measurement exists for Home Assistant.

# 4.1

No published work builds or evaluates runtime confinement for Home Assistant's third-party integrations, and **none measures the compatibility cost of confining extensions that already exist and cannot be rewritten**. That cost is what decides whether any such scheme is deployable. Existing proposals either need a platform operator willing to redesign the extension model (the browser and SmartThings work), or act at a network layer that cannot mediate calls that never become packets and cannot attribute traffic to a single plug-in (the gateway MUD work). The gap matters because the exposure is large, documented, and currently carries no impact control of any kind.

# 4.2

- **A retrofit confinement architecture.** The novelty is not the permission manifest, which is established practice, but enforcing a declared authority boundary on code written to assume it has none — without changing the integrations, the platform, or relying on the authors — using kernel primitives available unprivileged on a Raspberry Pi.
- **A measured security/compatibility/cost trade-off.** Paired confined-versus-unconfined measurements over real community integrations, so that the failures caused by confinement can be separated from failures the platform causes anyway.
- **An empirical account of the API surface** community integrations actually depend on, measured over the HACS catalogue, to ground the design in data rather than assumption.

# 4.3

| Criterion | Existing Work / Baseline | Proposed Approach | Expected Improvement / Difference |
|---|---|---|---|
| Performance / Accuracy | Stock Home Assistant: no mediation cost, but no enforcement. Gateway MUD [@corno2023]: no per-request cost, enforcement at the router | Mediated platform and network access for each confined integration | Enforcement at a measured cost; target under 1 ms added per mediated request |
| Cost / Complexity | MUD approach needs an OpenWrt router running osMUD plus declarations written by every developer | Python standard library and `ctypes` only; runs on the device the user already owns | No extra hardware, no third-party dependencies, no change to integrations or to Home Assistant |
| Usability / Accessibility | Stock: an integration's reach is invisible to the user | The declared authority is rendered in plain language before installation | Authority becomes visible to non-programmers; enforcement does not depend on them reading it |
| Scalability / Efficiency | MUD evaluation: 3 integrations, 2 of them purpose-built | Two corpora of about 40 real community integrations each; per-sandbox memory measured on a 4 GB device | Evidence at corpus scale; a capacity figure compared against the mean of 4.02 integrations per installation |
| Security / Reliability | Stock: full in-process authority, cross-integration heap access. MUD: network-only, union of all plug-ins' declarations | Per-integration process isolation, default-deny API mediation, per-integration egress, hash-chained audit log | Closes the in-process attack paths; attributes every decision and connection to one integration |
| Context-specific factor | Browser and SmartThings solutions require the platform operator or the developers to migrate | Imposed from outside by an unprivileged supervisor | Deployable in a volunteer ecosystem where neither the platform nor the authors can be required to change |

# 5.1

To design, build and evaluate a mechanism that declares, enforces and audits the authority of unmodified Home Assistant community integrations, and to measure what that confinement costs against an unconfined baseline on a Raspberry Pi 5.

# 5.2

Objective 1: A working confinement framework that runs an unmodified community integration in its own sandbox on a Raspberry Pi 5, without root, with all platform and network access mediated and denied by default unless declared in the manifest.

Objective 2: Demonstrated effectiveness: the published attack patterns (credential file theft, cross-integration garbage-collector access, credential recovery, and absent, over-broad or mismatched manifests) succeed without confinement and fail with it, on the same host and release.

Objective 3: A measured compatibility cost: the fraction of real community integrations that fail because of confinement, separated from those that fail anyway, on two independently drawn corpora.

Objective 4: A measured resource cost — latency per mediated request, memory per sandbox, and the resulting sandbox capacity of a 4 GB device — compared with the number of community integrations a typical installation runs.

# 5.3

| Objective / Claim | Metric or Evidence | Target / Acceptance Criterion |
|---|---|---|
| O1 — framework works, unmodified and unprivileged | Integration source trees hashed before and after every run; privilege of the supervisor; self-test suites on the target | Zero changed files across all runs; no root at any point; all self-test suites pass on the Pi |
| O1 — default deny | Requests for undeclared entities, services, hosts and paths in the test suites | 100% refused, each refusal recorded in the audit log |
| O2 — confinement is effective | Adversarial integration run in both arms | Every attack succeeds unconfined (otherwise the test is invalid) and fails confined |
| O2 — threat coverage | Threat register scored against this project's model and Corno and Mannella's published model [@corno2022] | Every threat rated Critical has a treatment with evidence; every untreated threat is stated as a residual risk |
| O3 — confinement is compatible | Import-level setup outcome per integration, confined vs unconfined, on both corpora; end-to-end execution on a credential-free subset | Failures attributable to confinement (fails confined, passes unconfined) at most 5% of each corpus; at least one real integration shown end to end against its real service |
| O4 — confinement is affordable | Median mediation latency; proportional set size per sandbox with several running; audit record durability | Median added latency under 1 ms; at least 10 sandboxes within 60% of 4 GB (over 2× the 4.02 mean); every audit record durable before its action executes |

# 6

**Methodology.** Staged engineering research with a gate between phases, following three rules: (1) every requirement must trace to a finding in the problem analysis or literature, or it is cut; (2) the threat model is written *before* the architecture, so controls answer threats rather than justify a design; (3) predictions are registered in writing before each measurement and are not edited afterwards.

**Threat model.** ISO 31000 [@iso31000] provides the risk-management process (context, identification, analysis, evaluation, treatment, residual risk); STRIDE [@shostack2014] is applied per trust boundary for identification; the model is drawn with OWASP Threat Dragon [@threatdragon]. The risk owner is the householder, and the impact scale is derived from the assets (physical control of the home, occupancy data, credentials, cameras, availability, the audit record, the home network).

**Architecture and major components.** The published garbage-collector attack eliminates any in-process permission layer, and modifying Home Assistant's loader is ruled out by C2, so enforcement will live **outside the integration's process**:

- **Supervisor** — spawns each integration in user, mount, PID, network, IPC and UTS namespaces, under a seccomp-BPF syscall filter and a cgroup v2 slice bounding memory, CPU, processes and disk, without root.
- **Stripped Home Assistant inside the sandbox** — the integration imports the genuine helper layer and receives a genuine but *local* platform object whose state and service registries start empty, so an undeclared capability is absent rather than merely refused.
- **Manifest permissions clause** — added to the `manifest.json` the integration already ships; granularity at the level of individual services so risk-asymmetric operations (lock vs unlock) are declared separately [@tyche].
- **Mediator** — the only component holding the platform credential; reached through one inherited Unix socket so identity comes from the channel, never from the message.
- **Egress broker** — the sandbox has no network route; the broker resolves declared hostnames itself, refuses private and internal destinations unless declared [@rfc1918], and hands back a connected socket.
- **Audit log** — hash-chained and keyed, written durably before the action it records.
- **Renderer** — prints an integration's declared authority in plain language before installation.

Alternative isolation primitives (WebAssembly, gVisor, microVMs, language-level sandboxing) will be compared against C1 and C4 and the choice recorded.

**Data sources.** Home Assistant's published per-integration install counts [@ha-custom-integrations], from which the ecosystem figures in §2.2 are computed rather than quoted, against a pinned snapshot; the HACS index for two corpora — the most-installed integrations, and a uniform random draw with a recorded seed — pinned by manifest so they can be re-fetched; and the Home Assistant core source at 2026.8.3 for the API-surface measurement.

**Hardware and tools.** Raspberry Pi 5 (4 GB, Raspberry Pi OS, aarch64) as the only measurement host; Python 3.14 standard library and `ctypes`; Linux kernel interfaces (namespaces, seccomp, cgroup v2, `SCM_RIGHTS`); a development laptop.

**Reproducibility.** All code, experiment scripts, corpus manifests and raw result files in a Git repository; every figure in the report traceable to a named script and result file; each measurement instrument tested against a known-bad case to confirm it can report a failure.

# 7

The evaluation is designed around one principle: **every result is paired** — the same integration, host, Home Assistant release and session, run once confined and once unconfined. Without the unconfined arm, a failed attack could mean the attack was broken and a failed integration could mean the platform was broken. The plan tests three assertions against the success criteria in §5.3:

- **A — Confinement is effective.** A purpose-built adversarial integration reproduces the 2021 credential-theft pattern, the published garbage-collector attack, credential recovery, and absent, malformed, over-broad and mismatched manifests. Each case must succeed unconfined and fail confined. The threat register is then scored against both this project's model and Corno and Mannella's eleven threats [@corno2022], the evaluation framing the systematic review proposes [@thingnes2025].
- **B — Confinement is compatible.** Both corpora are set up confined and unconfined, and outcomes are classified identically by one shared function; the headline metric is the number of integrations that fail *only* when confined. A credential-free subset is then executed end to end, including at least one integration against its real public service.
- **C — Confinement is affordable.** Mediation latency (repeated runs, median and tail), memory per sandbox by proportional set size across several live sandboxes, audit-log durability cost, and mediator headroom against realistic request rates — all on the Pi.

Constraint C1 is verified by hashing each integration's source tree before and after every run. Predictions for each measurement are registered before it runs and scored afterwards, whether right or wrong. Functional correctness is covered by self-test suites for every component, run on the target device.

# 8

| Deliverable | Description / Acceptance Condition |
|---|---|
| D1 — Confinement framework | Supervisor, stripped platform, mediator, egress broker, audit log and renderer. Accepted when an unmodified community integration runs confined on the Pi without root and publishes its entities through the mediator |
| D2 — Test and adversary suites | Self-test suites for every component plus the adversarial integration. Accepted when all suites pass on the Pi and every adversary case is shown succeeding unconfined and failing confined |
| D3 — Corpora and paired measurement harness | Two reproducible corpora of real community integrations with manifests, and a harness producing raw result files for both arms. Accepted when both arms run to completion on both corpora and every reported figure is regenerable from a result file |
| D4 — Threat model | ISO 31000 / STRIDE register with treatments, residual risks and a mapping to the published gateway threat model. Accepted when every threat has a rating, a treatment or a stated residual, and evaluation evidence where treated |
| D5 — Final report, repository and presentation | Report against the programme template, public-quality Git repository, and defence presentation with a live or recorded demonstration. Accepted on submission by the programme deadline |

# 9

| Phase / Milestone | Major Tasks / Output | Start | End | Evidence of Completion |
|---|---|---|---|---|
| = | Problem statement; ecosystem figures from telemetry; initial literature search; this proposal | 31 Aug 2026 | 18 Sep 2026 | Proposal submitted and approved |
| = | Structured literature review; requirements traced to findings; threat model (ISO 31000 / STRIDE); API-surface measurement; kernel feature probe on the Pi | 14 Sep 2026 | 2 Oct 2026 | Requirements register and threat register frozen |
| = | Architecture decisions against named alternatives; manifest schema; mediator protocol; corpus selection; evaluation protocol with registered predictions | 28 Sep 2026 | 16 Oct 2026 | Design document; predictions committed before any measurement |
| = | Supervisor and sandbox; stripped platform; mediator; egress broker; audit log; renderer; self-test suites; adversarial integration | 12 Oct 2026 | 13 Nov 2026 | All self-test suites passing on the Pi |
| = | Paired security, compatibility and cost measurements; source-tree hashing; end-to-end runs; threat model scored; predictions scored | 9 Nov 2026 | 4 Dec 2026 | Raw result files committed; results tables regenerated from them |
| = | Final report, figures, repository clean-up, presentation and defence preparation | 30 Nov 2026 | 11 Dec 2026 | Report and presentation submitted |

# 9.1

| Milestone | Target date |
|---|---|
| Requirements and threat model frozen; kernel features confirmed on the Pi | 2 Oct 2026 |
| Architecture and evaluation protocol fixed; predictions registered | 16 Oct 2026 |
| Framework feature-complete; all self-test suites passing on the Pi (scope freeze) | 13 Nov 2026 |
| Evaluation complete and results frozen; final report and presentation submitted | 4 Dec 2026 / 11 Dec 2026 |

# 9.2

- **Hardware:** the Raspberry Pi 5 is the only measurement host; every cost figure depends on it being available and stable.
- **Kernel configuration:** cgroup v2 controllers on Raspberry Pi OS (the memory controller may need enabling at boot; I/O control may not be delegable to an unprivileged user) — confirmed in Phase 2 before the design depends on them.
- **Home Assistant internals:** the stripped in-sandbox platform depends on undocumented helper-layer behaviour of release 2026.8.3; the release stays pinned for the whole project.
- **External data:** Home Assistant analytics and the HACS index / GitHub for the corpora; third-party public APIs for end-to-end runs; credentials for integrations that need a cloud account.
- **Prerequisite ordering:** the threat model must precede the architecture, and the architecture the evaluation protocol; implementation cannot start until the kernel probe confirms the primitives.

# 10.1

| Resource | Purpose | Availability / Source |
|---|---|---|
| Raspberry Pi 5, 4 GB, with power supply and storage | The target device and the only measurement host | Already owned by the student |
| Development laptop | Writing code and the report; remote access to the Pi | Already owned by the student |
| Home Assistant core source, release 2026.8.3 | Platform under test, pinned for reproducibility | Open source (Apache 2.0), GitHub |
| HACS index and integration repositories | The two corpora of real community integrations | Public, GitHub |
| Home Assistant analytics | Raw install counts, from which §2.2's ecosystem figures are computed | Public web data [@ha-custom-integrations] |
| Research literature | Related work and the threat model the evaluation is scored against | University library access and open-access sources |
| Python 3.14 and Linux kernel facilities | The entire framework, with no third-party packages | Free and open source |
| OWASP Threat Dragon | Drawing the threat model | Free and open source [@threatdragon] |
| Generative AI assistant (Claude, via Claude Code) | Coding, drafting and review support, used as described in §12 | Student's own account |

# 10.2

| Item | Quantity | Unit Cost (MAD) | Total (MAD) | Justification |
|---|---|---|---|---|
| Raspberry Pi 5 (4 GB) with power supply and storage | 1 | 0 | 0 | Already owned; no purchase needed |
| Software, libraries and tools | — | 0 | 0 | All open source; no licences required |
| Cloud services and APIs | — | 0 | 0 | None required; only public, unauthenticated endpoints are used |
| **Total** | | | **0** | **This project requires no direct expenditure.** |

# 11

| Potential Risk | Likelihood | Impact | Mitigation / Fallback |
|---|---|---|---|
| The stripped Home Assistant cannot be built inside the sandbox, or a platform helper fails there | Med | High | Build the smallest possible integration against it in Phase 3 before committing; fallback is a proxy platform object forwarding every call to the mediator |
| Required kernel features are unavailable to an unprivileged user on Raspberry Pi OS | Med | Med | Probe on the device in Phase 2; enable controllers at boot where possible; record any control that cannot be enforced as a residual risk rather than claim it |
| Many corpus integrations need a cloud account, limiting end-to-end testing | High | Med | Measure import-level compatibility for the whole corpus; run end to end on a credential-free subset; report the limit explicitly |
| Tests pass because they were written by the author of the thing tested, or an instrument reports a false "clean" result | Med | High | Unconfined baseline for every result; real third-party integrations rather than only purpose-built ones; each instrument tested against a known-bad case |
| Implementation overruns and squeezes the evaluation | Med | High | Scope freeze at the 13 Nov milestone; evaluation harness built alongside the framework; unfinished features moved to future work rather than delaying measurement |
| Adversarial test code causes harm outside the test environment | Low | Med | Adversary purpose-built to reproduce attack *patterns*; run only on the student's own device and test installation; no vulnerable versions of real integrations used |

# 12

| Consideration | Guiding Question | Project Response |
|---|---|---|
| = | = | Not applicable. No user studies, surveys or participants; the user-comprehension question is explicitly out of scope. |
| = | = | No personal data is collected. All runs use the student's own device and a test Home Assistant installation with no real household data. Integration source is fetched from public repositories for local analysis only. |
| = | = | Security is the subject of the project: an ISO 31000 / STRIDE threat model drives the design and is scored in the evaluation. The adversarial integration reproduces published attack patterns only on the student's own test installation, never against third-party systems, and does not use disclosed-vulnerable versions of real integrations. No vulnerability disclosure is expected; if one is found, it will be reported privately to the affected project first. |
| = | = | Home Assistant is Apache 2.0 licensed and used unmodified; community integrations are used under their own licences for local analysis and are not redistributed. Public APIs are used unauthenticated at ordinary polling rates. Research papers obtained for the review are stored privately and not redistributed. |
| = | = | ISO 31000 risk management [@iso31000]; STRIDE threat identification [@shostack2014]; OWASP Threat Dragon [@threatdragon]; least-privilege access control in the sense of ISO/IEC 27001:2022 [@iso27001]; RFC 1918 private addressing for egress decisions [@rfc1918]; RFC 8520 (MUD) as the closest prior network-layer approach [@rfc8520]; Linux kernel interfaces (namespaces, seccomp-BPF, cgroup v2). |
| = | = | Generative AI (Anthropic's Claude, used through Claude Code) will be used for drafting code and prose and for reviewing arguments. Its output is verified rather than trusted: every measurement is run by the student on the Pi; every reported figure is reproducible from committed scripts and raw result files; code is covered by self-test suites, and each instrument is checked against a known-bad case; every reference is checked against the source, and the key papers are read in full. The student remains responsible for, and must be able to explain, all submitted code and text. AI use is declared in the final report. |
| = | = | Not applicable: the system under development contains no AI or machine-learning component. |
| = | = | The framework runs on a low-power single-board computer already in use and adds no hardware; heavier isolation (virtual machines) is avoided partly for this reason. Keeping community integrations working lets users keep devices whose vendor cloud support has ended. The plain-language renderer is aimed at household members who cannot read code. |

# refs

[@ha-analytics]: Home Assistant. (2026). *Analytics* [Dashboard]. https://analytics.home-assistant.io/ (accessed 21 August 2026). Cited for the count of reporting installations, which the dashboard renders client-side and which is therefore transcribed rather than parsed.
[@ha-custom-integrations]: Home Assistant. (2026). *Custom integration install counts* [Data set]. https://analytics.home-assistant.io/custom_integrations.json (retrieved 21 August 2026). The derived figures in §2.2 are the author's own computation over this dataset.
[@ha-devdocs]: Home Assistant. (n.d.). *Creating your first integration* and *Service actions*. Home Assistant Developer Documentation. https://developers.home-assistant.io/docs/creating_component_index/
[@hacs-include]: HACS. (n.d.). *Include default repositories*. HACS Documentation. https://hacs.xyz/docs/publish/include/
[@corno2022]: Corno, F., & Mannella, L. (2022). A threat model for extensible smart home gateways. *7th International Conference on Smart and Sustainable Technologies (SpliTech)*. IEEE.
[@ha-disclosure1]: Home Assistant. (2021, January 22). *Disclosure: Security vulnerabilities in custom integrations HACS, Dwains Dashboard, Font Awesome and others*. https://www.home-assistant.io/blog/2021/01/22/security-disclosure/
[@ha-disclosure2]: Home Assistant. (2021, January 23). *Security disclosure 2: Vulnerabilities in custom integrations HACS, Font Awesome and others*. https://www.home-assistant.io/blog/2021/01/23/security-disclosure2/
[@ha-security]: Home Assistant. (n.d.). *Security*. https://www.home-assistant.io/security/
[@gh-securitylab]: GitHub Security Lab. (n.d.). *Securing our home labs: Home Assistant code review*. The GitHub Blog. https://github.blog/security/vulnerability-research/securing-our-home-labs-home-assistant-code-review/
[@xz]: Rapid7. (2024). *Backdoored XZ Utils (CVE-2024-3094)*. https://www.rapid7.com/blog/post/2024/04/01/etr-backdoored-xz-utils-cve-2024-3094/
[@ha-rfc-remote]: Cohen, T. (2026, May 12). *Remote integration execution* [Request for comment]. Home Assistant Community. https://community.home-assistant.io/t/remote-integration-execution/1010130
[@thingnes2025]: Thingnes, T. R., & Meland, P. H. (2025). Security challenges for users of extensible smart home hubs: A systematic literature review. *Future Internet, 17*(6), 238. https://doi.org/10.3390/fi17060238
[@ha-addons]: Home Assistant. (n.d.). *Add-ons*. Home Assistant Developer Documentation. https://developers.home-assistant.io/docs/add-ons
[@barth2010]: Barth, A., Felt, A. P., Saxena, P., & Boodman, A. (2010). Protecting browsers from extension vulnerabilities. *Network and Distributed System Security Symposium (NDSS)*.
[@fernandes2016]: Fernandes, E., Jung, J., & Prakash, A. (2016). Security analysis of emerging smart home applications. *IEEE Symposium on Security and Privacy*.
[@flowfence]: Fernandes, E., Paupore, J., Rahmati, A., Simionato, D., Conti, M., & Prakash, A. (2016). FlowFence: Practical data protection for emerging IoT application frameworks. *USENIX Security Symposium*.
[@contexiot]: Jia, Y., Chen, Q. A., Wang, S., Rahmati, A., Fernandes, E., Mao, Z. M., & Prakash, A. (2017). ContexIoT: Towards providing contextual integrity to appified IoT platforms. *Network and Distributed System Security Symposium (NDSS)*.
[@smartauth]: Tian, Y., Zhang, N., Lin, Y.-H., Wang, X., Ur, B., Guo, X., & Tague, P. (2017). SmartAuth: User-centered authorization for the Internet of Things. *USENIX Security Symposium*.
[@tyche]: Rahmati, A., Fernandes, E., Eykholt, K., & Prakash, A. (2018). Tyche: A risk-based permission model for smart homes. *IEEE Secure Development Conference (SecDev)*. https://doi.org/10.1109/SECDEV.2018.00012
[@rfc8520]: Lear, E., Droms, R., & Romascanu, D. (2019). *Manufacturer Usage Description specification* (RFC 8520). IETF. https://www.rfc-editor.org/rfc/rfc8520
[@corno2023]: Corno, F., & Mannella, L. (2023). A gateway-based MUD architecture to enhance smart home security. *8th International Conference on Smart and Sustainable Technologies (SpliTech)*. IEEE. https://doi.org/10.23919/SpliTech58164.2023.10193747
[@mannella2024]: Mannella, L. (2024). *Securing IoT gateways in smart home environments* [Doctoral dissertation]. Politecnico di Torino.
[@ladisa2023]: Ladisa, P., Plate, H., Martínez, M., & Barais, O. (2023). SoK: Taxonomy of attacks on open-source software supply chains. *IEEE Symposium on Security and Privacy*.
[@li2025]: Li, Z., Li, K., Ma, B., Xu, M., Zhang, Y., & Cheng, X. (2025). *We urgently need privilege management in MCP: A measurement of API usage in MCP ecosystems* (arXiv:2507.06250). arXiv.
[@iso31000]: International Organization for Standardization. (2018). *Risk management — Guidelines* (ISO 31000:2018). https://www.iso.org/standard/65694.html
[@shostack2014]: Shostack, A. (2014). *Threat modeling: Designing for security*. Wiley.
[@threatdragon]: OWASP. (n.d.). *OWASP Threat Dragon* [Software]. https://owasp.org/www-project-threat-dragon/
[@rfc1918]: Rekhter, Y., Moskowitz, B., Karrenberg, D., de Groot, G. J., & Lear, E. (1996). *Address allocation for private internets* (RFC 1918). IETF. https://www.rfc-editor.org/rfc/rfc1918
[@iso27001]: International Organization for Standardization & International Electrotechnical Commission. (2022). *Information security, cybersecurity and privacy protection — Information security management systems — Requirements* (ISO/IEC 27001:2022).
