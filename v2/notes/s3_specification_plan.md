# §3 Project Specification — plan and decisions (2026-10-13)

Budget 1,000 words, 3 pp. Skill loaded before drafting. Rebuilt from the working report, not the
2026-09-08 draft, whose figures were stale.

**Stale in the old draft, corrected:** "19 self-test suites" (now 29); S3 "partial, push loop not built"
(met 2026-10-04, §7.36); N2 "end-to-end for 5" (13, Table 12.3); "Nineteen met, one partial" (all twenty
met, S9 and N2 in narrowed form); "18 threats" (19, §8/§12.1); C1 "unmodified" without the manifest
(decision 2026-10-12); C4 "unprivileged and without root" (one boot-time root step, `REPRODUCE.md`);
mediator "holding the platform credential" (now an ordinary non-admin user, F45); key features had no
approval or Repairs (F57, F57c); pointer to a §12.7 that no longer exists.

**Sources checked:** requirements, derivations, stakeholders, non-goals `report/03_requirements.md`
§3.2–§3.8; verdicts `report/07_evaluation.md` §7.5 (all twenty ✅; S9 narrowed, N2 met by reporting);
S3/F1 in a live instance §7.36/§7.37; manifest clauses `framework/confine/manifest.py:116`
(`KNOWN_CAPABILITIES`: seven capabilities + `resources`); 29 `selftest_*.py`; mutants M01–M50; 60
findings and 153 claims (Appendix F); threat and residual counts §8.5, §12.1; MUD quote [18] from
`report/02` §2.4.2; 4,220 [1] and "users install them at their own risk" [4] from `report/01`.

**Decisions for Younes to check:**
1. **Order of sub-sections.** The template's six heads run Objective · Scope · Key features ·
   Deliverables · Constraints · Expected outcome. The draft puts Constraints and Requirements before
   Key features, so that each feature can name the requirement it answers. Revert if the template order
   matters more than the flow.
2. **Stakeholders** (from `report/03` §3.2) are one paragraph inside Scope, not a table.
3. **Verdicts are stated at the cut-off with post-cut-off fixes**, and the change history (S3 met late,
   S7/S8 qualified) is one sentence; Appendix B keeps the detail.
4. **C1 uses the agreed "unmodified" wording**, with "no existing integration carries one" (true by
   construction: the `permissions` clause is this project's schema) instead of a corpus count.
5. **N3's verdict** names both preflight refusal and failing closed when the mediator stops (FI1/FI4).
