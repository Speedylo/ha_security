# Retest of 2026-10-04's work (§7.43)

`results/review_20261004/first/` — every subject touched that day, on the code **before** the
review's fixes (`summary.txt` has each step's exit code). `pirateweather` exit 2 there is the
wrapper looking in the wrong corpus; it was run again in the follow-up. The stand-in push run shows
15 publishes and no push: the harness regression §7.43.2 describes.

`results/review_20261004/followup/` — after the fixes: the stand-in push run, both local-network
subjects, `nordpool`, `pirateweather` from the right corpus, and `selftest_real_platform` re-run with
(A) started outside a systemd unit. `suites_followup/` — the full suite on the fixed code (24 passing
there, and `selftest_real_platform` failing only because (A) had stopped with the previous unit).
