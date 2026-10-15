# 2. Problem Statement

Section 1 described how an integration runs inside Home Assistant's own process. This section sets out what that position allows it to reach, why no existing control bounds it, and who carries the resulting risk.

## 2.1 What an integration can reach

An integration's authority follows from where it runs, not from any vulnerability. Table 2.1 lists what it can reach, and its last column separates what is deduced from the loading model from what is stated or demonstrated, because the two carry different weight as evidence.

**Table 2.1 — Authority held by any community integration**

| Asset | Reach | Consequence of abuse | Basis |
|---|---|---|---|
| Entity states | Every entity in the installation | Occupancy, presence, sleep patterns, absence from home | Deduced from the loading model [2] |
| Service calls | Any service, including unlocking a door and disarming an alarm | Physical access to the dwelling | Deduced; no scoping rule or caller check is documented [2] |
| Stored credentials | Any file the process can read, including stored secrets | Compromise of every linked cloud account | Stated by the platform [3] |
| File system | Whatever the process's user can read | Configuration, history database, tokens | Stated by the platform [3] |
| Network | Unrestricted outbound access and the home network | Exfiltration; a foothold inside the home | Reported for code running in the platform [4] |
| Other integrations' live objects | Any object in the shared interpreter | Theft or alteration of another integration's secrets | Demonstrated experimentally [5] |

The last row shows that the missing boundary lies between integrations as well as between an integration and the platform. Corno and Mannella [5] showed that one integration can walk Python's garbage collector to reach another integration's live object and read or modify its private state. Any permission check inside the shared process is reachable by the same technique, so enforcement has to sit outside it. The consequence column also sets this platform apart: a compromised browser extension costs its user data, whereas a compromised integration can unlock the front door through the platform's own control path, indistinguishably from the owner.

## 2.2 What bounds that authority today

No control in the ecosystem acts on what an integration does once installed. The community store's inclusion criteria [6] require a public repository, valid metadata, a release and passing structural checks, and none of them concerns the code's behaviour. This is a reasonable limit for a volunteer project facing 4,220 integrations [1], but it means that inclusion in the default store, which users may reasonably read as curation, carries no security meaning.

The platform's own history shows the exposure in practice. In January 2021, Home Assistant disclosed a directory-traversal flaw in the community store and the same flaw class in seven other widely installed integrations, through which an attacker could "access any file that is accessible by the Home Assistant process," including stored credentials, in most cases without authentication [3], [7]. The response was fast and thorough [3], but it closed a vulnerability class and left integrations' authority unchanged: an integration that reads the secrets file directly, or calls the unlock service, traverses no path. The episode also showed that the threat includes honest authors whose code is exploitable, with the same harm as malice.

Community review is the one safeguard that works, since integration source is public and obvious malice in a popular integration is likely to be noticed. Its limits, however, are structural. It is weakest where the population is largest, since 3,095 of the 4,220 integrations have fewer than 100 installations [1]; it covers the revision that was read, while later releases arrive through an update path the user has already authorised; and it can miss what is not obvious, as the 2021 flaws were found by a researcher rather than by reviewers [3], and the XZ Utils backdoor was planted by a contributor who spent about two and a half years earning trust [8]. Review lowers the likelihood that hostile code arrives; nothing limits its impact once it has.

## 2.3 Who carries the risk

The platform states its position plainly. Attacks that require a user to install a community integration are excluded from its security programme [9], and custom integrations are installed "at their own risk" [3]. The platform does distinguish administrators from other users of its interfaces, but an integration never passes through those interfaces: it calls the core object directly, a service call made that way carries no user, and the permission check is skipped when no user is present [10]. The user is therefore assigned the risk without any means to act on it, being unable to see what an integration will access before installing it, to restrict what it accesses while running, or to find out afterwards what it accessed.

The single-process design is recognised as a limit within the project: a 2026 request for comment proposes running integrations on separate machines, mainly for reliability [11]. Relocation alone does not bound authority, however, because a remote integration still needs a credential to act on the platform, and an unscoped credential gives it the same reach from elsewhere.

## 2.4 The statement

> Home Assistant loads community-written integrations into its own process, where they hold unscoped authority over every entity, service, credential and network path available to the platform, including control of locks and alarms. This code reaches more than half of reporting installations through a channel that checks repository structure but not behaviour. The platform excludes it from its security programme and assigns the risk to the user, and the one working safeguard, community review, acts on the likelihood that hostile code arrives rather than on what it can do once it runs.
>
> What is missing is a mechanism through which an integration's authority is declared, enforced and recorded, so that the risk the user is told to own becomes one the user can see and limit.

Section 3 turns this statement into an objective, four constraints and the requirements a solution must meet.
