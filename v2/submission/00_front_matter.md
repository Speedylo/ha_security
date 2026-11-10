# Confining Unmodified Community Integrations in Home Assistant

### A Declared-Authority Architecture and Its Measured Cost

**Younes Rahati**

| | |
|---|---|
| Degree and programme | *[to be supplied — handbook]* |
| Institution | *[to be supplied]* |
| Supervisor | *[to be supplied]* |
| Submitted | *[to be supplied]* |

---

## Abstract

Home Assistant, an open-source home-automation platform with 669,743 reporting installations, runs community integrations inside its own process with the platform's full authority, so an integration installed to show electricity prices can also read the household's stored passwords and see when the house is empty. This project designed, built and evaluated a framework that confines each integration in a sandbox of its own, without changing the integration or the platform. What an integration may do is declared before it is installed, approved by a person in Home Assistant's interface, enforced while it runs and recorded each time it is used. Every test was run on a Raspberry Pi 5 with the same integration both confined and unconfined, so that any difference comes from the framework. The published attacks that motivated the project succeeded unconfined and found nothing confined. Across 75 real community integrations, confinement caused none of the failures to load, fifteen named integrations worked end to end, and the framework now represents the device kinds of 36 of the 37 most-installed integrations in the household's installation. The device holds at least 17 sandboxes, about four times what the average installation needs. The results are bounded by attacks written within the project, permission declarations written by the project and a single release of Home Assistant on one device.

**Keywords:** Home Assistant; Internet of Things; smart home; smart-home gateways; extension sandboxing; least privilege; cybersecurity.

## Résumé

Home Assistant, une plateforme domotique open source comptant 669 743 installations déclarées, exécute les intégrations communautaires dans son propre processus, avec l'autorité complète de la plateforme : une intégration installée pour afficher le prix de l'électricité peut aussi lire les mots de passe enregistrés du foyer et savoir quand la maison est vide. Ce projet a conçu, réalisé et évalué un cadre logiciel qui confine chaque intégration dans son propre bac à sable, sans modifier ni l'intégration ni la plateforme. Ce qu'une intégration peut faire est déclaré avant son installation, approuvé par une personne dans l'interface de Home Assistant, appliqué pendant son exécution et enregistré à chaque utilisation. Chaque test a été réalisé sur un Raspberry Pi 5, avec la même intégration confinée puis non confinée, afin que toute différence provienne du cadre. Les attaques publiées à l'origine du projet ont réussi sans confinement et n'ont rien trouvé avec. Sur 75 intégrations communautaires réelles, le confinement n'a causé aucun des échecs de chargement, quinze intégrations nommées ont fonctionné de bout en bout, et le cadre représente désormais, dans l'installation du foyer, les types d'appareils de 36 des 37 intégrations les plus installées. L'appareil accueille au moins 17 bacs à sable, soit environ quatre fois ce dont l'installation moyenne a besoin. Ces résultats sont limités par des attaques écrites au sein du projet, des déclarations de permissions rédigées par le projet et une seule version de Home Assistant sur un seul appareil.

**Mots-clés :** Home Assistant ; Internet des objets ; maison intelligente ; passerelles domotiques ; confinement des extensions ; moindre privilège ; cybersécurité.

---

## Acknowledgements

*[To be supplied.]*

## Declaration

*[Wording to be supplied from the programme handbook.]* The factual content it will need:

- The design, implementation, measurements and text of this report are the author's own work. Sources are cited at every use and listed in the References.
- An earlier two-week feasibility study by the same author preceded this project. Nothing learned in it is relied on here unless it was established again within this project.
- Generative AI was used as a working tool throughout, for writing code, drafting prose and reviewing arguments. Every measurement reported here was run on the reference device, and every figure can be reproduced from the scripts and result files in the repository (Appendix A).

## Contents

*[Generated at typeset time.]*

## List of Figures

*[Generated at typeset time.]*

## List of Tables

*[Generated at typeset time.]*

## Abbreviations and identifiers

| | |
|---|---|
| **Arm** | One of two paired runs of the same integration, on the same device and platform release: confined (in the framework) or unconfined (as Home Assistant runs it today) |
| **Community Store** | The Home Assistant Community Store (HACS), the usual channel for installing community integrations |
| **Integration** | A Python module that connects Home Assistant to a device or service and runs inside its process. Distinct from an add-on, which runs in its own container |
| **Manifest** | The `manifest.json` file every integration ships. This framework adds a `permissions` block to it, which states what the integration may do |
| **Mediator** | The separate process that holds the platform credential and decides every request a confined integration makes |
| **Sandbox** | The confined environment of one integration: its own Linux namespaces, a system-call filter and a control group |
| **Release** | Home Assistant 2026.8.3, the platform version used throughout |
| **F1–F4, S1–S9, C1–C4, N1–N3** | Functional, security, constraint and non-functional requirements (Section 3, Appendix B) |
| **T01–T19, R1–R7** | Threats and residual risks of the threat model (Section 8, Appendix C) |
| **F01–F63** | Findings of the verification campaign, written with two digits to distinguish them from requirements (Appendix F) |
| **M01–M50** | Deliberate defects (mutants) used to test whether the test suites detect a removed check (Section 12.4) |
