# References

Numbered in **order of first appearance across the whole report**. Chapters 1 and 2 each carried an
independent list until 2026-09-04 and the two schemes collided: `[3]` was the 2021 Home Assistant
disclosure in Chapter 1 and FlowFence in Chapter 2. Both chapters' inline markers were remapped to
this list; neither chapter's text was otherwise touched.

**Twenty-eight sources, and four of them were not in either chapter's list.** *(Twenty-nine since
2026-10-05: [29] was added with §7.44.)* ISO 31000, STRIDE and
OWASP Threat Dragon are Chapter 4's own methodological foundations — the chapter follows ISO
31000's clause structure section by section and names the clause it discharges each time — and none
of the three had a bibliography entry anywhere in the report. RFC 1918 is normative for what
`is_public` refuses (§7.25.2). They are entries [25]–[28] and each now carries an inline marker at
first use.

**One source was dropped, and this is the record of it.** Chapter 2's former `[15]` — L. Mannella,
*Supporting Developers in the Cybersecurity of IoT Systems*, PhD Day research summary, Politecnico
di Torino, 2022 — was listed and **never cited in the body**. A reference list is a record of what
the argument used, so it is removed rather than carried; the line of work it summarises is
represented by [20], the completed thesis, which §2.4 does cite and which was read in full.

---

## Platform and ecosystem

**[1]** Home Assistant, *Analytics*. https://analytics.home-assistant.io/ — 669,743 active
installations; retrieved 21 August 2026. Per-domain custom-integration install counts from
https://analytics.home-assistant.io/custom_integrations.json, same date.

**[2]** Home Assistant, Developer Documentation: *Creating your first integration*
(https://developers.home-assistant.io/docs/creating_component_index/) and *Service actions*
(https://developers.home-assistant.io/docs/dev_101_services/). The latter documents registration
and invocation of service actions and specifies no permission model, scoping rule or caller check.

**[3]** Home Assistant, *Add-ons* (apps), Developer Documentation.
https://developers.home-assistant.io/docs/add-ons

**[5]** HACS, *Include default repositories*. https://hacs.xyz/docs/publish/include/

**[10]** Home Assistant, *Security*. https://www.home-assistant.io/security/

**[11]** T. Cohen (titilambert), *Remote Integration Execution*, Home Assistant Community RFC,
12 May 2026. https://community.home-assistant.io/t/remote-integration-execution/1010130

## Disclosures and incidents

**[4]** Home Assistant, *Disclosure: security vulnerabilities in custom integrations HACS, Dwains
Dashboard, Font Awesome and others*, 22 January 2021.
https://www.home-assistant.io/blog/2021/01/22/security-disclosure/

**[6]** Home Assistant, *Security Disclosure 2: vulnerabilities in custom integrations HACS, Font
Awesome and others*, 23 January 2021.
https://www.home-assistant.io/blog/2021/01/23/security-disclosure2/

**[7]** elttam, *PwnAssistant — Controlling /home's via a Home Assistant RCE* (CVE-2023-27482).
https://www.elttam.com/blog/pwnassistant

**[8]** *XZ Utils backdoor* (CVE-2024-3094), March 2024. Backdoor introduced by a contributor who
had acquired maintainer trust over approximately two years; discovered by A. Freund while
investigating an SSH latency regression rather than through code review.
https://en.wikipedia.org/wiki/XZ_Utils_backdoor — see also
https://www.rapid7.com/blog/post/2024/04/01/etr-backdoored-xz-utils-cve-2024-3094/

**[22]** GitHub Security Lab, *Securing our home labs: Home Assistant code review*.
https://github.blog/security/vulnerability-research/securing-our-home-labs-home-assistant-code-review/

## Extensible smart-home gateways — the closest prior art

**[9]** F. Corno and L. Mannella, "A Threat Model for Extensible Smart Home Gateways",
*7th International Conference on Smart and Sustainable Technologies (SpliTech)*, 2022.
https://iris.polito.it/handle/11583/2963822

**[18]** F. Corno and L. Mannella, "A Gateway-based MUD Architecture to Enhance Smart Home
Security", 2023.

**[20]** L. Mannella, *Securing IoT Gateways in Smart Home Environments*, PhD thesis, Politecnico
di Torino, 2024.

**[21]** T. R. Thingnes and P. H. Meland, "Security Challenges for Users of Extensible Smart Home
Hubs: A Systematic Literature Review", *Future Internet*, 17(6):238, 2025.
https://doi.org/10.3390/fi17060238

## Extension and application permission models

**[12]** A. Barth, A. P. Felt, P. Saxena and A. Boodman, "Protecting Browsers from Extension
Vulnerabilities", *NDSS*, 2010.
https://www.adambarth.com/papers/2010/barth-felt-saxena-boodman.pdf

**[13]** E. Fernandes, J. Jung and A. Prakash, "Security Analysis of Emerging Smart Home
Applications", *37th IEEE Symposium on Security and Privacy*, 2016.

**[14]** E. Fernandes, J. Paupore, A. Rahmati, D. Simionato, M. Conti and A. Prakash, "FlowFence:
Practical Data Protection for Emerging IoT Application Frameworks", *USENIX Security*, 2016.

**[15]** Y. Jia, Q. A. Chen, S. Wang, A. Rahmati, E. Fernandes, Z. M. Mao and A. Prakash,
"ContexIoT: Towards Providing Contextual Integrity to Appified IoT Platforms", *NDSS*, 2017.

**[16]** Y. Tian, N. Zhang, Y.-H. Lin, X. Wang, B. Ur, X. Guo and P. Tague, "SmartAuth:
User-Centered Authorization for the Internet of Things", *USENIX Security*, 2017.

**[17]** A. Rahmati, E. Fernandes, K. Eykholt and A. Prakash, "Tyche: A Risk-Based Permission Model
for Smart Homes", *IEEE Secure Development Conference (SecDev)*, 2018.
DOI 10.1109/SECDEV.2018.00012. Preprint: arXiv:1801.04609.

**[24]** Z. Li, K. Li, B. Ma, M. Xu, Y. Zhang and X. Cheng, "We Urgently Need Privilege Management
in MCP: A Measurement of API Usage in MCP Ecosystems", arXiv:2507.06250, 2025.

## Supply chain

**[23]** P. Ladisa, H. Plate, M. Martínez and O. Barais, "SoK: Taxonomy of Attacks on Open-Source
Software Supply Chains", *IEEE Symposium on Security and Privacy*, 2023.

## Standards and methodology

**[19]** E. Lear, R. Droms and D. Romascanu, "Manufacturer Usage Description Specification",
RFC 8520, IETF, March 2019. https://www.rfc-editor.org/rfc/rfc8520

**[25]** ISO, *ISO 31000:2018 — Risk management — Guidelines*, International Organization for
Standardization, 2018. https://www.iso.org/standard/65694.html — the clause numbers Chapter 4
discharges section by section (§6.3.2 scope and assets, §6.3.3 context, §6.3.4 risk criteria,
§6.4.2 risk identification) are this edition's.

**[26]** A. Shostack, *Threat Modeling: Designing for Security*, Wiley, 2014. The systematic
treatment of STRIDE this chapter applies per trust boundary. The acronym originates with
L. Kohnfelder and P. Garg, *The Threats to Our Products*, Microsoft, 1999.

**[27]** OWASP, *Threat Dragon*. https://owasp.org/www-project-threat-dragon/ — the model format
`figures/fig_4_1_current_state.py` emits, from which Figures 4.1 and 5.1 are generated.

**[28]** Y. Rekhter, B. Moskowitz, D. Karrenberg, G. J. de Groot and E. Lear, "Address Allocation
for Private Internets", BCP 5, RFC 1918, IETF, February 1996.
https://www.rfc-editor.org/rfc/rfc1918

## Audit systems

**[29]** P. Jiang, R. Huang, D. Li, Y. Guo, X. Chen, J. Luan, Y. Ren and X. Hu, "Auditing Frameworks
Need Resource Isolation: A Systematic Study on the Super Producer Threat to System Auditing and Its
Mitigation", *32nd USENIX Security Symposium*, 2023. arXiv:2307.15895. Cited in §7.44.1 for the
threat Chapter 4 now carries as T19. *(Added 2026-10-05; authors, title and venue checked against the
arXiv record.)*

---

## Verification status

Four PDFs are held locally in `v2/refs/` and were read in full: [9], [18], [20] and [21].
`00_METHOD.md` §2's evidence rule applies to what they say, and §2.4 is written from the papers
rather than from their abstracts.

**Bibliographic detail not yet verified against the source itself**, and owed to the Stage 5 pass:
[18]'s venue and DOI (the PDF is held but the entry carries a year only), [26]'s ISBN and the
Kohnfelder & Garg attribution, and [25]'s clause numbering against the published 2018 edition
rather than against the chapter's use of it. Every other entry's identifiers are either a URL that
resolves or were transcribed from the chapters that cited them.
