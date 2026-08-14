# Threat Model — Sandboxed Execution Framework for Home Assistant Integrations

**Version 0.1 — 2026-08-14**
Method: **ISO 31000:2018** risk management process, with **STRIDE** as the identification
technique inside it.

---

## Part 0: Why these two frameworks, and how they fit together

This is the first question an auditor will ask, so answer it before the content starts.

**They do different jobs, and neither is a substitute for the other.**

| | ISO 31000:2018 | STRIDE |
|---|---|---|
| What it is | A *process* for managing risk — a management standard | A *taxonomy* for finding threats — an engineering heuristic |
| Origin | ISO/TC 262, published 2018 | Microsoft SDL, Kohnfelder & Garg, 1999 |
| What it tells you | The order of operations: establish context → identify → analyse → evaluate → treat → monitor → record | Six categories to check each part of a system against |
| What it does *not* tell you | How to find a threat in a Unix process boundary | What to do once you have found one, or which ones matter |
| Certifiable? | **No** — 31000 is explicitly guidance, not requirements. (ISO/IEC 27001 is the certifiable one) | Not applicable |

**The join is one specific step.** ISO 31000 clause 6.4.2 is *risk identification*, and the
standard deliberately does not prescribe a technique for it — that is left to
IEC 31010, which catalogues techniques and expects you to pick. STRIDE is the technique
this project plugs into that slot. Everything around it — context, criteria, analysis,
evaluation, treatment, monitoring — comes from 31000.

```
ISO 31000 clause 6 — the process
│
├── 6.3  Scope, context, criteria ........... Part 1 of this document
├── 6.4  Risk assessment
│        ├── 6.4.2 Risk identification ...... Part 2  ← STRIDE goes HERE
│        ├── 6.4.3 Risk analysis ............ Part 3
│        └── 6.4.4 Risk evaluation .......... Part 4
├── 6.5  Risk treatment .................... Part 5
├── 6.6  Monitoring and review ............. Part 7
└── 6.7  Recording and reporting ........... Part 8
```

**Say this in the defence, in one sentence:** *"ISO 31000 supplies the process and the
decision discipline; it does not tell you how to find threats in a Unix process boundary, so
STRIDE fills clause 6.4.2, which 31000 leaves open on purpose."*

**One honest caveat about the fit.** ISO 31000 is written for organisational risk, where a
named risk owner accepts residual risk on behalf of an organisation. Here the "organisation"
is a household, and the risk owner is a hobbyist who is simultaneously the system
administrator, the person who installs the untrusted software, and the asset owner. That is
not a defect in the method, but it changes what "risk acceptance" can realistically mean —
see §1.6, which treats it as a finding rather than glossing over it.

---

# Part 1: Scope, context and criteria (ISO 31000 §6.3)

## 1.1 Scope of this assessment

**In scope.** The execution of third-party Home Assistant custom integrations (obtained via
HACS) on a user's own hardware, and specifically the security boundary this project
introduces between such an integration and the rest of the house.

**Out of scope, deliberately, and each for a stated reason:**

| Excluded | Why |
|---|---|
| Home Assistant's own vulnerabilities | The framework is a retrofit alongside stock HA (§9 of `PROJECT_STATUS.md`). HA's own bugs are upstream and unchanged by this work |
| Physical attacks on the Raspberry Pi | Anyone with the SD card owns the house regardless of software boundaries |
| The user's network perimeter (router, WAN) | Assumed hostile-adjacent but not this project's control surface |
| Malicious *Home Assistant core* code | If core is compromised, the supervisor's isolation is meaningless — core is in the TCB |
| Full decentralised attestation of the audit log | Explicitly out of scope, `supervisor.py:83–85`. See T03 residual |
| Supply-chain compromise of Python/pip/the OS | Below the project's boundary; the same assumption every application makes |

**Time horizon:** the assessment covers the system as it exists on 2026-08-14, running
polling-sensor integrations. Actuators are analysed as a *foreseeable extension* (T21) because
Decision 3 makes them a stretch goal, and a threat model that says nothing about the stretch
goal is not much use for deciding whether to build it.

## 1.2 External context

- **HACS distributes ~2,000 integrations with no security review.** There is no signing, no
  sandbox, no permission declaration, and no review gate. Installation grants the code the full
  privilege of the Home Assistant process.
- **An integration today runs *inside* HA's own Python process.** It therefore has, by
  construction: every entity's state, every service call, `secrets.yaml`, the config directory,
  the network, and the same uid as HA. There is no boundary to cross because there is no
  boundary.
- **The precedent for the proposed control already exists in adjacent ecosystems** — browser
  extension permissions, Android manifest permissions. Both are declarative, both are reviewable,
  and both are known to be imperfect in exactly the way §1.6 and T16 describe. That precedent is
  an argument *for* the design and a limit *on* the claim, and the report should use it as both.
- **Upstream is moving in a compatible direction** for unrelated reasons (HA's "Remote
  Integration Execution" RFC). That mechanism would need a policy layer; this is one.

## 1.3 Internal context

The deployment assumed throughout: a single Raspberry Pi 5 in a private home, running
Home Assistant plus this framework, administered by one non-specialist user who is also the
occupant. Integrations are installed by that user, on their own initiative, from HACS.

Two consequences follow, and both shape the whole model:

1. **There is no security team, no monitoring, and no incident response.** Any control that
   depends on someone reading a log is a control that will not fire. This is why detection is a
   separate column in the register and why so many rows read "none".
2. **The person accepting the risk is the person least equipped to evaluate it.** ISO 31000
   assumes an informed risk owner. Here, the risk owner's expertise is the binding constraint —
   which is precisely the argument for making capability *declared and visible* rather than
   relying on the user's judgement about code they cannot read.

## 1.4 Assets

Ranked by consequence of loss, because that ranking drives Part 3.

| ID | Asset | Why it matters | Worst case |
|---|---|---|---|
| A1 | **Physical access control** — locks, garage doors, alarm arm/disarm | Directly protects the occupants and property | Burglary; personal harm |
| A2 | **Presence and occupancy data** — device trackers, motion history, camera feeds | Reveals when the house is empty, and who is in it | Enables A1 attacks; stalking; blackmail |
| A3 | **The HA long-lived access token** | A single unscoped credential granting full read/write over every entity and service | Equivalent to losing A1 + A2 + A4 at once |
| A4 | **`secrets.yaml` and integration credentials** | Cloud accounts, API keys, sometimes reused passwords | Lateral compromise of the user's online accounts |
| A5 | **Other devices on the LAN** — router admin, NAS, printers, IP cameras | Frequently unpatched, frequently unauthenticated, and reachable from the Pi | Beachhead into the whole home network |
| A6 | **The audit log** | The evidence trail; the project's non-repudiation claim | Attacker acts without attributable record |
| A7 | **Availability of the home automation itself** | Heating, lighting, alarms | Nuisance to genuine harm (heating off in winter) |

**Note A5 explicitly.** It is the asset most often forgotten in HA threat discussions, because
the instinct is to reason about "what HA data can leak". But an integration is a *program on
your home network*, and the network is usually the softest thing it can touch. This is the asset
that motivated the egress work (§5.10), and it is where T14 landed — twice, since closing the
sandbox's route to the LAN is what created the broker that reopened it.

## 1.5 Actors

| ID | Actor | Capability | Motivation |
|---|---|---|---|
| P1 | **Malicious integration author** | Writes arbitrary Python; publishes via HACS; authors the manifest that is supposed to constrain them; can ship an update at any time | Credential harvest, botnet, targeted burglary, cryptomining |
| P2 | **Compromised-but-honest author** | Same code capability, no intent — account takeover, or a malicious dependency pulled in | Attacker's, not theirs |
| P3 | **The user** | Installs integrations; can read manifests; cannot audit Python; owns all assets | Wants the integration to work; will click through anything that blocks that |
| P4 | **Network-adjacent attacker** | Sees LAN traffic, can reach the Pi's ports; no code execution | Opportunistic |
| P5 | **The HA community reviewer** | Reads public source; no privileged position; **acts as a control multiplier, not an actor with intent** | Reputation, curiosity |

**P5 is deliberately in the actor list even though they are not a threat.** The integrations
this framework runs are open source, and the design leans on that: a declared manifest is
reviewable in a way that opaque code behaviour is not. P5 is why T16's residual risk is
"reduced" rather than "unchanged" — but P5 is unreliable, unpaid, and unassigned, so no control
may *depend* on them. The right claim is that the manifest raises the probability that abuse is
noticed, not that it guarantees it.

## 1.6 Trust boundaries

```
                    ┌───────────────────────────────────────────┐
  HACS / author ══► │  TB4: authorship & distribution           │
     (P1, P2)       │  the manifest is written by the party     │
                    │  it is meant to constrain                 │
                    └────────────────┬──────────────────────────┘
                                     │ (install time)
   ┌─────────────────────────────────┼───────────────────────────────────┐
   │  The Raspberry Pi               │                                   │
   │                                 ▼                                   │
   │   ┌────────────────────────────────────────────┐                    │
   │   │ SANDBOX (untrusted)                        │                    │
   │   │   integration code + compat shim           │                    │
   │   │   uid mapped, own PID/mount/user ns        │                    │
   │   └──────┬──────────────────────────┬──────────┘                    │
   │          │ TB1                      │ TB5                           │
   │          │ unix socket, JSON        │ syscalls → host kernel        │
   │          │ ONE socket per sandbox   │ seccomp denylist              │
   │          ▼                          ▼                               │
   │   ┌────────────────────────────────────────────┐    TB3             │
   │   │ SUPERVISOR (trusted)                       │───────────► internet
   │   │   manifest enforcement, audit log,         │    egress broker    │
   │   │   egress broker, HOLDS THE TOKEN           │                    │
   │   └──────┬─────────────────────────────────────┘                    │
   │          │ TB2: REST/WebSocket + unscoped token                     │
   │          ▼                                                          │
   │   ┌────────────────────────────────────────────┐                    │
   │   │ HOME ASSISTANT (trusted, unmodified)       │                    │
   │   │   + sandbox_bridge (trusted, ~250 lines)   │                    │
   │   └────────────────────────────────────────────┘                    │
   └─────────────────────────────────────────────────────────────────────┘
                                                       LAN devices (A5) ◄─ TB3
```

| ID | Boundary | What crosses it | Enforced by |
|---|---|---|---|
| **TB1** | sandbox ↔ supervisor | Every mediated operation, as JSON lines | Manifest policy in `supervisor.py`; one 0600 socket per sandbox |
| **TB2** | supervisor ↔ Home Assistant | REST/WebSocket calls carrying the unscoped token | Nothing — the supervisor is fully authorised here by design |
| **TB3** | sandbox ↔ network | All outbound HTTP, via the broker | seccomp `AF_INET` denial + `egress.py` allowlist |
| **TB4** | author/HACS ↔ user's machine | The integration code *and* its manifest | Nothing technical. The user's judgement, plus P5 |
| **TB5** | sandbox ↔ host kernel | Syscalls | seccomp-bpf denylist; user/PID/mount namespaces |

**TB4 is the weakest boundary in the system and it is not a Python problem.** It is the
boundary the project cannot close technically, and being explicit about that is worth more than
pretending otherwise — see T16, T17, T18.

## 1.7 Risk criteria (ISO 31000 §6.3.4)

> ⚠️ **This section is the one that is properly yours to set, not mine.** ISO 31000 §6.3.4 puts
> criteria in the hands of the risk owner, and the whole register downstream moves if you change
> these scales. What follows is a *proposal* calibrated to a single household — argue with it.

**Likelihood** — probability that a household running one malicious or compromised integration
experiences this, per year:

| | Level | Meaning |
|---|---|---|
| L1 | Rare | Requires a kernel 0-day, physical access, or resources beyond a hobbyist attacker |
| L2 | Unlikely | Requires targeted effort against *this framework specifically* — study, custom tooling |
| L3 | Possible | A competent author could do it from public knowledge, but must choose to |
| L4 | Likely | Trivial with off-the-shelf tooling; needs no framework-specific knowledge |
| L5 | Almost certain | Happens by default; requires no attacker skill or intent at all |

**Consequence** — to the household:

| | Level | Meaning |
|---|---|---|
| C1 | Negligible | Nuisance; no data leaves and no control is lost |
| C2 | Minor | Non-sensitive data leaves the house (e.g. broadband quota figures) |
| C3 | Moderate | Sensitive data leaves — presence, occupancy patterns, camera stills |
| C4 | Major | Attacker gains control of non-safety devices, or a foothold on other LAN hosts (A5) |
| C5 | Severe | Physical security compromised (locks, alarms, cameras) or full house control |

**Risk matrix and tolerance:**

| | C1 | C2 | C3 | C4 | C5 |
|---|---|---|---|---|---|
| **L5** | Med | High | High | Critical | Critical |
| **L4** | Low | Med | High | High | Critical |
| **L3** | Low | Med | Med | High | High |
| **L2** | Low | Low | Med | Med | High |
| **L1** | Low | Low | Low | Med | Med |

**Tolerance, as proposed:**

- **Critical** — must be treated before the framework is presented as usable. No exceptions.
- **High** — must be treated, or formally retained with the reason recorded in Part 6.
- **Medium** — may be retained, but must be monitored and must appear in the residual-risk
  statement given to the user.
- **Low** — retained without further action.

**Why this scale and not a 3×3.** A 3×3 collapses "requires a kernel 0-day" and "trivial with
public tooling" into one bucket, and those two drive completely different treatment decisions.
Five levels is the smallest scale that keeps them apart.

---

# Part 2: Risk identification — STRIDE per boundary (ISO 31000 §6.4.2)

STRIDE applied *per trust boundary* rather than per element. The per-element variant generates
more rows; the per-boundary variant is what maps onto this architecture, where the interesting
question is always "what does crossing this line let you do?"

Reminder of the six, with the property each violates:

| | Threat | Violates | The question to ask |
|---|---|---|---|
| **S** | Spoofing | Authentication | Can something claim to be something it is not? |
| **T** | Tampering | Integrity | Can data or code be modified without authorisation? |
| **R** | Repudiation | Non-repudiation | Can an actor deny having done something? |
| **I** | Information disclosure | Confidentiality | Can data reach someone who should not have it? |
| **D** | Denial of service | Availability | Can the system be made unusable? |
| **E** | Elevation of privilege | Authorisation | Can an actor gain capability it was not granted? |

## TB1 — sandbox ↔ supervisor

| ID | S/T/R/I/D/E | Threat |
|---|---|---|
| **T01** | S | Sandbox claims another integration's identity on the bridge, to borrow a wider manifest |
| **T02** | T | Sandbox edits its own manifest on disk to widen its own policy |
| **T03** | T | Sandbox rewrites the audit log and recomputes the chain |
| **T04** | R | Sandbox acts outside mediation entirely, so no record is ever created |
| **T05** | I | Sandbox reads the HA token and calls HA's API directly, bypassing policy |
| **T06** | I | Sandbox reads entity state outside its declared scope *through* the mediated path |
| **T07** | D | Sandbox exhausts CPU, RAM or PIDs and takes the house automation down |
| **T08** | E | Sandbox escapes its namespaces through a kernel vulnerability |

## TB2 — supervisor ↔ Home Assistant

| ID | | Threat |
|---|---|---|
| **T09** | E | The token is unscoped, so compromise of the supervisor is compromise of the whole house |
| **T10** | I | The token at rest (`.ha_token`) is readable by any process running as the same user |
| **T11** | T | `sandbox_bridge` accepts whatever the supervisor sends, with no independent policy check |

## TB3 — sandbox ↔ network

| ID | | Threat |
|---|---|---|
| **T12** | I | Exfiltration of house data to a host the manifest legitimately declares |
| **T13** | E | Direct socket to LAN devices (A5) — lateral movement needing no HA credential at all |
| **T14** | E | The broker is re-targeted at the LAN or loopback by DNS: the allowlist matches host *names*, and the author owns the DNS records those names point at |
| **T15** | E | The broker is used to reach HA's own API with the supervisor's network position |

## TB4 — author / HACS ↔ the user's machine

| ID | | Threat |
|---|---|---|
| **T16** | E | An over-declaring manifest that nobody reads — a weather widget declaring lock access |
| **T17** | T | A benign integration is updated to a malicious version through HACS's normal update path |
| **T18** | R | The manifest is self-declared by the party it is meant to constrain |

## TB5 — sandbox ↔ host kernel

| ID | | Threat |
|---|---|---|
| **T19** | E | The seccomp filter is a *denylist*; anything not enumerated is permitted |
| **T20** | E | Unprivileged user namespaces are themselves a well-known privilege-escalation surface — the control adds attack surface |

## Foreseeable extension — actuators (Decision 3 stretch goal)

| ID | | Threat |
|---|---|---|
| **T21** | E | Abuse of a capability the integration legitimately declared — the "3am unlock" |

---

# Part 3 & 4: Risk analysis and evaluation (ISO 31000 §6.4.3–6.4.4)

**Inherent** = risk with no framework at all (today's HACS reality).
**Residual** = risk as the system stands on 2026-08-14, with isolation, seccomp and the egress
broker built and measured.

| ID | Threat (short) | Inherent L×C | Inherent | Control now | Residual L×C | Residual | Evidence |
|---|---|---|---|---|---|---|---|
| T01 | Identity spoofing on the bridge | L2×C4 | Med | One 0600 socket per sandbox; identity is *positional*, never asserted | L1×C4 | **Low** | `supervisor.py:393–397` |
| T02 | Manifest self-modification | L4×C5 | Critical | Manifest is outside the sandbox's filesystem allowlist | L1×C5 | **Med** | `isolate.py:105–120` |
| T03 | Audit-log rebuild | L3×C3 | Med | Mount ns hides `audit/`; **chain is still unkeyed** | L2×C3 | **Med** | `test_audit.py`, asserted as a limit |
| T04 | Acting outside mediation | L5×C5 | Critical | Isolation makes mediation the only route | L2×C5 | **High** | probe 6/10 → 10/10 |
| T05 | Token theft (4 doors) | L5×C5 | Critical | Env scrub + PID ns + mount ns; all four closed | L1×C5 | **Med** | probe check 6, measured before/after |
| T06 | Reading undeclared entities | L5×C3 | High | Manifest `reads_entities` enforced per request | L2×C3 | **Med** | 43 entities baseline → 2 under policy |
| T07 | Resource exhaustion | L3×C2 | Med | **None — cgroups not implemented** | L3×C2 | **Med** | Known gap |
| T08 | Namespace escape via kernel bug | L1×C5 | Med | Namespaces + seccomp reduce reachable surface | L1×C5 | **Med** | Structural |
| T09 | Unscoped token → supervisor = house | L4×C5 | Critical | **None available** — HA offers no scoped tokens | L2×C5 | **High** | Upstream limitation |
| T10 | Token at rest on disk | L4×C5 | Critical | Excluded from sandbox allowlist | L2×C5 | **High** | Door 4, `isolate.py` |
| T11 | `sandbox_bridge` trusts the supervisor | L2×C4 | Med | By design — it is inside the TCB | L2×C4 | **Med** | `PROJECT_STATUS.md` §5.7 |
| T12 | Exfiltration to a *declared* host | L4×C3 | High | **Structural — an allowlist governs destination, not content** | L4×C3 | **High** | By construction |
| T13 | Direct socket to LAN devices | L4×C4 | High | seccomp denies `socket(AF_INET)` | L1×C4 | **Med** | probe checks 7, 8 |
| T14 | **Broker re-targeted by DNS** | L3×C4 | High | ✅ **Treated** — broker resolves, refuses every non-public address, and connects to the address it checked | L1×C4 | **Med** | **probe check 9, ALLOWED → BLOCKED** |
| T15 | Broker reaches HA's own API | L3×C5 | High | ✅ **Treated by the same change.** `blocked_hosts` is name-only and never covered this; the destination check does | L1×C5 | **Med** | **probe check 10, ALLOWED → BLOCKED** |
| T16 | Over-declaring manifest | L4×C5 | Critical | Declaration is visible and reviewable (P5); nothing forces review | L3×C5 | **High** | Android/browser precedent |
| T17 | Malicious update through HACS | L3×C5 | High | **None** — no pinning, no re-review on update | L3×C5 | **High** | Ecosystem property |
| T18 | Manifest self-declared | L5×C4 | Critical | Same as T16 — visibility, not prevention | L4×C4 | **High** | By construction |
| T19 | Seccomp denylist gaps | L2×C4 | Med | 25 entries covering the known escape primitives | L2×C4 | **Med** | `syscall_filter.py` |
| T20 | userns as escalation surface | L1×C5 | Med | Accepted cost of the control | L1×C5 | **Med** | Introduced by treatment |
| T21 | Declared-capability abuse (actuators) | L3×C5 | High | **Structurally impossible to prevent by confinement** | L3×C5 | **High** | Decision 3 analysis |

## What the evaluation says

**Inherent profile: 7 Critical, 7 High, 7 Medium.** That is the HACS status quo, and it is not
an exaggeration — an integration today runs in HA's process with HA's privileges and no
declared limits.

**Residual profile: 0 Critical, 6 High, 15 Medium, 1 Low** — after T14 and T15 were treated the
same day they were identified (§5.1).

**Every Critical was eliminated.** That is the headline result and it is defensible, because
each one is backed by a measurement rather than an assertion.

**The six remaining High risks split into two groups, and the distinction matters more than the
count:**

| Group | Risks | Character |
|---|---|---|
| **Structural** — cannot be fixed by this design | T12, T18, T21, and T09 (upstream) | An allowlist governs destination not content; a self-declared contract is self-declared; confinement cannot distinguish legitimate use of a declared capability from abuse of it |
| **Ecosystem** — outside the project's control surface | T16, T17 | Require HACS-side review or signing; the framework can only make the information available |
| ~~**Implementation — fixable**~~ | ~~T14, T15~~ | **Treated 2026-08-14, hours after being identified. See §5.1** |

**Not one of the six survivors is unfinished work.** Four are structural limits of the design and
two need a change to HACS. That is a meaningfully different position from "eight things still to
do", and it is the sentence to lead with.

---

# Part 5: Risk treatment (ISO 31000 §6.5)

## 5.1 T14 / T15 — the broker checked names, not destinations

**Found while writing this document on 2026-08-14, and treated the same day.** Both halves —
the finding and the fix — are measurements rather than assertions.

`egress.py:86–102` authorises a request by parsing the URL and comparing `parsed.hostname`
against the manifest allowlist and against `blocked_hosts`. **It never resolves the name, and
never inspects the address it is about to connect to.** `urlopen` then does its own resolution.

The consequence is that the manifest constrains *names*, and an attacker controls the mapping
from names to addresses. An author declares `cdn.their-domain.example` — an entirely plausible
entry that survives review by P5 — and points its A record at `192.168.1.1`. The supervisor,
which is trusted and which is *not* subject to the seccomp `AF_INET` denial, then makes the
request on the sandbox's behalf and hands back the response body.

**Demonstration run today**, using only the existing `Egress` class and a local stub, with
`blocked_hosts=("127.0.0.1",)` exactly as `supervisor.py` passes it:

```
manifest:  network: ["localhost"]      # resolves to 127.0.0.1
request:   GET http://localhost:<port>/admin
result:    status: 200  body: PRETEND-THIS-IS-A-LAN-DEVICE-ADMIN-PAGE
```

The request was authorised, performed, and its body returned to the sandbox.

**Why this matters more than an ordinary bug.** §5.10 closed lateral movement to the LAN by
denying the sandbox `AF_INET` outright — probe checks 7 and 8 went from ALLOWED to BLOCKED. But
denying the sandbox sockets required giving the *supervisor* the job of making requests for it,
and the supervisor sits on the trusted side with no such restriction. **The control that closed
the hole re-opened a version of it one layer up, through the deputy it created.** That is a
textbook confused deputy, and it is the clearest possible illustration of the design principle
governing this project: *every control adds attack surface, so the question is never "is it
closed" but "what did closing it cost".*

It also says something about the audit log: a T14 request is logged as an **allowed** request to
a **declared** host. The log is complete and intact and tells you nothing is wrong.

### Treatment applied (ISO 31000 §6.5.2 — *changing the likelihood*)

Probe checks 9 and 10 were written **first**, against the unfixed broker, so the before/after is
a measurement:

```
BEFORE  [ALLOWED] broker: declared host → LAN address   allowed by policy, failed in transit
        [ALLOWED] broker: declared name → loopback      supervisor fetched localhost for us

AFTER   [BLOCKED] broker: declared host → LAN address   192.0.2.10 is private, not a public destination
        [BLOCKED] broker: declared name → loopback      127.0.0.1 is loopback, not a public destination
```

The fix, in `egress.py`:

1. **Resolve in the broker** before connecting (`Egress.resolve`).
2. **Refuse every non-public address** (`forbidden_reason`) — loopback, link-local, multicast,
   unspecified, reserved and private, in that order so the reason names the most specific one.
   Broader than "no LAN" on purpose: link-local covers cloud metadata (169.254.169.254), loopback
   covers whatever the supervisor is listening on. It costs nothing, because a vendor host is on
   the public internet by definition.
3. **Refuse if *any* answer is bad**, not merely the one about to be used. A resolver replying
   `[93.184.216.34, 192.168.1.1]` is not a host reachable two ways; it is an attempt to have the
   check read one answer and the connection use the other.
4. **Connect to the checked address** rather than re-resolving the name — see below.
5. **Per redirect hop**, since `_authorise` is already called once per hop.
6. **The audit trail now records the address, not only the name** — `vendor.example[93.184.216.34]`.
   A T14 request used to be logged as "allowed, to a declared host", which is why a complete and
   intact log said nothing was wrong.

**Step 4 is the only part that is not routine Python, and it is the part worth being able to
explain.** Checking an address and then handing the *name* to `urlopen` means two DNS lookups:
the one that was checked and the one that is used. An attacker who controls the zone answers
differently the second time — a short TTL is enough — so the check passes on a public address and
the connection lands on `192.168.1.1`. That is **DNS rebinding**, and structurally it is a
time-of-check-to-time-of-use bug. The fix is to connect to the exact address already checked:
`http.client` resolves `self.host` inside `connect()`, so overriding `connect()` is the whole
change. `self.host` is left alone, so the `Host:` header and the TLS certificate check still use
the declared name — **pinning changes where the connection goes, never who it claims to be
talking to**, which matters because a pin that broke certificate validation would trade one hole
for a worse one.

### Verification

`test_egress.py` grew from 17 cases to **35**:

- 14 classification cases as a pure function — RFC 1918, loopback, link-local, multicast,
  unspecified, IPv6 ULA, and `::ffff:192.168.1.1` (RFC 1918 wearing an IPv6 hat), plus three
  genuinely public addresses that must still be allowed.
- Four attacker-controlled-DNS cases through a `ScriptedEgress` whose answers are written by the
  test rather than by DNS — because **rebinding is a difference between two resolutions, and that
  cannot be demonstrated against a resolver you do not control.**
- Four pinning cases proving the connection reaches the checked address, that resolution happens
  **exactly once** per hop, that `Host:` still carries the declared name, and that the hop is
  recorded with its address. The pinning proof is self-evidencing: the test's hostname does not
  resolve in real DNS at all, so a 200 is only explicable by the pin having been used.

Full matrix: **15/15 without Docker, 24/24 against real Home Assistant**, stable across repeated
runs. Against real HA the destination check is what stops probe check 10 — `blocked_hosts`
contains `127.0.0.1` as a *string* and never matched `localhost`, which is precisely T15.

### The defect in the check itself

**Probe check 9 reported a false BLOCKED on its first run.** Against the unfixed broker it showed
`BLOCKED — transport failure: timed out`: the request had been authorised and attempted, and
merely never arrived, because 192.0.2.10 is not routed. Every supervisor refusal reaches the
sandbox as the same `PermissionDenied`, whatever caused it.

**A check that cannot tell a control from a timeout would have shown the fix working before the
fix existed.** It now reads the reason string and reports three outcomes — blocked by the
destination check, *not measured* because the allowlist got there first, or allowed-and-failed-in-
transit. Same failure mode as the `gaierror` confound in checks 7 and 8 and the two wrong versions
of check 2: **four of the five defects found in this project have been in measurement code, not
in controls**, which is the more dangerous kind, because a broken measurement reports success.

## 5.2 Treatment options actually used

ISO 31000 §6.5.2 lists seven options. Naming which one each control is makes the register a
decision record rather than a list of features.

| Option (§6.5.2) | Where this project uses it |
|---|---|
| **Avoiding** the risk by not starting the activity | Decision 3: actuators are out of implemented scope, which avoids T21 for now rather than pretending to solve it |
| **Removing the risk source** | Environment scrub — the token is not in the child's environment at all (T05, door 1) |
| **Changing the likelihood** | Namespaces, seccomp, the filesystem allowlist, the egress allowlist — the bulk of the work (T02, T04, T05, T10, T13) |
| **Changing the consequences** | The audit log: it does not prevent anything, it bounds how long an incident goes unexplained (A6) |
| **Sharing the risk** | Open-source review by P5 (T16) — genuinely a form of sharing, and genuinely unreliable |
| **Retaining by informed decision** | T09, T12, T18, T21 — see Part 6 |
| Taking/increasing risk to pursue an opportunity | Not used |

## 5.3 One control, many threats

The strongest structural argument in the model, and worth a figure in the report:

| Control | Threats it treats |
|---|---|
| **Process isolation** (user+PID+mount ns) | T02, T03, T04, T05, T06, T10 — **six** |
| **seccomp filter** | T04, T08, T13, T19 (and adds T20) |
| **Manifest enforcement** | T06, T12*, T13, T16* (*bounds rather than prevents) |
| **Egress broker** | T13, T14, T15 (and T14 was surface the broker itself introduced) |
| **Audit log** | T04*, T18* (*detection and attribution only, never prevention) |

Isolation treats six threats across three STRIDE categories from one mechanism, because all six
trace to the same physical fact: the sandbox used to run as the same uid with an unrestricted
view of `/proc` and the filesystem. **Controls that map many-to-one are the ones worth
building**; controls that map one-to-one are usually patches.

## 5.4 Treatment plan — what to do next, in order

| Priority | Action | Treats | Cost | Why this order |
|---|---|---|---|---|
| ~~1~~ | ~~Resolve-and-pin in the egress broker (§5.1)~~ | ~~T14, T15~~ | — | ✅ **Done 2026-08-14**, the day it was identified |
| 1 | **Verify on aarch64 (Pi 5)** | all of TB5 | ~1 hour | Every isolation result is x86_64-only. If `pivot_root` is wrong on ARM, **nothing above holds on the target hardware** |
| 2 | HMAC the audit chain | T03 | ~1 hour | Cheapest risk reduction available; makes two controls fail independently |
| 3 | cgroups (pids, memory, cpu) | T07 | ~1 day | The only threat with no control at all |
| 4 | Distinct uid for the sandbox | T05, T08 | ~half day | Defence in depth: stops the boundary resting solely on namespace correctness |
| 5 | Manifest signing / review workflow | T16, T17, T18 | Design work | Cannot be finished by this project; can be specified |

**Item 1 is not really a security task and it is now the most schedule-critical thing in this
table.** Every measurement in this document was taken on x86_64 under WSL2. The claim being
made is about a Raspberry Pi.

---

# Part 6: Residual risk statement (ISO 31000 §6.5.3)

Risks formally **retained**, with the reason. In a real 31000 process each of these carries a
signature from the risk owner; here it carries yours.

### R1 — The supervisor holds an unscoped credential (T09)

**Retained because no treatment exists.** Home Assistant issues only long-lived access tokens
with full account privilege; there is no scoping mechanism to use. Compromise of the supervisor
is therefore compromise of every asset. This is an **upstream limitation, not a design flaw
here**, and stating it that way is accurate rather than defensive — but the framework must not
claim to bound the blast radius of its own compromise, because it does not.

### R2 — An allowlist governs destination, not content (T12)

**Retained because it is structural.** An integration legitimately declaring
`api.weatherapi.com` may send anything it likes to that host, including your presence history
encoded in a query string. No destination-based control can distinguish a weather lookup from
an exfiltration to the same endpoint. Content inspection would require understanding every
vendor protocol, and would fail against TLS and against trivial encoding. **The control reduces
the *set* of possible recipients from "the entire internet" to "hosts the author declared in
public" — which is a real and large reduction, and is not confidentiality.**

### R3 — A self-declared contract is self-declared (T16, T18)

**Retained, with the honest framing borrowed from an established precedent.** The manifest does
not stop a determined malicious author from declaring what they need, exactly as an Android
permission list does not. What it changes is that capability becomes **declared, static and
reviewable** instead of **invisible and dynamic**: a weather widget requesting lock access is a
visible anomaly at install time, and today it is not visible at all. The framework closes the
*silent full-trust default*; it does not create trustworthiness. Anyone claiming more than that
is overselling it.

### R4 — A local audit log cannot be authoritative against whoever controls the writer (T03)

**Retained.** The supervisor legitimately holds the key and legitimately writes the file; a
compromised supervisor can write whatever it likes. Only external anchoring changes this, and
full decentralised attestation is explicitly out of scope. Two narrower claims *are* supportable
and should be the ones made: the log is **tamper-evident against after-the-fact edits** (once
keyed), and it is **complete with respect to mediated operations** (once isolation makes
mediation unavoidable). Neither is "tamper-proof", and the report must not use that word.

### R5 — Confinement cannot prevent abuse of a declared capability (T21)

**Retained, and it is the reason Decision 3 went the way it did.** If an integration legitimately
controls a lock, the framework cannot distinguish a scheduled unlock from a 3am one. Preventing
that needs *behavioural* policy — time windows, rate limits, anomaly detection — which is a
different and much larger project. Naming this limit is what makes the actuator stretch goal an
informed choice rather than an oversight.

### R6 — The controls themselves add attack surface (T20, and T14 as precedent)

**Retained as an accepted cost, and stated as a general property rather than an apology.**
Unprivileged user namespaces are a known escalation surface. T14 is the worked example: closing
lateral movement at the socket layer required a broker, and the broker reopened lateral movement
one layer up until it was fixed. T14 is now treated; the *pattern* is not, and will recur with
every future control. Both were accepted because the risk removed is larger than the risk added —
but that is a **judgement**, and the honest form of the claim is "net reduction", never
"elimination".

---

# Part 7: Monitoring and review (ISO 31000 §6.6)

What actually watches this system, and how each control is verified rather than assumed:

| Mechanism | What it monitors | Cadence | Limitation |
|---|---|---|---|
| **Adversarial probe** (`probe.py`, 10 checks) | Whether each boundary still holds | Every run | Tests the *mediated* path, 4 escape routes and 2 broker abuses; it is not exhaustive |
| **Test matrix** (`test_matrix.sh`, 15 / 24 assertions) | Regression across 3 integrations × 4 modes | Before any claim | Stub-house scenarios unless `HA=1`; **x86_64 only** |
| **`test_egress.py`** (35 cases) | Egress policy and destination checking | Every run | The first 17 **did not catch T14** — see below |
| **`test_audit.py`** (5 cases) | Chain integrity *and* its asserted limits | Every run | 3 of 5 encode limits, not requirements |
| **The audit log itself** | What each integration attempted | Continuous | Nobody reads it (§1.3) |

**Trigger conditions for re-assessing this model:**

1. Any new capability crosses TB1 (actuators, WebSockets, storage) — new threats by construction.
2. Any change to `egress.py`, `isolate.py` or `syscall_filter.py`.
3. Migration to different hardware or a different kernel — **including the pending move to
   aarch64**.
4. A new Python or kernel CVE affecting namespaces, seccomp or `urllib`.
5. Any change in what HACS does about review or signing.

**The most important lesson from monitoring so far, and it belongs in the report.** Of the four
defects found by widening the test matrix, **three were in the measurement code, not in the
controls** — a hardcoded entity prefix, a discarded `--isolate` flag, and an audit `run_id`
collision that produced a *false* tamper report. A broken control fails visibly; a broken
measurement reports success — and probe check 9 made it four out of five, reporting a false
BLOCKED on its first run because a timeout is indistinguishable from a refusal unless you read
the reason (§5.1).

T14 extends the lesson in the other direction: `test_egress.py` had 17 cases covering both
directions of every rule it knew about, and it did not find T14, because **a test suite can only
test the threats someone already thought of. Tests demonstrate the absence of known failures,
never the absence of failures.** That is exactly why threat modelling is a separate activity from
testing, and this project can now say so from its own evidence: the model found a real gap in
code that had passed a targeted suite, and the suite grew from 17 cases to 35 as a result.

---

# Part 8: Recording and reporting (ISO 31000 §6.7)

| Artifact | Contains |
|---|---|
| `THREAT_MODEL.md` (this) | Context, criteria, register, treatment plan, residual risks |
| `PROJECT_STATUS.md` | Rolling decision record, measurements, open decisions |
| `FINDINGS_2026-08-14_token_leak.md` | Detailed walk-through of T05 and T03, teaching-first |
| `ANALYSIS_2026-08-14_isolation_coverage.md` | Predicted coverage of isolation, written *before* it was built |
| `RESULTS_2026-08-14_isolation_spike.md` | Measured 6/8 snapshot (superseded) |
| `RESULTS_2026-08-14_egress_broker.md` | Measured 8/8 snapshot — and the surface the broker added, which §5.1 then found and closed |
| `spike/audit/*.jsonl` | Per-run hash-chained decision log |

**For the user, the residual-risk statement must be one paragraph, not this document.** Suggested
wording:

> This framework stops an integration reading your other devices' data, stealing your Home
> Assistant credential, or contacting anything on your home network. It does **not** stop an
> integration sending data to the vendor it openly declares, and it does not verify that the
> integration's declaration is honest — it only makes that declaration visible so you, or
> anyone else, can question it.

---

# Part 9: Limits of this threat model

Stating these is part of the method, not a hedge — an auditor will test whether you know where
your own analysis stops.

1. **Single-analyst, no adversarial review.** One person's imagination bounds the threat list.
   T14 was found on the day of writing — evidence that the list is not closed, and no reason to
   believe the next pass would find nothing.
2. **STRIDE finds design threats, not implementation bugs.** A buffer overflow in a Python C
   extension appears nowhere here. Complementary techniques — fuzzing, dependency scanning — are
   not part of this project.
3. **Likelihood values are judgements, not data.** No incident dataset for malicious HACS
   integrations exists to calibrate against. The scale is defensible; the individual numbers are
   arguable, and they should be argued with.
4. **The register is a point-in-time snapshot.** It describes 2026-08-14 on x86_64.
5. **Some entries are unverified on the target hardware.** Everything about TB5 is x86_64-only
   until item 3 of the treatment plan is done.
6. **The economics are asserted, not modelled.** The design goal is to make attack unprofitable
   rather than impossible; nothing here actually quantifies attacker cost. Naming that is more
   honest than pretending the risk matrix does it.

---

# Part 10: Questions to be ready for

Worth being able to answer these cold.

1. *Why ISO 31000 rather than 27005 or NIST 800-30?* — 31000 is the generic process and does not
   presuppose an organisational ISMS, which a household does not have. 27005 assumes 27001's
   context. NIST 800-30 is a reasonable alternative and the difference would be presentational.
2. *STRIDE per element or per interaction?* — Per boundary here, because the architecture's
   security content is entirely in what crosses each line. Per-element would generate more rows
   and less insight.
3. *Your residual list has eight High risks. Is the framework worth building?* — Yes, and the
   inherent column is the answer: **7 Critical and 7 High became 0 Critical and 8 High**, and
   four of the eight survivors are structural or upstream rather than unfixed work. The
   comparison that matters is against the status quo, not against perfection.
4. *Who accepts these risks?* — The householder, who is also the least qualified party to judge
   them (§1.3). That tension is real and the model does not resolve it; it is the strongest
   argument for making capability declared rather than inferred.
5. *You found T14 yourself. Doesn't that undermine the results?* — It confirms them, in the sense
   that matters: the method found a real, measured, previously unknown gap in code that had
   already passed 17 targeted tests, and it was closed the same day with the fix measured by two
   new probe checks written *before* it. A threat model that finds nothing is not reassuring, it
   is unfinished.
