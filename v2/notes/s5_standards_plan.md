# §5 Engineering Standards — plan and decisions (2026-10-15)

Budget 900 words, 3 pp; drafted at 911 prose words. Skill loaded before drafting. Rebuilt from the
approved §8 and §9, the code and the working report, with the 2026-09-08 draft as a skeleton only.
Each subsection: what the standard requires → how the project meets it → its limit (the pattern Younes
accepted for §4).

**Sources checked:**
- ETSI EN 303 645 V3.1.3 (2024-09) read in the PDF: scope lists "connected home automation and alarm
  systems, especially their gateways and hubs"; Provision 5.6-7 least privilege. New reference [57].
- NIST SP 800-53 AC-6 (least privilege, processes acting on behalf of users) — same document as [31];
  wording seen on mirrors only.
- FAU_STG.4 and AU-5: as read in their primary texts on 2026-10-06 (report §7.44, finding F40):
  neither *prefers* stopping; both recognise it. §5.3 is worded to that reading, not the old one.
- Seccomp: `framework/confine/seccomp.py` — 29 calls in `DENIED_BY_REASON`, `SECCOMP_RET_ERRNO` (EPERM).
- A failed audit write stops the mediator: `mediator.py` comment on `REQUEST_ERRORS` ("no record, no
  decision", F28).
- Memory controller: `REPRODUCE.md` §1 (`cgroup_disable=memory`); `io` not delegated [48].

**Stale or changed against the old draft:** §-pointers to the working report (§6.3.2 …, §7.3.2, §13.3,
§9.4) removed; "eighteen threats" gone; ISO/IEC 27001 moved to "considered, not applied" (an
organisation's ISMS; its Annex A control numbers were never verified); OWASP Secure Coding Practices
dropped (no reference entry, principles now carried by EN 303 645 and AC-6); RFC 6598 added after F58;
the mediator's non-admin user (F45) added as least privilege applied to the framework itself;
ISO/IEC 27400 dropped (not checked).

**For Younes:**
1. EN 303 645 is new to the report. It is the strongest standard anchor found (it names hubs in its
   scope), and it is applied only for 5.6-7; the rest of it is set aside in §5.6 as the manufacturer's.
2. ISO/IEC 27001 is no longer "applied". Examiners often expect it; keeping it as applied would need
   the 2022 Annex A control numbers checked against the standard, which is paywalled.

**Revised 2026-10-15 after Younes's review:** §5.5 (kernel interfaces, "not standards") and §5.6
(not applied, "not that important") dropped; intro now promises requirement → how met → departure.
Both questions above are closed: 27001 and 62443 no longer appear, refs [58]/[59] removed (gap until
week-5 renumbering, like [54]); EN 303 645 stays as the §5.2 anchor. Kernel facts (memory controller,
io not delegated [48], T16 partial) remain in §3/§8/§10. Younes also cut the Threat Dragon
single-script clause from §5.1. §5 now 632 words vs 900.
