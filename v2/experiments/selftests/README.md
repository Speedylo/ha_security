# Every self-test suite, on the Pi

`suites_all.sh` runs `selftest.py` and every `selftest_*.py` (the 20 the report counts) against the
current framework, one log per suite and one exit status per line in `summary.txt`. The four suites
that spawn sandboxes (`bridge`, `egress_sandboxed`, `gc`, `reads`) are given `--python
~/r2exp/ha314/bin/python`; without it they exit 2 on argparse, which is the invocation and not a
failure.

## `results/final_20261003/` — the state handed to the next session

Run on 2026-10-03 after T4's audit wiring and §7.35's changes, at commit `9ee4bde` (framework code
verified identical on the Pi by checksum). **All 21 exit 0.** It supersedes the T6 run of the same
morning (logs on the Pi in `~/r2exp/t2/suites_20261003/`), which predated those changes.
