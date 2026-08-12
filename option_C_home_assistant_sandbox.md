# Option C: A Sandboxed Execution Framework for Home Assistant Integrations

## 1. Project Overview

Home Assistant is a widely used, open-source (Apache 2.0) home automation platform that people self-host, commonly on a Raspberry Pi or repurposed computer, to control smart-home devices (lights, locks, cameras, sensors) from one place. Its functionality is extended through "integrations" — small pieces of code that know how to talk to a specific device or service. Many integrations are official and vetted; a large number are community-written "custom integrations," typically installed via HACS (Home Assistant Community Store), with no formal security review.

Currently, every integration — official or custom — runs as regular code inside Home Assistant's own process, with the same level of system access as Home Assistant's core. This project builds a framework that lets integrations run instead in an isolated, sandboxed process (via gVisor), independently monitored at the kernel level (via eBPF), and communicating with Home Assistant only through its existing, public REST/WebSocket API — rather than through direct in-process access. A malicious or compromised integration is contained to its sandbox and killed immediately if it attempts behavior outside its declared role.

## 2. Where the Gap Is

- **The risk is real and documented, not hypothetical.** A 2021 Home Assistant security disclosure found multiple popular custom integrations (including ones distributed via HACS) that allowed an attacker to steal any file accessible to the Home Assistant process, without even logging in. Home Assistant's official response stated plainly that custom integrations are not created or maintained by the Home Assistant team, and that users install them at their own risk.
- **Home Assistant's own security documentation confirms the architecture assumes trust.** Its official security page states that Home Assistant assumes every logged-in user is trusted and does not currently enforce fine-grained privilege separation for third-party code.
- **A dedicated third-party security code review reached the same conclusion.** A GitHub security research team's audit of Home Assistant explicitly noted they did not have time to examine community integrations, but warned that these integrations have complete access to a user's Home Assistant installation, and that any vulnerability in them could compromise the entire system.
- **The community has directly raised this concern with no resolution.** A 2023 Home Assistant community forum thread asks plainly whether anything prevents a third-party integration from "just doing what it wants" — the honest answer today is no.
- **A live, unresolved community RFC (dated May 2026) proposes a related but distinct fix.** Titled "Remote Integration Execution," it proposes letting integrations run outside the main Home Assistant process — but its stated motivation is primarily resource distribution and crash isolation (so one integration can't take down the whole system or require an overpowered single machine), not security-focused sandboxing of untrusted code specifically.
- **No existing project implements security-focused sandboxing of Home Assistant integrations.** Searches for existing frameworks, add-ons, or proposals combining process isolation and behavioral monitoring for Home Assistant integrations returned nothing matching this description; a similarly-named repository (`home-assistant-sandbox`) turned out to be an unrelated development/testing environment, not a security isolation framework.

**Stated gap:** Home Assistant's own team, an independent security research team, and its own user community have all acknowledged that custom integrations run fully trusted with no sandboxing, and a live community proposal addressing process separation exists but is not focused on this security angle. No existing project provides a security-focused, sandboxed execution framework for Home Assistant integrations.

## 3. Architecture

```
Real, unmodified Home Assistant instance
        ↑  (existing public REST / WebSocket API)
        │
Sandboxing supervisor (this project)
├── gVisor sandbox (per integration)
│   └── Untrusted integration process
│       — reports sensor data / responds to service calls
│       — ONLY via the supervisor's controlled API bridge
├── Host kernel
│   └── eBPF programs — watch each sandboxed integration's syscalls
└── Policy agent
    ├── Receives eBPF events
    ├── Decides allow / log / kill
    └── Kills and quarantines a sandboxed integration on violation
```

Home Assistant's own source code is not modified. The supervisor is a separate system that plugs into Home Assistant purely through its existing, documented, public API — the same interface any external tool is allowed to use.

## 4. Extension: A Decentralized Trust Layer

Beyond protecting a single installation, the sandbox naturally produces something valuable to the wider community: real, observed evidence of whether a given integration ever misbehaves. This extension turns that evidence into a shared, decentralized trust signal — without any central authority (HACS, Home Assistant's team, or any company) deciding what counts as safe.

**What gets shared — a signed attestation, not an opinion.** Each time a sandboxed integration finishes a run, the supervisor can (with the user's consent) produce a small signed record: the integration's identity and exact code hash, whether the run was clean or triggered a violation, a timestamp, and the reporting node's own public key and signature. Tying trust to a content hash, not just a name, is deliberate: it directly closes the kind of attack seen in real supply-chain incidents (such as the tj-actions/changed-files compromise, discussed in Option A), where a trusted name shipped different, compromised code. A new code hash is treated as unproven, regardless of the old version's reputation.

**Identity is self-sovereign.** Each Home Assistant instance running the framework generates its own local keypair — the same model used by PGP and Nostr. There is no company or registry issuing identities.

**Propagation is gossip-based, not server-based.** Nodes periodically exchange attestations with a handful of peers, either directly or through small, optional, community-run relay nodes (interchangeable, replaceable by anyone — never a single point of control, following Nostr's relay model).

**Scoring is computed locally by each node, not globally agreed.** This avoids needing blockchain-style consensus: each node calculates its own trust view from whatever attestations it has personally received (e.g. "347 independent nodes ran this exact code hash clean over 6 months, 0 violations") — the same subjective, locally-computed approach PGP's web of trust uses.

**Honest limitation: Sybil resistance is not fully solved.** Nothing inherently stops someone from running many fake nodes to inflate a malicious integration's score. The mitigation used here is a hybrid: weighting attestations more heavily from long-established nodes or ones the user already transitively trusts, rather than counting raw attestation volume. This raises the cost of an attack meaningfully but does not eliminate it, and this should be stated plainly in the proposal rather than implied away — Sybil resistance is a known, still-debated open problem across all web-of-trust systems, not something specific to this project's design.

## 5. Day-to-Day Work, by Phase

**Phase 1 — Learn the integration interface and API surface (weeks 1-2)**
Study Home Assistant's public developer documentation for building integrations (entity registration, service calls, state reporting) and its REST/WebSocket API for external tools. Stand up a real, local Home Assistant instance for development and testing. Day-to-day work: documentation study, small test scripts talking to a real HA instance via its API.

**Phase 2 — Sandbox core (weeks 3-5)**
Build the orchestrator that launches a chosen integration inside a gVisor sandbox and connects it to Home Assistant only through the supervisor's controlled bridge. Pick a deliberately narrow initial scope: support one or two simple integration patterns (e.g., a periodic sensor reading, a switch responding to on/off commands) rather than the full integration API surface. Day-to-day work: gVisor configuration, designing the API bridge, testing round-trip communication (sandboxed integration reports state, Home Assistant reflects it correctly).

**Phase 3 — eBPF guard (weeks 6-8)**
Write eBPF programs watching each sandboxed integration process for behavior outside its declared role: filesystem access beyond its permitted scope, unexpected network activity, attempts to reach other integrations' data. Wire violations into the policy agent for real-time kill and logging. This is the highest-risk phase, consistent with prior variants using this technique — expect slow, iterative debugging. Day-to-day work: eBPF program development, adversarial self-testing with deliberately bad test integrations.

**Phase 4 — Demonstration, packaging, and write-up (weeks 9-12)**
Package the supervisor as an installable, documented framework usable by any Home Assistant user, not a one-off script tied to a personal setup. Prepare a live demo: a legitimate sandboxed integration reporting real data, and a deliberately malicious fake integration attempting to read unrelated files or exfiltrate data, caught and killed in real time. Write up the architecture, threat model, and honest scope limits. Optionally, share the working prototype with the Home Assistant community (e.g. the relevant RFC thread) for real external feedback. Day-to-day work: packaging/documentation, demo rehearsal, write-up.

**Optional Phase 5 — Decentralized trust layer, if time allows (stretch goal, beyond week 12)**
Implement attestation generation and signing after each sandboxed run, a simple gossip exchange between a small number of test nodes (or a lightweight relay), and local trust-score computation. Demo: two or three simulated nodes sharing attestations for the same integration, with a visibly computed trust score updating as clean runs accumulate, and a deliberately compromised version (different code hash) starting from zero trust. Day-to-day work: attestation format design, gossip protocol implementation, local scoring logic, adversarial testing of the trust computation itself (e.g. simulating a Sybil attempt to show the mitigation's effect, not just describe it).

## 6. Feasibility Assessment

| Factor | Assessment |
|---|---|
| Learning Home Assistant's integration/API surface | Low-moderate risk — well-documented, deliberately built for external developers |
| Not modifying Home Assistant core | Reduces risk significantly — avoids the genuinely infeasible task of understanding HA's full internal architecture |
| Sandbox core (gVisor) + API bridge | Moderate risk — real design work, but bounded by deliberately narrow initial integration-pattern scope |
| eBPF guard | **Highest risk**, consistent with other variants — same caveats about debugging difficulty apply |
| Decentralized trust layer (optional) | Moderate risk, but scoped as a stretch goal — a small-scale simulated demo (a few nodes) is achievable even if a full gossip network is not; should not be attempted before the core sandbox (Phases 1-4) is solid |
| Overall 12-week fit | Core sandbox (Phases 1-4) is feasible if scoped narrowly and if July/August prep time is spent on gVisor/eBPF fundamentals; the trust layer is an explicit stretch goal, not part of the guaranteed deliverable |

**Fallback plan:** if eBPF proves too difficult, fall back to `seccomp-bpf` plus namespaces for the monitoring layer, same fallback used in the other variants. If time runs short, the trust layer is the first thing to cut — the core sandboxing framework stands on its own without it.

## 7. Honest Limitations

- This framework does not retroactively secure the thousands of existing community integrations already in use — those were written assuming direct in-process access and were not built against this sandboxed pattern. The honest framing is "a safer way to write new integrations going forward," not "makes all existing integrations safe."
- Only a narrow set of integration patterns would be supported within a 3-month scope, not the full breadth of Home Assistant's integration API.
- As with the other variants, gVisor and eBPF are established techniques; the contribution is their specific application to this real, currently-open problem in Home Assistant, not new isolation theory.
- Getting this merged into Home Assistant core itself is not a realistic 3-month outcome; sharing it as a working, documented, external prototype with the relevant community is.
- The decentralized trust layer's underlying concept (web of trust) is a well-established, 30+ year old idea (originating with PGP in 1992); the contribution here is grounding it in objective sandbox-observed behavior rather than pure subjective vouching, applied to this specific ecosystem — not inventing a new trust model. Sybil resistance remains a known, unsolved limitation, mitigated but not eliminated.

## 8. Sources Consulted

- Home Assistant official security disclosures (January 2021), describing file-theft vulnerabilities in popular custom integrations
- Home Assistant official security page (security assumptions and scope)
- GitHub Security Lab code review of Home Assistant ("Securing our home labs: Home Assistant code review")
- Home Assistant Community forum: "What's the security concept for third party integrations?" (2023)
- Home Assistant Community forum / GitHub Discussion: "RFC: Running Integrations on Separate Machines" / "Remote Integration Execution" (2026)
- Home Assistant developer documentation (integration development, REST/WebSocket APIs)
- General gVisor and eBPF sources as cited in Option A
- OpenPGP Web of Trust documentation and Sequoia-PGP implementation notes
- Nostr Web of Trust tooling documentation (social-graph-based decentralized reputation)
- DCoSL protocol (decentralized reputation and web of trust, GitHub)
