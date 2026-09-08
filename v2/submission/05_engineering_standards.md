# 5. Engineering Standards

Standards are listed here only where they are **load-bearing** — where the work follows the
standard's structure, adopts its vocabulary, or is checkable against it. A standard named without
being used is not a standard the project applied.

## 5.1 Risk management and threat modelling

### 5.1.1 ISO 31000 — Risk management

**Used as the process framework for the entire threat model (§8).** ISO 31000 [25] specifies a
risk-management process — establish scope and context, identify, analyse, evaluate, treat,
monitor, record — and deliberately does *not* prescribe a technique for identification.

The threat model follows its clause structure explicitly, and **each section names the clause it
discharges**, so the process is auditable rather than merely invoked: scope and context (§6.3.2,
§6.3.3), assets (§6.3.2), risk criteria (§6.3.4), identification (§6.4.2), analysis and
evaluation (§6.4.3–6.4.4), treatment (§6.5), residual risk (§6.5.3) and monitoring (§6.6).

One deliberate departure is recorded. ISO 31000 is generic and supplies no impact criteria. Rather
than importing a published generic scale, the impact scale here is **derived from the asset
valuation**, because no general-purpose scale contains a rung for defeat of a life-safety function
in a dwelling. Calibration to the actual risk owner — the occupying householder, who has no
security function and no incident-response capability — is what makes the ratings mean anything.

### 5.1.2 STRIDE — Threat identification

**Used to fill the identification slot ISO 31000 leaves open.** STRIDE [26] supplies a systematic
enumeration — spoofing, tampering, repudiation, information disclosure, denial of service,
elevation of privilege — and it is applied here **per trust boundary** rather than per component,
which produces the six-boundary structure of §8.4 and the eighteen threats of §8.5.

Its known limitation is stated in §8.9: STRIDE is boundary-oriented, and is consequently weaker on
threats arising from the *composition* of individually permitted actions. That limitation is why
one residual risk is retained rather than solved.

### 5.1.3 OWASP Threat Dragon — Threat model representation

**Used to draw the model.** Threat Dragon [27] is an open-source threat-modelling tool with a
documented JSON model format. Both figures in the threat-model chapter are produced by a script
that emits the Threat Dragon model **and** the rendered figure from one source, so the diagram and
the model cannot drift apart — the same discipline the project applies to every other number.

## 5.2 Information security management

### 5.2.1 ISO/IEC 27001 — Access control

The design's core principle is ISO/IEC 27001's Annex A access-control position: access to
information and assets should be **restricted to what is required for the authorised purpose**,
and granted by explicit rule rather than by default. Home Assistant's integration model is the
exact inverse — every integration receives every capability, and the manifest of §9.4 is the
mechanism that supplies the missing rule.

> *[To verify before submission: cite the current edition (ISO/IEC 27001:2022) and the specific
> Annex A control identifiers used. Currently argued from the principle rather than the clause.]*

### 5.2.2 OWASP Secure Coding Practices

Three practices are applied and each is checkable in the artifact:

- **Default deny.** Anything not declared is refused, and the majority of the manifest is enforced
  *structurally* — the capability is absent from the sandbox rather than refused on request.
- **Validate at the trust boundary, in the trusted party.** Identity is taken from the socket the
  request arrived on, never from a field in the message the sandbox composes. The one place this
  rule was violated — a flag read from the sandbox's own request — was a genuine security defect,
  and §13.3 records that it was found by writing the attack rather than by reading the code.
- **Fail legibly.** The seccomp filter returns `EPERM` rather than killing the process, so a
  refusal stays diagnosable. Where a control cannot do this — the cgroup kill — the report records
  that the audit trail is weakest exactly where the control is strongest.

## 5.3 Network and platform interfaces

### 5.3.1 RFC 1918 — Private address space

**Normative for what the egress broker refuses.** RFC 1918 [28] defines the private IPv4 ranges,
and the broker's `is_public` check treats those ranges — with loopback, link-local and their IPv6
equivalents — as non-public destinations requiring a separate explicit declaration. This is what
prevents a declared public hostname from becoming a route to the router's admin page.

### 5.3.2 Linux kernel interfaces

These are stable kernel ABIs rather than standards, and they are listed here because the design's
security properties rest on them:

| Interface | Used for |
|---|---|
| **Namespaces** (user, mount, PID, network, IPC, UTS) | The isolation boundary itself |
| **seccomp-BPF** | Syscall restriction — 29 calls denied, returning `EPERM` |
| **cgroup v2** | Memory, CPU, process-count and disk-space bounds |
| **SCM_RIGHTS** | File-descriptor passing, so a connected socket crosses the boundary without the sandbox ever holding a route |

**The kernel's behaviour was verified on the target rather than assumed**, and the verification
found two things a specification would not have: cgroup v2's `memory` controller is absent on a
stock Raspberry Pi OS installation, and its `io` controller is present but **not delegated** to a
user manager — which is why one residual risk is retained as *inherited* rather than fixed.

## 5.4 Standards considered and not applied

Recorded because their absence is a decision.

- **ISO/IEC 27400** (IoT security and privacy guidelines) is addressed to device manufacturers and
  service providers. Its guidance for a *platform operator* has no addressee here, since the
  operator is the householder.
- **IEC 62443** targets industrial automation, and its zone-and-conduit model does not transfer to
  a single-process consumer hub.
- **MUD (RFC 8520)** [19] is directly relevant and is treated as **prior work rather than as an
  applied standard** (§7.3.2): the closest published work applies it to this exact problem, and
  §7.3.2 states precisely why network-layer enforcement cannot reach the platform-API authority
  that Table 2.1 shows to be most consequential.
