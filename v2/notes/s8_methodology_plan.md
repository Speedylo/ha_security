# Submission §8, Methodology and Capstone Design — plan and decisions

**Agreed with Younes 2026-10-11, before drafting.** Budget 2,000 words of prose (draft: 2,021), from the
working report's Chapter 4 (threat model; full register stays in Appendix C) and §7.36–§7.45 (the
verification campaign). Outline: 8.1 method and three rules; 8.2 framework, scope, owner; 8.3 assets,
actors, boundaries (two figures); 8.4 risks, treatment, S9; 8.5 residual risks; 8.6 how the claims
were verified; 8.7 what the method does not establish.

**Decisions (Younes, 2026-10-11).**
- **R3 re-rated "High, narrowed"** after F45: the mediator is an ordinary user (no admin functions),
  still controls every device; reason is no longer "upstream limitation" but "the per-domain policy
  cannot be configured through a supported interface". Locks (A1) still reachable, so High.
- **Figure 8.2 = `figures/fig_8_2_confined.py`**, a copy of `fig_5_1_confined.py` (which stays as the
  working report's Figure 5.1): TB2 NARROWED; new flow A (approval: an administrator in Repairs, or the
  operator at the device, F57); the working report's section numbers removed from labels; the Home
  Assistant box 15 px taller with its title at the bottom so flow A does not cross it. Self-checks:
  TB4 unchanged, TB2 narrowed, TB5/TB6 crossed by nothing. Figure 8.1 = `fig_4_1_current_state.svg`
  unchanged (its drawn labels carry no section numbers).
- **Corno and Mannella comparison** (old draft §8.8) moves to §7 as related work (week 4); §12.5 still
  scores against both registers.
- §8.2 states the consequence of excluding a compromised platform: an administrator of (A) approving a
  wider grant is that case, which is why Table 9.2 lists it as a limit.

**Checked while drafting.** [9] p. 3: "gateway's resource saturation up to a frozen state" (read from
`refs/A_Threat_Model_for_Extensible_Smart_Home_Gateways.pdf`); the garbage-collector technique is
[9]'s own validation (working report §2.4.1), so AC4's [9] is right. [12] (Barth et al., browser
extensions) carries R1's precedent. Counts: 153 claims (119 V, 27 Q, 5 A, 2 W); 34 prediction notes;
53 mutants (M25 equivalent); 9 faults (5 held, 4 defects).

**References owed** (provisional; the list is rebuilt in week 5): **[46]** Y. Jia and M. Harman, "An
analysis and survey of the development of mutation testing," *IEEE Trans. Softw. Eng.*, vol. 37,
no. 5, pp. 649–678, Sep. 2011, doi: 10.1109/TSE.2010.62 (checked against Crossref). Still owed from
before: replace [8]'s Wikipedia source for XZ Utils (CVE-2024-3094).

**Numbers that move at the final rerun:** the mutant count and kill statement, the note count, and the
fault outcomes; the week-6 read-through checks them against the rerun.

**2026-10-11 (later): checklist pass with the academic-research-writer skill** (Younes asked; the first
draft was written with the skill's guidelines in context but not checked against its list). Fixed:
- 8.1 rule 2: "a recognised failure" (uncited) became the project's reasoning, anchored on ISO 31000's
  order, assessment before treatment [25].
- 8.2: ISO 31000 "does not prescribe a technique for identifying risks" [25]; **to verify against the
  2018 text (clause 6.4.2) at the week-5 rebuild** — the standard is paywalled and was not fetched.
  The first paragraph now links to the next.
- **[8] replaced** (no Wikipedia): P. Przymus and T. Durieux, "Wolves in the Repository: A Software
  Engineering Analysis of the XZ Utils Supply Chain Attack," in *Proc. 2025 IEEE/ACM 22nd Int. Conf.
  Mining Software Repositories (MSR)*, Ottawa, ON, Canada, 2025, pp. 91–102, doi:
  10.1109/MSR66628.2025.00026 (Crossref). Their §III-B: involved "from 2021.10.29 to 2024.03.28,
  spanning 2.6 years"; AC2's cell now says 2.6 years, not "two years".
- 8.4: the ecosystem's existing control cited as [5] (checked: HACS runs automated checks of structure
  and metadata; the page says nothing of reviewing behaviour).
- R1: [12] now carries a checked figure — "76% of these extensions use unnecessarily powerful APIs"
  (read from the PDF, p. 1 abstract). Felt et al., CCS 2011, was considered and **not** cited: its
  abstract could not be fetched to verify the over-privilege figure.
- R5: **[47]** E. Rescorla, "The Transport Layer Security (TLS) Protocol Version 1.3," RFC 8446, IETF,
  Aug. 2018 (§1: "Data sent over the channel after establishment is only visible to the endpoints").
- R7: **[48]** systemd, `units/user@.service.in`, https://github.com/systemd/systemd (line
  `Delegate=pids memory cpu`; checked 2026-10-11). The project's own measurement on the Pi is §7.22.
- 8.6: "closes that gap" → "narrows that gap"; the fault paragraph now links to the post-cut-off rule.
