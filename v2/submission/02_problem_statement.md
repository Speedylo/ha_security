# 2. Problem Statement

## 2.1 What an integration can reach today

Combining the loading mechanism of §1 with the impact statements the platform itself publishes,
Table 2.1 sets out what a community integration can reach in a stock installation. **This is not
a list of vulnerabilities.** It is a list of ordinary capabilities that follow from running
in-process.

**Table 2.1 — Authority held by any custom integration**

| Asset | Reach | Consequence of abuse | Basis |
|---|---|---|---|
| Entity states | All entities in the installation | Occupancy, presence, sleep patterns, absence from home | Deduced from the loading model [2] |
| Service calls | Any service, including `lock.unlock`, alarm disarm | Physical access to the dwelling | Deduced; **no scoping check is documented** [2] |
| Stored credentials | Any file readable by the process, incl. stored secrets | Lateral compromise of every linked cloud account | **Stated by the platform** [4] |
| Camera and media entities | Same as any other entity | Surveillance | Deduced [2] |
| Filesystem | Whatever the process user can read | Configuration, database, tokens | **Stated by the platform** [4] |
| Network | Unrestricted outbound; internal network reachable | Exfiltration; pivot into the home LAN | Reported in an RCE assessment [7] |
| **Other integrations' live objects** | Any object on the Python heap, via the garbage collector | Theft or alteration of another integration's secrets and state | **Demonstrated experimentally** [9] |

The final column distinguishes what is *deduced* from the architecture from what has been
independently *demonstrated* or *stated*, because the two carry different evidential weight.

The last row is the least obvious. Corno and Mannella [9] show that a Home Assistant integration
can obtain a reference to *another* integration's live object by iterating the Python garbage
collector and matching on class and name, then read and modify that object's private state.
Because every integration shares one interpreter, the absence of a boundary is not only between
an integration and the platform but **between integrations**. This single published result
constrains every possible solution, and §8 returns to it.

The distinguishing feature of this platform, relative to the general problem of untrusted
plug-ins, is the consequence column. A compromised browser extension costs a user data. A
compromised Home Assistant integration can also **unlock the front door**, using the platform's
own legitimate control path, indistinguishably from the user's own action.

## 2.2 Nothing checks behaviour before the code arrives

HACS publishes the criteria a repository must satisfy for inclusion in its default store [5]:
that it be public and hosted on GitHub, pass the HACS Action and Hassfest, have at least one
release, a valid manifest and brands entry, a valid `hacs.json`, issues enabled, topics defined,
not be archived, and that certain files be valid JSON and sorted alphabetically.

Every one of these is structural or procedural. **None concerns the behaviour of the code.**
There is no security review, no static analysis, no declaration of intent and no audit. Correct
alphabetical sorting is a listing requirement; what the code does is not. This is not a criticism
of HACS — reviewing 4,220 repositories and their every subsequent release is not something a
volunteer project can undertake, and HACS does not claim to. The point is narrower: **the gate
users reasonably perceive as curation carries no security meaning at all.**

## 2.3 The exposure is documented, not hypothetical

In January 2021 Home Assistant published two security disclosures concerning custom integrations
[4][6]. A directory-traversal vulnerability was reported in HACS itself; investigating, the
project found the same vulnerability class in a set of other widely-installed integrations. The
impact, in the platform's own words, was that an attacker could "access any file that is
accessible by the Home Assistant process. This access includes any credential that you might have
stored to allow Home Assistant to access other services" [4]. In most of the affected
integrations **no authentication was required** [6].

The platform's response was fast and multi-layered: a core release with traversal protection,
Supervisor warnings, companion-app notifications, and blocking of insecure instances from remote
access [4]. Its significance here is what it did *not* change. The remediation blocks a
**vulnerability class**; it does not alter what an integration is permitted to do. An integration
that reads `secrets.yaml` directly, or calls `lock.unlock`, is not performing directory traversal
and is untouched by any of those measures. The 2021 response is therefore evidence *for* the
argument rather than against it.

Two features of the episode are decisive. **The flaw was systemic rather than individual** —
several independently written integrations exhibited the same class simultaneously, which is the
signature of an extension model that makes the insecure thing easy. And **these were
vulnerabilities, not malice** — so the threat model must address both the malicious author and
the honest author whose code is compromised. The mechanism of harm is identical in both cases.

## 2.4 Review exists, and it acts on the wrong variable

Integration source is public and the Home Assistant user base is unusually technical. Informal
peer review is a real control, and it is reasonable to expect blatant malice to be noticed in a
popular integration. Any honest account has to credit that. Its coverage, however, is uneven in
three measurable ways: **it is weakest where the population is largest** (3,095 of 4,220
integrations have under 100 installs); **it is point-in-time while distribution is continuous**
(HACS delivers subsequent releases through an already-authorised update path); and **it is
demonstrably permeable to the non-obvious** (the 2021 class was found by a researcher, not by the
community, and the XZ Utils backdoor [8] survived two years of trust-building in a library
present in every Linux distribution).

The conclusion is not that review is ineffective. It is that review and confinement occupy
**different roles in risk treatment**: review acts on the *likelihood* that hostile code arrives;
confinement acts on the *impact* once it has. The first exists in this ecosystem and works. **The
second does not exist at all.**

## 2.5 The statement

> Home Assistant loads community-written integrations into its own process, granting them
> unscoped authority over every entity, service, credential and network path available to the
> platform — including physical control of locks and alarms. This code is distributed at scale
> through a channel whose inclusion criteria verify repository structure but never code
> behaviour, and it is installed on the majority of reporting installations. The platform
> explicitly places such code outside its security programme and assigns the resulting risk to
> the user [10]. The ecosystem's one real safeguard is informal review of public source, which is
> effective against obvious malice in popular integrations but weakens across a long tail where
> the median integration has twenty installs, covers only the revision actually read, and did not
> prevent the documented case.
>
> **Every control in place today acts on the likelihood that hostile code arrives. None bounds
> what it can do once it is running. What is missing is a mechanism: a way for an integration's
> required authority to be declared, enforced and audited, so that the risk the user is told they
> own becomes a risk they can actually see and limit.**
