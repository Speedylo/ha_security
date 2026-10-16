# Tables 12.3 and 12.5 against the final rerun — draft for Younes (2026-10-16)

Nothing in `submission/` is changed until Younes chooses. Sources: `experiments/verify/results/final_20261016/`
(step 7 `step07_e2e/verdict.txt`, step 8 `step08_retest/verdicts.txt`, step 10 `step10_timing/timing_stats.txt`
and the per-pass `depth_*.json`), against the verification campaign's five passes
(`experiments/verify/results/phase3_timing/final_f45_stats.txt`: pass1, pass2, pass3, final, final_f45).

## 1. Table 12.5

### What the rerun gives, row by row

| Row | Table 12.5 now | Verification, five passes | Final rerun, five passes |
|---|---|---|---|
| Memory, no components | 56.5 · 58.6–58.8 MB | 58.6–58.8 | 59.0 every pass |
| Memory, two components | 92.3 · "not re-measured" | **94.7–94.9** (measured, never reported) | **95.0 every pass** |
| Memory, ten components | 135.6 · 141 every pass | 141 | 141 every pass |
| Mediation latency, one | 43 · 41.2–43.4 µs | 41.2–43.4 | 41.4–44.4 (median 43.0) |
| Mediation latency, 26 | 800 · 794–814 µs | 794–814 | 794–816 |
| Durable record | 3.67 · 3.62–3.69 ms | 3.62–3.69 | 3.66–3.69 |
| Push, mediator cost | 10.9 · 11.3–11.5 µs | 11.3–11.5 | 11.4–11.7 |
| Change in (A) reaching the sandbox | 0.50 · 0.50–0.52 (final rerun) | 0.71–0.93 | 0.50–0.52 (F62) |
| User's command | 11–16 · 11.1–15.7 ms | 11.1–15.7 | 11.9–13.5 |
| Flood to cut-off | 0.81 · 0.807–0.818 s | 0.807–0.818 | 0.805–0.810 |
| `powercalc`, compiled | 1.87 · 1.87–1.94 s | 1.87–1.94 | 1.87–1.90 |

Every rerun value is inside its criterion except the push row (F62, already in the submission).

**A correction the rerun exposed, whichever option is chosen.** The two-component row says "not
re-measured", but every timing pass measures it (`depth_two.json`, three sandboxes per pass):
94.7–94.9 MB in verification, 95.0 MB in the rerun, +2.6% to +2.9% against 92.3, inside 5%. The
harness's judge (`timing_stats.py`) has no line for it, which is how the table came to say it was not
measured. At 60% of 4,050 MB, 95.0 MB gives a budget of **25** sandboxes against §12.3's 26 from the
development figure. The 17-sandbox floor (ten components, 141 MB → 17) and the 41 for no components
(59.0 MB → 41) do not move.

*Not a contradiction, but worth knowing at the defence:* step 11's depth series (six sandboxes per round)
gives lower figures than the timing passes (three sandboxes): 57.0 against 59.0, 92.9 against 95.0.
Proportional set size divides shared pages among the sandboxes that map them, so more sandboxes leave
each one a smaller share. The table's development figures come from the six-sandbox series. This
explanation follows from how proportional set size is defined; it was not tested separately.

### Option B (recommended): one range across all ten passes

The column becomes "Range across ten passes". This keeps the verification passes' separate boots, which
is what §11.3 promises, adds the submitted version, and removes the push row's special label, because
its range 0.50–0.93 ms now spans the same runs as the rest.

| Quantity | Figure | Range across ten passes |
|---|---|---|
| Memory per sandbox (proportional set size), no platform components | 56.5 MB | 58.6–59.0 MB |
| Memory per sandbox, two components (`http`, `websocket_api`) | 92.3 MB | 94.7–95.0 MB |
| Memory per sandbox, all ten components | 135.6 MB | 141 MB in every pass |
| Mediation latency, one sandbox (median) | 43 µs | 41.2–44.4 µs |
| Mediation latency, 26 sandboxes saturating the mediator (median) | 800 µs | 794–816 µs |
| Durable audit record, written to disk before the action | 3.67 ms | 3.62–3.69 ms |
| Mediator cost of one state change pushed to a sandbox | 10.9 µs | 11.3–11.7 µs |
| A change in Home Assistant reaching the sandbox (median) | 0.50 ms | 0.50–0.93 ms |
| A user's command reaching the integration's code | 11–16 ms | 11.1–15.7 ms |
| A flooding sandbox, from first request to cut-off | 0.81 s | 0.805–0.818 s |
| Start-up to first report, `powercalc`, with bytecode compiled at installation | 1.87 s | 1.87–1.94 s |

Text that changes with it:

- **§12.3, the paragraph before the table**, last two sentences become: "Each figure was measured during
  development and then re-measured in ten passes on frozen code: five during the verification campaign,
  the first three each on a separate boot, and five in a final rerun of the submitted version. The time
  a change in Home Assistant takes to reach the sandbox is the one figure taken from that final rerun,
  for the reason given below (finding F62)."
- **§12.3, the memory paragraph:** "(41 on the verification passes' figure)" becomes "(41 on the
  re-measured figure)", and "with 26 for a sandbox that sets up the two web components" gains "(25 on the
  re-measured figure)".
- **§11.3:** "re-measured in five passes over frozen code, the first three each on a separate boot"
  becomes "re-measured in five passes over frozen code, the first three each on a separate boot, and in
  five more passes at the submitted version".
- **§12.3, the push paragraph:** no change. Its run-to-run account (0.71–0.93, F46's 0.50–0.66, the
  rerun's 0.50–0.52, "a range of 0.5 to 0.9 ms") already matches the new range.

### Option A: the final rerun alone

The column becomes "Range across the final rerun's five passes", filled from the right-hand column
above (two components 95.0). This is simpler to cite, since it is a single tag, but all five passes ran
on one boot, so §11.3's "each on a separate boot" no longer describes the table. That sentence would
have to separate the two campaigns, and the variation between boots would leave the table.

## 2. Table 12.3

The rerun repeated all thirteen rows at the submitted version, and each held as the table states it
(step 7; step 8 43/45). Four cells quote a value that a live run produces, and the rerun produced
different ones:

| Row | Cell now (earlier run) | Final rerun |
|---|---|---|
| `nordpool` | 0.033 in both arms | 0.029 in both arms |
| `regensburg_transport` | 16:05 against 16:04 unconfined, a minute apart | 12:17 in both arms |
| `pirateweather` | 17.6 °C against 17.62 °C | 12.41 °C against 12.39 °C |
| `adaptive_lighting` | brightness 38 from 15.05% against 39 from 15.16% | brightness 255 from 100% in both arms (midday; colour 5,395 K against 5,390 K) |

The other nine cells are unchanged: dew point 9.96 °C and 15 entities; `watchman` 2+1, 1+1, and 1+1
when declared; `powercalc` 8.06, 3.00, 0.00 W, and 8.06 W without the subscription; `scheduler`
brightness 200 at the scheduled second; `dwd_weather` with the same issue and measurement times (03:00,
09:00); `smhi_brandrisk`, `midea_ac_lan`, `localtuya` and `trakt_tv` as stated.

**Recommended:** take the three network rows from the rerun, so that they come from the submitted
version, and keep `adaptive_lighting`'s evening values. At midday its output sits at its 100% ceiling,
which shows the arms agreeing but not the computation behind the number. One sentence after the table
says so: "The final rerun repeated all thirteen at the submitted version with the same outcome; the
network-facing rows give its values, and `adaptive_lighting`'s row an earlier evening run, because at
midday its output stands at its 100% ceiling."
**Alternative:** leave all four cells as they are and add only the first half of that sentence.

§12.2's "42 of its 45 predictions held" stays, because it describes the retest. If wanted, a clause can
add "and 43 when it was repeated at the submitted version, the target now carried".

## Applied 2026-10-16 (Younes: option B, all ten passes; Table 12.3 rerun values for the three network rows, `adaptive_lighting` kept)

Table 12.5 as in option B; §12.3's lead-in and memory paragraph (41 and 25 "on the re-measured figure") and
§11.3 as drafted. Table 12.3: nordpool 0.029, regensburg 12:17 in both arms, pirateweather 12.41 against
12.39 °C, and one sentence before `watchman`'s in the paragraph after the table. The optional "43 when repeated"
clause was not added. `consistency.py` 0 problems.
