# 10. Feasibility Study

Feasibility was not assumed. Each dimension below was settled before the work that depended on it,
and two of the technical answers changed the design.

## 10.1 Technical feasibility

Three questions had to be answered before the architecture could be committed to, and each was
answered by measurement on the target device rather than from documentation.

**Does the host support the primitives?** Probed directly on the Raspberry Pi 5 (Pi OS trixie,
kernel 6.12.47): unprivileged user, network and PID namespaces are available and were created as
an ordinary user; all seven namespace types are present; seccomp-BPF is present including
`user_notif`; cgroup v2 offers `pids`, `cpu`, `io` and `cpuset`. **Two findings changed the
design.** The `memory` controller is **absent** on a stock installation and must be enabled at
boot — a genuine deployment constraint, not a detail. And the `io` controller is present but **not
delegated** to a user manager, which is why I/O bandwidth is a retained residual risk rather than
an unimplemented feature.

**Can a stripped Home Assistant be built at all?** Home Assistant's own entry point cannot be
used: `bootstrap.py` imports `.components` at module level, pulling in the frontend and the
recorder — precisely the weight a sandbox exists to avoid. The sandbox therefore **constructs** a
`HomeAssistant` object directly and wires the registries the helper layer reaches for. *Measured:*
an ordinary integration — a config entry, a `DataUpdateCoordinator`, a `SensorEntity`,
`async_add_entities` — reaches `LOADED` and publishes its entity against such an instance, with no
HTTP server, no recorder, no frontend and no authentication.

**Does it fit?** This is the question C4 turns on, and the arithmetic is the argument.

| | RSS, one sandbox | **PSS per sandbox, six live** | Sandboxes in 60% of 4 GB |
|---|---|---|---|
| With the platform's base component | 161.3 MB | **136.6 MB** | **17** |
| Without it | 109.4 MB | **90.0 MB** | **26** |
| Difference | 51.9 MB | **46.6 MB** | **+9 — a factor of 1.53** |

**The method is not a subtraction, and that is the whole of it.** The obvious experiment builds one
sandbox each way and subtracts two resident-memory figures. That is wrong, because most of a
sandbox is interpreter and library pages the kernel maps into every sandbox from the same physical
memory: a megabyte removed from one process's resident set is a megabyte removed from the *budget*
only if it was private to that process. The saving was therefore measured across six live sandboxes
per arm by **proportional set size**.

**Verdict: technically feasible, and the budget is 26 sandboxes against a measured mean of 4.02
community integrations per HACS-running installation** — a margin of about 6×.

## 10.2 Economic feasibility

The framework uses only the Python standard library and `ctypes`. There is no licence cost, no
service cost, and no additional hardware: it runs on the device the user already owns. The
marginal cost of confining one integration is about **120 MB of memory** and **31.5 µs per
mediated request**.

The dependency decision is deliberate and worth stating as an economic one. **A confinement tool
that pulls a dependency tree has enlarged the attack surface it exists to reduce**, and it has
also acquired a maintenance liability that a volunteer ecosystem cannot carry.

The costs that are real are not resource costs. They are **integration effort** — the framework is
a research artifact, not a packaged product — and **maintenance against a moving platform**, which
§12.6 shows is not hypothetical.

## 10.3 Legal and ethical feasibility

No personal data was collected. Every measurement ran on the author's own hardware against the
author's own test installation. The one measurement touching a live third-party service used an
ordinary unauthenticated public endpoint at ordinary polling rates.

**The adversarial work is the part that needed a position, and §4.7 states it:** the adversary is
purpose-built to reproduce the *pattern* of the 2021 disclosures rather than to exploit the eight
named integrations at their vulnerable versions. Those versions are not in the corpus, and the
report states this as a limitation of the evaluation rather than as a design choice with no cost —
it means the adversary exercises the class of attack and not the historical instances.

The four third-party papers obtained for this work are stored privately and are not redistributed.

## 10.4 Operational feasibility

**The supervisor does not need to be privileged**, which is what makes the design deployable by a
user rather than by a distribution. Unprivileged user namespaces are available on the target, and
the whole framework runs as an ordinary user.

Two operational constraints are real and are stated rather than smoothed over. The `memory`
controller must be enabled at boot, which is a one-line change to the kernel command line and a
reboot. And **where the supervisor runs turns out to matter more than when it acts**: a measurement
of four cgroup placement mechanisms found that `clone3(CLONE_INTO_CGROUP)` fails with the same
`EACCES` as migration, so what binds the sandbox is the supervisor's own position in the cgroup
hierarchy. That corrected an assumption made in the design chapter, and it is a deployment
requirement rather than an implementation detail.

## 10.5 Scheduling feasibility

The work was staged with gates, and the gates were used rather than passed through: **two of the
four architectural decisions diverged** from the first pass when re-examined against evidence, and
one profile decision was reversed by a measurement that contradicted its own prediction.

The schedule risk that remains is stated in §14: the largest missing piece — the push loop — is
*building* rather than *testing*, and the largest evaluation gap — running many integrations end to
end — is blocked on something no schedule can fix, namely that **26 of 37 corpus integrations
require a credential before their own configuration flow can complete.**

## 10.6 Market need and integration with existing systems

**Need** is established by measurement rather than asserted: 379,326 installations run HACS, a mean
of 4.02 community integrations each, and the platform states plainly that such code is outside its
security programme and installed "at your own risk" [4][10].

**Integration with existing systems** is the design's central constraint and its main claim. The
framework requires **no change to any integration** and **no change to Home Assistant**. It is
additive to the ecosystem's existing control — informal community review — because the two act on
different variables: review acts on likelihood, confinement on impact.

It is also **complementary to the platform's own direction of travel.** A 2026 request for comment
proposes running integrations on separate machines [11], motivated principally by reliability and
scale. Relocation without scoping changes *where* untrusted code runs without changing *what it may
do* — an integration that must still read and write platform state across a process boundary needs
a credential, and unless that credential is scoped by something, nothing is bounded. **If that
proposal is adopted it becomes a natural substrate for the enforcement described here rather than
a substitute for it.**
