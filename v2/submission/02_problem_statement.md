# 2. Problem Statement

This section sets out what an integration can reach, why nothing limits it, and who carries the risk.

## 2.1 What an integration can reach

An integration's authority follows from where it runs, not from a flaw: sharing the platform's process, it can call any of the platform's actions, unlocking a door and disarming an alarm included, and read the state of every device, which reveals when a household is asleep or away (Home Assistant, n.d.-g). It can also read any file the platform can, and nothing restricts what it connects to. When flaws in several community integrations exposed those files in 2021, the platform warned that this "includes any credential that you might have stored" (Home Assistant, 2021a). Corno and Mannella (2022) showed that one integration can even read or change another's private data in memory. Appendix C (Table C.7) gives each reach with its source. The harm is what sets this platform apart: a compromised browser extension costs its user data, whereas a compromised integration can open the front door through the platform's own controls.

## 2.2 What limits that authority today

Community code is the normal configuration of the platform rather than an exception, as Table 2.1 shows.

**Table 2.1**
*Scale of the community-integration ecosystem*

| Measure | Value |
|---|---|
| Active installations reporting analytics | 669,743 |
| Installations running the Community Store | 379,326 (56.6%) |
| Distinct community integrations reporting | 4,220 |
| Total community-integration installations | 1,904,297 |
| Mean community integrations per Community Store installation, the store itself not counted | 4.02 |
| Median installations per community integration | 20 |
| Community integrations with at least 1,000 installations | 257 |
| Community integrations with fewer than 100 installations | 3,095 |

*Note.* Computed from Home Assistant's published per-integration analytics, retrieved 21 August 2026 (Home Assistant, n.d.-d). Participation in the analytics is optional, so every figure is a lower bound.

No control in this ecosystem acts on what an integration does once installed. The community store admits a repository that is public, has valid metadata and a release, and passes structural checks, none of which concerns what the code does (HACS, n.d.). Inclusion in the store, which users may read as curation, therefore says nothing about safety. In version 2026.11, released on 4 November 2026, the store became part of the platform as the Marketplace, which states that its content "is not tested, audited, or supported by the Home Assistant project, and it runs inside your Home Assistant" (Home Assistant, 2026b). The platform now acknowledges the risk, and it answers that risk with the user's consent rather than with a limit. Table 2.1 therefore keeps the August 2026 snapshot, taken before the store was counted as part of the platform.

Those 2021 flaws, in the community store and seven other community integrations, let an attacker "access any file that is accessible by the Home Assistant process" (Home Assistant, 2021a). Most were patched within days, after a second disclosure found the first patches incomplete (Home Assistant, 2021b). The patches closed the flaws but left an integration's authority unchanged, since one that reads the passwords file itself needs no flaw.

Community review is the one safeguard that works, since the code is public and obvious malice in a popular integration is likely to be noticed. Its limits are structural. It is thinnest where integrations are most numerous, as nearly three in four have fewer than 100 installations; it covers the version that was read, not the updates that follow; and it misses what is not obvious, as the XZ Utils backdoor, planted by a contributor after about two and a half years of earning trust, showed (Przymus & Durieux, 2025). Review lowers the chance that hostile code arrives, but nothing limits what it does once it runs.

## 2.3 Who carries the risk

Attacks that require installing a community integration fall outside the platform's security programme (Home Assistant, n.d.-f), and such integrations are installed "at their own risk" (Home Assistant, 2021a). The platform's permissions apply to the people who use it: where it checks whether an action is allowed, it checks the user who asked. An integration's code asks for an action with no user behind it, and the check then lets the action through (Home Assistant, 2026a). The household is given the risk without any means to act on it: it cannot see what an integration will access before installing it, limit it while it runs, or find out afterwards what it did. Running integrations on separate machines, as a 2026 proposal suggests for reliability (Cohen, 2026), would not change this, because an integration moved elsewhere still acts through an unrestricted credential.

## 2.4 The statement

> Community integrations run with Home Assistant's full authority, locks and alarms included, in more than half of reporting installations, and nothing in the ecosystem limits what they can do once installed. The platform leaves that risk with the household.
>
> What is missing is a way for an integration's authority to be declared, enforced and recorded, so that the risk the household is told to own becomes one it can see and limit.

Section 3 turns this statement into an objective, four constraints and the requirements a solution must meet.
