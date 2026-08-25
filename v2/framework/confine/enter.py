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

Not run directly. `python -m confine.enter` with the spec on stdin and a status pipe on fd 3.
"""

from __future__ import annotations

import os
import sys

from . import namespaces, sandbox
from .sandbox import SandboxSpec

STATUS_FD = 3

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


def _report(message: str) -> None:
    try:
        os.write(STATUS_FD, (message + "\n").encode())
    except OSError:
        pass


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
    devnull = os.open("/dev/null", os.O_RDONLY)
    os.dup2(devnull, 0)
    os.close(devnull)

    env = dict(BASE_ENV)
    env.update(spec.env)
    _report("ready")
    os.close(STATUS_FD)  # so the supervisor's read returns rather than blocking on exec
    try:
        os.execve(spec.argv[0], spec.argv, env)
    except OSError:
        os._exit(126)
    return 0  # unreachable


if __name__ == "__main__":
    sys.exit(main())
