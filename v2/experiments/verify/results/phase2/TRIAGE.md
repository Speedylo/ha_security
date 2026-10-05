# Phase 2 — L2, L3 and the golden comparison, triaged

Run on the frozen tree (`verify-2026-10`) on 2026-10-05, after the reboot. Every new result was
compared with the golden file chosen before the run (`verify/golden.json`) by `verify/compare.py`;
the per-file comparisons are in `compare/`. Every difference is classified below. **None is
unexplained except F12, and F12 touches no subject's own entity.**

## L1 — 26 suites (`suites_run1/`)

25 of 26 pass with every internal count equal to the last committed log. `selftest` fails one check,
"the user's home directory: ABSENT", only because this run's scratch was under home: with `/tmp` it
passes (`suites_run1/selftest_tmpdir_tmp.log`). Finding F10; the probe behind F11
(`probe_home_visibility.json`) shows home then holds only the skeleton to the granted file.

## L2

| Step | Result |
|---|---|
| `selftest_real_platform --restart` | 48/48 |
| `drive_demo` under the supervisor | press 12 ms; cut-off 0.55 s later; 102 decisions (command, publish, 100 refusals) and one `cutoff`; fix flow confirm → create_entry; restart 0.10 s; switch back off 0.62 s |

## L3 against the golden files

| Result | Exact / numeric | Triage |
|---|---|---|
| `e2e_real_thermal` | 0 / 0 | identical |
| `e2e_real_adaptive` | 0 / 0 | identical |
| `oauth_trakt` | 0 / 0 | identical (tokens normalised away) |
| `e2e_standin` (5 subjects, 5/5 load) | 3 / 0 | `watchman`'s timestamp (live); `wcwidth` 0.9.1 → 0.9.2 (dependency drift, F13) |
| `egress_nordpool` 16/16 | 9 / 0 | price 0.002 → 0.001 in **both** arms (live, L holds); sun states and times; a rotated DNS answer; `aiohttp` 3.14.3 → 3.14.4 (F13) |
| `egress_pirateweather` 17/17 | 14 / 1 | temperature 13.2 → 16.7 °C, equal across arms (L holds); weather state; one check more than the golden (harness gained it); F12; F13 |
| `egress_dwd_weather` 15/16 | 17 / 2 | the one failure is the known undeclared host (§7.31.5), as in the golden's 13/14; forecast times and state live; F12; F13 |
| `egress_smhi_brandrisk` 20/20 | 36 / 2 | fire-risk indices live, equal across the confined arms; one more audit record per arm (one more poll in the window); F13 |
| `egress_regensburg_transport` 16/16 | 16 / 2 | one fewer publish *event*, not entity: the delay value did not change, so it was not re-published; F12; F13 |
| `local_midea_ac_lan` | 6 / 1 | sun times live; the device saw 4,440 bytes against 4,352 (timing); F12 |
| `local_localtuya` | 6 / 1 | sun times live; 82 broadcasts against 88 in the window (timing); F12 |

## Findings raised in phase 2

- **F12 (Note).** Every baseline (unconfined) arm published `conversation.home_assistant` on
  2026-10-04 and none has since 2026-10-05 (absent already in the flood campaign's `nordpool`, before
  `houseA-deps` was touched). It is a default entity of the platform, not of any subject; no subject's
  own entity moved. Ruled out: `hassil` missing (it has been in `platform-deps` since August). Cause
  not established; the Pi rebooted between the two dates.
- **F13 (Minor, reproducibility).** Per-run installs are not pinned: `aiohttp`, `pycares`,
  `pycryptodome` and `wcwidth` resolved to newer releases than in the golden runs. A re-run months later
  tests different library versions, and the run record does not capture them (F08).
