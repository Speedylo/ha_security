# Acceptance, the human path (verification 4.11) — the run and its pass conditions, written before it

**2026-10-06.** Plan §7.11. This is the one phase that has to be done by a person: the question is
whether someone in the house can use what the framework puts in Home Assistant's interface, and a
script clicking through it would not answer that. It is also the defence demo's rehearsal. Younes
runs it, by hand, in a browser.

**Code under test:** `verify-2026-10-accept`, which is `verify-2026-10-review` plus F42's fix to
`house_a.py`. Use that tag's clone on the Pi, `~/r2exp/verify-accept/v2`, not the older `~/r2exp/v2`.

*Checked before the run (2026-10-06):* step 7 as first written would have failed. Restarting (A)
from its own interface stopped it for good (finding F42, fixed). Step 7's path has since been run
through the same service the button calls, with a supervisor running, and passed
(`experiments/verify/results/phase4/acceptance/`). The run below is still the test: the check
used the API, not a browser.

**Pass, overall:** every step below works without touching a terminal, apart from step 1 (starting
things) and reading the supervisor's lines. Anything that needs a terminal, or reads as wrong to
someone who did not build it, is a finding.

## The run

1. **On the Pi** (terminal allowed here):

       cd ~/r2exp/verify-accept/v2/framework
       python3 -m confine.house_a restart     # so (A) runs under F42's keeper
       systemd-run --user --scope -q python3 -u -m confine.supervise \
           --component ../experiments/flood/demo_flood --python ~/r2exp/ha314/bin/python

   *Pass:* it prints `demo_flood started (run 1, …)`, with no traceback.

2. **On your machine:** `ssh -L 8123:127.0.0.1:8123 younes@100.86.243.57`, then browse to
   <http://localhost:8123> and **log in** as `capstone` (password: `OWNER` in `house_a.py`).
   *Pass:* the dashboard loads, and no onboarding wizard appears.

3. **See the confined integration's entity.** Settings → Devices & services → Confined Integration
   Bridge, or search for *Demo Flood Misbehave*. *Pass:* it is there, and off.

4. **Operate it:** turn *Misbehave* on. In this demo integration, turning it on is the flood.
   *Pass:* within about a second the supervisor prints `demo_flood cut off by the mediator`, and
   the interface shows nothing broken beyond the switch becoming unavailable.

5. **Read the Repairs issue as someone in the house would.** Settings → Repairs. *Pass:* an issue
   named for demo_flood says, in plain language, that it was stopped and what pressing the button
   will do, and it offers one action. That action restarts the integration and never widens what
   it may do.

6. **Act on it:** open the issue and submit. *Pass:* the issue disappears; the supervisor prints
   `reinstated (recorded); starting it again` and `started (run 2, …)`; *Misbehave* is back, off.

7. **Restart the house's Home Assistant from its own interface** (Settings → System → the power
   icon → Restart Home Assistant). *Pass:* after the restart, *Misbehave* is still there, and the
   supervisor prints `went away`, then `back; starting demo_flood again` and `started (run 3, …)`,
   with nothing typed in a terminal. This is F29's recovery, seen from the house's side for the
   first time.

8. **Stop:** Ctrl-C the supervisor (terminal allowed). The durable record is in
   `~/r2exp/supervise-audit/decisions-<start>-<pid>.jsonl`.

## Record

For each step: pass or fail, and a sentence on anything that read as odd. A screenshot of steps 3, 5
and 7 is worth keeping for the defence. Results go in
`experiments/verify/results/phase4/acceptance/`.
