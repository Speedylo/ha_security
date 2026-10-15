# Your check of the literature screening

For each record: read the title (open the link if you need the abstract), then fill in the **Agree** line
with `yes` or `no`. If `no`, write one line after **Why** saying what it should be.

**The question:** does this work build or evaluate a way to restrict what third-party code (plug-ins,
integrations, apps) can do on a smart-home hub, or measure what such code uses or what confining it costs?
If yes, it should be at least **B** (relevant). If it is about devices, networks, users or something else,
excluding it is right.

Save the file when done and tell me.

---

## Part 1 — the 5 records I kept as relevant (B)

### 1. Security and robustness analysis of encrypted communications for local home automation: ESPHome Native API and MQTT over TLS 1.3

- Year: 2026 · Record R0003 · [link](https://doi.org/10.5121/ijnsa.2026.18502)
- My decision: **kept as relevant (B)**
- My reason: Home Assistant work at the network layer: ESPHome Native API vs MQTT over TLS 1.3. Does not concern integration code; does not change §7.

**Agree:** No

**Why (only if no):** drop (Younes: only P3CRID kept)

### 2. SHERLOC: a privacy-preserving smart home system with secure message routing and privilege control

- Year: 2026 · Record R0057 · [link](https://doi.org/10.1186/s42400-026-00621-3)
- My decision: **kept as relevant (B)**
- My reason: SHERLOC (2026): cryptographic enforcement of app permissions on a pub/sub smart-home platform; a new system that apps are written for, not confinement of existing extensions; not Home Assistant.

**Agree:** no

**Why (only if no):** drop (Younes: only P3CRID kept)

### 3. P3CRID: A Threat Model Methodology for Smart Homes

- Year: 2026 · Record R0226 · [link](https://doi.org/10.3390/a19050347)
- My decision: **kept as relevant (B)**
- My reason: P3CRID threat model (2026): names Home Assistant integrations as an attack vector; its only mitigation for integration code from GitHub is the owner reviewing it. No run-time confinement proposed. Supports the gap.

**Agree:** yes

**Why (only if no):** 

### 4. TAPShield: Securing Trigger-Action Platforms against Strong Attackers

- Year: 2025 · Record R0497 · [link](https://doi.org/10.1109/eurosp63326.2025.00013)
- My decision: **kept as relevant (B)**
- My reason: TAPShield (Euro S&P 2025): SGX + language-level sandboxes (vm2, SandTrap) for apps on Node-RED and IFTTT; abstract reports security, performance and compatibility trade-offs on real-world apps. Not Home Assistant. Full text not obtained (IEEE paywall; Younes's institution has no access; no repository copy at KTH DiVA, Lund, ResearchGate, 2026-10-15). Judged on the abstract (Younes, 2026-10-15): §7's claim is narrowed so that it holds whatever its compatibility evaluation measured.

**Agree:** no

**Why (only if no):** drop (Younes: only P3CRID kept)

### 5. A comprehensive examination of cybersecurity in communication protocols utilized by home automation technologies: an in-depth exploration of potential …

- Year: 2026 · Record R0639 · [link](http://repositorio.ipvc.pt/jspui/handle/20.500.11960/4839)
- My decision: **kept as relevant (B)**
- My reason: Thesis (2026) on the security of home-automation communication protocols, using Home Assistant's Bluetooth proxy; network layer, does not change §7.

**Agree:** no

**Why (only if no):** drop (Younes: only P3CRID kept)

---

## Part 2 — 20 records I excluded, picked at random

### 6. From Visualization to Purchase: How Augmented Reality (AR), Virtual Reality (VR) and Artificial Intelligence (AI) Influence Consumer Purchase Decisions in Housing Design Decisions

- Year: 2025 · Record R0219 · [link](https://doi.org/10.38124/ijisrt/25apr1332)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 7. Using AI Tools to Enhance Educational Robotics to Bridge the Gender Gap in STEM

- Year: 2025 · Record R0206 · [link](https://doi.org/10.3390/educsci15060711)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 8. From Basket to Closet: A Task-Centric Survey of Robotic Laundry

- Year: 2026 · Record R0454 · [link](https://doi.org/10.36227/techrxiv.176823103.36643182/v1)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 9. Integration of innovative technologies in geriatric care: balancing efficiency and human dignity

- Year: 2025 · Record R0496 · [link](https://doi.org/10.4103/agingadv.agingadv-d-25-00008)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 10. Ep. 1073: Beyond YAML: Building the Agentic Smart Home

- Year: 2026 · Record R0012 · [link](https://doi.org/10.5281/zenodo.19362325)
- My decision: **excluded after reading the abstract**
- My reason: AI-generated podcast episode on LLM agents in Home Assistant; not scholarly.

**Agree:** yes

**Why (only if no):** 

### 11. DefenDoor: An electromagnetic fingerprint-based access control system with forced-entry detection and SMS notification

- Year: 2026 · Record R0043 · [link](https://doi.org/10.63498/injeni3)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 12. Exploring Multi-User Access Control Design in IoT-assisted In-Home Dementia Care

- Year: 2025 · Record R0032 · [link](https://doi.org/10.1145/3733801.3764205)
- My decision: **excluded after reading the abstract**
- My reason: Survey of multi-user access control preferences in dementia care; users, not third-party code.

**Agree:** yes

**Why (only if no):** 

### 13. JAEGER: Joint 3D Audio-Visual Grounding and Reasoning in Simulated Physical Environments

- Year: 2026 · Record R0201 · [link](https://doi.org/10.48550/arxiv.2602.18527)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 14. EMI Optimization of a Wi-Fi-Enabled Relay Module for Smart Home Application Using ESP8266/N76E003

- Year: 2025 · Record R0542 · [link](https://doi.org/10.38124/ijisrt/25sep483)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 15. Italian Report on Care Workers’ Job Quality and Inclusive Working Conditions

- Year: 2025 · Record R0436 · [link](https://doi.org/10.36253/979-12-215-0864-2.06)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 16. MemCompiler: Compile, Don't Inject -- State-Conditioned Memory for Embodied Agents

- Year: 2026 · Record R0409 · [link](https://doi.org/10.48550/arxiv.2605.07594)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 17. PVDF Nanocomposites for Advanced Functional Applications

- Year: 2026 · Record R0591 · [link](https://doi.org/10.1007/978-981-95-6718-8_9)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 18. Context-Contingent Privacy Concerns and Exploration of the Privacy Paradox in the Age of AI, Augmented Reality, Big Data, and the Internet of Things: Systematic Review

- Year: 2025 · Record R0406 · [link](https://doi.org/10.2196/71951)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 19. Development of a hybrid inverter monitoring device

- Year: 2026 · Record R0242 · [link](https://openalex.org/W7204502408)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 20. Podcasts Across Rooms Without Home Assistant

- Year: 2026 · Record R0514 · [link](https://doi.org/10.5281/zenodo.19577462)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 21. A comprehensive survey on securing the social internet of things: protocols, threat mitigation, technological integrations, tools, and performance metrics

- Year: 2025 · Record R0062 · [link](https://doi.org/10.1038/s41598-025-23865-4)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 22. A Harmonised Dashboard for Smart Home Device Security

- Year: 2026 · Record R0243 · [link](https://doi.org/10.34190/eccws.25.1.4637)
- My decision: **excluded after reading the abstract**
- My reason: User dashboard for device security settings across vendors.

**Agree:** yes

**Why (only if no):** 

### 23. Integrated Communication Protocols and Platform Architectures for the Internet of Things and Industrial Control Systems: A Comprehensive Theoretical and Applied Analysis

- Year: 2025 · Record R0570 · [link](https://openalex.org/W7215252790)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 24. Improving Energy Efficiency in Buildings with an IoT-Based Smart Monitoring System

- Year: 2025 · Record R0187 · [link](https://doi.org/10.3390/en18051269)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 

### 25. Integrating Sensor Technologies with Conversational AI: Enhancing Context-Sensitive Interaction Through Real-Time Data Fusion

- Year: 2025 · Record R0065 · [link](https://doi.org/10.3390/s25010249)
- My decision: **excluded on the title**
- My reason: Title shows it is not about third-party code on a smart-home hub.

**Agree:** yes

**Why (only if no):** 
