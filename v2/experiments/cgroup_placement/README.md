# Experiment — where must the supervisor run, for it to put a sandbox in a cgroup?

**Run:** 2026-08-25 · **Target:** Raspberry Pi 5, Raspberry Pi OS trixie, kernel
6.12.47, aarch64, uid 1000 · **Feeds:** §6.4 · **Corrects:** §5.7.4, §6.3.4

§5.7.4 recorded a finding and drew a design rule from it. The finding was real: an
unprivileged process could not create a cgroup and then move a running process into it,
because migration needs write access to the **common ancestor** of source and destination and
that ancestor was root-owned. The rule was *"the sandbox must therefore be placed in its
cgroup **at creation**, not confined after the fact"*.

The rule contains an assumption the failed command could not test — that placement at
creation is permitted where migration is not. **It is not.** This experiment establishes what
the actual constraint is, because §6.4 has to implement it and the two candidate rules lead to
very different supervisors.

## Result

Four operations, attempted from two positions, all as an ordinary user:

| | as launched (ssh session) | inside the delegated subtree |
|---|---|---|
| own cgroup | `user-1000.slice/session-N.scope` | `user@1000.service/app.slice/run-….scope` |
| common ancestor with destination | `user-1000.slice` — **owned by root** | `…/app.slice` — **owned by the user** |
| `mkdir` the sandbox's cgroup | **OK** | **OK** |
| migrate a running child in | **EACCES** | **OK** |
| child migrates itself in | **EACCES** | **OK** |
| `clone3(CLONE_INTO_CGROUP)` | **EACCES** | **OK** |
| 192 MB against a 64 MB cap | untestable | **killed — cap enforced** |

Raw output: `results/pi5_placement.json`.

## What this changes

**Placement at creation is governed by the same permission rule as migration.**
`clone3(CLONE_INTO_CGROUP)` fails with exactly the same `EACCES`, in the same position, as
writing a pid into `cgroup.procs`. The kernel checks the common ancestor either way; creating
the process there is not a way around a rule about *moving* it there, because it is not a rule
about moving.

So §5.7.4's rule does not follow from §5.7.4's finding. The correct statement is about
**where the supervisor is**, not **when the placement happens**:

> **The supervisor must run inside the cgroup subtree that is delegated to its user.** On a
> systemd host that means being started as a systemd *user unit*; an interactive login or an
> ssh session lands in `user-<uid>.slice/session-N.scope`, which is outside it, and from there
> no placement mechanism works at all.

Note the trap this closes, because it is the reason the original finding was misread:
`mkdir` **succeeds** from the wrong position. The supervisor can create the cgroup, write
`memory.max` into it, and see every file it expects — and then fail at the only step that
matters. A confinement framework that checked for the cgroup's existence and concluded it was
enforcing would be reporting a control it does not have, which is §1.6's complaint about the
status quo wearing a security label.

## What §6.4 takes from this

1. **The supervisor ships as a systemd user unit.** Not a convenience: the unprivileged design
   of §5.7.4 depends on it, and there is no fallback short of privilege.
2. **`clone3` is not needed, so the supervisor stays in Python.** Migration works from the
   right position, and `clone3(CLONE_INTO_CGROUP)` buys nothing there that migration does not
   already give. A C component would have been a real cost against the requirement that this
   code be maintainable by one person.
3. **The child places itself, immediately before `exec`.** Ordinary migration leaves a window
   between fork and the parent's write in which the sandbox runs uncapped; having the child
   write its own pid closes it without needing `clone3`, and self-migration was measured to
   work from the right position. This keeps the *spirit* of §5.7.4's rule — nothing
   substantial executes before the limit applies — while dropping its false premise.
4. **Startup check, under N3.** The supervisor tests placement at start, in the position it is
   actually in, and refuses to start with a stated reason if it fails. Testing for the
   controller's presence is not enough; §5.7.4 already established that presence and
   enforcement are different claims, and this adds a third: enforcement and *permission to
   enforce* are different again.

## Reproducing

```bash
./place.py                                  # both positions, all four operations
./place.py --json results/pi5_placement.json
./place.py --probe                          # one position only, as currently placed
```

Needs `python3` and a C compiler (for the `clone3` arm only; without one that row reports
`NOCC` and the rest still runs). Deliberately does not need root — needing root would itself
have been the finding.

`clone_into_cgroup.c` is thirty lines and exists because there is no `clone3` in Python's
standard library, and raw-cloning a running interpreter to find out would have tested the
interpreter as much as the kernel.

## Limits

- **One host, one init system.** The result is about systemd's delegation boundary. A host
  without systemd delegates differently or not at all, and Home Assistant OS and Docker
  deployments are different environments again — §5.7.4's limitation, unchanged.
- **It does not test the supervisor.** No supervisor exists yet. This establishes which of two
  designs is available, not that the chosen one works.
- **The `app.slice` destination is systemd's convention, not a kernel rule.** The experiment
  locates the delegated root by checking ownership of `cgroup.subtree_control` rather than by
  assuming a path, but it still prefers `app.slice` beneath it because that is where a user's
  own units live and where `memory` is already enabled in `cgroup.subtree_control`.
