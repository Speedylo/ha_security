# 1. Introduction

Home Assistant is an open-source home-automation platform that households run on their own hardware, where it controls the physical devices of a home: lights, thermostats, cameras, alarm panels, door locks, and so on. Its opt-in analytics reported 669,743 active installations on 21 August 2026 [1].

The platform's reach comes from integrations, the modules that connect it to a particular device or online service. Beyond the 1,482 integrations shipped with the platform, users install integrations written by the community, commonly through the Home Assistant Community Store. An integration is not a separate program that the platform supervises. It is a Python module that Home Assistant imports into its own running process and hands the platform's core object, through which the integration reads and changes the state of the whole system [2]. Two consequences follow. No boundary separates the integration from the platform, since both run in the same process with the same privileges, memory and network access. And nothing in the interface records what an integration needs, so one that reports pollen counts and one that operates a door lock receive the same object and the same authority.

This design is reasonable for code that the platform's maintainers review. The problem arises because the same mechanism carries code that no one reviews, and Table 1.1 shows how widely it does.

**Table 1.1 — Scale of the community-integration ecosystem** (computed from Home Assistant's published per-integration analytics, retrieved 21 August 2026 [1])

| Measure | Value |
|---|---|
| Active installations reporting analytics | 669,743 |
| Installations running the Community Store | 379,326 (56.6%) |
| Distinct community integrations reporting | 4,220 |
| Total community-integration installations | 1,904,297 |
| Mean community integrations per Community Store installation | 4.02 |
| Median installations per community integration | 20 |
| Community integrations with at least 1,000 installations | 257 |
| Community integrations with fewer than 100 installations | 3,095 |

Three observations follow from the table. Community code is the normal configuration rather than an exception, since more than half of reporting installations run the store. The distribution has a long tail: 3,095 of the 4,220 integrations have fewer than 100 installations, and small projects of this kind are the least likely to attract independent review. Its head concentrates risk instead, because 27 integrations exceed 10,000 installations each, so one hostile release among them would reach thousands of homes through an update channel their owners already trust. Because participation in the analytics is optional, every figure is a lower bound, which strengthens the claim that the exposure is widespread.

This project builds and evaluates a framework that confines each community integration without changing its code or the platform. Each integration runs in its own Linux sandbox, against a minimal copy of the platform, and every effect it has on the household's real installation passes through a separate process, the mediator, which holds the credential that the integration never sees. What an integration may do is declared in a `permissions` block of the manifest it already ships, approved by a person in the platform's own interface, enforced while it runs, and recorded in a tamper-evident log. The integrations' code is unmodified, but confinement additionally requires such a manifest for each integration. In the evaluation every manifest was written by hand, so the cost of producing manifests at scale, whether by authors, by analysis or by curation, remains unmeasured.

The evaluation measures whether the confinement holds against the published attacks on the platform and what it costs, comparing each integration confined with the same integration unconfined on the same device. The published attacks succeed unconfined and find nothing confined. Across 75 real community integrations, confinement caused no failure to load that did not also occur without it, thirteen integrations ran confined end to end through their own setup, and a Raspberry Pi 5 holds at least 17 sandboxes, even when each loads every platform component, against a mean of 4.02 community integrations per installation that runs the store [1]. The results describe one platform release, 2026.8.3, and one device.

The report is organised as follows. Section 2 states the problem, and Section 3 specifies the project. Sections 4 to 6 examine its wider context, the engineering standards it follows and its logic model, and Section 7 reviews the literature and locates the gap. Section 8 gives the method and the threat model, Section 9 the architecture, and Section 10 its feasibility. Sections 11 and 12 present the data and the results, Section 13 reflects on what the work taught, and Sections 14 and 15 set out future work and conclude.
