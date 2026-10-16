# Confining Unmodified Community Integrations in Home Assistant

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

Home Assistant, an open-source home-automation platform with 669,743 reporting installations, loads community-written integrations into its own process with its full authority, so an integration installed to display electricity prices can read stored credentials, operate door locks and reach any device on the home network. This project designs, builds and evaluates a framework that confines such integrations without changing their code or the platform. Each integration runs in its own Linux sandbox, built from namespaces, a system-call filter and control groups, against a minimal copy of the platform, and it reaches the household's installation and the network only through a separate mediator that holds the credential the integration never sees. What an integration may do is declared in a permissions block of its manifest, approved by a person in the platform's interface, enforced while it runs and recorded in a tamper-evident log. Every result was measured against the same integration unconfined, on a Raspberry Pi 5. The published attacks on the platform succeed unconfined and find nothing confined. Across 75 community integrations, confinement caused no failure to load that did not also occur without it, thirteen integrations ran confined end to end, the mediator runs about sixty times clear of realistic demand, and the device holds at least 17 sandboxes against a mean of 4.02 integrations per installation. The results are bounded by attacks written within the project, manifests written by hand and a single platform release.

**Keywords:** Home Assistant; Internet of Things; smart home; smart-home gateways; extension sandboxing; least privilege; cybersecurity.

---

## Acknowledgements

*[To be supplied.]*

## Declaration

*[Wording to be supplied from the programme handbook.]* The factual content it will need:

- The design, implementation, measurements and text of this report are the author's own work. Sources are cited at every use and listed in the References.
- An earlier two-week feasibility study by the same author preceded this project. Nothing learned in it is relied on here unless it was established again within this project.
- Generative AI was used as a working tool throughout, for writing code, drafting prose and reviewing arguments. Every measurement reported here was run on the reference device, and every figure can be reproduced from the scripts and result files in the repository (Appendix A).

## Contents

*[Generated at typeset time.]*

## List of Figures

*[Generated at typeset time.]*

## List of Tables

*[Generated at typeset time.]*

## Abbreviations and identifiers

| | |
|---|---|
| **Arm** | One of two paired runs of the same integration, on the same device and platform release: confined (in the framework) or unconfined (as Home Assistant runs it today) |
| **Community Store** | The Home Assistant Community Store (HACS), the usual channel for installing community integrations |
| **Integration** | A Python module that connects Home Assistant to a device or service and runs inside its process. Distinct from an add-on, which runs in its own container |
| **Manifest** | The `manifest.json` file every integration ships. This framework adds a `permissions` block to it, which states what the integration may do |
| **Mediator** | The separate process that holds the platform credential and decides every request a confined integration makes |
| **Sandbox** | The confined environment of one integration: its own Linux namespaces, a system-call filter and a control group |
| **Release** | Home Assistant 2026.8.3, the platform version used throughout |
| **F1–F4, S1–S9, C1–C4, N1–N3** | Functional, security, constraint and non-functional requirements (Section 3, Appendix B) |
| **T01–T19, R1–R7** | Threats and residual risks of the threat model (Section 8, Appendix C) |
| **F01–F63** | Findings of the verification campaign, written with two digits to distinguish them from requirements (Appendix F) |
| **M01–M50** | Deliberate defects (mutants) used to test whether the test suites detect a removed check (Section 8.6) |
