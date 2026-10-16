# Appendix G draft — cover note (2026-10-16)

The draft is `notes/appendix_g_draft.md`. Every statement in it was read from `framework/confine/manifest.py`
(the code is unchanged since `final-2026-10`), `sandbox.py`, `cgroup.py` (defaults), `audit.py`
(`target_of`) and `describe.py`. The example is the manifest `endtoend_local.py` gives `midea_ac_lan`.
The working report's §5.10 was not used as the authority, because it predates ports, `local`, `discover`
and `disk_mb`.

## A gap found while writing it (a possible F63)

- **`files`:** the parser validates `files.read`/`files.write` and rejects forbidden paths, and `sandbox.py`
  can mount a `files_ro`/`files_rw` list. But no production code fills that list from the manifest. The
  supervisor's `SandboxSpec` (`supervise.py`, ~line 246) never sets it, and neither do `endtoend*.py` or
  `compat.py`. Only self-tests build specs with declared files.
- **`http.register`:** it is parsed and rendered at approval (`describe.py`), but no request operation maps to it
  (`OPERATIONS` in `manifest.py`), and nothing else reads it.
- **`network.allow_private`:** it is accepted for old manifests, and nothing reads it (`egress.py`'s
  `allow_private` is a caller parameter that no production caller sets). That is consistent with the code
  comment, so it is not a defect, only a fact for Table G.1.

All three fail closed: the integration gets less than the clause says, never more. This is the same class as F50,
but the body doesn't say so. §3.5's feature 1 lists files and HTTP routes among the clauses that "grant
capability", and Table 9.2 names only F50's three operations. No evaluation manifest used `files` or `http`.

Options:
- **(a) Record it, no code change (recommended).** F63, Minor, method "Writing Appendix G". Table 9.2's row
  becomes "Five declarable clauses are accepted but not acted on", naming `event.fire`, `event.subscribe`,
  `config_entries.read_all`, `files` and `http.register`. §14 row 7 is extended to match, and §3.5's feature 1
  gets one clause. The count changes 62 → 63 (front matter F01–F63, §3 D7, §6, §12.4, Appendix F's total,
  Minor 38 → 39).
- **(b) Wire `files` into the supervisor now.** This is a code change after the final tag: a prediction note, a test
  shown failing first, its own tag, a suite regression. §8.6's "every number in Section 12 was checked against
  [the final tag]" would then need a sentence. `http.register` would still be (a).
- **(c) Leave the body as is** and let Appendix G's table carry the facts. Not recommended: §3.5 and Table 9.2
  would then disagree with Appendix G.

## Applied 2026-10-16 (Younes: record as F63, option a)

Appendix G inserted from the draft (files and http rows name F63). F63 in Appendix F (Minor, "Writing Appendix G"; carried as a stated limitation with F53); totals 63 / 39 Minor. Table 9.2: five declarable clauses accepted but not acted on (F50, F63), fail closed. §3.5 feature 1 names the four kinds of clause. §14 row 7 "five declarable clauses". §12.4: ten after the cut-off, all but F63 resolved, 63 in Appendix F. Front matter F01–F63; §3 D7, §6 63 findings.
