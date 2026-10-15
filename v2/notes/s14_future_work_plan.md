# §14 Future Work — plan and decisions (2026-10-15)

Budget 700 words, 2 pp; drafted at ~615 prose words + Table 14.1 (10 rows). Skill loaded first.

**Old draft's items already done, so dropped:** push loop (W1, §7.36), real Home Assistant behind the
mediator (§7.37), T12 the unevaluated threat (§7.30), API-surface uniform run (T5, §7.33, now §9.3),
other network stacks (§7.31, W2a), asyncio datagrams (W2b), durable log engaged (T4); 14.1's
"composition" table (all four parts now exist). Item 11 "enforcement inside the loader" replaced: it
contradicted §9's first decision.

**Rebuilt from the bounds the approved sections state:** independent adversary (§8.7, §12.1, §12.5
says §14 begins with it); manifests at scale (agreed wording, C1, §9.3; authors / analysis / curation,
Younes 2026-10-15); months of household use and the credential ceiling (§12.2); releases (§4.2);
user study (§4.7, §6.2, R6); T16 and the data-store limit (§9.8); F54, F50, F53 (§9.8); automated
mutation not run and F18 (§8.6, §12.4); R4 off-box anchoring; R2 and R5 as research questions;
upstream process boundary + per-entity policy (R3, §9.8).

**For Younes:**
1. **Approved §12.5 has two stale statements.** "functionally checked for nine integrations" — since
   the 2026-10-09 retest, §12.2 says every row of Table 12.3 (13) carries a predicted, checked value.
   And "Section 14 … beginning with an independent adversary and a functional retest of the integrations
   whose runs showed setup only" — the retest is done. Proposed: "functionally checked for the thirteen
   executed end to end", and "beginning with an independent adversary".
