# Confining Unmodified Third-Party Integrations in Home Assistant

### A Declared-Authority Architecture and Its Measured Cost

**Younes Rahati**

| | |
|---|---|
| Degree and programme | *[to be supplied — handbook]* |
| Institution | *[to be supplied]* |
| Supervisor | *[to be supplied]* |
| Submitted | *[to be supplied]* |

---

## Abstract

Home Assistant is the largest open-source home-automation platform, reporting **669,743 active
installations** [1], and its capability comes from integrations — modules that connect it to a
device or a cloud service. Community-written integrations are installed by more than half of
those installations, and every one of them runs **inside Home Assistant's own process with Home
Assistant's own authority**. There is no permission model, no scoping rule and no caller check
[2]. An integration installed to display electricity prices may read every stored credential,
call `lock.unlock`, reach any host on the home network, and — as Corno and Mannella demonstrate
[9] — walk the Python garbage collector into another integration's live objects and read its
secrets. The 2021 disclosures show this is not hypothetical for this ecosystem [4][6].

This project **designs, builds and evaluates confinement for these integrations without
modifying them**, on the ground that the declaration such a scheme needs already exists in every
integration's manifest and is currently spent on a log line and a discovery heuristic.
Enforcement is placed outside the integration's process, because the garbage-collector result
eliminates every in-process design; the integration runs unmodified inside Linux namespaces,
seccomp-BPF and cgroup v2, against a real stripped Home Assistant, and reaches the platform and
the network only through a mediator that holds the credential it never sees.

**The cost of confinement, measured against an unconfined baseline on the same host and release,
is zero at the import level.** Across 77 community integrations on two corpora sharing 5% of
their members — 37 by install count and 40 drawn uniformly — the confined and unconfined arms
fail on the *same* integrations for the *same* reasons: 84% and 92% clean in both arms, so the
failures attributable to the design number none, twice. Five integrations were executed end to
end; one, `nordpool`, published the same electricity price confined as unconfined, in the same
minute, through a mediated connection logged to a named host and port. On a Raspberry Pi 5,
mediation costs 31.5 µs, the audit record is made durable before the action it records at 3.67 ms,
and the mediator is 63× clear of realistic demand. Nineteen self-test suites pass.

**The most useful result was a failure, and it arrived last.** Running one real community
integration confined against its own real API found that the platform's own HTTP helper could
not be constructed inside the sandbox at all, so the egress design had been unusable for the 41%
of the corpus it exists to serve — behind eighteen suites that all passed, because every earlier
test subject had been written by the author of the sandbox. Six of eight predictions registered
before measurement were wrong and none was revised.

**Keywords:** Home Assistant; smart-home gateway; extension security; permission manifest;
sandboxing; Linux namespaces; seccomp; cgroup v2; least privilege; threat modelling; STRIDE;
ISO 31000; empirical evaluation.

---

## Acknowledgements

*[To be supplied.]*

## Declaration

*[Wording to be supplied from the programme handbook.]* The factual content it will need:

- The design, implementation, measurements and text of this report are the author's own work.
  Sources are cited at every use and consolidated in the References.
- **A prior two-week feasibility spike by the same author exists** and is not part of this
  submission. Everything learned in that spike was treated as private knowledge and was not
  citable until re-derived in this pass; where it is mentioned it is labelled as prior work with
  its date and explicitly not relied on.
- **Generative AI was used as a working tool throughout**, for drafting prose, writing code and
  reviewing arguments. Every measurement reported here was executed by the author on the hardware
  named in §3.5, and every figure is reproducible from the scripts and result files in the
  repository.

## Contents

## List of Figures

*[Generated at typeset time — see the figure register in §9 and §12.]*

## List of Tables

*[Generated at typeset time.]*

## Abbreviations

| | |
|---|---|
| **HA** | Home Assistant. Version pinned throughout: **2026.8.3** |
| **HACS** | Home Assistant Community Store — the distribution channel for third-party integrations |
| **Integration** | Third-party Python code loaded into Home Assistant's process. The subject of this report. Distinct from an **add-on**, which is a separate container and already isolated |
| **Mediator** | The out-of-process component holding the platform credential and deciding every request a confined integration makes |
| **Manifest** | An integration's declaration. `manifest.json` already exists; this work adds a permissions clause and makes it load-bearing |
| **Sandbox** | One confined integration: its own user, mount, PID, network and IPC namespaces, a seccomp filter and a cgroup |
| **F*n* / S*n* / C*n* / N*n*** | Functional, security, constraint and non-functional requirements (§3) |
| **T*nn* / R*n*** | Threats and residual risks in the register (§8) |
| **P*n*** | Predictions registered *before* the corresponding measurement (eight; six were wrong) |
| **PSS** | Proportional set size — the memory accounting used for per-sandbox cost |
| **netns** | Linux network namespace |
