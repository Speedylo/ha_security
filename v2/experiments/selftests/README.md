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

## Which Chapter 7 sections rest on which suites

*Added 2026-10-06 (verification finding F07).* Several results sections rest on suites rather than
on a results directory of their own, and until this date no README named them. Each suite's log
from every run is in `results/` here, and in the campaign's runs under `../verify/results/`.

| Section | What it reports | Suites |
|---|---|---|
| §7.16 | C3 and the remaining security criteria, re-verified | `selftest_policy`, `selftest_c3`, `selftest_channel`, `selftest_audit`, `selftest_describe`, `selftest_bridge`, `selftest_gc` |
| §7.22 | S9 wired to the manifest | `selftest_resources` |
| §7.25 | F2 and S4 closed: the egress proxy | `selftest_egress`, `selftest_egress_sandboxed`, `selftest_egress_shim`, `selftest_fdpass`, `selftest_udp`, `selftest_bridge` |
| §7.29 | C1 counted | `selftest_integrity`, with the comparisons in `../compat/` |
| §7.30 | T12 measured | `selftest_t12`, `selftest_describe` |
| §7.32 | the durable audit log engaged where decisions are made | `selftest_audit`, `selftest_t12`; T4's run in `../durability/results/t4_20261003/` |
| §7.38 | commands from the house into a confined integration | `selftest_real_platform` |
| §7.41 | asyncio datagram endpoints | `selftest_udp` |

§7.19 and §7.20 have results directories of their own: `../mediation_latency/` and `../durability/`.
