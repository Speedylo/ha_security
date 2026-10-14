# References

Numbered in **order of first appearance across the whole report**. Chapters 1 and 2 each carried an
independent list until 2026-09-04 and the two schemes collided: `[3]` was the 2021 Home Assistant
disclosure in Chapter 1 and FlowFence in Chapter 2. Both chapters' inline markers were remapped to
this list; neither chapter's text was otherwise touched.

**Twenty-eight sources, and four of them were not in either chapter's list.** ISO 31000, STRIDE and
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

**[8]** P. Przymus and T. Durieux, "Wolves in the Repository: A Software Engineering Analysis of the
XZ Utils Supply Chain Attack", in *Proc. 2025 IEEE/ACM 22nd Int. Conf. Mining Software Repositories
(MSR)*, Ottawa, ON, Canada, 2025, pp. 91–102. doi:10.1109/MSR66628.2025.00026 — §III-B gives the
attacker's involvement as 2.6 years (2021-10-29 to 2024-03-28). *(Replaced the Wikipedia source
2026-10-11; checked against Crossref 2026-10-12.)*

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

## Added in the rewrite (2026-10-12)

Entries [30]–[51] are cited by Sections 8, 9, 11 and 12. Their numbers are provisional and follow the
working report's; the list is renumbered by first appearance in week 5. [29] (Jiang et al., USENIX
Security 2023) is in the working report's list but is not cited in the submission, so it is not
carried here.

### Audit standards

**[30]** Common Criteria Recognition Arrangement, *Common Criteria for Information Technology
Security Evaluation, Part 2: Security functional components*, version 3.1 revision 5,
CCMB-2017-04-002, April 2017. Component FAU_STG.4, *Prevention of audit data loss*.
https://www.commoncriteriaportal.org/files/ccfiles/CCPART2V3.1R5.pdf

**[31]** Joint Task Force, *Security and Privacy Controls for Information Systems and
Organizations*, NIST Special Publication 800-53 Revision 5, National Institute of Standards and
Technology, September 2020. doi:10.6028/NIST.SP.800-53r5. Control AU-5, *Response to Audit Logging
Process Failures*, and its enhancement AU-5(4), *Shutdown on Failure*.

### Platform (continued)

**[32]** Home Assistant, Developer Documentation: Integration Quality Scale rule *The integration
dependency supports passing in a websession*.
https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/inject-websession
— recommends `async_get_clientsession(hass)`; opened 2026-10-08.

**[42]** Home Assistant, Developer Documentation: *Config entries*.
https://developers.home-assistant.io/docs/config_entries_index — entries are persistently stored
and set up during startup; checked 2026-10-11.

**[43]** Home Assistant, Developer Documentation: *Repairs*.
https://developers.home-assistant.io/docs/core/platform/repairs — issues are brought to the
user's attention, and a `RepairsFlow` fixes them; checked 2026-10-11.

**[44]** Home Assistant Core 2026.8.3, `homeassistant/components/repairs/websocket_api.py`.
https://github.com/home-assistant/core — `require_admin(permission=POLICY_EDIT)` on both fix
endpoints. The documentation says nothing about administrators, so the source is the evidence.

### Linux kernel interfaces

**[33]** Linux man-pages project, *namespaces(7)*. https://man7.org/linux/man-pages/man7/namespaces.7.html

**[34]** Linux man-pages project, *seccomp(2)*. https://man7.org/linux/man-pages/man2/seccomp.2.html

**[35]** The Linux kernel documentation, *Control Group v2*.
https://docs.kernel.org/admin-guide/cgroup-v2.html — also carries the common-ancestor rule for
moving processes between control groups (stated as well in *cgroups(7)*).

**[36]** Linux man-pages project, *unix(7)*. https://man7.org/linux/man-pages/man7/unix.7.html —
socket pairs and `SCM_RIGHTS`.

**[37]** Linux man-pages project, *chroot(2)*. https://man7.org/linux/man-pages/man2/chroot.2.html
— not intended as a security mechanism; the `mkdir foo; chroot foo; cd ..` escape.

**[38]** Linux man-pages project, *pivot_root(2)*.
https://man7.org/linux/man-pages/man2/pivot_root.2.html

**[39]** Linux man-pages project, *user_namespaces(7)*.
https://man7.org/linux/man-pages/man7/user_namespaces.7.html — a process in a new user namespace
holds the full set of capabilities inside it.

**[48]** systemd, `units/user@.service.in`. https://github.com/systemd/systemd — the line
`Delegate=pids memory cpu`; checked 2026-10-11.

### Network and protocols

**[40]** C. Jackson, A. Barth, A. Bortz, W. Shao and D. Boneh, "Protecting Browsers from DNS
Rebinding Attacks", in *Proc. 14th ACM Conf. Computer and Communications Security (CCS)*, 2007,
pp. 421–431. doi:10.1145/1315245.1315298 *(Checked against Crossref 2026-10-12.)*

**[41]** J. Weil, V. Kuarsingh, C. Donley, C. Liljenstolpe and M. Azinger, "IANA-Reserved IPv4
Prefix for Shared Address Space", BCP 153, RFC 6598, IETF, April 2012.
https://www.rfc-editor.org/rfc/rfc6598

**[45]** D. Hardt, Ed., "The OAuth 2.0 Authorization Framework", RFC 6749, IETF, October 2012.
https://www.rfc-editor.org/rfc/rfc6749 — §4.1 step (A).

**[47]** E. Rescorla, "The Transport Layer Security (TLS) Protocol Version 1.3", RFC 8446, IETF,
August 2018. https://www.rfc-editor.org/rfc/rfc8446 — §1.

### Testing

**[46]** Y. Jia and M. Harman, "An Analysis and Survey of the Development of Mutation Testing",
*IEEE Transactions on Software Engineering*, vol. 37, no. 5, pp. 649–678, September 2011.
doi:10.1109/TSE.2010.62 *(Checked against Crossref 2026-10-12.)*

### Measurement and statistics

**[49]** The Linux kernel documentation, *The /proc Filesystem*, §1.1, `/proc/PID/smaps`.
https://docs.kernel.org/filesystems/proc.html — the proportional set size is "the count of pages it
has in memory, where each page is divided by the number of processes sharing it"; checked 2026-10-12.

**[50]** B. Efron, "Bootstrap Methods: Another Look at the Jackknife", *The Annals of Statistics*,
vol. 7, no. 1, pp. 1–26, 1979. doi:10.1214/aos/1176344552 *(Checked against Crossref 2026-10-12.)*

### Method

**[51]** K. R. Popper, *The Logic of Scientific Discovery*. London, U.K.: Hutchinson, 1959. English
translation of *Logik der Forschung*, Vienna: Springer, 1934 (dated 1935). Falsifiability as the
criterion of demarcation and the methodological rule against saving a theory by ad hoc adjustment:
Part I, ch. 4 ("Falsifiability"). Publisher and year checked against the Open Library record
2026-10-12. Cited in §8.1 and §11.1; to cite in §6 and §13 when they are rewritten.

### Platform source

**[52]** Home Assistant Core 2026.8.3, `homeassistant/core.py` (`ServiceRegistry.async_call`: a call
made without a context receives `Context()`, whose `user_id` is `None`, line 2881) and
`homeassistant/helpers/service.py` (`verify_domain_control`: the permission check returns early when
the call's context names no user, line 1027). https://github.com/home-assistant/core/tree/2026.8.3 —
checked against the pinned source 2026-10-14. Cited in §2.3.

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
