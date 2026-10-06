# Verification 4.11 — acceptance, the human path

The run itself is Younes's, by hand, with the checklist in `notes/acceptance_4_11.md`; its results go
here when it is done.

## What a check of the checklist found before the run (2026-10-06): finding F42

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
