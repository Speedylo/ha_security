# F59, a restarted integration loses what it stored: predictions for the fix

**Written 2026-10-11, before the test is written and before any run.** F59 (new; until now a limit
stated in §9.7 and Table 9.2): the supervisor gives every start of an integration a fresh data
directory (`supervise.py`, `launch`), so a restarted integration loses its configuration entry and
everything else it stored, an OAuth token included. Found on the Pi on 2026-10-05: with the
directory reused, the sandbox's Home Assistant loads the stored entry but never sets it up, and flow
mode runs the setup dialog again, which stops as `already_configured`; the integration then ran and
published nothing. **Younes decided on 2026-10-11 to fix it**, keeping only Home Assistant's
`.storage`, durably, with a size check at start. Commit this note before the test runs; do not edit it
after a run (`verify/prereg.py`). Results go to `experiments/verify/results/f59/`.

## 0. Why not simply keep the data directory

Inside the sandbox the writable data directory is Home Assistant's whole configuration directory.
The integration is placed in it as a symbolic link to the read-only copy, and `place_component`
creates the link only `if not link.exists()`. Kept across starts, the directory would let an
integration replace the link on one run with a directory of its own code, which the next start would
load: F57's gate checks the host's copy, which is unchanged, so it would pass while different code
ran. It could equally plant `custom_components/http`, which Home Assistant prefers to its own. Today
this is impossible only because every start is fresh. The fix therefore keeps **data that is never
loaded as code**, and nothing else.

## 1. The rule

1. **Every start still gets a fresh configuration directory**, which the host creates; the
   integration's code is linked into it from the read-only copy, as now. Nothing the integration
   writes there survives the start.
2. **Only `.storage/` is kept**, in one folder per integration that survives restarts of the
   sandbox, of the supervisor and of the Pi: by default `<config-root>/confine/kept/<domain>/`, beside
   the approvals, or `--keep-dir`. It is mounted read-write at `/sandbox/data/.storage`. Home
   Assistant keeps its configuration entries, registries and an integration's `Store` files there,
   all JSON it reads as data.
3. **A start with a stored entry sets it up, as Home Assistant's own start-up does**
   (`async_setup_component`, which sets up every stored entry of the domain, `setup.py:467` at
   2026.8.3), and does not run the setup dialog. With no stored entry, the dialog runs as now.
4. **The kept folder is held to the manifest's `disk_mb`** (default 64 MB), the limit `/tmp` already
   has, counted separately. Before each start the supervisor adds up the apparent size of every file in
   it, without following links. Above the limit, the integration is not started; the supervisor says
   so, and the house sees F57c's `not_started` issue with the reason `too_much_data`. Its one button
   is **Try again**, which asks the supervisor to check again and grants nothing.
5. **Each start's throwaway folder is deleted as soon as its sandbox is gone** (Younes, 2026-10-11).
   On the Pi `/tmp` is a 2 GB tmpfs, held in memory, and until now every start's folder stayed there
   until the supervisor exited. The deletion is in `stop()` and `reap()`, **after** the cgroup is
   killed and the sandbox's process waited for, so nothing still running can write into it. It uses
   `shutil.rmtree`, which on Linux removes a link without following it
   (`rmtree.avoids_symlink_attacks`), so a link the integration planted towards the host's files
   removes only the link. The kept `.storage` is not reachable through it: the bind mount exists only
   in the sandbox's mount namespace, and on the host the throwaway folder's `.storage` is an empty
   directory. A directory the integration made unreadable (mode `000`) would make `rmtree` give up
   on it, so each failure restores the owner's permissions and retries once; whatever still cannot be
   removed is said in a line. What is lost is what the integration wrote there: the sandbox's report and
   Home Assistant's log are kept in the audit directory, as now.

**What this does not do.** The check is at start: within one run the folder can grow past the limit,
and the next start refuses. A change stored in the last second before the sandbox is killed can be
lost, because the supervisor kills the sandbox rather than stopping Home Assistant, and Home
Assistant writes its entries one second after a change (`SAVE_DELAY`). And an OAuth integration
still cannot be set up under the supervisor in the first place: the supervisor answers the setup
dialog with nothing, and an OAuth login needs a person's browser. This fix keeps an entry once one
exists; how the first login is done under the supervisor stays future work. A supervisor killed
with SIGKILL cannot delete its folders; they stay in `/tmp` until the Pi restarts, which empties it.

## 2. The change

- **`sandbox.py`.** `SandboxSpec.kept_dir: str | None = None`. When set, the mount step creates
  `.storage` in the fresh data directory, refusing anything already there, and binds `kept_dir`
  read-write onto it. Every harness that does not set it is unchanged.
- **`sandbox_runtime.py`, flow mode.** If `hass.config_entries` holds an entry for the domain after
  `async_initialize`, the stored entries are set up through `async_setup_component(hass, domain, {})`
  and the report says `"flow": {"stored": <count>}`, with one line on standard error saying so
  (the run's log); otherwise `drive_flow` runs as now.
- **`supervise.py`.** `--keep-dir`; the folder created `0700` if missing; `kept_size` (the walk);
  `launch` checks the size, then registers, then starts with `kept_dir` set, and prints each
  start's throwaway folder (`<domain> run <n> folder <path>`), which step 12 reads. The fresh directory per
  start and its comment stay, reworded. `remove_start_dir` (rule 5), called from `stop()` and
  `reap()`. A retry request from (A) for its own integration, while it is not running, calls `launch`
  (F57c's `retry_handlers`).
- **`ha_bridge/confine_bridge`.** `not_started` also accepts `too_much_data`; its fix flow sends
  `{"retry": ...}`. Its words, the summary:

> **{name} was not started**
>
> **{name}** was not started because it has stored more information than it is allowed to keep.

And the screen behind it:

> **Try {name} again?**
>
> This limit protects your system from running out of storage space. It is usually caused by a bug
> in the integration, and it is worth checking whether an update is available for it. The person who
> looks after this system can clear what it stored.
>
> Select **Try again** to check again. Trying again does not give it any new permissions or any more
> space; if it still has too much stored, it will stay stopped.

- **`selftest_supervise.py`.** Its supervisors get a `--keep-dir` in the suite's temporary directory,
  so no test writes into the repository.

## 3. The test, written first

A new suite, `selftest_keep` (29 suites), against (A), with a new test integration,
`experiments/keep/demo_keep`, written for this. Its setup dialog asks nothing and stores
`{"token": "login", "refreshes": 0}`, standing for an OAuth login. Each setup reads its entry, stores
`{"token": "refresh-<n>", "refreshes": n}` with `n` one more than it read, standing for a token
refresh, and publishes a sensor whose state is that token. It then **plants code**: it replaces its
`custom_components/demo_keep` link with a copy of its own code plus a file `PLANTED`, and reports
whether that worked in the sensor's `plant` attribute. A copy that finds `PLANTED` beside itself
publishes the state `planted` instead of a token. Last, it makes a directory in its configuration
folder holding one file, then sets the directory's mode to `000`, so nobody may read it, and reports
that in the sensor's `locked` attribute: the case rule 5's retry exists for.

1. Supervisor A, with a new empty kept folder and `demo_keep` approved first (F57), as `selftest_supervise`
   approves `demo_flood`: the integration starts, and its sensor reads
   `refresh-1`.
2. The plant succeeded (`plant` attribute `done`), so the test of rule 1 is not vacuous.
3. The kept folder holds `core.config_entries` naming `demo_keep`.
4. A ended (SIGTERM) at least 3 s after the sensor read `refresh-1`; supervisor B started with the same
   kept folder: the sensor reads **`refresh-2`**: the stored entry was set up and its data read back.
5. B's run log (its Home Assistant log, in the audit directory) says it set up 1 stored entry
   and ran no setup dialog. The report on standard output is no use here: it is printed when a
   run ends by itself, and the supervisor kills the sandbox.
6. The sensor does not read `planted`: the planted code was not loaded.
7. B ended; a sparse file of `disk_mb` + 1 MB written into the kept folder, as an integration that
   stored too much would leave it; supervisor C: it says "not started", no sandbox starts.
8. (A) shows `not_started_demo_keep` with the key `too_much_data`, fixable.
9. **Try again** submitted with the file still there: still not started, and the issue is back.
10. The file removed, **Try again** submitted: C starts the integration (run 1), and the sensor reads
    `refresh-3`.
11. And the issue is gone.
12. (A) restarted, as `selftest_supervise` does: C stops run 1 and, once (A) is back, starts run 2.
    **While C is still running**, run 1's throwaway folder is gone, its `000` directory included
    (`locked` was `done`), and the kept folder still holds `core.config_entries` (rule 5; the
    supervisor prints each folder's path). The check is made while C runs because a supervisor that
    exits deletes its whole root anyway, so only a restart inside one supervisor shows rule 5.
13. Run 2's sensor reads `refresh-4`: a restart inside one supervisor keeps the entry too.

## 4. Predictions

**K1, the test before the fix** (the test commit, on the Pi with (A) up and F57c's bridge): the
supervisor does not know `--keep-dir` yet, so the test commit adds the option and nothing else to
`supervise.py` (accepted, ignored). Steps 1 and 2 pass: a fresh start runs the dialog, and the plant
works within one run. The suite stops at **step 3**, because nothing mounts the kept folder, so it
stays empty. Exit 1.

**K2, after the fix**: `selftest_keep` passes every check on the Pi, exit 0. Not run on the laptop,
which has no (A).

**K3, every suite twice** at the tag, on the Pi, (A) restarted first: **29/29 twice**.

**K4, `nordpool` end to end** at the tag: 16/16. Its harness sets no `kept_dir` and starts fresh, so
flow mode takes the dialog path as before.

**K5, mutants** at the tag: every mutant patching `sandbox.py`, `sandbox_runtime.py` or `supervise.py`
stays killed, M41–M44 (F57c) too, plus five new ones:
**M45**, the kept folder is mounted as the whole data directory (the design §0 rejects), killed by
step 6 (`planted`); **M46**, the size check always passes, killed by step 7; **M47**, flow mode always
runs the dialog, killed by step 4; **M48**, the throwaway folder is not deleted, killed by step 12;
**M49**, the deletion does not restore permissions before retrying, killed by step 12 (the `000`
directory is left).

## 5. After the runs

Ledger line; Appendix F row F59 (59 findings); the findings table; §9's limit paragraph (the restart
limit becomes the three limits in §1's "What this does not do"), Table 9.2 and §14; `REPRODUCE.md`
names the kept folder; `.gitignore` gains `confine/kept/`.
