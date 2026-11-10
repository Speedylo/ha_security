# 4. STEEPLE Analysis

The risk this project addresses lies in software, but its causes and consequences reach beyond it. This section examines the project's setting under seven headings and states, for each, what the framework changes and where its effect stops.

## 4.1 Social

What is at risk is a household rather than a computer. A smart home's devices record when a house is occupied and when it stands empty, and they open locks and garage doors, so a hostile integration can watch a family or let someone in, and neither harm can be undone. Everyone in the home is exposed, including people who never chose the integration. The framework makes what an integration may do visible, in plain language, before it starts. That makes the risk knowable; it does not make the integration safe.

## 4.2 Technological

The technological problem is that every integration runs inside the platform with all of its authority. Web browsers avoided the same problem by requiring a permission model while their extension platforms were still new (Barth et al., 2010). Home Assistant cannot, because thousands of integrations already exist, so confinement has to be added afterwards. The project shows that this is possible with isolation features already in the Linux kernel, without changing any integration or the platform. Because it relies on the platform's internals, however, it must be rechecked with each new platform release.

## 4.3 Economic

Most community integrations are small volunteer projects: the median one has 20 installations (Home Assistant, n.d.-d), and no revenue pays for a rewrite. A control that asked authors to change their code would not be adopted, so the framework leaves the code as it is. The cost moves to the household's device, where it is small, and to writing a permissions manifest for each integration, which is the main effort adoption would require.

## 4.4 Environmental

A self-hosted platform can keep a device working after its maker closes the online service it depends on, often through a community integration, which keeps hardware out of landfill; this benefit is argued here, not measured. A security measure could undo it by requiring new hardware or by breaking the integrations that keep old devices in use. The framework does neither: it runs on the same device as the platform, and it caused no integration in the evaluation to stop loading.

## 4.5 Political

Responsibility for what a community integration does falls between the parties that might carry it. The platform declines it (Home Assistant, 2021a). The European Cyber Resilience Act places its duties on commercial suppliers and states that providing non-monetised open-source software is not a commercial activity (Regulation (EU) 2024/2847, 2024, recital 18). The volunteer authors have neither the obligation nor the means. The risk therefore stays with the household, which until now had no means to act on it. The framework gives the household a bound that holds whoever is eventually made responsible.

## 4.6 Legal

Where the law imposes a duty, it assumes evidence that a standard installation cannot produce. Since 11 September 2026, a manufacturer has had to report an actively exploited vulnerability in its product within 24 hours of becoming aware of it (Regulation (EU) 2024/2847, 2024, Article 14). Knowing what was exploited requires knowing what an integration did. The platform records changes to devices but not what an integration read, and an integration's actions carry no user (Home Assistant, 2026), which a review of the literature found reduces the ability to audit logs and locate malicious extensions (Thingnes & Meland, 2025). The framework records every request an integration makes, allowed or refused, before acting on it, so a household can show what an integration accessed.

## 4.7 Ethical

The central ethical question is who controls information about the people in a home. One person approves an integration for the whole household, and such approval is weak even on one's own behalf: in one study of phone users, only 17% paid attention to an app's permissions when installing it (Felt et al., 2012). The framework limits each integration to the devices it declared and the hosts it named, and records each access. Its control is partial. It decides where data may go but cannot see what is sent to an allowed host, and without a study of users there is no evidence that the person who approves a grant understands it.
