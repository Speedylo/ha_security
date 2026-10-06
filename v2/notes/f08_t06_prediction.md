# F08 fixed, T06 restated — written before the code (2026-10-06)

Younes decided both: "Restate T06, and fix F08 properly".

## F08 — the identity's third part hashes resolved versions

**The gap.** §5.12.1 defines the third part of an integration's identity as "its declared
requirements, with resolved versions". `Identity.compute` hashes only the declared strings
(`aiohttp>=3.9`), with a comment saying installation "is not built yet". It is built: `compat.py`'s
`install_requirements` installs each integration's requirements into its own directory, outside the
sandbox, **before** the sandbox registers, in `compat.py`, `endtoend.py` and `endtoend_egress.py`.
So a dependency that moves (F13: `aiohttp` 3.14.3 → 3.14.4 between runs) leaves the identity
unchanged, and the log cannot show the change §5.12.1 says this part exists to show.

**The fix.**
- `Identity.compute(component, installed=None)`. Given the directory the requirements were
  installed into, it reads every distribution there (`importlib.metadata`, name and version) and
  hashes the declaration **and** the sorted `name==version` list as the third part. The list itself
  goes into the identity as `resolved`, so every run record carries the resolved versions (claim
  CS05).
- **With no directory, the hash is exactly today's.** Approvals are made before anything is
  installed and are compared against a fresh computation with no directory (`describe.py`, T12), so
  every recorded approval stays comparable. `resolved` defaults to `None` ("nothing was installed
  here"), which is distinct from `[]` ("installed, and nothing was there"), and older records
  without the field still load.
- `Mediator.register(..., installed=…)` passes the directory through. The three harnesses that
  install pass theirs. The supervisor passes its own, which is empty because it installs nothing,
  and records `[]`, which is true.

**Tests, failing first** (`selftest_audit`):
1. two install directories differing only in one package's version give different `requirements`
   and composites, with the same `source` and `manifest`, and `changes_from` names `requirements`
   alone;
2. with no directory, the identity is byte-for-byte the one computed before the change. The hash
   of a fixed component is pinned in the test from today's code, before the change;
3. a mediator registering with an install directory writes a run record whose identity lists the
   resolved versions.

Against today's code, (1) and (3) fail (`compute` takes no directory) and (2) passes. (2) is the
guard that the fix does not move every past approval.

**Regression:** all suites twice, `nordpool` end to end (a real install whose versions now enter
the identity, and the run record must list them), the T12 suite, and `recompute.py`.

## T06 restated

The verdict becomes ✅ Demonstrated, paired. Reads: 36/36 readable unconfined against 1/36
confined. Subscriptions: 4 of 4 undeclared changes delivered unconfined against 0 of 3 confined,
with mutant M10 showing the zero is the filter's (§7.36), repeated on the real platform (§7.37).
The count becomes **sixteen demonstrated, one partial (T16), two retained**. Dated pointers go at
T06's row, the T1 row, §7.44.4 and §8.2.1. Rows written before today are not edited. F38 is then
resolved.
