# Option A: Sandboxed Community Console — Raspberry Pi 5, gVisor, and eBPF

## 1. Project Overview

This variant builds an open, Linux-based handheld device (Raspberry Pi 5, 4GB) that lets community members submit and run original homebrew games and scripts safely. Two independent security layers protect the device and other users' data:

- **gVisor**, which intercepts every syscall made by an untrusted game process through a userspace kernel implementation (the "Sentry"), preventing it from talking to the real host kernel directly.
- **eBPF programs**, running inside the real host kernel, independently watching the sandboxed process's behavior via kernel tracepoints. If a process attempts something outside its allowed behavior (filesystem access outside its directory, unexpected network activity, excessive process spawning), a userspace policy agent kills it and logs the violation.

The result is a "defense in depth" architecture: gVisor is prevention, eBPF is detection-and-response for cases where the first layer's guarantees are tested or bypassed.

## 2. Where the Gap Is

Isolating and running untrusted code safely is a mature, well-studied engineering problem, but the existing work clusters almost entirely around cloud and server-scale contexts, not personal or hobbyist hardware:

- **Online judge / code execution platforms** are the closest existing precedent for "run community-submitted untrusted code safely." Judge0 is the most prominent open-source example, used for competitive programming, e-learning, and increasingly AI-agent code execution, and relies on OS-level sandbox isolation. A published comparison paper analyzing Judge0's design explicitly identifies a limitation: it does not include built-in security features for monitoring the code-execution containers or ensuring the code being executed does not pose a threat to the underlying system, leaving that responsibility to whoever deploys it (*A Secure and Scalable System for Online Code Execution*, OpenReview). This is a directly citable, documented gap this project addresses by adding a dedicated eBPF monitoring layer.
- **eBPF-based runtime security monitoring** (Falco, Cilium's Tetragon) is an established, production-grade pattern for watching container behavior at the kernel level. Recent commercial tooling (e.g. ARMO) has begun applying this specifically to AI-agent workloads, confirming the sandbox-plus-eBPF combination is validated and current.
- **Cloud sandboxes built for AI-agent code execution** (E2B, Modal, Northflank) apply gVisor/microVM-style isolation at large scale — E2B alone grew from roughly 40,000 sandbox sessions per month in March 2024 to about 15 million per month by March 2025 — but exclusively as hosted cloud infrastructure for organizations, never as personal, offline-capable physical hardware.
- **Console/embedded homebrew security research** addresses the opposite problem: defeating a manufacturer's existing protections to run unauthorized code (documented, for example, in published work on defeating the Nintendo Switch's security chain), rather than designing an open platform where safe execution of untrusted code is a supported, built-in feature from the start.

**Stated gap:** no existing work applies the sandbox-plus-eBPF pattern to a personal, offline-capable, community-oriented physical device, where the goal is giving a hobbyist community a tangible, safe way to share and run each other's original homebrew code — rather than maximizing throughput for a business.

## 3. Architecture

```
Host machine (Raspberry Pi 5)
├── gVisor sandbox (per game process)
│   └── Untrusted game process — syscalls intercepted here
├── Host kernel
│   └── eBPF programs — watch sandboxed process via tracepoints
└── Policy agent (userspace)
    ├── Receives eBPF events
    ├── Decides allow / log / kill
    └── Sends kill signal back into the sandbox on violation
```

## 4. Day-to-Day Work, by Phase

**Phase 1 — Hardware bring-up (weeks 1-3)**
Wire up a small SPI display, GPIO button matrix, I2S audio DAC/amp, and battery/power-management HAT to the Pi 5. Get each peripheral individually working and tested before adding software complexity. Day-to-day work: wiring, datasheet reading, debounce logic for buttons, debugging display driver configuration.

**Phase 2 — Sandbox core (weeks 4-6)**
Install and configure gVisor (`runsc`) on the device. Write a minimal orchestrator (Python or Go) that takes a submitted game, launches it inside a gVisor sandbox, captures its output, and tears the sandbox down afterward. Day-to-day work: reading gVisor configuration docs, debugging silent failures, writing simple test scripts (both benign and deliberately bad) to confirm isolation behavior.

**Phase 3 — eBPF guard (weeks 7-9)**
Start with `bpftrace` to observe a sandboxed process's syscalls informally, then write dedicated eBPF programs attached to specific tracepoints (file access, network calls, process spawning). Wire these into the orchestrator so a detected violation triggers an immediate kill and log entry. This is the highest-risk, most unpredictable phase — expect slow debugging cycles and real trial and error. Day-to-day work: eBPF program development, kernel tracepoint research, adversarial self-testing.

**Phase 4 — Integration, games, and polish (weeks 10-12)**
Build a simple on-device menu/launcher UI. Add a small set of original demo games plus deliberately malicious test cases for the live defense demo. Write up the architecture, threat model, and what was and wasn't fully solved. Day-to-day work: UI development, demo scripting, documentation.

## 5. Feasibility Assessment

| Factor | Assessment |
|---|---|
| Hardware bring-up | Low risk — well-documented, off-the-shelf breakout modules for the Pi 5 |
| gVisor integration | Moderate risk — mostly configuration and documentation-reading |
| eBPF guard | **Highest risk** — genuinely uncommon territory without prior Rust/Linux-internals background; debugging is often slow and silent-failure-prone |
| Hardware resource budget | Low risk — Pi 5 (4GB) comfortably handles gVisor overhead plus 2D game workloads |
| Overall 12-week fit | Feasible, but tight — success depends heavily on July/August prep time spent specifically on gVisor and `bpftrace`/eBPF fundamentals before the semester starts |

**Fallback plan:** if eBPF proves too difficult to complete within budget, drop to `seccomp-bpf` plus Linux namespaces for the monitoring/restriction layer — less flashy, but well-documented and a legitimate, statable risk-mitigation plan for the proposal.

## 6. Honest Limitations

- Individual components (gVisor, eBPF, sandboxed code execution) are established, not novel in themselves. The contribution is the specific combination and physical/community form factor.
- The "embedded" claim is comparatively weaker here — the Pi 5 running Linux is, at the OS layer, a small general-purpose computer, not truly bare-metal firmware work.
- Security guarantees are bounded to the specific behaviors the eBPF policy is designed to catch (filesystem escape, unexpected network activity, resource abuse), not a claim of protection against all possible sandbox-escape techniques or kernel vulnerabilities.

## 7. Sources Consulted

- gVisor project documentation
- Falco and Cilium Tetragon documentation (eBPF-based runtime security monitoring)
- ARMO eBPF-based agent monitoring for AI workloads
- Judge0 project documentation and *A Secure and Scalable System for Online Code Execution* (OpenReview)
- *A Comparison of Sandbox Technologies Used in Online Judge Systems*
- *Online Judge System: Requirements, Architecture, and Experiences*
- E2B, Modal, and Northflank documentation on ephemeral AI-agent code execution sandboxes
- Published research on defeating Nintendo Switch console security (opposite-direction precedent)
