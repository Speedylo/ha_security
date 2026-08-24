# Experiment — what isolation primitives does the target host actually offer?

**Run:** 2026-08-24 · **Target:** Raspberry Pi 5, Raspberry Pi OS trixie, kernel 6.12.47,
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
| cgroup v2 `memory` | **MISSING** |

Raw output in `results/pi5.txt`.

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
# /boot/firmware/cmdline.txt — remove cgroup_disable=memory, then add:
cgroup_enable=memory cgroup_memory=1
```

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

## Limits

- **One host, one distribution.** It establishes that the primitives exist on the target, not
  that they exist across the deployment landscape. Home Assistant OS and Docker deployments
  are different environments and are Chapter 6's problem.
- **Presence, not correctness.** The probe shows the kernel offers these features; it does
  not test that a sandbox built on them actually confines anything. That is the adversarial
  evaluation in Chapter 7.
- **Nothing was built.** No supervisor exists yet. This measures the ground, not the building.
