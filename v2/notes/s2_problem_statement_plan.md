# §2 Problem Statement — plan and decisions (2026-10-14)

Budget 700 words, 2 pp. Skill loaded before drafting. Rebuilt from `report/01_problem_and_context.md`
§1.4–§1.10, not the 2026-09-08 draft (which was a near-verbatim lift at ~1,200 words).

**Division with §1.** §1 (week 4, later) carries how Home Assistant is extended (the `hass` object,
in-process loading) and the scale of the ecosystem (Table 1.1). §2 starts from there: what that
authority reaches, why nothing upstream bounds it, and the statement. §2 therefore cites Table 1.1's
figures by name only (median 20 installs, 3,095 of 4,220 under 100) and leaves the table to §1.

**Structure.**
- 2.1 What an integration can reach (Table 2.1, the report's Table 1.2, Basis column kept) +
  the garbage-collector row + the consequence that sets this platform apart (the front door).
- 2.2 What bounds it today: the HACS listing criteria [5] (structure, not behaviour); the 2021
  disclosures [4], [6] and why the response did not change authority; community review (likelihood,
  not impact; long tail, point in time, XZ [8]).
- 2.3 Who carries the risk: the platform's stated positions [4], [10]; the user with no means.
  **New since the working report (F45):** the platform does distinguish administrators from other
  users of its interfaces, which is what lets the mediator run with reduced rights (§9). An
  integration does not pass through those interfaces. Checked at 2026.8.3: an in-process service call
  gets a context with no user (`homeassistant/core.py:2881`), and the permission wrapper skips the
  check when no user is present (`homeassistant/helpers/service.py:1027`). Cited as new reference [52].
- 2.4 The RFC [11]: the single-process limit is recognised inside the project, framed as reliability;
  relocation without a scoped credential does not bound authority. One paragraph.
- 2.5 The statement (block quote), shortened.

**Stale or changed against the old draft:**
- XZ: "two years" → about two and a half years, per [8] (2021-10-29 to 2024-03-28). The "500 ms
  latency" discovery detail is dropped: [8] was not checked for it.
- "this single published result constrains every possible solution, and §8 returns to it" → points to
  S1 in §3, which is where the constraint lands.
- Table 2.1's Basis column no longer says "Deduced from §1.2"; it says "the loading model [2]".

**Decisions for Younes:**
1. The F45 paragraph (user permissions exist; integrations bypass them) is new to the problem
   statement. It pre-empts the examiner's obvious question ("why not give each integration a
   restricted user?") and is the reason the mediator can be a non-admin user while integrations cannot.
2. The RFC [11] stays in §2 rather than §7, because it is evidence that the problem is recognised, not
   prior work on confinement.
3. Over budget if the statement counts: see the word count in the commit.
