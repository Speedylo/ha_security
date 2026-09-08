# Appendices

## Appendix A — Open-source repository and artifact index

| | |
|---|---|
| Framework | `v2/framework/confine/` — standard library plus `ctypes`, no third-party dependencies, no override flag |
| Self-tests | **19 suites**, all passing on the test hardware. `selftest_*.py` in the same directory |
| Experiments | `v2/experiments/` — each with its script, its raw result file and a readable write-up |
| Figures | `v2/figures/` — each figure and its threat model generated from one source, so they cannot drift |
| Corpora | `hacs_corpus_manifest.json` — both corpora, redrawable; the uniform draw records its seed (20260902) |
| Working notes | `v2/notes/` — decision records, evidence write-ups and the pre-registered predictions |
| Test hardware | Raspberry Pi 5, 4 GB, Raspberry Pi OS trixie. **Every measurement in this report was taken on it** |

*[Repository URL and access statement to be supplied on submission.]*

---

## Appendix B — Requirements register

*[To be lifted verbatim from the working report: all twenty requirements with their derivation, their
verification criterion as frozen before measurement, the verdict, and the evidence pointer for each.
This is the table §3.6 summarises.]*

**Structure of each row:** ID · statement · derivation (the §2 or §7 finding it traces to) ·
verification criterion · verdict · evidence.

---

## Appendix C — Threat register

*[To be lifted verbatim: eighteen threats T01–T18 with STRIDE category, trust boundary, impact,
likelihood, inherent rating, treatment option, the control applied, the requirement it maps to, and
the mapping to the closest published model. Followed by the seven residual risks R1–R7 with their
retention rationale and residual rating.]*

**Also to include:** the impact and likelihood scales, with the note that they are **ordinal, not
cardinal** — they order risks for treatment priority, and the product of two ordinal scales is not
a quantity and is not treated as one.

---

## Appendix D — Full compatibility results

*[To be lifted verbatim: for each of the 77 integrations across both corpora, in both arms — the
outcome on the ladder (not found → import failed → imports clean → platform import failed →
platforms clean), the error string where one occurred, the declared components and packages, and
the install count.]*

**The point of the appendix is the column comparison**: the confined and unconfined outcome for
each integration side by side, so a reader can verify the set difference is empty in both
directions rather than taking §12.2's zero on trust.

---

## Appendix E — Self-test suites

*[To be lifted: the 19 suites, what each asserts, and its pass count.]*

Two are worth flagging to a reader scanning the list. **One suite passes when a surprising thing is
true** — connected UDP sockets were assumed peer-pinned and are not, and the test passes when a
datagram is redirectable, so a future kernel change fails the suite rather than silently
invalidating the design's foundation. **One exists because an instrument lied**: the integrity
checker's first version reported a clean zero by comparing the baseline tree against itself, and
the self-test written for that failure mode is what caught it.

---

## Appendix F — Manifest schema

*[To be lifted: the full JSON schema for the `permissions` block, the eight top-level capabilities
and ten declarable clauses beneath them, the parse-time rejection rules, and the clause-pointer
format that makes every enforcement decision attributable.]*
