# 1 Introduction

Home Assistant is an open-source home-automation platform that households run on their own hardware, where it controls the physical devices of a home such as lights, thermostats, cameras, alarm panels and door locks. Its opt-in analytics reported 669,743 active installations on 21 August 2026 (Home Assistant, n.d.-b).

The platform's reach comes from integrations, the modules that connect it to a particular device or online service. Beyond the 1,482 integrations shipped with the platform, users install integrations written by the community, commonly through the Home Assistant Community Store. An integration is not a separate program that the platform supervises. It is a Python module that Home Assistant imports into its own process and hands the platform's core object, through which it can read and change the state of the whole system (Home Assistant, n.d.-a). No boundary therefore separates an integration from the platform, and nothing records what an integration needs: one that reports pollen counts and one that operates a door lock receive the same authority. This design is reasonable for code that the platform's maintainers review, but the same mechanism carries code that no one reviews, and Table 1 shows how widely it does.

**Table 1**
*Scale of the community-integration ecosystem*

| Measure | Value |
|---|---|
| Installations running the Community Store | 379,326 of 669,743 (56.6%) |
| Distinct community integrations reporting | 4,220 |
| Mean community integrations per Community Store installation | 4.02 |
| Community integrations with fewer than 100 installations | 3,095 |
| Community integrations with more than 10,000 installations | 27 |

*Note.* Computed from Home Assistant's published per-integration analytics, retrieved 21 August 2026 (Home Assistant, n.d.-b). Participation is optional, so every figure is a lower bound.

The table supports three observations. Community code is the normal configuration rather than an exception, since more than half of reporting installations run the store. Most of that code sits in a long tail of small projects, which are the least likely to attract independent review. At the head, a single hostile release of a popular integration would reach thousands of homes through an update channel their owners already trust.

This project builds and evaluates a framework that confines each community integration without changing its code or the platform. Each integration runs in its own Linux sandbox against a minimal copy of the platform, and every effect it has on the household's real installation passes through a separate process, the mediator, which holds a credential the integration never sees. What an integration may do is declared in a `permissions` block of the manifest it already ships, approved by the owner in the platform's own interface, enforced while it runs and recorded in a tamper-evident log. The integrations' code is unmodified, but each one needs such a declaration, and in the evaluation every declaration was written by hand.

The evaluation compares each integration confined with the same integration unconfined on the same device, a Raspberry Pi 5. The published attacks on the platform succeed unconfined and find nothing confined. Across 75 real community integrations, confinement caused no failure to load that did not also occur without it, and the device holds at least 17 sandboxes, against a mean of 4.02 community integrations per installation that runs the store. The results describe one platform release, 2026.8.3, and one device.

The report is organised as follows. Section 2 states the problem and Section 3 the objectives. Section 4 reviews the literature and locates the gap, and Section 5 describes the research methodology. Section 6 reports how AI was used and evaluated. Sections 7 and 8 present and discuss the results, and Sections 9 and 10 conclude and set out future work.
