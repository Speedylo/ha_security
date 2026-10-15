# §13 Learning Strategies — plan and decisions (2026-10-15)

Budget 800 words, 2 pp; drafted at ~910 words. Skill loaded first. Four template sub-heads kept.

**One instance per strategy, told for an outside reader:**
- 13.1 Read prior work in full: [9]'s heap walk ruled out in-process designs. Check claims in the
  platform's source: 91% of 1,482 shipped integrations use the helper layer → a real runtime, not a stand-in
  (§9.2). Late instance: "no restricted credential" was wrong (F45, §8.5) → mediator is an ordinary user.
- 13.2 Predictions committed first (Table 6.1; first eight, six wrong; least-installed loaded more often).
  Paired arms corrected conclusions both ways (powercalc / scheduler, §12).
- 13.3 "A test that cannot fail proves nothing" (plan: 4.12), three times: nordpool's HTTP client (§12),
  drive_demo always exit 0 (F48), supervisor-kill mutant surviving because demo_flood stopped itself →
  demo_stubborn. Adaptation: every check paired with a mutant (53). F34 as the limit.
- 13.4 Requirements with verification first; standard library only; AI-assisted code → curriculum
  (`notes/learning_curriculum.md`); dated corrections not rewrites; 141,682-word working report condensed.

**Dropped from the old draft:** "six of eight" as the whole story; the mDNS four-layer diagnosis (told in
§12); "every correction was to a sentence, none to a measurement" (no longer true after 2026-10-03:
the aiodns share and memory premiums moved); the five mechanisms ranking (too long; its content is in
13.2–13.3); the egress `allow_private` self-grant (needs too much context).

**For Younes:**
1. 13.4 says the code was AI-assisted (already disclosed in §8.7 and §12.1) and that a curriculum was
   written to rebuild each mechanism from the kernel documentation. It claims only that the curriculum
   exists, not how far you have worked through it. Keep, change, or say more?
