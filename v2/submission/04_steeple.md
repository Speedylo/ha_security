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

Responsibility for what a community integration does falls between the parties that might carry it. The platform disclaims it [10]. Regulation might be expected to fill that gap, but the Cyber Resilience Act [53] places its duties on commercial suppliers, and its recital 18 states that providing non-monetised open-source software is not a commercial activity. The authors, volunteers whose median integration has 20 installations [1], have neither the obligation nor the means. The risk therefore rests with the user, the one party with no means to act on it [4]. The project's contribution is to give the user that means without waiting for the question to be settled: a bound that is declared, enforced and recorded holds whoever is eventually made responsible. That allocation may yet change, since the platform's own hardware is designed by a company associated with the project [55], and a platform held responsible would need exactly such a bound.

## 4.6 Legal

Where the law imposes a duty, it presupposes evidence that a stock installation cannot produce. Since 11 September 2026, Article 14 of the Cyber Resilience Act has required a manufacturer to report an actively exploited vulnerability in its product within 24 hours of becoming aware of it [53]. Becoming aware requires knowing what was exploited, yet an integration's calls carry no user and pass no permission check [52], so extensions "are free to perform actions without being authenticated, reducing the ability to audit logs and locate malicious extensions" [21]. No household, author or manufacturer can show what an integration accessed. The framework's decision record (requirement S7) supplies that evidence: each request, granted or refused, is recorded with the integration and the clause that decided it, on disk before the action is taken.

## 4.7 Ethical

The evaluation raised few ethical questions, because it was confined to the project's own systems. The attacks reproduce the patterns of the 2021 disclosures [4], [6] in a purpose-built integration rather than the named projects' vulnerable versions, devices on the home network were simulated, and live services were reached only at the integrations' own polling rates.

The framework raises a harder question, because it asks a person to consent. An integration starts only once someone approves its grant, and an over-broad grant that is approved is honoured (T13, retained). Such consent is weak in practice: of Android users shown install-time permissions, 17% paid attention to them and only 3% of those surveyed answered all three comprehension questions correctly [56]. The approval screen was designed with that in mind, stating what the integration cannot do at the same weight as what it can, marking a grant its author did not write, and asking again whenever the code or the grant changes. No user study was run, however, so the framework makes the risk visible without showing that the person approving has understood it.
