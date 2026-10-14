# 7. Literature Review

## 7.1 Scope and method

§2 ended with a mechanism that does not exist: a way for an integration's required authority to be
declared, enforced and audited. This chapter asks whether it exists already — in Home Assistant,
in comparable extension ecosystems, or in the research literature — and states what remains
undone.

Searches were run across Google Scholar, Semantic Scholar, OpenAlex and the ACM/IEEE/USENIX/NDSS
proceedings, using combinations of *smart home*, *IoT platform*, *extension*, *plug-in*,
*integration*, *permission*, *capability*, *sandbox*, *least privilege* and *Home Assistant*,
followed by forward and backward citation chasing. This is a **structured narrative review, not a
systematic review**: the search was not pre-registered, inclusion was by judgement, and no second
reviewer screened the results. §7.6 states what follows if relevant work was missed.

## 7.2 Least privilege for extensions is a solved problem elsewhere

The problem is not new and not specific to home automation. Barth, Felt, Saxena and Boodman [12]
analysed the Firefox extension system and described exactly Home Assistant's present situation:
extensions "run with the user's full privileges and can read and write arbitrary files and launch
new processes". Their empirical finding is the one that matters here. Of 25 popular Firefox
extensions, **88% needed less than the full set of available privileges** and **76% used
unnecessarily powerful APIs**, which made reducing their privileges difficult. The architecture
they proposed — a declared permission manifest, privilege separation, isolated worlds — was
adopted by Chrome and is now standard.

Two things follow. First, **the idea at the centre of this work is not novel and this report does
not claim it is.** The problem is best read as *proven elsewhere, absent here*. Second, Barth et
al. also identified the obstacle that governs this project's difficulty: most extensions used
unnecessarily powerful APIs, making privilege reduction hard. Chrome could address that because it
was designing a **new** platform and could require developers to migrate. Home Assistant cannot.
**The precedent establishes that the destination is right while saying almost nothing about how to
reach it from where Home Assistant stands.**

## 7.3 Smart-home platforms: a decade of work on a different platform model

### 7.3.1 The SmartThings literature

Fernandes, Jung and Prakash [13] performed the foundational analysis of 499 SmartApps and 132
device handlers, identifying two intrinsic design flaws producing significant **overprivilege**
and demonstrating attacks including programming a backdoor PIN into a door lock. The subsequent
literature proposed mechanisms: **FlowFence** [14] requires applications to declare intended data
flows and runs sensitive computation in sandboxed Quarantined Modules; **ContexIoT** [15] provides
contextual integrity and prompts the user at runtime; **SmartAuth** [16] reconciles what an app
*says* it does with what it does; and **Tyche** [17] proposes a risk-based permission model
grouping operations "into units of similar risk", motivated by the observation that physical
operations are **risk-asymmetric** — unlocking a door is not the inverse of locking it.

**Tyche's asymmetry observation carries directly into this project's design** and produces one of
its requirements: a manifest whose granularity is the domain will grant `lock.unlock` to anything
permitted to call `lock.lock`. Granularity is a security property, not a formatting detail.

This is a mature body of work and its framing of overprivilege applies directly. Its *assumptions*
do not.

**Table 7.1 — Platform assumptions in prior work versus Home Assistant**

| | SmartThings, as studied in [13]–[17] | Home Assistant |
|---|---|---|
| Who operates the platform | A vendor, centrally | The end user, self-hosted |
| Where applications execute | Vendor cloud, in a Groovy sandbox | In the platform's own Python process, on the user's hardware |
| Existing permission model | Yes — a capability system, found over-permissive | **None** |
| Can the platform be changed? | Yes, by the vendor | Only by the open-source project |
| Can applications be required to change? | Yes, via developer terms and review | **No** — authors are volunteers, code already exists |
| Distribution | Vendor-controlled store | Community store, no code review |

Prior mechanisms improve a permission model that already exists, on a platform whose operator can
mandate migration, for applications running in a sandbox the operator built. Tyche is the clearest
illustration: it does not require apps to be rewritten, but it does require the **platform
operator** to implement a new framework — an option available to Samsung and unavailable here.

### 7.3.2 Extensible hubs, and the closest prior work

**Corno and Mannella [9]** propose the only published threat model for smart-home gateways
extensible through plug-ins, validated on Home Assistant. Their validation is offensive and
valuable: they wrote three integrations in which two attack the third, reaching another
integration's live object by walking the Python garbage collector, then reading and modifying its
private state.

**This result constrains every possible solution.** It is not merely that an integration holds
full authority over the *platform*; co-residence in one interpreter means **there is no boundary
between integrations either**. A permission layer implemented as an in-process API wrapper cannot
be a security boundary, because the code it purports to constrain can enumerate the heap and reach
past it — including to any credential the layer holds. Isolation must be at least at process
granularity. That conclusion is normally asserted; here it is demonstrated by independent
published work, and it is the single most load-bearing citation in this report.

**What the paper recommends, and does not build.** Its own summary: "the gateway itself (and its
APIs) should enforce more controls. Then, the plug-ins should authenticate themselves while
interacting with the platform". That is a description of a mediating, per-plug-in-authenticated
API boundary — precisely the mechanism this project builds — offered as a recommendation. No such
mechanism is implemented or evaluated. The paper's stated future work is diagnostic and
developer-facing throughout.

**The same authors' subsequent work [18]** adapts the Manufacturer Usage Description standard [19]
to extensible gateways: plug-in developers specify which endpoints they need, the gateway
consolidates the declarations into one signed gateway-level MUD file, and osMUD enforces the
result as `iptables` rules on an OpenWrt router. Three properties bound what this can achieve,
all evident from the paper itself:

- **Enforcement is at the network layer, not the platform's.** An integration reading every entity
  state or calling `lock.unlock` is exercising Home Assistant's own API, in-process. The
  garbage-collector attack crosses no network at all. **A firewall cannot mediate a call that
  never becomes a packet.**
- **Consolidation removes per-plug-in attribution.** Because all declarations merge into one
  gateway-level file and the firewall sees a single host, the effective policy for any plug-in is
  the **union of every plug-in's declarations**. An integration that declares nothing still
  reaches every endpoint any other integration declared.
- **It depends on the developer's cooperation, and the authors say so** — acknowledging that
  "anyone accessing the integrations source code could alter it" and proposing developer
  allow-lists as mitigation.

Validation covered three integrations, two of them purpose-built.

**Mannella's doctoral thesis [20]** consolidates this line of work, and its future work confirms
the direction of travel: applying the threat model to a large corpus, machine learning for traffic
analysis, usability studies. **No item proposes runtime confinement of plug-in authority.**

### 7.3.3 An independent systematic review names this exact work

**Thingnes and Meland [21]** screened 713 papers from 2019–2024, selected 16, and synthesised
eight prevalent security challenges for users of extensible smart-home hubs. **Two of the eight
are this project's subject**: "Insecure Extension Runtime" and "Insufficient Access Control". The
concrete solutions they can point to are *suggestions* or *other platforms* — sandboxing cited as
existing in Apple HomeKit, and the one access-control prototype targeting SmartThings.

Their Future Research Directions section then proposes, unprompted, exactly the work reported
here:

> "Extensible smart home hubs often lack fine-grained access control… **A proof-of-concept
> implementation for Home Assistant, for instance, could be evaluated based on the threat model
> introduced by Corno and Mannella**, providing insight into its applicability and effectiveness."
> [21]

This is stronger evidence for the gap than any argument this chapter could construct, and it
supplies the evaluation framing §12 adopts.

**GitHub Security Lab's professional audit [22]** found six vulnerabilities in the core platform,
assessed its layered architecture favourably, and **explicitly declined to examine community
integrations**: "we did not examine these community integrations. However, it's important to
exercise caution when using them because they will have complete access to your Home Assistant
installation." A dedicated security audit confirmed the full-access property and left the area
unexamined.

## 7.4 Supply chain, and measurement as method

Ladisa, Plate, Martínez and Barais [23] systematise attacks on open-source supply chains,
including the maintainer-compromise route realised in XZ Utils [8]. This literature addresses
**how hostile code gets in**, and its countermeasures — signing, provenance, reproducible builds —
are all controls on likelihood. None bounds what an artifact does once running.

One methodological precedent validates this project's approach. Li et al. [24] measured API usage
across 2,562 Model Context Protocol servers to argue for privilege management in that ecosystem.
The structure — *measure empirically what extensions actually use, then design a privilege model
that fits the measurement* — is directly transferable, and **no equivalent measurement exists for
Home Assistant**.

## 7.5 The gap, and the contribution

> **No published work builds or evaluates runtime confinement of Home Assistant's community
> integrations, and none measures the compatibility cost of confining extensions that already
> exist and cannot be rewritten — the constraint that determines whether any such scheme is
> deployable at all.**

The gap is not conceptual but **constructive and empirical**. Three contributions follow, each
stated so it can be checked:

1. **An empirical account of the API surface community integrations actually depend on**, measured
   over the HACS catalogue, making the retrofit problem quantitative rather than rhetorical.
2. **A confinement architecture for an extension model that cannot be changed.** The novelty is
   not the manifest, which is established practice [12], but **the retrofit**: enforcing a declared
   authority boundary on code written to assume it has none, without the cooperation of either the
   platform's maintainers or the extension's author.
3. **A quantified security/compatibility trade-off.** Prior work asserts that confinement is
   desirable [9][21] or that overprivilege is prevalent [13]; **none reports what fraction of
   real, unmodified extensions still function once confinement is applied.** The closest evaluation
   [18] covers three integrations, two purpose-built. This is the contribution most likely to
   survive scrutiny, because it is the one nobody else has data for.

## 7.6 Threats to the validity of this review

The contribution claim depends on an absence, and absences are the hardest thing to establish.
The review is narrative rather than systematic. The claim is that no *published* work does this;
unpublished work may exist and the Home Assistant project could implement confinement at any
time. **If the gap closes, the contribution reduces to items 1 and 3** — the measurement and the
quantified trade-off — which remain valid and unclaimed regardless of who builds the mechanism.
The project is deliberately structured so that outcome weakens it rather than invalidating it.
