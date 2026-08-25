"""What is checked before the framework confines anything, and what it says when it cannot.

N3 requires the framework to have a stated failure mode rather than a silent one, and §5.7.4
applied that to one case: if the memory controller is unavailable, refuse to start with a
reason, because starting anyway would leave T16 uncontrolled while implying protection. This
module generalises it, and the generalisation is not tidiness — each of these checks exists
because something that looked fine turned out not to be.

    §5.7.4   the `memory` controller is absent by default on Raspberry Pi OS, and the
             framework must not run without it
    probe    a controller being *listed* is not the same as a limit being *enforced*
    §6.4.1   a limit being enforceable is not the same as this supervisor being *permitted*
             to enforce it — and `mkdir` succeeds from the position where it is not

The last is why every check here is a live test rather than an inspection. The failure §6.4.1
found is invisible to inspection: the directory can be created, the limit written, every file
read back, and only the placement refused.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field

from . import namespaces, seccomp
from .cgroup import CGROUP_FS, Delegation, PlacementUnavailable, SandboxCgroup, spawn_confined

# The enforcement check asks a child for three times its cap. Large enough that no interpreter
# start-up could account for it, small enough to be over in a moment on the C4 device.
CHECK_CAP_BYTES = 64 * 1024 * 1024
CHECK_ASK_BYTES = 192 * 1024 * 1024


@dataclass(frozen=True)
class Check:
    """One thing that must be true, what was actually observed, and what to do about it."""

    name: str
    ok: bool
    detail: str
    remedy: str = ""


@dataclass
class Preflight:
    checks: list[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def first_failure(self) -> Check | None:
        return next((c for c in self.checks if not c.ok), None)

    def render(self) -> str:
        width = max((len(c.name) for c in self.checks), default=0)
        lines = []
        for c in self.checks:
            lines.append(f"  {'PASS' if c.ok else 'FAIL'}  {c.name:<{width}}  {c.detail}")
            if not c.ok and c.remedy:
                lines.append(f"        {' ' * width}  -> {c.remedy}")
        return "\n".join(lines)


class NotConfinable(RuntimeError):
    """The framework will not start, and carries the reason N3 requires it to state."""


def run(deep: bool = True) -> Preflight:
    """Run every check, in dependency order, stopping at the first one that fails.

    Stopping matters: once placement is known to be impossible, the enforcement check would
    fail too, and reporting two failures for one cause invites fixing the wrong one.
    """
    pre = Preflight()
    delegation = Delegation.discover()

    pre.checks.append(Check(
        "cgroup v2 hierarchy",
        delegation.own is not None,
        (f"this process is in {delegation.own.relative_to(CGROUP_FS)}"
         if delegation.own else "no unified (0::) entry in /proc/self/cgroup"),
        "the host must use the unified cgroup v2 hierarchy; v1 and hybrid are not supported",
    ))
    if not pre.ok:
        return pre

    pre.checks.append(Check(
        "cgroup subtree delegated",
        delegation.root is not None,
        (f"delegated at {delegation.root.relative_to(CGROUP_FS)}"
         if delegation.root else f"nothing delegated to uid {os.getuid()}"),
        "start the framework as a systemd user unit, so that systemd delegates a subtree",
    ))
    if not pre.ok:
        return pre

    inside = delegation.unavailable is None or "outside" not in delegation.unavailable
    pre.checks.append(Check(
        "supervisor inside it",
        inside,
        delegation.describe(),
        "start the framework as a systemd user unit; a login shell or ssh session is in "
        "user-<uid>.slice/session-N.scope, which is outside the delegated subtree, and from "
        "there no placement mechanism is permitted (§6.4.1)",
    ))
    if not pre.ok:
        return pre

    pre.checks.append(Check(
        "memory controller",
        delegation.available,
        delegation.unavailable or
        f"available in {delegation.parent.relative_to(CGROUP_FS)}",  # type: ignore[union-attr]
        "add `cgroup_enable=memory cgroup_memory=1` to the kernel command line and reboot; "
        "on Raspberry Pi OS the disable is prepended by the firmware and is not in "
        "cmdline.txt, so it is appended rather than removed (§5.7.4)",
    ))
    if not pre.ok:
        return pre

    pre.checks.append(_check_placement(delegation))
    if not pre.ok:
        return pre

    if deep:
        pre.checks.append(_check_enforcement(delegation))
        if not pre.ok:
            return pre

    ok, detail = namespaces.probe()
    pre.checks.append(Check(
        "unprivileged namespaces", ok, detail,
        "the kernel must allow unprivileged user namespaces; on Debian-family hosts check "
        "kernel.unprivileged_userns_clone and user.max_user_namespaces",
    ))
    if not pre.ok:
        return pre

    pre.checks.append(_check_seccomp())
    return pre


def _check_seccomp() -> Check:
    """Install the filter in a throwaway child and make the calls it claims to deny.

    The syscall numbers are hard-coded per architecture and a wrong one denies the wrong call
    silently, so what is checked is behaviour. `chroot` and `unshare` are the useful probes:
    both *succeed* inside a user namespace, so seeing them refused is evidence of the filter
    rather than of the namespace.
    """
    result = seccomp.probe()
    if "_error" in result:
        return Check("seccomp filter", False, result["_error"],
                     "this architecture needs a syscall table in confine/seccomp.py")
    allowed = [name for name, verdict in result.items() if verdict != "DENIED"]
    detail = ", ".join(f"{k} {v.lower()}" for k, v in sorted(result.items()))
    return Check("seccomp filter", not allowed, detail,
                 f"these were not denied: {', '.join(allowed)} — check the syscall numbers "
                 f"for this architecture" if allowed else "")


def _scratch_name() -> str:
    return f"preflight-{os.getpid()}"


def _check_placement(delegation: Delegation) -> Check:
    """Actually put a process in a cgroup, and read back where it ended up.

    Not `mkdir` — that succeeds in the position where everything else fails, which is the
    whole of §6.4.1. The child reports its own cgroup after `exec`, so there is no race
    between the supervisor reading and the child arriving.
    """
    try:
        with SandboxCgroup.create(delegation, _scratch_name()) as cgroup:
            proc = spawn_confined(
                [sys.executable, "-c",
                 "import sys; sys.stdout.write(open('/proc/self/cgroup').read())"],
                cgroup, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = proc.communicate(timeout=60)
            landed = out.strip().removeprefix("0::")
            expected = "/" + str(cgroup.path.relative_to(CGROUP_FS))
            if landed == expected:
                return Check("placement permitted", True, f"child ran in {expected}")
            return Check("placement permitted", False,
                         f"child ran in {landed or err.strip() or '?'}, expected {expected}",
                         "the supervisor's cgroup and the sandbox's must have a common "
                         "ancestor this user owns")
    except PlacementUnavailable as err:
        return Check("placement permitted", False, str(err),
                     "start the framework as a systemd user unit (§6.4.1)")
    except OSError as err:
        return Check("placement permitted", False, err.strerror or str(err),
                     "start the framework as a systemd user unit (§6.4.1)")


def _check_enforcement(delegation: Delegation) -> Check:
    """Ask a capped child for three times its cap, and see which of the two wins.

    S9 is a claim about what happens when a sandbox asks for too much, so this asks. The
    cgroup's own `memory.events` counter is read afterwards rather than the child's exit
    status alone: a process can die for many reasons and only one of them is this one.
    """
    try:
        with SandboxCgroup.create(delegation, _scratch_name(),
                                  memory_max=CHECK_CAP_BYTES) as cgroup:
            proc = spawn_confined(
                [sys.executable, "-c", f"bytearray({CHECK_ASK_BYTES})"],
                cgroup, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rc = proc.wait(timeout=120)
            oom = cgroup.event_count("oom_kill")
            asked, cap = CHECK_ASK_BYTES // 2**20, CHECK_CAP_BYTES // 2**20
            if rc != 0 and oom > 0:
                return Check("memory limit enforced", True,
                             f"{asked} MB against a {cap} MB cap: killed, "
                             f"oom_kill={oom}")
            return Check("memory limit enforced", False,
                         f"{asked} MB against a {cap} MB cap: allowed "
                         f"(exit {rc}, oom_kill={oom})",
                         "the controller is present but the limit is not biting; check that "
                         "memory.max was written and that swap is capped")
    except (PlacementUnavailable, OSError) as err:
        return Check("memory limit enforced", False, str(err), "")


def require_ready(deep: bool = True) -> Preflight:
    """Run the checks and refuse to continue if any failed, naming the reason.

    This is the N3 behaviour §5.7.4 specified, generalised: the framework does not start in a
    degraded state. There is no flag to override it, deliberately — a framework that can be
    told to run without its controls is one whose users will eventually be running without
    them, which is §1.6's complaint about the status quo.
    """
    pre = run(deep=deep)
    failure = pre.first_failure
    if failure is not None:
        raise NotConfinable(
            f"cannot confine: {failure.name} — {failure.detail}"
            + (f"\n  {failure.remedy}" if failure.remedy else ""))
    return pre


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--shallow", action="store_true",
                    help="skip the enforcement check, which allocates 192 MB")
    args = ap.parse_args()

    pre = run(deep=not args.shallow)
    print(f"confinement preflight — uid {os.getuid()}, "
          f"python {sys.version.split()[0]}\n")
    print(pre.render())
    print()
    if pre.ok:
        print("READY — every control this framework claims is available and was exercised")
        return 0
    failure = pre.first_failure
    assert failure is not None
    print(f"NOT READY — {failure.name}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
