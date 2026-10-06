"""The supervisor side of starting a sandbox.

Three things happen here that are not obvious from the design, and each is a consequence of
something measured rather than a preference:

  - **The supervisor declares itself a child subreaper.** The process that unshares exits as
    soon as it has forked the sandbox (see `enter.py`), so the sandbox would otherwise be
    reparented to init and become unwaitable. `PR_SET_CHILD_SUBREAPER` keeps it a child of the
    supervisor without the supervisor having to keep a Python interpreter alive per sandbox.
  - **The sandbox places itself in its cgroup**, between `fork` and `exec`, via `preexec_fn`
    (§6.4.1). That is why the supervisor must be single-threaded.
  - **The spec goes over stdin, not argv.** Not length — a sandbox's declared paths are
    readable in `/proc/<pid>/cmdline` by anything running as the same user, and the sandbox's
    own view of the world is not something to publish for the convenience of the caller.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .cgroup import SandboxCgroup, spawn_confined
from .sandbox import SandboxSpec

_libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
PR_SET_CHILD_SUBREAPER = 36


def become_subreaper() -> None:
    if _libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), "PR_SET_CHILD_SUBREAPER")


class SandboxFailed(RuntimeError):
    """The sandbox did not reach the point of executing, and says how far it got."""


@dataclass
class Sandbox:
    domain: str
    pid: int
    cgroup: SandboxCgroup

    def wait(self, timeout: float | None = None) -> int:
        """Wait for the sandbox to exit and return its status, as `waitpid` reports it."""
        if timeout is None:
            return os.waitpid(self.pid, 0)[1]
        fd = os.pidfd_open(self.pid)
        try:
            import selectors
            with selectors.DefaultSelector() as sel:
                sel.register(fd, selectors.EVENT_READ)
                if not sel.select(timeout):
                    raise TimeoutError(f"{self.domain} still running after {timeout}s")
        finally:
            os.close(fd)
        return os.waitpid(self.pid, 0)[1]

    def kill(self) -> None:
        """Kill the sandbox through its cgroup, not through its PID.

        Killing PID 1 of a namespace does take the namespace with it, but the cgroup is the
        thing that is guaranteed to hold every descendant however the sandbox rearranged
        itself, and it is the supervisor's own handle rather than one the sandbox can affect.
        """
        self.cgroup.remove()


def start(spec: SandboxSpec, cgroup: SandboxCgroup, *,
          stdout: int | None = None, stderr: int | None = None,
          channel_end: int | None = None) -> Sandbox:
    """Start one sandbox and return once it has reported that it is about to execute.

    `channel_end` is the sandbox's half of a socket pair the caller has already created —
    already, because §5.11.2 requires the channel to exist before the sandbox does. The
    supervisor closes its copy on return, so that the mediator's end is the only one left and
    the socket closes when the sandbox dies.
    """
    status_r, status_w = os.pipe()
    os.set_inheritable(status_w, True)
    passed = (status_w,) if channel_end is None else (status_w, channel_end)
    if channel_end is not None:
        os.set_inheritable(channel_end, True)
        spec.channel_fd = channel_end

    # `confine.enter` runs in a fresh interpreter, which finds the package on `sys.path` and
    # not on the caller's. A supervisor started from anywhere but the package's parent
    # directory would otherwise fail with `No module named 'confine'` — and, because that
    # happens before the child can write to the status pipe, it presents as "the sandbox never
    # reported a pid" with nothing else. This is the third time that message has meant
    # something different (§6.4.5, §6.10.4).
    package_parent = str(Path(__file__).resolve().parent.parent)
    existing = os.environ.get("PYTHONPATH", "")
    child_env = {**os.environ, "CONFINE_STATUS_FD": str(status_w),
                 "PYTHONPATH": f"{package_parent}:{existing}" if existing else package_parent}

    # A session of its own, so the sandbox has no controlling terminal. Without it, a supervisor
    # started from a terminal shared that terminal with the integration, and a process can push
    # input into its controlling terminal where the kernel still allows it (verification 4.7,
    # finding F34). `/dev/tty` is gone from the sandbox's `/dev` as well, so this is not the
    # only layer.
    proc = spawn_confined(
        [sys.executable, "-m", "confine.enter"], cgroup,
        stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
        pass_fds=passed, env=child_env, start_new_session=True,
    )
    os.close(status_w)
    try:
        assert proc.stdin is not None
        proc.stdin.write(spec.to_json().encode())
        proc.stdin.close()

        sandbox_pid: int | None = None
        with os.fdopen(status_r, "r") as status:
            for line in status:
                head, _, rest = line.strip().partition(" ")
                if head == "pid":
                    sandbox_pid = int(rest)
                elif head == "fail":
                    raise SandboxFailed(f"{spec.domain}: {rest}")
        proc.wait(timeout=30)
    except BaseException:
        proc.kill()
        raise

    if sandbox_pid is None:
        raise SandboxFailed(f"{spec.domain}: the sandbox never reported a pid")
    if channel_end is not None:
        os.close(channel_end)
    return Sandbox(spec.domain, sandbox_pid, cgroup)
