# Whole-report reread: discrepancies, repetition, unnecessary detail — 2026-10-16

Read in full, front matter to Appendix G, after the week-6 number check and §12's trims. Nothing in the
submission changes until Younes chooses.

## Discrepancies

**D1. Appendix G is a placeholder.** It reads "[To be lifted: the full JSON schema for the `permissions`
block …]", yet §3.5, §9.3 and Table 9.1 send the reader there. This is the one gap that blocks
submission. Drafting it means lifting the schema from the working report and checking it against the parser
in `framework/confine/`. It is a separate piece of work, so it gets its own draft for review.

**D2. "75 source trees" reads as 75 integrations, and it isn't.** The count is 37 + 38 tree comparisons on the
head-weighted corpus in September (report §7.29: one arm-B retry made 38). The uniform corpus was added on
3 October (Appendix D), and the final rerun counted zero changed files again. The figure matches the 75
distinct integrations only by coincidence.
- §3, Table 3.2, C1 → "Met: every source tree, in both arms of both corpora, unchanged after its run"
- Appendix B, Table B.2, C1 evidence → "Every source tree hashed before and after its run, in both arms of
  both corpora and again at the final rerun: no source changed, no line differed (Appendix D)"
- §12.4 ("the 75 comparisons later found no change") is historical and accurate; leave it.

**D3. Appendix E names the wrong last full run.** It says "last run in full at the final fix of the writing phase
(tag `fix-2026-10-f59`)". The final rerun ran all 29 twice at `final-2026-10`, and every check count in
Table E.1 is identical in both of its runs (checked suite by suite). → "They were last run in full at the
final tag, `final-2026-10`, twice on the Raspberry Pi 5, and all 29 passed both times with the counts below."

**D4. Appendix D dates its results to 3 October only.** The final rerun reproduced every row and every message
exactly (step 5). → add "and the final rerun reproduced every outcome and message exactly" after "…as in its
first run."

**D5. The platform's policy is called "per-domain" in §6.6.3 and §8.5 (three times), and "per-entity" in §9.8,
§14 and §15.** Home Assistant's policy restricts a user's entities by domain or by entity ID. Proposed: use
"per-entity" throughout; §8.5's "an entity policy by domain is enforced" → "an entity policy, by domain or by
entity, is enforced".

**D6. §6.4 says the architecture was "chosen against measured alternatives".** Nothing measured gVisor or
microVMs. They were rejected by arithmetic on the measured cost of a sandbox (report §5.6). → "chosen
against alternatives".

**D7. Appendix F twice writes "§12.4" and "§14", where the rest of the report writes "Section".** → "Section 12.4",
"Section 14".

## Repetition

**R1. The missing independent adversary is stated eight times** (§6.3.2, §8.7, §12.1, §12.4, §12.5, §13.3,
§14, §15), three of them in §12. §12.1 repeats §8.7's explanation of why it was dropped (AI assistance).
Proposed: §12.1 keeps the limitation and F34 and drops the AI-assistance clause, which §8.7 gives. §12.4
drops "No independent adversary attacked the framework, as Section 12.1 records." (≈ 45 words)

**R2. "Every manifest was written by hand" appears eight times.** On 2026-10-12 you placed it in the abstract,
§1, §3 C1, §14 and §15. It also appears in §4.3, §6.1 and §10.4. §10.4 is where operational feasibility
belongs; §4.3 and §6.1 restate it. Proposed: cut the clause from §6.1 and keep §4.3's "each integration still
needs a manifest", dropping "every evaluation manifest was written by hand".

(Left as they are: the HTTP-client defect told in §4.2, §9.5, §12.2 and §13.3, each for a different purpose;
the garbage-collector technique explained where each section needs it; the headline results in the
abstract, §1, §6.6.1, §10 and §15, which the template's sections require.)

## Unnecessary detail (the deferred trims)

- **U1.** §9.2, the `chroot`/`pivot_root` paragraph (~300 words) → about 150, keeping why `chroot` is not a
  boundary and what `pivot_root` does.
- **U2.** §9.7, the stored-data paragraph (~330) → about 200.
- **U3.** §8.6, the F61 paragraph (~260) → about 150; the detail is in Appendix F.
- **U4.** §9.4, "Messages are framed as a four-byte length followed by a JSON object…" (~35) → cut.
