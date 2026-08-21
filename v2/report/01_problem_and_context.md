# Chapter 1 — Problem and Context

## 1.1 Introduction

Home Assistant is an open-source home-automation platform that users run on their own
hardware, and which acts as the control plane for the physical devices in a home: lights,
thermostats, cameras, alarm panels and door locks. As of 21 August 2026 its opt-in
telemetry reports **669,743 active installations** [1].

Its capability comes from *integrations* — modules that connect the platform to a
particular device or cloud service. Beyond those shipped with the platform, users install
community-written integrations through a third-party distribution channel. This chapter
establishes three things: that such code runs with the full authority of the platform
itself; that this is a current and documented exposure rather than a hypothetical one; and
that while the ecosystem does have one real safeguard — informal community review of public
source — every existing control acts on the likelihood that hostile code arrives, and none
bounds what it can do once it is running.

The argument is deliberately built from primary sources — the platform's own
documentation, its own security disclosures, its own telemetry, and the distribution
channel's own published criteria — because a claim about a system's trust model is
strongest when made in that system's own words.

## 1.2 How Home Assistant is extended

An integration is not a program the platform runs at arm's length. It is a Python module
placed in the `custom_components` directory of the user's configuration, which Home
Assistant imports into its own running process at startup and then calls into. The
platform invokes a setup entry point — `setup()` or `async_setup()` — and passes it the
live `hass` object, the platform's own core object, through which the integration reads
and writes system state via calls such as `hass.states.set()` [2].

Two consequences follow directly from this design, and neither is incidental:

1. **There is no boundary to cross.** The integration executes inside the platform's
   process, with the platform's operating-system privileges, its file descriptors, its
   network access and its memory. It is not sandboxed because there is no sandbox; the
   architecture has no place to put one.
2. **The `hass` object is unscoped authority.** It is a single handle onto the entire
   platform. Nothing in the calling convention expresses which entities an integration
   needs, which services it intends to call, or which hosts it will contact. An
   integration that reports pollen counts and one that controls a door lock receive
   the same object and the same reach.

This design is not a defect in the ordinary sense. It is a reasonable choice for
*first-party* code, where the platform's maintainers control what is loaded, and it buys
the simplicity and performance that make Home Assistant pleasant to extend. The problem
this project addresses is what happens when the same mechanism is used for code the
platform's maintainers have never seen.

## 1.3 The distribution channel and the scale of exposure

Community integrations reach users predominantly through the Home Assistant Community
Store (HACS), a third-party add-on that browses, installs and updates integrations from
GitHub repositories.

Table 1.1 summarises the ecosystem, computed from Home Assistant's published per-domain
telemetry (`figures/ecosystem_scale.py`, retrieved 21 August 2026).

**Table 1.1 — Scale of the custom-integration ecosystem**

| Measure | Value |
|---|---|
| Active installations reporting analytics | 669,743 |
| Installations running HACS | 379,326 (**56.6%**) |
| Distinct custom integrations reporting | 4,220 |
| Total custom-integration installs | 1,904,297 |
| Mean custom integrations per installation (excl. HACS) | 2.28 |
| Median installs per custom integration | 20 |
| Custom integrations with ≥ 1,000 installs | 257 |
| Custom integrations with ≥ 10,000 installs | 27 |
| Custom integrations with < 100 installs | 3,095 |

Three observations matter for what follows.

**The channel is mainstream, not marginal.** More than half of all reporting installations
run HACS. Unreviewed third-party code is the normal configuration of a Home Assistant
system, not an edge case.

**The distribution is extremely long-tailed.** The median custom integration has 20
installs, and 3,095 of 4,220 have fewer than 100. These are overwhelmingly single-author
projects serving small audiences — precisely the population least likely to attract
independent code review, and the one the platform's own disclosure identifies when it
notes that such authors "often work alone on this and that's why it's more likely for a
bug to go undetected" [3].

**The head of the distribution concentrates risk.** 257 integrations exceed 1,000 installs
and 27 exceed 10,000. A single compromised or malicious release in that group reaches
thousands of homes through an update mechanism users have already authorised.

**Limitation.** Analytics participation is opt-in, so every figure above is a lower bound
on the true population. The bias is not neutral either: users who enable telemetry are
plausibly more engaged than average, and more-engaged users are plausibly more likely to
install extensions. The 56.6% figure should therefore be read as a property of the
reporting population, not as a population estimate. It is used here to establish that the
exposure is *widespread*, a claim the direction of the bias does not threaten.

## 1.4 What HACS verifies before listing an integration

HACS publishes the criteria a repository must satisfy for inclusion in its default store
[4]. In full, they require that the repository be public and hosted on GitHub; that it
pass the HACS Action and, for integrations, Hassfest; that it have at least one release, a
valid integration manifest and brands entry, a valid `hacs.json` containing a name, a
repository description, issues enabled and topics defined; that it not be archived; that
the submitter be the owner or a major contributor; and that certain files be valid JSON
and sorted alphabetically.

Every one of these is structural or procedural. **None concerns the behaviour of the
code.** There is no security review, no static analysis for dangerous operations, no
declaration of what the integration intends to access, and no audit. The criteria verify
that a repository is well-formed and that its manifest is valid; correct alphabetical
sorting is a listing requirement, and what the code does is not.

This is not offered as a criticism of HACS. Reviewing 4,220 repositories and their every
subsequent release is not something a volunteer project can undertake, and HACS does not
claim to. The point is narrower and more important: **the gate that users reasonably
perceive as curation — inclusion in a default store — carries no security meaning at all.**

## 1.5 The exposure is documented, not hypothetical

In January 2021 Home Assistant published two security disclosures concerning custom
integrations [3][5]. A researcher had reported a directory-traversal vulnerability in HACS
itself; investigating, the project found the same vulnerability class in a set of other
widely-installed custom integrations, including Dwains Lovelace Dashboard, Font Awesome,
BWAlarm, Simple Icons, Custom Updater, Custom Icons and Hass-album.

The impact is stated by the platform in its own words: an attacker could "access any file
that is accessible by the Home Assistant process. This access includes any credential that
you might have stored to allow Home Assistant to access other services" [3]. In most of
the affected integrations **no authentication was required** — the attacker did not need
an account on the victim's system [5]. The HACS instance of the flaw was assigned
CVE-2021-3152.

Two features of this episode are decisive for the argument.

First, **the flaw was systemic rather than individual.** Several independently-written
integrations exhibited the same vulnerability class simultaneously. This is the signature
of a structural property — an extension model that makes the insecure thing easy and
provides no guard rails — not of one careless author.

Second, and this must be stated precisely: **these were vulnerabilities, not malice.** The
integrations were not backdoored; they contained bugs that an external attacker could
exploit. This project's threat model must therefore address two distinct actors — the
malicious author and the honest author whose code is compromised — and the 2021 evidence
speaks directly only to the second. It is nonetheless sufficient to establish the central
claim, because the mechanism of harm is identical in both cases: *code inside the Home
Assistant process holds unscoped authority over the home.* Whether that code became
hostile by intent or by exploitation changes the attacker's route, not the blast radius.

That the blast radius is real is corroborated by the platform's own history: CVE-2023-27482,
an authentication bypass in Home Assistant leading to remote code execution, was assessed
as giving "full access to control all smart home devices, stored data and credentials, and
also internal access to the home network" [6]. That vulnerability was in first-party code
and is not itself an argument about integrations, but it establishes what code execution
inside Home Assistant is worth to an attacker.

## 1.6 The review that does happen, and what it covers

Sections 1.4 and 1.5 describe the absence of a *formal* gate. They should not be read as
claiming that nobody looks at the code, because that is not true and the distinction
matters.

Integration source is published on GitHub, and the Home Assistant user base is unusually
technical — self-hosters, home-lab operators and IT practitioners who read code, file
issues and fork projects. Informal peer review is therefore a real control, and it is
reasonable to expect that **blatant** malice — a plaintext credential upload, an
unexplained connection to an unrelated host — would be noticed and reported, particularly
in an integration with a substantial user base. Any honest account of this ecosystem's
security has to credit that. It is the mechanism that currently does most of the work.

Its coverage, however, is uneven in three specific ways, each measurable rather than
speculative.

**It is weakest where the population is largest.** Informal review requires reviewers.
Table 1.1 shows 3,095 of 4,220 custom integrations have fewer than 100 installs, with a
median of 20. Attention scales with popularity, so the mechanism is strongest for the 257
integrations above 1,000 installs and close to absent across the long tail.

**It is point-in-time, while distribution is continuous.** Whatever review occurs happens
at some moment, to some revision. HACS then delivers subsequent releases through an update
path the user has already authorised. The artifact that was reviewed is not necessarily the
artifact that is running, and it is not realistic to expect users to diff each release.

**It is demonstrably permeable to the non-obvious.** The 2021 disclosures are direct
evidence about this ecosystem: the same directory-traversal class was present
simultaneously in eight custom integrations named across the two advisories, all of them
public, all installed widely enough to be worth disclosing — and it was found by a security
researcher, not by the community reading the code [3][5]. The general case is stronger
still. The backdoor introduced into XZ Utils (CVE-2024-3094) was placed in a library
present in effectively every Linux distribution, by a contributor who had spent roughly two
years earning maintainer trust, and was discovered by an engineer investigating a 500 ms
SSH latency regression rather than by review [9].

The conclusion is not that community review is ineffective. It is that review and
confinement occupy **different roles in risk treatment**, and neither substitutes for the
other:

- Community review acts on **likelihood**. It reduces the chance that hostile or careless
  code is published and installed in the first place.
- Confinement acts on **impact**. It bounds what code can do in the cases where review did
  not happen, happened to an earlier revision, or happened and missed.

The first control exists in this ecosystem and works. The second does not exist at all.
This project supplies the second and is complementary to the first by construction — a
point developed as defence in depth in Chapter 5, and carried into the threat model in
Chapter 4, where community review appears as an existing control with the coverage limits
set out above.

## 1.7 What is at stake

Combining the loading mechanism of §1.2 with the impact statements above, Table 1.2 sets
out what a custom integration can reach today. This is not a list of vulnerabilities; it
is a list of ordinary capabilities that follow from running in-process.

**Table 1.2 — Authority held by any custom integration**

| Asset | Reach | Consequence of abuse |
|---|---|---|
| Entity states | All entities in the installation | Occupancy, presence, sleep patterns, absence from home |
| Service calls | Any service, including `lock.unlock`, alarm disarm | Physical access to the dwelling |
| Stored credentials | Any file readable by the process, incl. stored secrets [3] | Lateral compromise of every linked cloud account |
| Camera and media entities | Same as any other entity | Surveillance |
| Filesystem | Whatever the process user can read | Configuration, database, tokens |
| Network | Unrestricted outbound; internal network reachable [6] | Exfiltration; pivot into the home LAN |

The distinguishing feature of this platform, relative to the general problem of untrusted
plugins, is the final column. A compromised browser extension costs a user data. A
compromised Home Assistant integration can also **unlock the front door**, and can do so
using the platform's own legitimate control path, which is indistinguishable from the
user's own action.

## 1.8 The stated positions of the platform and the channel

Home Assistant's security page defines what its security programme covers. Attacks "that
require the user to install a malicious other software, like a third-party integration,
app (formerly known as add-ons), or plugin" are listed among **non-qualifying**
vulnerabilities [7]. The same page states the platform's user model: "Home Assistant
assumes every user is trusted and does not enforce user privileges. It assumes every
logged in user has the same access as an owner account" [7]. The 2021 disclosure states
the position on third-party code directly: "Custom integrations are not created and/or
maintained by Home Assistant. Users install them at their own risk" [3].

These positions are defensible. A volunteer project cannot underwrite code it does not
write, and being explicit about the limits of a security programme is better practice than
implying a guarantee.

But placing the two positions side by side with §1.4 produces the problem this project
exists to address:

- The **platform** declares third-party integration behaviour outside its security scope.
- The **distribution channel** verifies structure and metadata, never behaviour.
- **Community review** (§1.6) partially covers the remainder, but only where an integration
  is popular enough to attract readers, only for the revision actually read, and only for
  malice obvious enough to be recognised as such.
- The **user** is assigned the risk — "at your own risk" — and is given **no technical means
  of bounding it**. They cannot see what an integration intends to access before installing
  it; they cannot restrict what it accesses once it is running; and they cannot detect
  afterwards what it accessed.

The gap is therefore not the absence of code review — review exists, and for popular
integrations it works. It is that every existing control acts on the *likelihood* that
hostile code arrives, and none acts on the *impact* once it has. Risk has been allocated to
the one party with neither the information nor the tools to act on it.

## 1.9 The problem is recognised, but not as a security problem

In May 2026 a request for comment titled *Remote Integration Execution* proposed allowing
integrations to run on separate machines while Home Assistant Core retains control of
configuration, scheduling and state [8]. Its stated motivations are principally
operational: that "one crashing integration can bring down the entire system", that
resource-intensive workloads demand a powerful single machine, that specialised hardware
cannot be exploited, and that capacity upgrades are costly. Isolation appears in the
problem statement, and the proposal does list a "security-conscious" use case —
isolating "untrusted/community integrations on separate worker".

This is significant in two ways. It confirms that the single-process architecture is
recognised *within the project* as a limitation, which strengthens the relevance of this
work. And it shows the framing is predominantly one of **reliability and scale**, with
security as an acknowledged secondary benefit.

The distinction matters technically, and it is developed in Chapter 5. Moving an
integration to another machine addresses fault isolation and resource contention. It does
not by itself address *authority*: an integration that must still read and write Home
Assistant state across a process boundary needs a credential to do so, and unless that
credential is scoped by something, relocation changes where the untrusted code runs
without changing what it may do. Process separation is a necessary building block. It is
not, on its own, a security control. This project should therefore be positioned as
complementary to that RFC rather than competing with it.

## 1.10 Problem statement

> Home Assistant loads community-written integrations into its own process, granting them
> unscoped authority over every entity, service, credential and network path available to
> the platform — including physical control of locks and alarms. This code is distributed
> at scale through a channel whose inclusion criteria verify repository structure but never
> code behaviour, and it is installed on the majority of reporting installations. The
> platform explicitly places such code outside its security programme and assigns the
> resulting risk to the user. The ecosystem's one real safeguard is informal review of
> public source, which is effective against obvious malice in popular integrations but
> weakens across a long tail where the median integration has twenty installs, covers only
> the revision actually read, and did not prevent the documented case: in 2021 a single
> vulnerability class across eight widely-installed integrations exposed arbitrary file
> contents, including stored credentials, to unauthenticated attackers.
>
> **Every control in place today acts on the likelihood that hostile code arrives. None
> bounds what it can do once it is running. What is missing is a mechanism: a way for an
> integration's required authority to be declared, enforced and audited, so that the risk
> the user is told they own becomes a risk they can actually see and limit.**

Chapter 2 examines whether such a mechanism exists — in this platform, in comparable
extension ecosystems, or in the research literature — and states precisely what remains
undone.

---

## References

[1] Home Assistant, *Analytics*. https://analytics.home-assistant.io/ — 669,743 active
installations; retrieved 21 August 2026. Per-domain custom-integration install counts from
https://analytics.home-assistant.io/custom_integrations.json, same date.

[2] Home Assistant, *Creating your first integration*, Developer Documentation.
https://developers.home-assistant.io/docs/creating_component_index/

[3] Home Assistant, *Disclosure: security vulnerabilities in custom integrations HACS,
Dwains Dashboard, Font Awesome and others*, 22 January 2021.
https://www.home-assistant.io/blog/2021/01/22/security-disclosure/

[4] HACS, *Include default repositories*. https://hacs.xyz/docs/publish/include/

[5] Home Assistant, *Security Disclosure 2: vulnerabilities in custom integrations HACS,
Font Awesome and others*, 23 January 2021.
https://www.home-assistant.io/blog/2021/01/23/security-disclosure2/

[6] elttam, *PwnAssistant — Controlling /home's via a Home Assistant RCE* (CVE-2023-27482).
https://www.elttam.com/blog/pwnassistant

[7] Home Assistant, *Security*. https://www.home-assistant.io/security/

[8] T. Cohen (titilambert), *Remote Integration Execution*, Home Assistant Community RFC,
12 May 2026. https://community.home-assistant.io/t/remote-integration-execution/1010130

[9] *XZ Utils backdoor* (CVE-2024-3094), March 2024. Backdoor introduced by a contributor
who had acquired maintainer trust over approximately two years; discovered by A. Freund
while investigating an SSH latency regression rather than through code review.
https://en.wikipedia.org/wiki/XZ_Utils_backdoor — see also
https://www.rapid7.com/blog/post/2024/04/01/etr-backdoored-xz-utils-cve-2024-3094/
