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

Responsibility for what a community integration does is assigned to no party able to carry it. The platform disclaims it, leaving the risk with the user [4], [10]. Regulation assigns duties to commercial suppliers: the Cyber Resilience Act [53] covers products made available in the course of a commercial activity, and its recital 18 states that providing non-monetised open-source software is not one, while organisations that support such software carry lighter duties (Article 24) and no fines (Article 64(10)). The volunteer authors have neither the obligation nor, at a median of 20 installations [1], the means. One question remains open: the platform's own hardware is designed by a company associated with the project [55], so the platform may itself be a product under the Act, and whether that would reach integrations a user adds is not resolved here. A technical bound holds whoever is eventually made to answer.

## 4.6 Legal

Where the law imposes a duty, it presupposes evidence that a stock installation cannot produce. Since 11 September 2026, Article 14 of the Cyber Resilience Act has required a manufacturer to report an actively exploited vulnerability in its product within 24 hours of becoming aware of it [53]. Becoming aware requires knowing what was exploited, yet an integration's calls carry no user and pass no permission check [52], so extensions "are free to perform actions without being authenticated, reducing the ability to audit logs and locate malicious extensions" [21]. No household, author or manufacturer can show what an integration accessed. The framework's decision record (requirement S7) supplies that evidence: each request, granted or refused, is recorded with the integration and the clause that decided it, on disk before the action is taken.

## 4.7 Ethical

Three ethical positions governed the evaluation. First, the adversary was purpose-built: the 2021 disclosures name real integrations at vulnerable versions [4], [6], but the attacks reproduce their patterns against the project's own installation, because weaponising disclosed flaws in named volunteer projects would add harm without adding evidence. Second, nothing was tested against anyone else's system. Devices on the home network were simulated, and the six live services contacted were reached at the integrations' own polling rates, four through public endpoints and two with the author's own account. Third, nothing required disclosure: the project found no vulnerability in Home Assistant or any integration, only a structural property the platform documents [10] and defects in its own framework.
