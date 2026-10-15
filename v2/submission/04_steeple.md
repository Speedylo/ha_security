# 4. STEEPLE Analysis

The problem of Section 2 lies in software, but its causes and consequences extend beyond it. This section examines the project's context under seven headings, separating in each what the evaluation measured from what is presented as argument.

## 4.1 Social

The asset at risk is a household rather than a computer. The platform's entities record occupancy and the hours a house stands empty, and its actions open locks and garage doors [2], so the harm of a hostile integration is surveillance of a household and physical access to it, neither of which can be reversed. The platform assigns this risk to whoever installs an integration [4], yet every occupant is exposed, including those who neither chose it nor could read its code. The project's social contribution is correspondingly narrow: authority that was invisible becomes declared, and is shown in plain language in the platform's interface before an integration starts. A declaration makes the risk knowable; it does not make an integration safe.

## 4.2 Technological

Running integrations in the platform's own process with its full authority is a structural property of the platform, the model that browsers replaced with declared permissions while their extension platforms were still new [12]. The project shows that confinement can instead be retrofitted to an existing ecosystem, with kernel facilities present on commodity hardware and no change to the platform's code. The retrofit has its own technological risk, because the framework depends on platform internals: the first real integration run confined could not start the platform's recommended HTTP client [32] until the framework accommodated it. Every compatibility figure in this report therefore holds for the release measured, 2026.8.3, and may not hold for the next.

## 4.3 Economic

The economics of the ecosystem explain why the problem is hard. The median community integration has 20 installations, and 3,095 of 4,220 have fewer than 100 [1]. These are volunteer projects without revenue, so no vendor exists to fund a rewrite, and a control that demands work from thousands of authors will not be adopted; requirement C1 follows from this. The framework's own costs are low: it needs no additional hardware or licence, the reference device holds 17 to 43 sandboxes against a mean of 4.02 integrations per installation [1], and a mediated request takes 43 µs (Table 12.4). The barrier to adoption is therefore the effort of maintaining the framework alongside the platform, not resource cost.

## 4.4 Environmental

The environmental footprint is small because confinement adds no hardware. It uses kernel facilities the device already has, and gVisor and microVMs were rejected partly because their memory per sandbox would have exceeded what a single-board computer can spare (Section 9). A second consideration is argued rather than measured. Self-hosted automation can keep devices working after their vendors withdraw cloud support, often through community integrations, so a confinement scheme that broke those integrations could push households toward vendor clouds and replacement hardware. Confinement caused no import-level failure across 75 integrations (Section 12.2), so on this evidence it does not impose that cost.

## 4.5 Political

Regulation of connected products places obligations on those who supply them commercially, a framing that community integrations largely fall outside. The European Union's Cyber Resilience Act [53] applies to products made available in the course of a commercial activity, and its recital 18 states that providing free and open-source software that is not monetised is not such an activity. Organisations that support open-source software intended for commercial use become stewards with lighter duties (Article 24) and no exposure to fines (Article 64(10)). Most community integrations, written by individuals and not monetised, therefore appear to carry no obligation under the Act, and the risk stays with the user. A technical bound on an integration does not depend on that allocation, which is the political case for it.

## 4.6 Legal

An integration can reach sensitive personal data, and the platform records nothing of who reads it. The General Data Protection Regulation [54] exempts purely household processing (Article 2(2)(c)), which generally covers the household running the platform, but its recital 18 keeps in scope those who provide the means for such processing; whether an integration author does so is not resolved here. Either way, attribution is what makes a later claim possible, and the platform offers none: its user permissions do not apply to an integration's calls [52], so extensions "are free to perform actions without being authenticated, reducing the ability to audit logs and locate malicious extensions" [21]. The framework's decision record (requirement S7) is therefore the component with the clearest legal rationale.

## 4.7 Ethical

Three ethical positions governed the evaluation. First, the adversary was purpose-built: the 2021 disclosures name real integrations at vulnerable versions [4], [6], but the attacks reproduce their patterns against the project's own installation, because weaponising disclosed flaws in named volunteer projects would add harm without adding evidence. Second, nothing was tested against anyone else's system. Devices on the home network were simulated, and the six live services contacted were reached at the integrations' own polling rates, four through public endpoints and two with the author's own account. Third, nothing required disclosure: the project found no vulnerability in Home Assistant or any integration, only a structural property the platform documents [10] and defects in its own framework.
