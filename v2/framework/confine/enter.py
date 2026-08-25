"""The child side of starting a sandbox: unshare, map, fork into the PID namespace, pivot, exec.

This module is what the supervisor executes. By the time it runs, the process is already in
its cgroup — the supervisor's `preexec_fn` put it there between `fork` and `exec` (§6.4.1) —
so everything below inherits the limit.

**Why there is a second fork here.** `unshare(CLONE_NEWPID)` does not move the calling process
into the new PID namespace; it arranges for its *children* to be born there. So the process
that unshares can never be PID 1, can never mount a `/proc` that shows only the sandbox, and
would keep an ordinary view of every process on the machine. The fork is what makes the PID
namespace real, and the parent exits immediately afterwards rather than idling: an idle Python
interpreter per sandbox would be a measurable share of §6.3.2's budget, spent on waiting.

The sandbox is then reparented to the supervisor, which has declared itself a child subreaper
so that it stays waitable.

Not run directly. `python -m confine.enter`, with the spec on stdin and a status pipe whose
descriptor number is named by `CONFINE_STATUS_FD` — the supervisor cannot choose the number,
because `subprocess` keeps a passed descriptor at whatever number it already had.
"""

from __future__ import annotations

import os
import sys

from . import namespaces, sandbox, seccomp
from .sandbox import SandboxSpec

# The supervisor names the descriptor rather than the child assuming one: `pass_fds` preserves
# a descriptor's *number*, and that number is whatever the supervisor's `os.pipe()` returned.
# An earlier version of this file assumed 3, wrote into whatever happened to be there, and
# reported nothing at all — see §6.4.5.
STATUS_FD = int(os.environ.get("CONFINE_STATUS_FD", "3"))

# What the sandbox's environment is, in full. Inherited environments carry the host's home
# directory, its proxy settings and whatever else the user's shell exported, none of which the
# sandbox has any business knowing.
BASE_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": SandboxSpec.DATA,
    "TMPDIR": "/tmp",
    "LANG": "C.UTF-8",
    # The component directory is read-only, so bytecode cannot be written beside the source.
    # Saying so avoids a warning on every import and a pointless failed write per module.
    "PYTHONDONTWRITEBYTECODE": "1",
}

# The sandbox is told the number, never the identity. §5.11.2: there is nothing to tell.
CHANNEL_FD_ENV = "CONFINE_CHANNEL_FD"


def _report(message: str) -> None:
    """Send one line to the supervisor, and complain loudly if that is not possible.

    Failing silently here is worse than crashing: the supervisor's only view of this process
    is what arrives on this pipe, so a swallowed error becomes "the sandbox never reported a
    pid" with no indication of why.
    """
    try:
        os.write(STATUS_FD, (message + "\n").encode())
    except OSError as err:
        print(f"confine.enter: cannot write to status fd {STATUS_FD}: {err}",
              file=sys.stderr, flush=True)


def main() -> int:
    spec = SandboxSpec.from_json(sys.stdin.read())

    # Before anything else, and before the namespace exists: inside a new user namespace the
    # answer to "who am I" is already `nobody`, and the kernel will only accept an identity
    # map naming the id this process actually had. §6.4.3 is the version of this that was
    # learned the hard way.
    outer_uid, outer_gid = os.getuid(), os.getgid()

    try:
        namespaces.unshare(namespaces.SANDBOX_NAMESPACES)
        namespaces.write_identity_maps(outer_uid, outer_gid)
        # The new namespace's loopback is down. Anything that binds a socket fails until it is
        # raised, and the interface reaches nothing outside this namespace (§6.12).
        namespaces.bring_loopback_up()
    except OSError as err:
        _report(f"fail unshare {err.strerror or err}")
        return 71

    pid = os.fork()
    if pid:
        # The process that unshared. Its only remaining job is to name the sandbox, because
        # the supervisor cannot see a PID it did not create.
        _report(f"pid {pid}")
        os._exit(0)

    # The sandbox: PID 1 of a namespace containing nothing else.
    try:
        sandbox.build_root(spec)
    except OSError as err:
        _report(f"fail mount {err.filename or ''} {err.strerror or err}")
        os._exit(71)
    except sandbox.GrantRefused as err:
        _report(f"fail grant {err}")
        os._exit(71)

    os.chdir(SandboxSpec.COMPONENT)
    if spec.channel_fd is not None:
        # It has to survive `exec`: this descriptor is the sandbox's only way to reach the
        # mediator, and its number is the mediator's only way to know who is calling.
        os.set_inheritable(spec.channel_fd, True)
    devnull = os.open("/dev/null", os.O_RDONLY)
    os.dup2(devnull, 0)
    os.close(devnull)

    # Last, because everything above needs syscalls the filter denies — `mount` and
    # `pivot_root` most obviously. A filter installed earlier would confine the construction
    # of the sandbox rather than the sandbox.
    try:
        covered = seccomp.install()
    except (OSError, seccomp.Unsupported) as err:
        _report(f"fail seccomp {err}")
        os._exit(71)

    env = dict(BASE_ENV)
    if spec.channel_fd is not None:
        env[CHANNEL_FD_ENV] = str(spec.channel_fd)
    env.update(spec.env)
    _report(f"seccomp {len(covered)}")
    _report("ready")
    os.close(STATUS_FD)  # so the supervisor's read returns rather than blocking on exec
    try:
        os.execve(spec.argv[0], spec.argv, env)
    except OSError:
        os._exit(126)
    return 0  # unreachable


if __name__ == "__main__":
    sys.exit(main())
