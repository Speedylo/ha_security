# Capability drop (F76) on the Pi, 2026-11-23

Prediction: `notes/capdrop_prediction_20261123.md`. Pi 5, aarch64, kernel 6.12.47+rpt-rpi-2712.
Clones of `ab2af16`; the fix was UNCOMMITTED, so `clone` = ab2af16 + `capabilities.py` (new),
`enter.py`, `selftest_adversary.py` copied in (sha256 in every summary), and `pre` = ab2af16 + the new
`selftest_adversary.py` only. Note: the `pre_adversary` summary's commit, dirty and sha256 lines describe
`clone` (common.sh reads `$T`); its `pre:` line is the one that describes `pre`.

- `pre_adversary/`: HEAD `enter.py` + the four capability attempts: FAILED, LEAKED 4, BLOCKED 25 (P1).
- `post_suites/`: fixed clone, (A) fresh, preflight READY, suites 36/36 twice; adversary BLOCKED 28,
  EMPTY 11, LEAKED 0 (P2/P3).
- `compat/`: the 77 confined measurements (final2 chunk E, confined arms), compared per integration with
  `final2_20261101/chunkE_step05_compat/` by `drivers/compare.py` (control: a planted level change is
  caught): DIFFERENCES 0 in both corpora.
- `real/`: final2 chunk G against the real (A). Same as 1 Nov: function pass, bridge step 5 36/36,
  retest 43 of 45, e2e_ext 8/10 (P7 is a fixed October date), dwd_weather the same undeclared
  `www.dwd.de:443`, pirateweather a live value fetched minutes apart; waste, smhi, LAN pair, trakt pass.
  Differs from 1 Nov only in the live-value check: nordpool failed (0.023 vs 0.025), regensburg passed
  (it failed on 1 Nov).
- `extra/`: nordpool rerun on the fixed clone 16/16 (both arms 0.023); timing control from `pre`
  (no drop) 390 s vs 400 s fixed: the 2–3x longer install-bearing steps since 1 Nov are not the drop
  (likely the 22 Nov install path, not measured).
