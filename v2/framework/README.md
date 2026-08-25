# The framework — supervisor-side code

**Started:** 2026-08-25 · **Described by:** `report/06_implementation.md`

This is the artifact Chapter 6 builds. It is new code written against the design Chapter 5
produced; the earlier feasibility spike in `~/capstone/spike/` is prior work, cited in §6.2 and
not imported here.

## Layout

Modules follow Chapter 6's sections rather than convenience, so that a section and the code it
describes can be read side by side.

| Module | Section | What it is |
|---|---|---|
| `confine/cgroup.py` | §6.4.1 | Where a sandbox may be placed, and by whom |
| `confine/namespaces.py` | §5.7.3 | The seven namespaces, and whether this host grants them |
| `confine/preflight.py` | §6.4.2 | What is checked before anything is confined, and the N3 refusal |
| `confine/sandbox.py` | §6.4.4 | What a sandbox can see of the filesystem, and how that view is built |
| `confine/enter.py` | §6.4.4 | The child side: unshare, identity maps, the fork into the PID namespace, pivot, seccomp, exec |
| `confine/spawn.py` | §6.4.4 | The supervisor side: subreaper, spec over stdin, wait |
| `confine/seccomp.py` | §6.4.6 | The BPF filter, built by hand and verified by behaviour |
| `confine/channel.py` | §6.5.1 | The one socket that crosses the boundary, and its framing |
| `confine/mediator.py` | §6.5.1 | Who is asking, and what happens to the answer. Default-deny is S6 |
| `confine/selftest.py` | §6.4.5 | One sandbox built around a hostile configuration directory |
| `confine/manifest.py` | §6.6 | Reading a manifest, refusing a bad one, deciding one request |
| `confine/describe.py` | §6.7 | Rendering a declaration for the person deciding whether to install |
| `confine/audit.py` | §6.8 | Three-part identity, and the two chains over the record |
| `confine/platform.py` | §6.10 | Step 5 — acting, against a stand-in Home Assistant |
| `confine/sandbox_runtime.py` | §6.10 | **The bridge.** Runs inside the sandbox; imports nothing from this package |
| `confine/selftest_channel.py` | §6.5.2 | Two sandboxes, both claiming to be the same integration |
| `confine/selftest_policy.py` | §6.6 | S5's asymmetry, resolve-then-pin, and what is refused at parse time |
| `confine/selftest_describe.py` | §6.7 | Four states an integration can be in, four renderings |
| `confine/selftest_audit.py` | §6.8 | Identity's three components, and every form of tampering |
| `confine/selftest_adversary.py` | §6.9 | A hostile integration, inside a sandbox, trying everything |
| `confine/selftest_bridge.py` | §6.10 | An unmodified integration running, publishing, and confined |

## Running the preflight

```bash
python3 -m confine.preflight            # every check, including the enforcement test
python3 -m confine.preflight --shallow  # skip the check that allocates 192 MB
```

It exits non-zero and names the first failure. **It must be run from inside the cgroup subtree
delegated to the user** — a systemd user unit — because §6.4.1 established that placement is
refused anywhere else. From an ssh session it is expected to fail at `supervisor inside it`,
and doing so is the check working rather than the host being wrong.

```bash
systemd-run --user --scope -q python3 -m confine.preflight   # the right position, ad hoc
systemd-run --user --scope -q python3 -m confine.selftest    # build a sandbox and look inside
systemd-run --user --scope -q python3 -m confine.selftest_channel   # two sandboxes, both lying
```

Three of the self-tests need no sandbox and so need no delegated subtree:

```bash
python3 -m confine.selftest_policy     # what the manifest refuses, and S5's asymmetry
python3 -m confine.selftest_describe   # what the user is shown, in each of four states
python3 -m confine.selftest_audit      # identity, and every form of tampering with the log
```

The adversarial suite needs a sandbox, and takes about a minute — two of its attacks are
deliberately stopped by the memory limit and it waits for them:

```bash
systemd-run --user --scope -q python3 -m confine.selftest_adversary
```

It fails if either canary string reaches the adversary. Everything else it prints is diagnosis.

The bridge test needs an interpreter with `homeassistant` importable, which the supervisor does
not need itself:

```bash
systemd-run --user --scope -q python3 -m confine.selftest_bridge --python ~/r2exp/ha314/bin/python
```

`confine.selftest` builds a configuration directory containing a secrets file, the config-entry
store and a second integration, grants one integration one unrelated file, and reports what it
can see. The interesting rows are the ones that come back **absent**.

## Why the preflight is a self-test and not an inspection

Every check here exercises the operation it is checking, and that is a reaction to three
findings in a row, each of which was invisible to the check that preceded it:

| Found | The check that was not enough |
|---|---|
| `experiments/host_isolation_probe/`, 2026-08-24 | The `memory` controller is absent by default on Raspberry Pi OS — so *listing* the design's primitives is not enough |
| The same probe, re-run 2026-08-25 | A controller being **listed** is not a limit being **enforced** — so reading `cgroup.controllers` is not enough |
| `experiments/cgroup_placement/`, 2026-08-25 | A limit being enforceable is not this supervisor being **permitted** to enforce it — and `mkdir`, `memory.max` and every file read succeed from the position where placement does not |

The last one is the reason the pattern is worth stating: a framework that checked what it could
see would have reported itself ready in a position where it could confine nothing at all.

## No dependencies, and no override

Standard library only, and `ctypes` for the two syscalls Python does not wrap. That is a
constraint on the artifact rather than an accident: this code has to be defensible line by
line by one person.

There is also deliberately no flag that starts the framework with a failed check. N3 asks for a
stated failure mode; a framework that can be told to run without its controls is one whose
users will eventually be running without them, which is §1.6's complaint about the status quo.
