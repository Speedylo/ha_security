# The remaining minor findings — fixes and criteria, written before the work (2026-10-06)

Younes: "fix the remaining minor findings". Nine are open: F04, F06, F07, F10, F12, F13, F14, F15
and F16. For each: what is wrong, the fix, and how it is judged.

**F04 — CM-T7's row predates T19.** The external-register row for Corno and Mannella's T7
(availability, "resource saturation up to a frozen state") maps only to T16. T19, added on
2026-10-05, is denial of service against the audit log, which is a saturation route too.
*Fix:* a dated pointer on the row in §7.26.4 adding T19, and the claim register's row updated. The
row's verdict stays ⚠ Partial, because T16 is still partial. *Judged:* the row names T19.

**F06 — Contribution 2's suite tally.** *Already fixed:* §8.3's paragraph reaches twenty-five
(`selftest_flood`, 2026-10-05), and 25 `selftest_*.py` exist. It was corrected in F25's batch and
never closed in the log. *Judged:* the paragraph's last number equals the files on disk.

**F07 — results sections no README names.** §7.16, 7.19, 7.22, 7.25, 7.29, 7.30, 7.32, 7.38 and
7.41 are named by no experiment README, and `experiments/durability/` has none. Most of the nine
rest on suites, not on a results directory. *Fix:* `experiments/selftests/README.md` gains a table
naming each suite-backed section and its suites; `mediation_latency/` names §7.19; `compat/` names
§7.29; `durability/` gets a README (what `measure.py` measures, which sections cite
`results/pi5.json` and `results/t4_20261003/`). *Judged:* a script lists every `## 7.n` results
section and finds a README naming it, or records why none applies.

**F10 — the home-directory check passed for an unrealistic reason.** The base self-test puts its
configuration root in `/tmp`, so "the user's home directory: ABSENT" passes trivially. A real
installation keeps its configuration under home. *Fix:* the test puts its configuration root under
the user's home, as a real installation does. It then asserts what should hold there: home exists
only as the skeleton chain down to the granted file, with nothing else in it. *Judged, failing
first:* with the root under home, today's expectation ("home ABSENT") fails. The new assertion
passes, and the listing of every directory on the chain shows only the next link.

**F12 — a baseline stopped publishing `conversation.home_assistant`.** A Note: no subject's entity
moved, and no claim rests on it. *Fix:* close it as a note with what is known. `hassil` was ruled
out. The most likely cause is F13 itself: unpinned installs moved the platform's own packages
between the two dates (`home-assistant-intents` is a candidate). That is not established, and it is
recorded as unestablished.

**F13 — installs are unpinned.** A re-run resolves whatever is newest, so it tests different
versions (`aiohttp` 3.14.3 → 3.14.4). Since F08, the run record names the versions, which was half
of this finding. *Fix:* every requirements install resolves only packages uploaded before a fixed
moment (`uv pip install --exclude-newer`): `RESOLVE_BEFORE = 2026-10-06T00:00:00Z`, the campaign's
freeze day. It can be overridden on purpose with `CONFINE_RESOLVE_BEFORE`, and is recorded in each
install's result. *Judged:* `nordpool` end to end still passes 16/16, and its resolved versions are
listed and compared with today's unpinned run, with the differences stated. Two installs of the same
requirements give identical resolved lists.

**F14 — result files do not record how they were made.** *Fix:* a helper,
`confine/provenance.py`, writes `<result>.run.json` beside each harness's JSON output. It records
the command line, the working directory, the git commit and whether the tree was dirty, the
interpreter, the host, the time and `RESOLVE_BEFORE`. Result files keep their structure, because
`compare.py` and `recompute.py` read them. It covers the measurement harnesses: `compat`,
`endtoend`, `endtoend_egress`, `endtoend_local`, `endtoend_oauth`, `egress_shape`,
`figures/api_surface.py` and the measurement scripts under `experiments/`. Not `verify/`, whose
tools run from committed shell scripts, so their commands are already recorded. *Judged:* a run of
`nordpool` and of `api_surface.py` each leave a `.run.json` whose command line reproduces the run.

**F15 — the `aiodns` share is not stable.** 17% on 2026-10-03 (25 against 121), 11% in Phase 3a
(14 against 118, `frigate` alone 11 → 1). *Fix:* a dated pointer in §7.31.11 giving the range
11–17% and why it moves (one integration's polling), with the conclusion unchanged: both seams are
used, so the shim interposes at both.

**F16 — the 144-integration sample is not kept.** Its manifest was overwritten when the 40-integration
head corpus was fetched to the same default path the next day. *Fix:* rebuild it as F21 rebuilt the
corpora:
1. the selection, from the committed analytics snapshot (F37), which is the one the fetcher read;
2. today's HACS index, top 150 by installs;
3. each repository at its last commit before the run that produced
   `figures/api_surface_hacs.json` (commit `bd3ee7b`), from a blobless clone;
4. `api_surface.py` at the commit that wrote the result.

*Judged:* the rebuilt sample's parse is compared with the committed result, field by field. If
they are equal, the sample is pinned and its manifest committed (`hacs_top150_manifest.json`), and
F16 is resolved. If not, the differences are reported (index changes since 24 August, repositories
gone), and the finding is qualified rather than closed.

**Regression for the code changes (F10, F13, F14):** all suites twice, `nordpool` end to end, and
`recompute.py`, on a new tag.
