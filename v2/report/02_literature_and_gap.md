# Chapter 2 — Literature and the Gap

## 2.1 Scope and method of this review

Chapter 1 ended with a mechanism that does not exist: a way for an integration's required
authority to be declared, enforced and audited. This chapter asks whether that mechanism
exists somewhere already — in Home Assistant, in comparable extension ecosystems, or in
the research literature — and states what remains undone.

Five bodies of work are relevant, and each is reviewed in turn:

1. least-privilege architectures for **browser and mobile extensions**, where the problem
   of §1.2 was encountered first and addressed;
2. security analyses of **smart-home application platforms**, principally SmartThings;
3. work on **extensible smart-home hubs** specifically — the closest prior art;
4. **software supply-chain** attacks, which characterise the distribution channel of §1.3;
5. **empirical API-usage measurement** as a method for justifying privilege models.

**Method and its limits.** Searches were run across Google Scholar, Semantic Scholar,
OpenAlex and the ACM/IEEE/USENIX/NDSS proceedings, using combinations of *smart home*,
*IoT platform*, *extension*, *plug-in*, *integration*, *permission*, *capability*,
*sandbox*, *least privilege* and *Home Assistant*, followed by forward and backward
citation chasing from the papers found. This is a **structured narrative review, not a
systematic review** in the PRISMA sense: the search was not pre-registered, inclusion was
by judgement, and no second reviewer screened the results. It is therefore possible that
relevant work was missed, and §2.9 states what would follow if it were. Where a
publisher's site could not be retrieved, bibliographic data was taken from OpenAlex and
the claim made about the work was restricted to what could be confirmed.

## 2.2 The precedent: least privilege for extensions is a solved problem elsewhere

The problem described in §1.2 is not new, and it is not specific to home automation. It
was encountered in web browsers and resolved there more than fifteen years ago.

Barth, Felt, Saxena and Boodman [1] analysed the Firefox extension system and described
exactly the situation Home Assistant is in today: extensions "run with the user's full
privileges and can read and write arbitrary files and launch new processes", so a bug in
well-intentioned extension code is exploitable by a hostile web page. Their empirical
finding is the one that matters here. Examining 25 popular Firefox extensions, they found
that **88% needed less than the full set of available privileges**, and that **76% used
unnecessarily powerful APIs**, which made reducing their privileges difficult. The
architecture they proposed in response — a declared permission manifest, privilege
separation, and isolated worlds — was adopted by Google Chrome and is now the standard
model for browser extensions.

Two things follow for this project.

First, the *idea* at the centre of this work is **not novel**, and this report will not
claim it is. Declaring an extension's required authority in a manifest and enforcing it at
runtime is established practice in browsers and in mobile operating systems. Chapter 1's
problem statement is best read as *proven elsewhere, absent here*.

Second, and more usefully, Barth et al. also identified the obstacle that governs this
project's difficulty. Their observation that most extensions *used unnecessarily powerful
APIs, making privilege reduction hard* is the retrofit problem in miniature. Chrome could
address it because it was designing a **new** extension platform and could require
developers to migrate. Home Assistant cannot: 4,220 integrations already exist, written
against an API that presumes full authority, and their authors cannot be compelled to
rewrite them. The precedent therefore establishes that the destination is right while
saying almost nothing about how to reach it from where Home Assistant stands.

## 2.3 Smart-home application platforms: a decade of work on a different platform model

The security of smart-home *applications* has been studied intensively since 2016, almost
entirely on Samsung SmartThings.

Fernandes, Jung and Prakash [2] performed the foundational analysis, examining 499
SmartApps and 132 device handlers. They identified two intrinsic design flaws producing
significant **overprivilege**, and demonstrated concrete attacks including one that
programmed a backdoor PIN into a door lock. Their finding is the smart-home analogue of
Barth et al.: an extension model granted applications far more authority than they needed.

The subsequent literature proposed mechanisms to address it:

- **FlowFence** (Fernandes, Paupore, Rahmati, Simionato, Conti, Prakash) [3] requires
  applications to declare intended data flows and enforces them by running sensitive
  computation in sandboxed "Quarantined Modules" with opaque handles.
- **ContexIoT** (Jia, Chen, Wang, Rahmati, Fernandes, Mao, Prakash) [4] provides
  contextual integrity, identifying the context of a sensitive action at fine granularity
  and prompting the user at runtime.
- **SmartAuth** (Tian, Zhang, Lin, Wang, Ur, Guo, Tague) [5] extracts security-relevant
  information from an application's description, code and annotations, and generates an
  authorization interface that reconciles what an app *says* it does with what it does.
- **Tyche** (Rahmati, Fernandes, Eykholt, Prakash) [16] proposes a risk-based permission
  model that groups device operations "into units of similar risk" rather than by function,
  motivated by the observation that physical operations are **risk-asymmetric**: unlocking a
  door is not the inverse of locking it in risk terms, though a function-oriented permission
  model treats both as `lock` access.

Tyche's asymmetry observation carries directly into this project's design and is recorded
here for Chapter 5: a manifest whose granularity is the *entity* or the *domain* will grant
`lock.unlock` to anything permitted to call `lock.lock`. Granularity is a security
property of the manifest, not a formatting detail.

This is a mature body of work, and its framing of overprivilege is directly applicable.
Its *assumptions*, however, are not — and the difference is what makes Home Assistant a
distinct problem rather than a new instance of a solved one.

**Table 2.1 — Platform assumptions in prior work versus Home Assistant**

| | SmartThings (as studied in [2]–[5]) | Home Assistant |
|---|---|---|
| Who operates the platform | A vendor, centrally | The end user, self-hosted |
| Where applications execute | Vendor cloud, in a Groovy sandbox | In the platform's own Python process, on the user's hardware |
| Existing permission model | Yes — a capability system, found over-permissive | **None** |
| Can the platform be changed? | Yes, by the vendor | Only by the open-source project |
| Can applications be required to change? | Yes, via developer terms and review | **No** — authors are volunteers, code already exists |
| Distribution | Vendor-controlled store | Community store, no code review (§1.4) |

The consequence is specific. Prior mechanisms improve a permission model that already
exists, on a platform whose operator can mandate migration, for applications that run in a
sandbox the operator built. Tyche [16] is the clearest illustration: it does not require
apps to be rewritten, but it does require the *platform operator* to implement a new
permission framework — an option available to Samsung and unavailable here. Home Assistant has no permission model to improve, no operator
who can mandate anything, and no sandbox: the untrusted code is `import`ed into the
platform's own process. FlowFence's Quarantined Modules require applications to be written
against its programming model; SmartAuth requires an app store position from which to
mediate installation. Neither transfers to an ecosystem of 4,220 unmodifiable Python
modules distributed peer-to-peer from GitHub.

## 2.4 Extensible hubs, and the closest prior work

A smaller literature addresses hubs extended by third-party plug-ins, which is the Home
Assistant case exactly. This section examines it in detail, because it contains the closest
prior work to this project and because the contribution claim in §2.8 depends on
characterising it accurately.

### 2.4.1 Corno and Mannella: the threat model, and what it demonstrates

**Corno and Mannella [6]**, presented at SpliTech 2022, propose a threat model for smart
home gateways extensible through plug-ins. The paper states its purpose as "twofold": to
help developers understand attacks arising "from a malicious or defective implementation of
a plug-in", and to serve as "a set of guidelines", since "plug-in developers should not
create plug-ins acting like the threats reported in the paper". It is validated on Home
Assistant.

Their validation is **offensive**, and it is valuable. The authors wrote three custom
integrations — `switch_target`, `light_simple_access` and `light_altering_state` — in which
the latter two attack the first. The attack technique deserves quoting in full, because it
bears directly on this project's design. To reach another integration's live object, they
walk the Python garbage collector:

```python
def get_target(self):
    for obj in gc.get_objects():
        if isinstance(obj, SwitchEntity):
            if obj.name == "Switch Target":
                return obj
```

Having obtained the reference, `light_simple_access` reads a secret held by the target
integration and can then either use it directly or exfiltrate it; `light_altering_state`
modifies the target's state and secret, breaking integrity and partial availability.

This result extends Chapter 1's Table 1.2 in a way that constrains any solution. It is not
merely that an integration holds full authority over the *platform*; **co-residence in one
Python process means there is no boundary between integrations either**. Any object on the
heap is reachable by name and type. The consequence for design is decisive and is carried
into Chapter 5: a permission layer implemented as an in-process API wrapper cannot be a
security boundary, because the code it purports to constrain can enumerate the heap and
reach past it — including to any credential such a layer holds. Isolation must be at least
at process granularity. That conclusion is normally asserted; here it is demonstrated by
published, independent work.

**What the paper recommends, and does not build.** Its own summary states the direction
plainly: "to reduce the presence of the previously described threats is necessary to act on
different components. First of all, the gateway itself (and its APIs) should enforce more
controls. Then, the plug-ins should authenticate themselves while interacting with the
platform (or among them)." That is a description of a mediating, per-plug-in-authenticated
API boundary — precisely the mechanism this project builds — and it is offered as a
recommendation. No such mechanism is implemented or evaluated in the paper. Its stated
future work is to develop a proof of concept per threat, to broaden the attack targets, and
to analyse "a large set of Home Assistant extensions to observe how many plug-ins present
the described threats", with the aim of helping "developers create more secure and reliable
smart home systems". The programme is diagnostic and developer-facing throughout.

### 2.4.2 The MUD architecture: enforcement at the network layer

The same authors' subsequent work [8] adapts the Manufacturer Usage Description standard
[9] to extensible gateways. MUD applies the declare-and-enforce principle at the network
layer: because most IoT devices have narrow, predictable communication patterns, the
manufacturer publishes a machine-readable profile of intended communications; the device
advertises a URL for it on joining the network; a *MUD manager* retrieves the profile; and
the resulting access-control lists are enforced by network infrastructure. A compromised
bulb that begins scanning the local network is blocked, because scanning was never declared.

This is the same *shape* of idea as the manifest proposed in this work, which is why it must
be distinguished carefully rather than dismissed. Corno and Mannella's extension lets plug-in
developers "specify which endpoints their plug-ins need to reach"; the gateway consolidates
these declarations into a single gateway-level MUD file, signs it, exposes it over Home
Assistant's own web server, and advertises it by DHCP. Their proof of concept enforces the
result with osMUD on an OpenWrt router, which instantiates the policies as `iptables` rules.

Three properties of that design bound what it can achieve, all evident from the paper itself.

**Enforcement is at the network layer, not the platform's.** The policies become firewall
rules on a router. The most consequential capabilities in Table 1.2 never reach a router: an
integration reading every entity state or calling `lock.unlock` is exercising Home
Assistant's *own* API, in-process, with the platform's own authority. The garbage-collector
attack of §2.4.1 crosses no network at all. This is a difference of layer, not of
granularity — a firewall cannot mediate a call that never becomes a packet.

**Consolidation removes per-plug-in attribution.** Because the declarations of all plug-ins
are merged into one gateway-level file, and because the firewall sees a single host, the
effective network policy for any individual plug-in is the **union of every plug-in's
declarations**. An integration that declares nothing still reaches every endpoint that any
other installed integration declared. The architecture constrains the gateway in aggregate;
it does not isolate plug-ins from one another. Their reported evaluation is consistent with
this: eight policies across three integrations, enforced as ten firewall rules.

**It depends on the developer's cooperation, and the authors say so.** The declarations are
written by plug-in developers, and the paper acknowledges that "anyone accessing the
integrations source code could alter it (and alter the snippets)", proposing signing or a
list of "authorized HAss-MUD developers" as mitigation — that is, trusting the developer.
The paper further leaves to future work how to handle conflicting, overlapping and *absent*
policies. A malicious author simply declares what they want, or declares nothing.

Validation was on three integrations — a weather integration and two emulated custom ones —
so no compatibility cost over the real extension ecosystem is reported.

None of this diminishes the work: within its stated aim, bringing MUD coverage to devices
that are not MUD-enabled, it succeeds and is evaluated. It addresses a different axis of the
problem, and this project needs that axis too (§1.6, Table 1.2). It does not address
authority exercised through the platform's own API.

### 2.4.3 The consolidated statement: the 2024 doctoral thesis

Mannella's doctoral thesis [17] is the fullest statement of this line of work, and it
settles the question of what was ultimately built. Its three contributions are the threat
model of §2.4.1, extended with a survey of experts and users to establish "whether developers
could potentially introduce undesired behaviors by mistake"; the extended MUD architecture of
§2.4.2, described as giving "plug-in developers the possibility of specifying the network
requirements of their plug-ins", together with an integrity-verification mechanism that
detects tampering with developers' declarations; and an *IoT Proxy* that outsources security
functions from resource-limited devices to the gateway using virtual network security
functions.

The thesis's own future work confirms the direction of travel. It proposes comparing groups
of programmers working with and without the threat model; "analyzing a large set of Smart
Home Gateway open-source extensions using the threat model" to assess the ecosystem's
security status; unsupervised machine learning and live traffic analysis for the IoT Proxy;
dataset diversification; and usability studies. **No item proposes runtime confinement of
plug-in authority.** The programme's framing is stated in its own conclusion: the work is
directed at "supporting novice developers and enhancing the security of smart home systems".

One item deserves explicit acknowledgement rather than quiet appropriation. Their proposal
to analyse a large set of extensions is *adjacent* to this project's first contribution, and
both remain open. They are not the same study: theirs applies a threat model to a corpus to
ask **how many plug-ins exhibit the modelled threats**; this project parses a corpus to ask
**what platform API surface plug-ins depend on**, in order to size the retrofit cost of
confinement. The corpus is shared; the question is not.

### 2.4.4 Independent confirmation from a systematic review

**Thingnes and Meland [7]**, a 2025 systematic review in *Future Internet*, screened 713
papers published between January 2019 and November 2024, selected 16, and synthesised eight
prevalent security challenges for users of extensible smart home hubs. **Two of the eight
are this project's subject**: "Insecure Extension Runtime" and "Insufficient Access
Control".

Their summary of the state of affairs is direct: "Corno and Mannella specifically found that
Home Assistant, the most popular open-source hub, has no firm extension isolation,
compromising the confidentiality and integrity of other extensions running on the hub.
Furthermore, extensions are free to perform actions without being authenticated, reducing
the ability to audit logs and locate malicious extensions." On access control they report
that "insufficient access control allows extensions in extensible hubs unrestricted access
to sensitive information and actions", citing five independent papers for the point that
extensions should be limited to the access they require.

Critically, the solutions they are able to point to are *suggestions* and *other platforms*.
Sandboxing extension runtimes is cited as existing in Apple HomeKit and as "an approach also
suggested by Corno and Mannella"; the remaining proposals are MUD labelling [8],
expectation-based analysis, behaviour-based approaches, and app-store-style third-party
verification. For access control, the concrete prototype they identify — context-based
access control by Yang and Sun — targets **SmartThings**, not Home Assistant.

Their Future Research Directions section then proposes, unprompted by this project, exactly
the work reported here:

> "Extensible smart home hubs often lack fine-grained access control, which is crucial for
> multi-user setups and less reputable extensions. Exploring the application of zero-trust
> principles from network security to develop fine-grained access control could be
> beneficial. **A proof-of-concept implementation for Home Assistant, for instance, could be
> evaluated based on the threat model introduced by Corno and Mannella**, providing insight
> into its applicability and effectiveness." [7]

An independent systematic review, having surveyed the field, names a fine-grained access
control proof of concept for Home Assistant — evaluated against Corno and Mannella's threat
model — as an open research direction. This is stronger evidence for the gap than any
argument this chapter could construct, and it also supplies an evaluation framing that
Chapter 7 adopts.

### 2.4.5 Industry security work points the same way

GitHub Security Lab's professional code review of Home Assistant [12] found six
vulnerabilities in the core platform and assessed its layered architecture favourably, but
**explicitly declined to examine community integrations**, noting: "Due to time constraints
during the audit, we did not examine these community integrations. However, it's important
to exercise caution when using them because they will have complete access to your Home
Assistant installation." A dedicated security audit thus confirmed the full-access property
of §1.2 and left the area unexamined.

## 2.5 The distribution channel: supply-chain attacks

Chapter 1 established that integrations arrive through a channel that verifies structure
but not behaviour (§1.4), and continue arriving through an authorised update path (§1.6).
This is the setting studied as open-source software supply-chain security. Ladisa, Plate,
Martínez and Barais [10] provide a taxonomy of attacks on open-source supply chains,
systematising the routes by which malicious code enters a package ecosystem — including
maintainer account compromise and the injection of malicious code into an otherwise
legitimate project, the route realised in XZ Utils [14].

This literature is important to position correctly. It addresses **how hostile code gets
in** — and its countermeasures, such as signing, provenance attestation, reproducible
builds and typosquatting detection, are all controls on likelihood. They reduce the
probability of a malicious artifact being delivered. None of them bounds what an artifact
does once it is running, which is the concern of §1.10. Supply-chain hardening and runtime
confinement are complements, and the argument of §1.6 applies unchanged.

## 2.6 Measurement as a method for justifying a privilege model

One methodological precedent deserves note because it validates this project's approach
rather than its subject. Li, Li, Ma, Xu, Zhang and Cheng [11] measured API usage across
2,562 real-world Model Context Protocol servers in order to argue for privilege management
in that ecosystem, observing that such servers run locally with high privileges, lack
runtime permission checks and isolation, and assume implicit trust.

The structure of that argument — *measure empirically what extensions actually use, then
design a privilege model that fits the measurement* — is the right one, and it is directly
transferable. It has been applied to MCP. No equivalent measurement appears to exist for
Home Assistant, or for smart-home hub extensions generally.

## 2.7 The gap

Synthesising the five strands:

- **Least-privilege extension architectures are well understood and proven** in browsers
  and mobile platforms [1], but were introduced on *new* platforms whose operators could
  require developers to migrate.
- **Smart-home application security is a mature field** [2]–[5], but its mechanisms assume
  a vendor-operated platform, an existing permission model, a sandboxed execution
  environment, and applications that can be required to change. Home Assistant has none of
  these (Table 2.1).
- **The problem is recognised on Home Assistant specifically** [6], [7], [12], and
  sandboxing of extension runtimes has been *suggested* [6], [7]. It has not been built for
  this platform. The mechanism pursued instead [8] enforces at the network layer, so it
  cannot reach the platform-API authority Table 1.2 shows to be most consequential, and its
  consolidated gateway-level profile grants every plug-in the union of all declarations.
  Corno and Mannella's own recommendation — that "the gateway itself (and its APIs) should
  enforce more controls" and that "plug-ins should authenticate themselves" [6] — remains
  unimplemented, and Thingnes and Meland [7] name a fine-grained access-control proof of
  concept for Home Assistant as an open research direction.
- **Supply-chain research** [10], [14] addresses how hostile code arrives, not what it may
  do on arrival.
- **Empirical API-usage measurement to justify a privilege model** has been done for
  another plugin ecosystem [11] but not for this one.

Stated as one sentence:

> **No published work builds or evaluates runtime confinement of Home Assistant's
> third-party integrations, and none measures the compatibility cost of confining
> extensions that already exist and cannot be rewritten — the constraint that determines
> whether any such scheme is deployable at all.**

The gap is therefore not conceptual but *constructive and empirical*. The design principle
is settled; what is missing is a mechanism that works under this platform's specific
constraints, and evidence about what adopting it would cost.

## 2.8 Contribution claim

Positioned against §2.7, this project claims three contributions, stated so that each can
be checked:

1. **An empirical account of the API surface that community integrations actually depend
   on**, measured over the HACS catalogue. This makes the retrofit problem of §2.2
   quantitative rather than rhetorical, and it is the evidence base any confinement design
   for this platform requires. Methodologically it follows [11], applied to a platform
   where no such measurement exists.

2. **A confinement architecture for an extension model that cannot be changed** — where
   the platform is self-hosted, the extensions are pre-existing and unmodifiable, and
   authority is exercised through the platform's own API. The novelty is not the manifest,
   which is established practice [1], but the retrofit: enforcing a declared authority
   boundary on code written to assume it has none, and doing so without the cooperation of
   either the platform's maintainers or the extension's author.

3. **A quantified security/compatibility trade-off.** Prior work asserts that confinement
   is desirable [6], [7] or that overprivilege is prevalent [2]; none reports what fraction
   of real, unmodified extensions still function once confinement is applied. The closest
   evaluation [8] covers three integrations, two of them purpose-built for the experiment.
   Reporting both the security effect and its compatibility cost is the contribution most
   likely to survive scrutiny, because it is the one nobody else has data for.

The framing is endorsed independently. Thingnes and Meland's systematic review [7] proposes
as future work "a proof-of-concept implementation for Home Assistant … evaluated based on
the threat model introduced by Corno and Mannella", which describes contributions 2 and 3 in
the words of authors with no connection to this project. Chapter 7 therefore adopts that
evaluation framing directly: the security axis is assessed against the threat model of [6],
so that the result is comparable against an existing published model rather than against
criteria invented here.

Contribution 2 is where the engineering lies; contributions 1 and 3 are where the
*research* lies, and the report's weight should be distributed accordingly.

This project is complementary to, not competing with, the Home Assistant community's
*Remote Integration Execution* proposal [13]: that work would supply process separation for
reliability and scale, and §1.9 argued that relocation without scoping does not constrain
authority. If it is adopted, it becomes a natural substrate for the enforcement described
here rather than a substitute for it.

## 2.9 Threats to the validity of this review

Stated explicitly, since the contribution claim depends on an absence, and absences are the
hardest thing to establish.

- **The review is narrative, not systematic** (§2.1). A pre-registered systematic search
  could surface work this review missed.
- ~~**The closest sources could not be retrieved in full.**~~ **Resolved.** [6], [7], [8]
  and the consolidating doctoral thesis [17] have now been read in full, and §2.4 is written from the papers themselves rather than
  from abstracts. The specific risk flagged in the earlier draft — that [8] might enforce at
  the gateway application layer, reducing the argument to one of granularity — **did not
  materialise**: enforcement is by `osMUD` on an OpenWrt router via `iptables`, so the
  layer distinction holds as stated.
- **Absence of evidence.** The claim is that no *published* work does this. Unpublished or
  in-progress work may exist, and the Home Assistant project could implement confinement
  at any time.
- **If the gap closes**, the contribution reduces to items 1 and 3 of §2.8 — the
  measurement and the quantified trade-off — which remain valid and unclaimed regardless of
  who builds the mechanism. The project is deliberately structured so that this outcome
  weakens it rather than invalidating it.

---

## References

[1] A. Barth, A. P. Felt, P. Saxena and A. Boodman, "Protecting Browsers from Extension
Vulnerabilities", *NDSS*, 2010.
https://www.adambarth.com/papers/2010/barth-felt-saxena-boodman.pdf

[2] E. Fernandes, J. Jung and A. Prakash, "Security Analysis of Emerging Smart Home
Applications", *37th IEEE Symposium on Security and Privacy*, 2016.

[3] E. Fernandes, J. Paupore, A. Rahmati, D. Simionato, M. Conti and A. Prakash,
"FlowFence: Practical Data Protection for Emerging IoT Application Frameworks",
*USENIX Security*, 2016.

[4] Y. Jia, Q. A. Chen, S. Wang, A. Rahmati, E. Fernandes, Z. M. Mao and A. Prakash,
"ContexIoT: Towards Providing Contextual Integrity to Appified IoT Platforms", *NDSS*, 2017.

[5] Y. Tian, N. Zhang, Y.-H. Lin, X. Wang, B. Ur, X. Guo and P. Tague, "SmartAuth:
User-Centered Authorization for the Internet of Things", *USENIX Security*, 2017.

[6] F. Corno and L. Mannella, "A Threat Model for Extensible Smart Home Gateways",
*7th International Conference on Smart and Sustainable Technologies (SpliTech)*, 2022.
https://iris.polito.it/handle/11583/2963822

[7] T. R. Thingnes and P. H. Meland, "Security Challenges for Users of Extensible Smart
Home Hubs: A Systematic Literature Review", *Future Internet*, 17(6):238, 2025.
https://doi.org/10.3390/fi17060238

[8] F. Corno and L. Mannella, "A Gateway-based MUD Architecture to Enhance Smart Home
Security", 2023.

[9] E. Lear, R. Droms and D. Romascanu, "Manufacturer Usage Description Specification",
RFC 8520, IETF, 2019.

[10] P. Ladisa, H. Plate, M. Martínez and O. Barais, "SoK: Taxonomy of Attacks on
Open-Source Software Supply Chains", *IEEE Symposium on Security and Privacy*, 2023.

[11] Z. Li, K. Li, B. Ma, M. Xu, Y. Zhang and X. Cheng, "We Urgently Need Privilege
Management in MCP: A Measurement of API Usage in MCP Ecosystems", arXiv:2507.06250, 2025.

[12] GitHub Security Lab, "Securing our home labs: Home Assistant code review".
https://github.blog/security/vulnerability-research/securing-our-home-labs-home-assistant-code-review/

[13] T. Cohen (titilambert), "Remote Integration Execution", Home Assistant Community RFC,
12 May 2026. https://community.home-assistant.io/t/remote-integration-execution/1010130

[14] *XZ Utils backdoor* (CVE-2024-3094), March 2024.
https://en.wikipedia.org/wiki/XZ_Utils_backdoor

[17] L. Mannella, *Securing IoT Gateways in Smart Home Environments*, PhD thesis,
Politecnico di Torino, 2024.

[16] A. Rahmati, E. Fernandes, K. Eykholt and A. Prakash, "Tyche: A Risk-Based Permission
Model for Smart Homes", *IEEE Secure Development Conference (SecDev)*, 2018.
DOI 10.1109/SECDEV.2018.00012. Preprint: arXiv:1801.04609.

[15] L. Mannella, "Supporting Developers in the Cybersecurity of IoT Systems", PhD research
summary (supervisors F. Corno and A. Lioy), PhD Day, Department of Control and Computer
Engineering, Politecnico di Torino, 2022.
http://www.phd-dauin.polito.it/events/phdday2022/Mannella.pdf
