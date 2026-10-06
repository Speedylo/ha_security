# Experiment — the refusal flood: a cut-off, and the household's way back

**Target:** Pi 5, (A) = Home Assistant 2026.8.3 · **Feeds:** §7.44 (to be written) ·
**Predictions:** `notes/flood_cutoff_prediction.md` (committed before any code)

## What is here

| | |
|---|---|
| `demo_flood/` | a test integration written for this experiment: one switch, *Demo Flood Misbehave*. Turned on, it retries a host its manifest does not declare (`updates.example.com:443`) in a loop, as a buggy integration retrying a host it missed would |
| `results/` | logs and durable records from the Pi runs (once run) |

The mechanism is in `framework/confine/mediator.py` (the window, `cutoff`, `reinstate`), the
household's half in `framework/ha_bridge/confine_bridge/` (`confine_bridge/cut_off`, `repairs.py`),
and the supervisor that keeps one integration running and restarts it in
`framework/confine/supervise.py`.

## Automated checks (on the Pi, from `~/r2exp/v2/framework`)

    python3 -m confine.selftest_flood                     # F1–F5, the window, S7; no (A) needed
    python3 -m confine.house_a down; python3 -m confine.house_a up --fresh
    python3 -m confine.selftest_real_platform             # includes F7, the Repairs path

## Testing it by hand

(A) listens only on the Pi's loopback, so the browser reaches it through an SSH tunnel.

1. **On the Pi**, start (A) if it is not up, then the supervisor, and leave it running:

       cd ~/r2exp/v2/framework
       python3 -m confine.house_a up --fresh
       systemd-run --user --scope -q python3 -u -m confine.supervise \
           --component ../experiments/flood/demo_flood --python ~/r2exp/ha314/bin/python

   It prints `demo_flood started (run 1, …)`.

2. **On your own machine**, open the tunnel and the interface:

       ssh -L 8123:127.0.0.1:8123 younes@100.86.243.57

   Browse to <http://localhost:8123> and log in as `capstone` (password: `OWNER` in
   `framework/confine/house_a.py`; a throwaway instance on loopback only).

3. Find **Demo Flood Misbehave** (Settings → Devices & services → Confined Integration Bridge, or
   search for it) and **turn it on**.

4. The supervisor prints `demo_flood cut off by the mediator; killing its sandbox`. In the
   interface, **Settings → Repairs** now shows *demo_flood was stopped*. Read it as someone in the
   house would.

5. **Click it, then Submit.** The issue disappears; the supervisor prints `reinstated (recorded);
   starting it again` and `started (run 2, …)`; *Misbehave* is back, off.

6. Optionally turn it on again: a second cut-off and a second issue, with the count starting
   from zero.

7. **Ctrl-C** the supervisor. The durable record of all of it is in
   `~/r2exp/supervise-audit/decisions.jsonl` (since 2026-10-06, one `decisions-<start>-<pid>.jsonl` per supervisor start, finding F31): the refusals, one `cutoff`, one `reinstate`, and a
   `run` record per start.
