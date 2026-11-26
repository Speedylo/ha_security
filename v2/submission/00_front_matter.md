# Confining Unmodified Community Integrations in Home Assistant

### A Declared-Authority Architecture and Its Measured Cost

**Younes Rahati**

The title page, the student statement and the supervisor's approval come from the programme's template, which `build_final.py` fills.

## Abstract

Home Assistant, an open-source home-automation platform with 669,743 reporting installations, runs community integrations inside its own process with the platform's full authority, so an integration installed to show electricity prices can also read the household's stored passwords and see when the house is empty. This project designed, built and evaluated a framework that confines each integration in a sandbox of its own, without changing the integration or the platform. What an integration may do is declared before it is installed, approved by a person in Home Assistant's interface, enforced while it runs and recorded each time it is used. Every test was run on a Raspberry Pi 5 with the same integration both confined and unconfined, so that any difference comes from the framework. The published attacks that motivated the project succeeded unconfined and found nothing confined. Across 75 real community integrations, confinement caused none of the failures to load, fifteen named integrations worked end to end, and the framework now represents the device kinds of 36 of the 37 most-installed integrations in the household's installation. The device holds at least 17 sandboxes, about four times what the average installation needs. The results are bounded by attacks written within the project, permission declarations written by the project and a single release of Home Assistant on one device.

**Keywords:** Home Assistant; Internet of Things; smart home; smart-home gateways; extension sandboxing; least privilege; cybersecurity.

## Résumé

Home Assistant, une plateforme domotique open source comptant 669 743 installations déclarées, exécute les intégrations communautaires dans son propre processus, avec l'autorité complète de la plateforme : une intégration installée pour afficher le prix de l'électricité peut aussi lire les mots de passe enregistrés du foyer et savoir quand la maison est vide. Ce projet a conçu, réalisé et évalué un cadre logiciel qui confine chaque intégration dans son propre bac à sable, sans modifier ni l'intégration ni la plateforme. Ce qu'une intégration peut faire est déclaré avant son installation, approuvé par une personne dans l'interface de Home Assistant, appliqué pendant son exécution et enregistré à chaque utilisation. Chaque test a été réalisé sur un Raspberry Pi 5, avec la même intégration confinée puis non confinée, afin que toute différence provienne du cadre. Les attaques publiées à l'origine du projet ont réussi sans confinement et n'ont rien trouvé avec. Sur 75 intégrations communautaires réelles, le confinement n'a causé aucun des échecs de chargement, quinze intégrations nommées ont fonctionné de bout en bout, et le cadre représente désormais, dans l'installation du foyer, les types d'appareils de 36 des 37 intégrations les plus installées. L'appareil accueille au moins 17 bacs à sable, soit environ quatre fois ce dont l'installation moyenne a besoin. Ces résultats sont limités par des attaques écrites au sein du projet, des déclarations de permissions rédigées par le projet et une seule version de Home Assistant sur un seul appareil.

**Mots-clés :** Home Assistant ; Internet des objets ; maison intelligente ; passerelles domotiques ; confinement des extensions ; moindre privilège ; cybersécurité.

---

## AI Evidence Box

**AI tool or agent.** Claude Code (Anthropic), running Claude Opus models: an agent that works in the project's repository on my laptop and, over SSH, on the Raspberry Pi, guided by persistent instruction files and an academic-writing skill.

**Task assigned.** The communication agent for this report: drafting each section from the project's records after comparing it with past capstone reports; editing, cutting and reorganising the text and appendices; enlarging the text in the figures; building the report in the programme's template; and checking its figures and claims against the raw results.

**Representative instructions.** Standing rules: third person except the AI material and Section 14, APA 7, "community integrations", and every section compared with past reports and approved before the next. Session instructions such as "drop 10.5", "across 77 or 75 integrations?" and "recheck the whole report".

**Output produced.** The sixteen sections, the abstract and French résumé, Appendices A to H, the script that builds the report, a script that recomputes 25 headline figures from the raw result files, and the enlarged figures.

**How the output was checked.** I read and approved every section before the next was started, including the French résumé. The number check found all 25 figures equal to their raw records and caught two errors planted to test it. At my request the AI read the whole report eight times, the later passes tracing each table to its result file or test code. Every reference was checked against its source.

**Accepted, modified or rejected.** Writing this report added 32 entries to the AI-use log (rows 41 to 72). I caught 13, among them "77" integrations where 75 were measured, "the same record" used before any record was introduced, and a paragraph, two subsections and a sentence I rejected. The AI's own checks caught 19, among them an attack reported as reading another process's environment when the test only lists the other processes, and an overclaim about single-board computers that I had corrected in one section but that survived in two others. I chose which appendices to cut and kept the threat model whole. Appendix H records every correction.

**Ethical, confidentiality and reliability considerations.** No personal data was given to the tool; credentials stayed on the Pi, and every push was preceded by a scan for them. The AI's recurring failure was overstatement and text carried over from earlier drafts, which my approval of a section did not always catch, so checks that do not depend on my attention, the number check and the read-throughs, were added. Section 13 and Appendices G and H disclose the AI's role. This box was drafted by the AI and checked by me, and I remain responsible for the whole report.

## Acknowledgements

I would like to thank my supervisor for the guidance and feedback given throughout this project. I am grateful to my family and friends for their support and patience during the months this work took. I also thank the developers and contributors of Home Assistant and its community integrations, whose open-source work this project builds on.

## Abbreviations and identifiers

| | |
|---|---|
| **Arm** | One of two paired runs of the same integration, on the same device and platform release: confined (in the framework) or unconfined (as Home Assistant runs it today) |
| **Community Store** | The Home Assistant Community Store (HACS), the usual channel for installing community integrations; part of the platform, as the Marketplace, from version 2026.11 |
| **Integration** | A Python module that connects Home Assistant to a device or service and runs inside its process. Distinct from an add-on, which runs in its own container |
| **Manifest** | The `manifest.json` file every integration ships. This framework adds a `permissions` block to it, which states what the integration may do |
| **Mediator** | The separate process that holds the platform credential and decides every request a confined integration makes |
| **Sandbox** | The confined environment of one integration: its own Linux namespaces, a system-call filter and a control group |
| **Release** | Home Assistant 2026.8.3, the platform version used throughout |
| **F1–F4, S1–S9, C1–C4, N1–N3** | Functional, security, constraint and non-functional requirements (Section 3, Appendix B) |
| **T01–T19, R1–R7** | Threats and residual risks of the threat model (Section 8, Appendix C) |
| **F01–F76** | Findings of the verification work, written with two digits to distinguish them from requirements (summarised in Appendix D; listed in the repository) |
| **M01–M88** | Deliberate defects (mutants), 92 in all, used to test whether the test suites detect a removed check (Section 12.4) |
