# Verification 4.11 — acceptance, the human path

## The run (2026-10-06, Younes, by hand in a browser): passed

Run on `verify-2026-10-accept` with the checklist in `notes/acceptance_4_11.md`. Every step passed,
and the only terminal use was step 1 (starting things) and reading the supervisor's lines.

| Step | Evidence (`Test Screenshots/`) | Result |
|---|---|---|
| 1 start (A) under the keeper, then the supervisor | `Screenshot (222).png`: `(A) restarted`, `demo_flood started (run 1, pid 62092)` | pass |
| 2 log in | (no screenshot) | pass |
| 3 see the confined integration's entity | `(199)`: the `demo_flood` device, "Runs in a sandbox, under its manifest", *Demo Flood Misbehave* | pass |
| 4 operate it | `(199)` switched on; `(222)`: cut off at 16:51:23 | pass |
| 5 read the Repairs issue | `(200)`: "demo_flood was stopped"; `(201)`: what happened and why in plain words, one **Submit**, "Restarting does not give it any new permissions" | pass |
| 6 act on it | `(202)`: "The issue is repaired!"; `(222)`: reinstated (recorded), run 2 at 16:51:48 | pass |
| 7 restart (A) from its own interface | `(203)`, `(221)`: System → Restart Home Assistant; `(222)`: went away 16:52:17, back and run 3 at 16:52:22, with nothing typed | pass. Before F42's fix this step would have stopped (A) for good |
| 8 stop | `(222)`: `stopped` | pass |

**The durable record** (`decisions-20261006T165043-62079.jsonl`, copied from the Pi): 110 records,
3 `run`, 105 decisions, 1 `cutoff`, 1 `reinstate`. The hash chain verifies with no sequence, link or
hash break. Every MAC fails to verify here, as it must: the key lives only in the mediator that wrote
the log (§6.8.4). The run reports are named per start (`…-62079-run1` to `run3`), F35 R2's fix.

**An observation, not a failure.** Repairs listed two other issues that come from (A)'s own setup
and not from the framework: *Unsupported installation method* (Home Assistant Core installed in a
plain virtual environment) and *HTTP YAML configuration is ignored after migration*. Someone in the
house sees three repairs, one of them the framework's. That is worth clearing before the defence
demo, so that the only issue on screen is the one the demo is about.

## Before the run

### What checking the checklist found (2026-10-06): finding F42

Step 7 restarts the house's Home Assistant from its own interface. Tried first through the same
service the Restart button calls (`homeassistant.restart`), it **stopped (A) for good**. In this
release, `hass` does not start itself again: it exits with code 100 and expects a process manager
to, as Docker or systemd does in a real installation. `house_a.py` started `hass` with no such
manager. Step 7 would have failed during the run, and in a defence demo.

`house_a` now runs `hass` under a keeper (`house_a keep`), which starts it again on exit code 100.
A SIGTERM is passed to `hass`, and the keeper then stops instead of restarting. Checked on the Pi:

- the restart service: a new `hass`, the same keeper, running again 6 s later; `down` ends both;
- step 7's whole path, with a supervisor running (`sup.log`): the supervisor sees (A) go and says
  so in one line, then starts `demo_flood` again 5 s after the restart, with nothing typed;
- (A)'s restart suite, which stops and starts (A) through `house_a`: 48/48
  (`real_platform_restart.log`);
- FI1, FI4 and the backstop, which take (A) down and up through `house_a`: every criterion held
  (`faults/results.txt`).

**A side effect of R7, fixed with it.** Since F35 R7, the mediator refuses to connect to an (A)
that has not finished starting, and `house_a up` returned as soon as (A)'s API answered, which is
earlier. So a connection straight after `up` was refused. Found while testing the keeper, where the
first attempt to request a restart was refused with `state NOT_RUNNING`. `up` and `restart` now
also wait for (A) to report `RUNNING`, and a connection straight after `up` is accepted.
