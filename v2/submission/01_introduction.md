# 1. Introduction

Home Assistant is an open-source home-automation platform that users run on their own hardware,
and which acts as the control plane for the physical devices in a home: lights, thermostats,
cameras, alarm panels and door locks. Its opt-in telemetry reported **669,743 active
installations** as of 21 August 2026 [1].

Its capability comes from *integrations* — modules that connect the platform to a particular
device or cloud service. Beyond the roughly 1,500 shipped with the platform, users install
community-written integrations through a third-party distribution channel, the Home Assistant
Community Store (HACS). An integration is not a program the platform runs at arm's length. It is
a Python module placed in the user's configuration directory, which Home Assistant **imports into
its own running process** at startup and then calls into, passing it the live `hass` object —
the platform's own core object — through which the integration reads and writes system state [2].

Two consequences follow directly, and neither is incidental. **There is no boundary to cross:**
the integration executes inside the platform's process, with the platform's operating-system
privileges, its file descriptors, its network access and its memory. It is not sandboxed because
there is no sandbox; the architecture has no place to put one. And **the `hass` object is
unscoped authority:** it is a single handle onto the entire platform, and nothing in the calling
convention expresses which entities an integration needs, which services it intends to call, or
which hosts it will contact. An integration that reports pollen counts and one that controls a
door lock receive the same object and the same reach.

This is a reasonable design for *first-party* code, where the platform's maintainers control what
is loaded. The problem this project addresses is what happens when the same mechanism carries
code the maintainers have never seen — which, on more than half of all reporting installations,
it does.

**Table 1.1 — Scale of the custom-integration ecosystem** (computed from Home Assistant's
published per-domain telemetry, retrieved 21 August 2026)

| Measure | Value |
|---|---|
| Active installations reporting analytics | 669,743 |
| Installations running HACS | 379,326 (**56.6%**) |
| Distinct custom integrations reporting | 4,220 |
| Total custom-integration installs | 1,904,297 |
| Mean custom integrations per **HACS-running** installation | 4.02 |
| Median installs per custom integration | 20 |
| Custom integrations with ≥ 1,000 installs | 257 |
| Custom integrations with < 100 installs | 3,095 |

Three observations shape everything that follows. **The channel is mainstream, not marginal** —
unreviewed third-party code is the normal configuration of a Home Assistant system. **The
distribution is extremely long-tailed** — 3,095 of 4,220 integrations have fewer than 100
installs, and these are overwhelmingly single-author projects serving small audiences, precisely
the population least likely to attract independent code review. And **the head concentrates
risk** — 27 integrations exceed 10,000 installs, so a single malicious release in that group
reaches thousands of homes through an update mechanism users have already authorised.

Analytics participation is opt-in, so every figure is a lower bound on the true population. The
56.6% figure is used here to establish that the exposure is *widespread*, a claim the direction
of the bias does not threaten.

**What this project builds.** A confinement framework that runs an unmodified community
integration in its own Linux sandbox, against a real but stripped Home Assistant instance, with
every effect on the user's actual platform passing through an out-of-process mediator that holds
the credential the integration never sees. What the integration may do is declared in the
`manifest.json` file it already ships, enforced at runtime, and recorded in a tamper-evident log.
**No integration is modified and Home Assistant itself is not modified.**

**What this project measures.** Whether that confinement works against the published attacks, and
what it costs — in compatibility, in memory, and in latency — on the hardware people actually run.
The compatibility figure, measured against an unconfined baseline on two independent corpora of
real community integrations, is the contribution nobody else has data for.

The report follows the structure below. §2 states the problem; §3 specifies the project; §4–§6
place it in its societal, standards and programme-logic context; §7 reviews the literature and
locates the gap; §8 gives the methodology and the threat model that drives the design; §9 gives
the architecture as built; §10 the feasibility study; §11 and §12 the data and the results; §13
what the process taught; §14 and §15 the future work and the conclusion.
