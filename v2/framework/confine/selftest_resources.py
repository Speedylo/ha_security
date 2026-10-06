"""S9's four bounds, each checked by making the sandbox try to exceed it.

§7.21.1 found that no `resources` clause reached an enforcement path: `memory_mb` and
`max_processes` were enforced from literals each harness carried, `cpu_percent` was validated,
rendered to the user by §6.7.1's surface and enforced nowhere, and disk was absent from the
schema entirely. That is the failure §5.10 legislates against one level up — a *recognised*
capability that is ignored is worse than an unrecognised one that is rejected — and it reached
the user, so it was an F4 defect as well as an S9 one.

This suite is the check that was missing. Its shape follows §6.4.2's rule rather than the
convenient one: **every case exercises the operation it is checking.** Reading `cpu.max` back
after writing it proves the write succeeded and nothing else, and §6.4.1 is the standing
reminder that a file this supervisor can write is not a limit this supervisor may enforce. So
each bound here is verified by a sandbox trying to exceed it and failing.

Four bounds, and they are not equally strong. The last one is why §7.22 narrows S9's text:

  memory        a sandbox allocating past `memory_mb` is OOM-killed          enforced
  processes     a sandbox forking past `max_processes` gets EAGAIN           enforced
  cpu           a spinner capped at N% is throttled to about N%              enforced
  disk (space)  a sandbox writing past `disk_mb` into /tmp gets ENOSPC       enforced
  disk (I/O)    ---                                                          NOT enforceable

The `io` controller is not delegated to a user manager on the target, so I/O *bandwidth* is
unbounded and this suite says so out loud rather than omitting the row. The last case asserts
that the framework refuses rather than pretends when a declared limit cannot be applied.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from .cgroup import CGROUP_FS, Delegation, PlacementUnavailable, ResourceLimits, spawn_confined
from .cgroup import SandboxCgroup
from .manifest import Manifest, ManifestRejected

HERE = Path(__file__).resolve().parent

# The CPU case is a proportion, so it needs a window long enough that scheduler granularity is
# noise. cpu.max's period is 100 ms; two seconds is twenty periods.
CPU_WINDOW_S = 2.0
CPU_CAP_PERCENT = 25
# Throttling is not exact — a process is allowed to finish the slice it is in — so the check is
# a band rather than an equality. Anything outside it means the cap is not doing its job.
CPU_TOLERANCE = 10
# The disk case fills a tmpfs, so the cap has to be small enough that filling it is quick and
# large enough that a page or two of slack does not decide the result.
DISK_CAP_MB = 8


def _child(script: str, cgroup: SandboxCgroup):
    """Run one probe inside `cgroup`, as an ordinary process rather than a full sandbox.

    The cgroup is the mechanism under test here, not the mount namespace, and using a bare
    child keeps each case readable. §6.9's suite is where these limits meet a real sandbox.
    """
    return spawn_confined([sys.executable, "-c", script], cgroup,
                          stdout=-1, stderr=-1)


def check_memory(delegation: Delegation) -> tuple[str, bool, str]:
    """A sandbox allocating past `memory_mb` is killed, and the cgroup says it was the kernel."""
    with SandboxCgroup.create(delegation, "res-memory",
                              ResourceLimits(memory_mb=64)) as cgroup:
        proc = _child("b = bytearray(); [b.extend(bytes(1 << 20)) for _ in range(512)]", cgroup)
        proc.wait(timeout=60)
        killed = proc.returncode == -9 or proc.returncode == 137
        oom = cgroup.event_count("oom_kill")
    return ("memory_mb: 512 MB asked against a 64 MB cap",
            killed and oom >= 1,
            f"exit {proc.returncode}, oom_kill={oom}")


def check_processes(delegation: Delegation, cap: int = 16) -> tuple[str, bool, str]:
    """A sandbox forking past `max_processes` is refused by the kernel, not by a check here."""
    script = ("import os, sys\n"
              "n = 0\n"
              "try:\n"
              "    for _ in range(200):\n"
              "        if os.fork() == 0: os.write(2, b''); os._exit(0)\n"
              "        n += 1\n"
              "except BlockingIOError: pass\n"
              "except OSError: pass\n"
              "sys.stdout.write(str(n))\n")
    with SandboxCgroup.create(delegation, "res-pids",
                              ResourceLimits(memory_mb=256, max_processes=cap)) as cgroup:
        proc = _child(script, cgroup)
        out, _ = proc.communicate(timeout=60)
    forked = int(out.decode().strip() or -1)
    # The cap counts every task in the cgroup including the parent, so the number of successful
    # forks is bounded by the cap and not equal to it. What matters is that 200 did not happen.
    if cap > 200:
        return (f"control: the same 200 forks against a cap of {cap} all succeed",
                forked == 200, f"{forked} forks succeeded")
    return (f"max_processes: 200 forks attempted against a cap of {cap}",
            0 <= forked < 200,
            f"{forked} forks succeeded before the kernel refused")


def check_cpu(delegation: Delegation) -> tuple[str, bool, str]:
    """A spinner capped at 25% of one processor gets about 25% of one processor.

    This is the case that did not exist. `cpu_percent` was in the schema and in §6.7.1's
    rendering and in nothing else, so a manifest declaring it produced a sentence to the user
    that was not true of the sandbox.
    """
    limits = ResourceLimits(memory_mb=256, cpu_percent=CPU_CAP_PERCENT)
    with SandboxCgroup.create(delegation, "res-cpu", limits) as cgroup:
        proc = _child(f"import time\nt=time.time()\n"
                      f"while time.time()-t < {CPU_WINDOW_S}: pass\n", cgroup)
        wall_start, cpu_start = time.monotonic(), cgroup.cpu_usage_us()
        proc.wait(timeout=60)
        wall = time.monotonic() - wall_start
        used = cgroup.cpu_usage_us() - cpu_start
        throttled = cgroup.throttled_us()
    share = 100.0 * (used / 1e6) / wall if wall > 0 else 0.0
    within = abs(share - CPU_CAP_PERCENT) <= CPU_TOLERANCE and throttled > 0
    return (f"cpu_percent: a busy loop capped at {CPU_CAP_PERCENT}% of one processor",
            within,
            f"consumed {share:.1f}% of one processor over {wall:.2f}s, "
            f"throttled {throttled / 1e6:.2f}s")


def check_disk_space(delegation: Delegation, cap: int = DISK_CAP_MB) -> tuple[str, bool, str]:
    """A sandbox writing past `disk_mb` into its private /tmp gets ENOSPC.

    Run against a tmpfs mounted the way `build_root` mounts the sandbox's own, in a private
    mount namespace, so that what is measured is the mechanism the sandbox will meet.
    """
    # The probe mounts the tmpfs through **the framework's own `mount`**, with the option
    # string `build_root` builds, rather than through a copy of it. §6.4.2 is explicit that a
    # check exercising a different mechanism from the one the supervisor uses is not a check —
    # and the first version of this probe proved the point by hand-rolling the `ctypes` call,
    # passing the options pointer where a 32-bit int was expected, and failing with EOVERFLOW
    # against a limit that was working. That is §6.4.5's absence problem in a test.
    script = (
        f"import ctypes, ctypes.util, os, sys, tempfile\n"
        f"sys.path.insert(0, {str(HERE.parent)!r})\n"
        f"from confine.sandbox import MS_NODEV, MS_NOSUID, mount\n"
        f"libc = ctypes.CDLL(ctypes.util.find_library('c') or 'libc.so.6', use_errno=True)\n"
        f"if libc.unshare(0x10000000) != 0: sys.exit('unshare userns failed')\n"
        f"open('/proc/self/setgroups', 'w').write('deny')\n"
        f"open('/proc/self/uid_map', 'w').write(f'0 {os.getuid()} 1')\n"
        f"open('/proc/self/gid_map', 'w').write(f'0 {os.getgid()} 1')\n"
        f"if libc.unshare(0x00020000) != 0: sys.exit('unshare mountns failed')\n"
        f"d = tempfile.mkdtemp()\n"
        f"mount('tmpfs', d, 'tmpfs', MS_NOSUID | MS_NODEV, 'mode=1777,size={cap}m')\n"
        f"written = 0\n"
        f"try:\n"
        f"    with open(os.path.join(d, 'fill'), 'wb') as fh:\n"
        f"        for _ in range(64):\n"
        f"            fh.write(bytes(1 << 20)); fh.flush(); written += 1\n"
        f"except OSError as err:\n"
        f"    sys.stdout.write(f'{{written}} {{err.errno}}'); sys.exit(0)\n"
        f"sys.stdout.write(f'{{written}} 0')\n")
    with SandboxCgroup.create(delegation, "res-disk",
                              ResourceLimits(memory_mb=256, disk_mb=cap)) as cgroup:
        proc = _child(script, cgroup)
        out, err = proc.communicate(timeout=60)
    fields = out.decode().strip().split()
    written, errno = (int(fields[0]), int(fields[1])) if len(fields) == 2 else (-1, 0)
    import errno as errno_mod
    if cap > 64:
        return (f"control: the same 64 MB into a {cap} MB private /tmp is all written",
                written == 64 and errno == 0, f"{written} MB written, errno {errno}")
    return (f"disk_mb: 64 MB written into a {cap} MB private /tmp",
            errno == errno_mod.ENOSPC and 0 < written <= cap + 1,
            f"{written} MB written, then errno {errno} "
            f"({os.strerror(errno) if errno else 'no error'})"
            + (f"; {err.decode().strip()}" if errno == 0 and err else ""))


def check_io_not_delegated(delegation: Delegation) -> tuple[str, bool, str]:
    """The `io` controller is not reachable, and the framework is honest about it.

    This is a **recorded limitation, not a passing control.** §4.10.1 wrote S9 as bounding
    "CPU, memory and disk"; the measurement here is why §7.22 narrows the disk half to space
    rather than bandwidth. It asserts the *fact* — that `io` is present at the host root and
    absent from a sandbox's cgroup — so that a host which one day delegates it makes this case
    fail and someone re-reads the requirement rather than inheriting a stale narrowing.
    """
    assert delegation.parent is not None
    root_controllers = (CGROUP_FS / "cgroup.subtree_control").read_text().split()
    child_controllers = (delegation.parent / "cgroup.controllers").read_text().split()
    return ("io.max: the disk-bandwidth half of S9, and why §7.22 narrows it",
            "io" in root_controllers and "io" not in child_controllers,
            f"host root delegates {sorted(root_controllers)}; this user's subtree has "
            f"{sorted(child_controllers)} — io is present and not delegated")


def check_refuses_unenforceable(delegation: Delegation) -> tuple[str, bool, str]:
    """A declared limit that cannot be applied is a refusal, not a silent no-op.

    N3, in the form §6.4.2 argued for it: a framework that could not apply a limit and started
    the sandbox anyway would leave T16 uncontrolled while §6.7.1 told the user the limit was in
    force. The unenforceable case is manufactured by pointing `create` at a cgroup path that
    the kernel will not accept a `cpu.max` write into.
    """
    broken = Delegation(delegation.own, delegation.root,
                        Path("/sys/fs/cgroup/does-not-exist"), None)
    try:
        SandboxCgroup.create(broken, "res-refuse", ResourceLimits(cpu_percent=50))
    except (PlacementUnavailable, OSError) as err:
        return ("an unenforceable declared limit refuses rather than no-ops", True,
                f"{type(err).__name__}: {str(err)[:90]}")
    return ("an unenforceable declared limit refuses rather than no-ops", False,
            "the sandbox was created with a limit that was never applied")


def check_parse_time_validation() -> list[tuple[str, bool, str]]:
    """The values, not only the keys. `"memory_mb": "lots"` used to reach a kernel file."""
    import tempfile
    results = []
    cases = [
        ({"memory_mb": "lots"}, "a non-integer memory_mb"),
        ({"cpu_percent": 0}, "cpu_percent below its floor"),
        ({"disk_mb": 99999}, "disk_mb above its ceiling"),
        ({"max_processes": True}, "a boolean where an integer belongs"),
        ({"gpu_percent": 50}, "an unknown member of a known capability"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        component = root / "custom_components" / "probe"
        component.mkdir(parents=True)
        for clause, label in cases:
            (component / "manifest.json").write_text(json.dumps(
                {"domain": "probe", "permissions": {"schema_version": 1, "resources": clause}}))
            try:
                Manifest.load(component, root)
                results.append((f"rejects {label}", False, "accepted"))
            except ManifestRejected as err:
                results.append((f"rejects {label}", True, str(err).split(": ", 1)[-1][:70]))
        # And the accepting case, so the suite is not passing by rejecting everything (§6.6.5).
        (component / "manifest.json").write_text(json.dumps(
            {"domain": "probe", "permissions": {"schema_version": 1,
             "resources": {"memory_mb": 192, "cpu_percent": 50,
                           "max_processes": 8, "disk_mb": 32}}}))
        manifest = Manifest.load(component, root)
        limits = manifest.resources
        results.append(("a well-formed clause reaches ResourceLimits intact",
                        (limits.memory_mb, limits.cpu_percent, limits.max_processes,
                         limits.disk_mb) == (192, 50, 8, 32),
                        f"{limits.memory_mb} MB, {limits.cpu_percent}%, "
                        f"{limits.max_processes} procs, {limits.disk_mb} MB disk"))
        # A declaration can only tighten the framework's bound, never loosen it (§7.22.3).
        # Until verification 4.7 (finding F32) these were applied as declared.
        (component / "manifest.json").write_text(json.dumps(
            {"domain": "probe", "permissions": {"schema_version": 1,
             "resources": {"memory_mb": 8192, "max_processes": 4096, "disk_mb": 4096}}}))
        loose = Manifest.load(component, root).resources
        floor = ResourceLimits()
        results.append(("a clause asking for more than the default gets the default (F32)",
                        (loose.memory_mb, loose.max_processes, loose.disk_mb)
                        == (floor.memory_mb, floor.max_processes, floor.disk_mb),
                        f"asked 8192 MB, 4096 procs, 4096 MB disk; got {loose.memory_mb} MB, "
                        f"{loose.max_processes} procs, {loose.disk_mb} MB disk"))
        # Absence is the framework's default, not the absence of a limit (§7.22).
        (component / "manifest.json").write_text(json.dumps(
            {"domain": "probe", "permissions": {"schema_version": 1}}))
        default = Manifest.load(component, root).resources
        results.append(("a manifest declaring no resources gets the default, not no limit",
                        default.memory_mb > 0 and default.max_processes > 0
                        and default.disk_mb > 0,
                        f"{default.memory_mb} MB, {default.max_processes} procs, "
                        f"{default.disk_mb} MB disk, cpu unset"))
    return results


def main() -> int:
    delegation = Delegation.discover()
    print("S9 — the resources clause, enforced")
    print("=" * 68)
    print(f"  {delegation.describe()}\n")

    results = check_parse_time_validation()
    if not delegation.available:
        print(f"  cgroup cases skipped: {delegation.unavailable}\n")
    else:
        # The two controls (verification 4.4): the same work with the bound raised succeeds,
        # so the refusal above is the bound and not some other limit of the host. Memory and
        # CPU carry their own attribution, the cgroup's `oom_kill` and `throttled_usec`.
        for check in (check_memory, check_processes,
                      lambda d: check_processes(d, cap=512), check_cpu, check_disk_space,
                      lambda d: check_disk_space(d, cap=128),
                      check_io_not_delegated, check_refuses_unenforceable):
            try:
                results.append(check(delegation))
            except Exception as err:                                  # noqa: BLE001
                results.append((check.__name__, False, f"{type(err).__name__}: {err}"))

    failed = 0
    for label, ok, detail in results:
        # The io row is a limitation the suite records rather than a control it claims, so it
        # is marked differently from a passing check. Printing it as `ok` would be this
        # chapter's own §6.6.5 mistake: a green line that means the opposite of what it reads.
        mark = "note" if label.startswith("io.max") else ("ok  " if ok else "FAIL")
        failed += 0 if ok else 1
        print(f"  {mark}  {label}")
        print(f"        {detail}")
    print()
    print(f"  {len(results) - failed}/{len(results)} — S9 bounds memory, processes, CPU and "
          f"disk space; I/O bandwidth is not bounded (§7.22)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
