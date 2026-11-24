# Change banner (F77) on the Pi, 2026-11-24

Prediction: `notes/banner_prediction_20261124.md` (P3). Pi 5, aarch64, kernel 6.12.47+rpt-rpi-2712.
Fresh clone of `a55734f` from a bundle (the fix is committed in `219d0ce`), unmodified (dirty=0 before
and after); drivers in `drivers/`.

- `post_suites/`: (A) fresh, preflight READY, suites **36/36 twice** (291 s, 282 s);
  `selftest_approval` 20/20 both passes (checks 15–19 included), `selftest_supervise` passed both.
