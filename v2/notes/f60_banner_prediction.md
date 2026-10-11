# F60, `describe` does not warn that a derived grant widened: predictions for the fix

**Written 2026-10-11, before the test is written and before any run.** F60 (new, Minor; found while
writing F57c's Repairs screen): `describe`'s terminal banner, "What this integration is allowed to do
has changed since you approved it", is decided by comparing identities only (`main`: `"manifest" in
moved or "requirements" in moved`). A derived grant lives in `<domain>.permissions.json`, which the
identity does not hash, so when that file is widened after an approval the identity does not move,
and `describe` shows the wider list **with no warning that it changed**. The operator reading it
before `--approve` is told nothing moved. Security is not affected: since F57 the gate compares the
grant digest and refuses the widened grant until it is approved again. What is wrong is what the
person deciding is shown. **Younes decided on 2026-10-11 to fix it.** Commit this note before the
test runs; do not edit it after a run (`verify/prereg.py`). Results go to
`experiments/verify/results/f60/`.

## 1. The rule

`describe`'s banner says the permissions changed when the identity's manifest or requirements moved
**or the loaded grant's digest differs from the last approval's**, the same comparison F57c's
Repairs screen makes (`changes_since_approval`). An approval written before F57, without a digest,
counts as a change, as it admits nothing at the gate either.

## 2. The change

`describe.py`, `main`: the banner's two flags come from `changes_since_approval`. Nothing else.

## 3. The test, written first

In `selftest_describe`, a sixth state, through the command line as an operator runs it:

1. A derived grant approved with `describe --approve`; `describe` then shows **no** banner.
2. The derived file widened (`services.call: ["lock.unlock"]`); `describe` now says **"allowed to do
   has changed"**, and does not say the code changed.

## 4. Predictions

**D1, the test before the fix** (the test commit, laptop): check 1 passes, check 2 fails, every
other check passes; exit 1.

**D2, after the fix** (laptop and Pi): `selftest_describe` passes, exit 0.

**D3, `selftest_approval`** 14/14 at the tag (it does not use the banner).

**D4, mutant M50**, the banner's permission flag ignores the digest (identity only, as before the
fix): killed by `selftest_describe` check 2. Run on the Pi with F59's mutants, since F59's tag
contains this fix.

The full suites run at F59's tag, which follows and contains this one.

## 5. After the runs

Ledger line; Appendix F row F60; the findings table.
