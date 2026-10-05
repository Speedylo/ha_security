# The refusal flood — a cut-off, and a way back for the household. Design and prediction

**Written 2026-10-05, before any code.** §5 is never revised; outcomes are appended below it.
Decision: Younes, 2026-10-05 — the cut-off (§8.7 #15's third option), surfaced in Home Assistant's
Repairs panel, because the person in the house is not assumed to be technical.

## 1. The problem

Every refusal is a durable record: written, fsynced, then answered (§5.12, §6.8). Nothing bounds how
many a sandbox can cause. In W2 (a)'s arm C a shim defect made `midea_ac_lan` retry a refused request
in a tight loop, and the mediator wrote 463,631 refusals, 289 MB, in 7.5 minutes (§7.40.4). That
defect is fixed, but a hostile integration can do the same on purpose. Every decision stays correct;
what is lost is availability. One durable record costs about 3.7 ms, so the mediator has a budget of
about 272 decisions a second, shared by every sandbox, and a flooding one spends all of it.

## 2. What the literature does, and the choice made

Two traditions answer this differently. Logging systems built for diagnostics keep the system up and
lose records: journald drops a service's messages past a per-service rate and writes one "Suppressed N
messages" line, and SELinux's `dontaudit` rules stop frequent, benign denials being logged at all.
Security audit standards take the other side. Common Criteria's FAU_STG.4 requires that, when audit
storage is exhausted, the system can at least *prevent auditable events*; NIST SP 800-53's AU-5 lists
shutting the system down among the responses. Jiang et al. (USENIX Security 2023) name the attack
itself: a "super producer", one unprivileged process generating events fast enough to corrupt a
centralised auditing framework or paralyse the system, caused by the absence of per-process isolation.

The mediator is such a centralised auditor. The cut-off takes the audit standards' side, because
losing records would break S7, but applies "prevent auditable events" to **one sandbox** rather than
the whole system: refusals are counted per integration, and the one that passes the limit is stopped
with a single record saying why. Every other sandbox keeps its share of the budget. *(Sources to be
verified against their primary texts before the report cites them.)*

## 3. The design

**The limit, chosen from data.** Across all 70 runs in `experiments/` whose decisions were recorded,
the most refusals any run made in its entire life is 12 (`demo_weather`, the S3 test, which asks for
undeclared entities on purpose). Real integrations reached 9 (`midea_ac_lan` with nothing declared)
and 2 (`localtuya`). The flood ran at about 1,000 refusals a second. The limit is **100 refusals in any
10-second window**: about eight times the worst honest *run*, and reached by a flood in about a tenth of
a second, so a flood costs about 100 records (≈ 0.4 s of fsync) instead of an unbounded number.

**What is counted.** Only refusals of requests the sandbox itself sent (`_handle_ready`), including a
refusal found while acting. Refusals of a *user's* command (`command`: no sandbox running, queue full)
are recorded as before but not counted, since they are not the sandbox's doing.

**What happens at the limit.** The mediator writes one `cutoff` record (integration, count, window),
closes the sandbox's channel, and marks the integration as cut off. The supervisor kills the sandbox
through its cgroup. A cut-off integration **cannot be registered again** until it is reinstated: a
respawn would otherwise reset the count and the flood would resume in bursts (systemd's start limit
behaves the same way: a unit that fails too often stays failed until an administrator resets it).

**What the household sees.** The mediator tells the bridge in (A), which raises a Repairs issue in
plain language: the integration was stopped because it kept trying to do things it is not allowed to
do, this is usually a bug, check for an update, then restart it. The issue's one action is **Restart**.
Confirming it sends a restart request to the mediator over the bridge's existing command stream; the
mediator writes a `reinstate` record and clears the mark, and the supervisor starts the sandbox again.
**Restarting never widens permissions**: the sandbox is registered again under the same manifest,
re-read at registration as every spawn is (§8.7 #14), so a user who clicks without reading cannot make
anything less safe. The worst case is another flood and another cut-off.

**Known limit, stated now.** The mark lives in the mediator's memory. A restart of the mediator itself
forgets it, so a hostile integration gets one more burst — at most 100 records — per mediator start.
Persisting the mark is possible and is not built.

**For the manual test**, a small integration of our own, `demo_flood`, publishes one switch,
*Misbehave*. Turning it on from (A) makes it retry an undeclared host in a loop, as a buggy
integration retrying a host its manifest misses would. A small supervisor keeps it running against (A)
and restarts it when told to. The flood is started from the house's own UI, so the whole path — a
user's command in, the flood, the cut-off, the Repairs issue, the restart — is one a person can drive.

## 4. What is built

1. `Mediator`: the per-integration window, the `cutoff` and `reinstate` records, the mark, and the
   refusal to register a cut-off integration. `AuditLog` gains the two record kinds, and
   `reconcile` keeps memory and the durable log in step.
2. `confine_bridge`: an admin-only `confine_bridge/cut_off` command that raises the issue, and a
   `repairs.py` fix flow whose confirm step sends the restart request.
3. `RealPlatform`: forwards a cut-off to the bridge, and a restart request to the mediator.
4. `selftest_flood` (stand-in platform, no (A) needed) and an (A) case in `selftest_real_platform`.
5. `demo_flood` and the supervisor, under `experiments/flood/`.
6. Chapter 4: threat T19, denial of service against the audit log.

## 5. Predictions

| | Prediction | Confidence |
|---|---|---|
| **F1** | A flooding sandbox is cut off after exactly 100 counted refusals; the durable log holds those 100 refusals and **one** `cutoff` record for it, and nothing after | high |
| **F2** | Time from the first refusal to the cut-off is under 1 s on the Pi | high |
| **F3** | A second sandbox's requests are answered throughout the flood, and none of its decisions is refused or delayed past 1 s | medium — it shares one loop and one fsync |
| **F4** | A cut-off integration cannot be registered again until it is reinstated, and the `reinstate` record is written before it can | high |
| **F5** | A user's refused commands do not count towards the limit | high |
| **F6** | No honest run trips it: all suites, `nordpool`, and the (A) end-to-end runs show zero `cutoff` records | high |
| **F7** | On the Pi, the Repairs issue is visible in (A) within 1 s of the cut-off, and confirming it brings `demo_flood` back, with its switch, under the same manifest | medium — first use of the Repairs API |
| **F8** | Something not listed is found | medium — §7.27's lesson; every first use of a real component has found one |

## 6. How Younes tests it by hand

(A) listens only on the Pi's loopback, so the browser reaches it through a tunnel:

    ssh -L 8123:127.0.0.1:8123 younes@100.86.243.57      # then open http://localhost:8123

1. Log in to (A) (`capstone` / the password in `house_a.py`, local to a throwaway instance).
2. Start the supervisor on the Pi (command in `experiments/flood/README.md`, once built).
3. Find *Misbehave* under the Confined Integration Bridge's device, and turn it on.
4. Settings → **Repairs** shows the issue within a second or so. Read it as a household member would.
5. Click it, then **Submit**. The issue disappears and *Misbehave* comes back, off.
6. Optionally, turn it on again: a second cut-off, a second issue.

---

## 7. Outcomes, 2026-10-05 (appended; §5 is unchanged)

Evidence: `experiments/flood/results/pi_20261005/`. Built in c16a151 and 354dc5d, fixed on the Pi in
705ff12 and in `selftest_channel` (below).

| | Outcome |
|---|---|
| **F1** | **Held.** `selftest_flood` on the Pi: exactly 100 refusals on disk for the flooder, then one `cutoff`, then nothing. The supervised `demo_flood`, pressed by a user in (A): 100 refused `network.egress` decisions to `updates.example.com:443`, one `cutoff`, then `reinstate`, `run` and the switch published again (`supervise_audit_run3/`) |
| **F2** | **Held, on the second run.** 0.81 s from the first refusal to the cut-off with the log on the SD card (`selftest_flood_disk.log`; the neighbour's grants fsynced too), measured in 0.2 s steps. The first run said 0.20 s and is **not** the result: its log was in `/tmp`, which is tmpfs on the Pi, so no fsync touched a disk (`selftest_flood.log`, kept and labelled). In the household run the cut-off came 0.41 s after the user's press |
| **F3** | **Held.** On disk, the neighbour was answered 235 times during and after the flood, every answer a grant, the slowest 26.1 ms |
| **F4** | **Held** (`selftest_flood`, Pi): registration refused while cut off; `reinstate` recorded before the new `run`; a second flood cut off the same way |
| **F5** | **Held** (`selftest_flood`, Pi): twenty refused user commands, recorded and answered, none counted |
| **F6** | **Wrong, and instructively.** `nordpool` (16/16, nothing refused in arm B, its arm C refused as before) and 25 of 26 suites tripped nothing. **`selftest_channel` was cut off**: its `demo_b` holds no manifest and times the refusal path with 2,000 refused requests in a tight loop, which is a flood by the only measure the mediator has, the rate. The cut-off cannot tell a benchmark of refusals from a hostile loop. The harness now lifts the limit for that one measurement, stated in its code; re-run, it passes with medians of 199–204 µs against 181–197 µs in the two previous runs, so the counting costs nothing measurable. The limit was not changed |
| **F7** | **Held.** `selftest_real_platform` 45/45: the issue was in (A) 302 ms after the cut-off (an upper bound; it includes the mediator thread's 0.3 s idle return), fixable, `cut_off`, naming the integration; the fix flow's confirm then submit reinstated it, recorded as "reinstated by a user, from the Repairs panel", and the issue was gone. (A) serves all four strings of the plain-language text. Household run: issue present at the first look after the cut-off; restart 0.10 s after submit; *Misbehave* back, off, 0.62 s later |
| **F8** | **Held, three times over, as expected of a first real use.** (1) A restarted integration given its previous data directory was never set up: the private instance finds the stored config entry, the config flow aborts `already_configured`, and flow mode never loads the stored entry. Every harness gives each run a fresh directory, and the runtime silently assumes it. The supervisor now does too, which means **keeping `/sandbox/data` across restarts — what an OAuth integration needs to stay logged in (§7.42) — is not supported**. (2) F6's benchmark. (3) Three defects in the new tooling: the supervisor did not mount `egress_shim`; the first driver script opened a second `RealPlatform`, which took the bridge's one-subscriber command stream from the supervisor, so the press reached the script; and a supervisor started in the background ignored SIGINT (inherited as ignored) and outlived `pkill -INT` — it now stops on SIGTERM, verified |

**What this establishes.** A sandbox that floods the mediator with refused requests now costs a bounded
amount — 100 records and under a second on the Pi — and is stopped, while another sandbox keeps being
answered. The person in the house is told in Home Assistant's own Repairs panel, in plain words, and
gets the integration back with one button that cannot widen its permissions. Every step is recorded.

**What it does not.** The limit sees only a rate, so an honest integration that is refused at more than
10 a second for 10 seconds is stopped too (F6). The cut-off mark is in memory only (§3). Data does not
persist across a restart (F8 (1)).
