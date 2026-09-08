# 4. STEEPLE Analysis

Each dimension is assessed against the project's own evidence where evidence exists, and the
absence of evidence is stated rather than filled with assertion.

## 4.1 Social

The asset at risk is a dwelling and the people in it. Home Assistant's entity model carries
occupancy, presence, sleep patterns and absence from home, and its service layer carries locks,
alarms and garage doors. The harm from a compromised integration is therefore not principally
financial: it is **surveillance of a household and physical access to it**, and both are
irreversible in a way that a fraudulent transaction is not. A door opened cannot be un-opened,
and a disclosure of when a house is empty cannot be withdrawn.

The social distribution of the risk is uneven in a way worth naming. The people best placed to
audit an integration's source are the technically expert minority; the people running the same
integrations are everyone else in the household, who did not install it and cannot read it. The
platform's own position — "users install them at their own risk" [4] — assigns the risk to the
installer, but the exposure is shared by every occupant.

**What this project changes socially** is narrow and should not be overstated: it converts
invisible authority into declared authority. A household member who cannot read Python can read
*"this integration may contact one host and read one sensor"*. That is a change in what can be
known, not a guarantee of safety.

## 4.2 Technological

Home Assistant is the largest open-source smart-home platform, with 4,220 community integrations
reporting through telemetry [1]. Its extension model — in-process import with an unscoped handle
— is a **structural** property, not a bug, and it is the same model browsers abandoned more than
fifteen years ago [12]. The technological significance of this work is that it demonstrates the
retrofit is possible at all: least-privilege confinement can be imposed on an ecosystem of
pre-existing, unmodifiable extensions, using kernel primitives available on commodity hardware,
without the platform's cooperation.

The project also produces a technological result that is not about security. Stripping the
platform to what an integration declares is not a compromise: the unconfined baseline loads a
median of **52 components** where the sandbox sets up **2**, and import-level compatibility is
identical. Whatever those other fifty components are for, loading a community integration is not
it.

**Technological risk to the work itself is real and measured.** The design couples to platform
internals — the resolver stack, one HTTP-client helper — and §12.6 records the first instance of
that coupling breaking under a real integration. A compatibility figure on this platform has a
shelf life, and the report says so.

## 4.3 Economic

The economics are what make the problem hard, and they are visible in Table 1.1. The **median
community integration has 20 installs** and 3,095 of 4,220 have fewer than 100. These are
single-author volunteer projects with no revenue, no security budget and no obligation. There is
no vendor to bear the cost of a rewrite, which is precisely why the browser solution — require
developers to migrate to a new manifest-based platform — is unavailable here. Any control that
imposes work on 4,220 volunteer authors will not be adopted.

The cost side is favourable and measured. The framework uses only the Python standard library and
`ctypes`; it requires no additional hardware, no cloud service and no licence. On the target
device the marginal cost of confining an integration is about **120 MB of memory**, and **26
sandboxes** fit in 60% of a 4 GB Raspberry Pi against a measured mean of **4.02** community
integrations per HACS-running installation — a margin of roughly 6×. Latency cost is 31.5 µs per
mediated request. The economic barrier to adoption is therefore not resource cost; it is
integration and maintenance effort in the platform project.

## 4.4 Environmental

The environmental footprint is small and it is worth stating why rather than claiming a benefit.
The whole system — platform, mediator and 26 confined integrations — runs inside 60% of a 4 GB
Raspberry Pi 5, a device drawing single-digit watts. Confinement adds no hardware: it uses kernel
facilities already present, and the design explicitly rejected the two stronger isolation
primitives (gVisor and microVMs) partly because each would have consumed the memory margin that
makes a single-board deployment viable.

A second-order environmental point is more genuine than the power figure: **self-hosted home
automation extends the useful life of connected devices** whose vendors have discontinued cloud
support, and community integrations are usually what makes that possible. A confinement scheme
that broke those integrations would push users back toward vendor clouds and device replacement.
That the measured compatibility cost of this design is zero is therefore an environmental result
as well as a technical one.

## 4.5 Political

Smart-home platforms sit inside an active regulatory conversation about the security of connected
consumer products, and the direction of travel in that conversation is toward placing obligations
on the *supplier* of a product rather than on its user. Home Assistant occupies an awkward
position in that framing: it is not a vendor, its integrations are not products, and its authors
are volunteers. A regime that assigned liability for integration behaviour to the platform
project would be unenforceable and would probably end the ecosystem.

This matters for how the contribution should be positioned. A mechanism that gives users a
technical means of bounding third-party code is a **better answer to that political pressure than
either liability or curation**, because it neither requires a vendor nor asks a volunteer project
to underwrite code it did not write.

> *[To verify before submission: the specific instrument to cite here is the EU Cyber Resilience
> Act and its treatment of open-source stewards. Currently unreferenced — this paragraph must
> either cite it or be rewritten to argue only from the platform's own stated position [10].]*

## 4.6 Legal

The data an integration can reach in a stock installation includes occupancy, presence and
behavioural patterns for identifiable individuals, and stored credentials for third-party
services. Under any modern data-protection regime this is personal data of a sensitive kind, and
today **any installed integration can read all of it with no record that it did**.

Two legal observations follow. First, the household deploying Home Assistant is generally outside
the scope of data-protection law by the domestic exemption — but the third-party integration
author receiving exfiltrated data is not. Second, and more useful to this project: **the absence
of an audit record is itself the legally significant gap.** Attribution is what makes any
subsequent claim possible, and the platform currently has none. The tamper-evident decision log
(S7) is the component with the clearest legal rationale, and the independent systematic review
[21] identifies precisely this absence: extensions "are free to perform actions without being
authenticated, reducing the ability to audit logs and locate malicious extensions".

## 4.7 Ethical

Three ethical positions were taken during this work and each is recorded rather than assumed.

**The adversary is purpose-built, not borrowed.** The 2021 disclosures name eight real
integrations at vulnerable versions. Those versions were **not** used. The adversarial integration
in this project reproduces the *pattern* — directory traversal toward `secrets.yaml`, the
published garbage-collector technique — against the author's own test installation, on the ground
that weaponising a disclosed vulnerability in named community projects would harm volunteer
authors without adding evidential value.

**Nothing was tested against anyone else's installation.** Every measurement ran on the author's
own hardware, and the one measurement involving a live third-party service (`nordpool` against a
public price API) used an ordinary unauthenticated public endpoint at ordinary polling rates.

**The disclosure position is that there is nothing to disclose.** This project found no
vulnerability in Home Assistant or in any community integration. It found a *structural* property
that the platform documents openly [10] and a defect in the author's own artifact. Where the
report identifies a change that would help — a scoped access token, §15.2 — it is framed as an
ask to the platform, not as a finding against it.
