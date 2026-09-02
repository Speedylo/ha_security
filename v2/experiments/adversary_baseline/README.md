# Experiment — the 2021 file-theft pattern, with and without the framework

**Run:** 2026-09-02 · **Target:** Raspberry Pi 5, 4 GB, aarch64 · **Feeds:** §7.13 ·
**Discharges:** §7.5's S8 criterion

S8's verification was fixed in §3.5 before any implementation existed, and it is deliberately
not "the attack is blocked":

> "the 2021 file-theft pattern is reproduced against a baseline installation **and** shown to be
> blocked under the framework."

Blocking an attack that would not have worked anyway proves nothing. `selftest_adversary` is the
confined half; `selftest_adversary_baseline` is the half that makes it mean something.

## Result

| | Unconfined | Confined |
|---|---|---|
| **Canaries recovered** | **2 of 2** | **0 of 2** |
| Attacks returning data | 11 | 0 |
| 2021 traversals that worked | 5 | 0 |
| Counts | BLOCKED 14 · EMPTY 4 · LEAKED 11 · NOT RUN 2 · UNMEDIATED 1 | BLOCKED 21 · EMPTY 10 · DENY 6 · PERMIT 1 |
| Verdict | PASS — reproduces | PASS — nothing reached it |

`open("../../secrets.yaml")` returns the credential unconfined and raises **`FileNotFoundError`**
confined — not `PermissionError`. The file is not in the mount namespace, so nothing was refused.

Raw output: `results/pi5_unconfined.txt`, `results/pi5_confined.txt`.

## What only the pairing shows

**Blocked in both arms — not the framework's doing:** `/etc/shadow` (root-only), connecting to
`127.0.0.1:8123` (nothing listening), resolving `example.invalid` (no such name). Reported alone,
the confined run would credit the design with three controls it does not provide.

**Succeeds unconfined, refused confined — the design's:** `unshare(CLONE_NEWUSER)` and
`ptrace(PTRACE_TRACEME)`, both by seccomp.

**Absent unconfined:** the mediated family reports `UNMEDIATED`. An unconfined integration is not
denied `lock.unlock`; there is nobody to ask.

**Incidental, and S7's:** unconfined, the audit-log search found a real `.jsonl` audit log on the
host. Confined the same search returns `EMPTY`.

## Corrections to §6.9 that came out of this

1. **`/dev/zero`.** The sweep called `getsize()` and read anything reported small; a character
   device reports zero. The attack read an infinite stream and was killed for memory, and §6.9
   read that as the resource limit stopping a search for secrets. Restricted to regular files it
   **completes and finds nothing** — `EMPTY`, the stronger outcome.
2. **Counts.** Over §6.9's original 37 attacks, *21 blocked / 9 empty* → **20 blocked / 10 empty**.
3. **Withdrawn.** An intermediate version reported S9's demonstration invalid. It is not — the
   harness had stopped distinguishing a kernel kill from its own timeout. §7.13.4 has the detail.

S9 gains a second, better demonstration anyway: an attack that **allocates** memory rather than
reading files, so it does not depend on how much data happens to be bound into the sandbox.

## The harness finding

The unconfined arm hung three times, fifteen minutes each, reporting nothing. `PTRACE_TRACEME`
succeeds unconfined; from then on every signal — including `SIGCHLD` from the attack's own forked
children — stops the process for a tracer that never answers. The harness had always trusted a
forked child to finish and to die, and that held for the whole history of the suite **because
confined, seccomp refuses the call**. It was fragile only where the attacks succeed, and that arm
had never been run.

## Reproducing

```bash
python3 -m confine.selftest_adversary_baseline          # unconfined; passes when it leaks
systemd-run --user --scope -q python3 -m confine.selftest_adversary
```
