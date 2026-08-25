# Experiment — what isolation primitives does the target host actually offer?

**Run:** 2026-08-24 · **Re-run 2026-08-25** after enabling the memory controller · **Target:** Raspberry Pi 5, Raspberry Pi OS trixie, kernel 6.12.47,
aarch64 · **Feeds:** §5.7.4

§5.7 chooses Linux namespaces + seccomp-BPF + cgroup v2 as the isolation primitive. That
choice is only defensible if those primitives are present on the C4 device, so they were
probed rather than assumed.

## Result

| Primitive | Result |
|---|---|
| Unprivileged user + net + pid namespaces | **Available** — created as an ordinary user; inside: uid 0, pid 1, one interface |
| All seven namespace types (mnt, uts, ipc, pid, net, user, cgroup) | Present |
| seccomp-BPF | Present — `kill_process kill_thread trap errno user_notif trace log allow` |
| cgroup v2, controllers `pids` `cpu` `io` `cpuset` | Available |
| cgroup v2 `memory` | **MISSING** on a stock install → **AVAILABLE and enforcing** after the boot change below |
| **S9 cap actually bites** | **Yes** — 192 MB against a 64 MB cap is OOM-killed; the same allocation uncapped succeeds. **Run unprivileged** |

Raw output: `results/pi5.txt` (stock, memory controller absent) and
`results/pi5_memory_enabled.txt` (after the boot change, with the enforcement check).

## The two findings that changed the design

**1. The supervisor need not be privileged.** Unprivileged user namespaces work on the
target, so sandboxes can be created without granting the framework root. A confinement
mechanism that must run as root to confine anything enlarges the surface it exists to reduce,
so this is worth having for its own sake and not only for convenience.

**2. `memory` is disabled by default on Raspberry Pi OS.** The probe found
`cgroup_disable=memory` on the kernel command line — the distribution's default — so the
memory controller is absent and **S9 cannot bound memory on a stock installation**. Enabling
it needs a boot-time change and a reboot:

```
# /boot/firmware/cmdline.txt — append to the single line, then reboot:
cgroup_enable=memory cgroup_memory=1
```

> **Corrected 2026-08-25, and the correction is the useful part.** This README first said to
> *remove* `cgroup_disable=memory` from `cmdline.txt`. On a Pi 5 that instruction cannot be
> followed: the parameter is on `/proc/cmdline` but **is not in `cmdline.txt` at all** — the
> firmware prepends its own parameters ahead of the file's contents. An operator following the
> original advice searches the file, does not find the string, and reasonably concludes the
> machine is already configured. `cgroup_enable` is parsed after `cgroup_disable`, so
> *appending* the enable is what overrides it, and there is nothing to remove.
>
> This was found by re-running the probe after a reboot and getting the same `MISSING` result.
> `probe.sh` now inspects `cmdline.txt` and prints whichever of the two instructions applies,
> because a probe that diagnoses correctly and then prescribes something impossible is worse
> than one that says nothing.

S9 exists because T16 is the one threat Chapter 4 found with no control at all. A framework
that started anyway, silently unable to enforce it, would leave T16 uncontrolled while
implying protection — which is the §1.6 complaint about the status quo, reproduced under a
security label. §5.7.4 therefore requires the framework to **refuse to start with a stated
reason** when the memory controller is unavailable, which is N3 applied to a concrete case.

## Reproducing

```bash
./probe.sh              # human-readable
./probe.sh > out.txt    # record it
```

Needs only coreutils and util-linux, and deliberately does not require root — needing root
would itself have been a finding.

## A third finding, from the re-run: how the sandbox must be placed in its cgroup

Verifying enforcement turned up an implementation constraint the first probe could not have
found. **An unprivileged process cannot create a cgroup and then migrate an existing process
into it** — migration requires write access to the *common ancestor* of source and
destination, and that is root-owned. The first attempt failed with `Permission denied` for
exactly this reason.

The consequence drawn at the time was that a sandbox must be placed in its cgroup **at
creation** (`CLONE_INTO_CGROUP`, or the equivalent), rather than confined after it is already
running.

> **Superseded 2026-08-25 by `../cgroup_placement/`, and the correction matters.** That
> consequence does not follow. `clone3(CLONE_INTO_CGROUP)` fails with the same `EACCES` from
> the same position, because the kernel checks the common ancestor whether the process is being
> moved into the cgroup or created inside it. What actually binds is **where the supervisor
> runs**: inside the subtree systemd delegates to its user — a systemd user unit — and not an
> ssh session, which is where this probe was run from and which is outside it. The finding
> above is correct; only the rule inferred from it was wrong, and it was inferred from a single
> failed command rather than measured. §6.4.1 carries the corrected version.

## Limits

- **One host, one distribution.** It establishes that the primitives exist on the target, not
  that they exist across the deployment landscape. Home Assistant OS and Docker deployments
  are different environments and are Chapter 6's problem.
- **Presence, not correctness — with one exception, added 2026-08-25.** The probe shows the
  kernel offers these features; it does not test that a sandbox built on them actually confines
  anything, which is the adversarial evaluation in Chapter 7. The exception is S9: because
  "the controller is listed" and "the limit is enforced" are different claims, and only the
  second is what S9 requires, the memory cap is now tested for effect rather than presence.
  That check is deliberately the *only* correctness test here, and it needs `systemd-run` and
  `python3` where the rest of the script needs neither.
- **Nothing was built.** No supervisor exists yet. This measures the ground, not the building.
