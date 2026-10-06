# Every self-test suite, on the Pi

`suites_all.sh` runs `selftest.py` and every `selftest_*.py` (26 in all since 2026-10-05) against the
framework of the checkout it sits in, one log per suite and one exit status per line in `summary.txt`.
The four suites that spawn sandboxes (`bridge`, `egress_sandboxed`, `gc`, `reads`) are given the Home
Assistant interpreter; without it they exit 2 on argparse, which is the invocation and not a failure.
`selftest_real_platform` needs (A) running (`../../REPRODUCE.md`, step 9).

```bash
bash experiments/selftests/suites_all.sh /tmp/suites            # from v2/; ~/r2exp/ha314 by default
bash experiments/selftests/suites_all.sh /tmp/suites /path/to/ha/python
```

*Until 2026-10-06 the script `cd`'d to `~/r2exp/v2/framework` whatever checkout it was run from (F19), and
this paragraph said twenty suites. The results below were produced that way, from the Pi's working copy.*

## `results/final_20261003/` — the state handed to the next session

Run on 2026-10-03 after T4's audit wiring and §7.35's changes, at commit `9ee4bde` (framework code
verified identical on the Pi by checksum). **All 21 exit 0.** It supersedes the T6 run of the same
morning (logs on the Pi in `~/r2exp/t2/suites_20261003/`), which predated those changes.
