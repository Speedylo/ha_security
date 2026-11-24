# Prediction: the change banner names what changed (F77), 2026-11-24

Written before the fix (freeze rule: prediction → fails first → fix). Younes chose option (a) on
2026-11-24 in defence session 9+11.

## The defect

`describe.changes_since_approval` returns "permissions changed" when the identity's `manifest`
component moved. That component hashes the whole `manifest.json`, `version` included, so every real
update (which bumps `version`) is shown as "code has changed, AND what it is allowed to do has
changed" even when the grant is identical. A dependency change is also shown as a permissions
change. The gate (`require_approval`) is right and is not touched: any change still needs a new
approval. Only the sentence on the screen is wrong, in the alarming direction.

## The rule after the fix

- **Permissions changed** exactly when the grant fingerprint (`grant_digest`) differs from the one
  approved (or the approval record cannot be read).
- **Code changed** when the source or the dependencies moved, or when `manifest.json` moved while the
  grant did not (some other part of the integration's own description changed: an update).
- A version bump alone is therefore "code has changed; what it is allowed to do has not changed".

## Checks (added to `selftest_approval.py`, 15–19)

| # | Change after approval | Expected (code, permissions) | HEAD (predicted) |
|---|---|---|---|
| 15 | one code line + version bump, grant the same | (True, False) | FAIL: (True, True) |
| 16 | a dependency added, nothing else | (True, False) | FAIL: (False, True) |
| 17 | author's permissions block widened to `lock.unlock`, code the same | (False, True) | ok |
| 18 | derived grant (file beside) widened, code the same | (False, True) | ok (F60) |
| 19 | code + version + widened grant | (True, True) | ok |

Plus: check 15's Repairs text says "What it is allowed to do has not changed" (FAIL on HEAD).

**P1 (fails first):** on HEAD, 15, 15's text and 16 fail; 17–19 and the existing 1–14 pass.
**P2 (after the fix):** 1–19 pass; `selftest_t12` and `selftest_describe` pass unchanged.
**P3 (Pi, next Pi session):** the 36 suites, including `selftest_supervise` (needs the HA
interpreter), pass.

Falsifier: if any of 17–19 fails on HEAD, the defect is not what this note says; stop and re-read.

## Outcome

- **P1 HELD (laptop, HEAD code + new checks):** 17/20; failed exactly 15 (`(True, True)`), 15's screen
  text ("…AND what it is allowed to do has changed"), and 16 (`(False, True)`); 17–19 and 1–14 ok.
- **Fix:** `describe.changes_since_approval` only (rule above); the gate is untouched.
- **P2 HELD (laptop):** `selftest_approval` 20/20, `selftest_t12` 33/33, `selftest_describe` PASS.
- **P3 HELD (Pi, 2026-11-24):** clone of a55734f, preflight READY, suites 36/36 twice; approval
  20/20 both; results `experiments/verify/results/banner_20261124/`.
- Uncommitted. Finding F77, rated **Minor** by Younes (2026-11-24): no authority changes, only the
  screen's sentence. Report counts 76→77 with the 28 Nov fixes.
