# 2 Problem Statement

Section 1 described how an integration runs inside Home Assistant's own process. This section sets out what that position allows an integration to reach, why no existing control bounds it, and who carries the resulting risk.

## 2.1 What an integration can reach

An integration's authority follows from where it runs, not from any vulnerability. Table 2 lists what it can reach and distinguishes what is deduced from the loading model from what is stated or demonstrated, because the two carry different weight as evidence.

**Table 2**
*Authority held by any community integration*

| Asset | Reach | Consequence of abuse | Basis |
|---|---|---|---|
| Entity states | Every entity in the installation | Occupancy, presence, absence from home | Deduced from the loading model (Home Assistant, n.d.-a) |
| Service calls | Any service, including unlocking a door and disarming an alarm | Physical access to the dwelling | Deduced; no scoping rule is documented (Home Assistant, n.d.-a) |
| Stored credentials and files | Any file the process can read | Compromise of every linked cloud account | Stated by the platform (Home Assistant, 2021a) |
| Network | Unrestricted outbound access and the home network | Exfiltration; a foothold inside the home | Reported for code running in the platform (elttam, n.d.) |
| Other integrations' objects | Any object in the shared interpreter | Theft or alteration of another integration's secrets | Demonstrated experimentally (Corno & Mannella, 2022) |

The last row shows that the missing boundary also lies between integrations. Corno and Mannella (2022) showed that one integration can walk Python's garbage collector to reach another's live objects and read or modify their private state. Any permission check placed inside the shared process is reachable by the same technique, so enforcement has to sit outside it.

## 2.2 What bounds that authority today

No control in the ecosystem acts on what an integration does once installed. The Community Store's inclusion criteria require a public repository, valid metadata, a release and passing structural checks, and none of them concerns the code's behaviour (HACS, n.d.). The platform's own history shows the resulting exposure. In January 2021, Home Assistant disclosed a directory-traversal flaw in the Community Store and in seven other widely installed integrations, through which an attacker could read any file accessible to the platform, including stored credentials (Home Assistant, 2021a, 2021b). The response closed that class of flaw but left integrations' authority unchanged, and it showed that the threat includes honest authors whose code is exploitable.

Community review is the one safeguard that works, because integration source is public. Its limits are structural, however. It is weakest in the long tail where most integrations sit; it covers the revision that was read, while later releases arrive through an update path the user has already authorised; and it can miss what is not obvious, as the XZ Utils backdoor, planted by a contributor who spent about two and a half years earning trust, demonstrated (Przymus & Durieux, 2025). Review lowers the likelihood that hostile code arrives, but nothing limits its impact once it does.

## 2.3 Who carries the risk

The platform excludes attacks that require installing a community integration from its security programme (Home Assistant, n.d.-c), and users install such integrations at their own risk (Home Assistant, 2021a). The platform's user permissions do not help, because an integration calls the core object directly, a call made that way carries no user, and the permission check is skipped when no user is present (Home Assistant, 2026). A 2026 proposal to run integrations on separate machines addresses reliability, not authority, since a remote integration with an unscoped credential has the same reach from elsewhere (Cohen, 2026). The user is therefore assigned the risk with no means to act on it: they cannot see what an integration will access before installing it, restrict it while it runs, or find out afterwards what it accessed.

## 2.4 Statement of the problem

Home Assistant loads community-written integrations into its own process, where they hold unscoped authority over every entity, service, credential and network path available to the platform, including control of locks and alarms. This code reaches more than half of reporting installations through a channel that checks structure but not behaviour, and the risk is assigned to a user who cannot see or limit it. What is missing is a mechanism through which an integration's authority is declared, enforced and recorded, so that the risk the user is told to own becomes one the user can see and limit.
