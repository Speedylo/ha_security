"""The namespaces a sandbox is given, and whether this host will hand them over.

§5.7.3 chose Linux namespaces as the isolation primitive and
`experiments/host_isolation_probe/` established that all seven types exist on the C4 device
and that an ordinary user can create them. That probe used the `unshare(1)` command; this
module does it with the syscall, because the supervisor cannot depend on util-linux being
installed at runtime and because a check that exercises a different mechanism from the one
the supervisor uses is not a check.

Only the *availability* question is answered here. Building the sandbox's mount namespace —
what it can see, which is §5.6.2's structural denial — is a separate problem and belongs with
the code that knows what the manifest declared.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os

CLONE_NEWNS = 0x00020000      # mount:  the filesystem the sandbox sees
CLONE_NEWCGROUP = 0x02000000  # cgroup: hides where in the tree the sandbox actually is
CLONE_NEWUTS = 0x04000000     # uts:    hostname
CLONE_NEWIPC = 0x08000000     # ipc:    System V IPC and POSIX message queues
CLONE_NEWUSER = 0x10000000    # user:   the one that makes the other six unprivileged
CLONE_NEWPID = 0x20000000     # pid:    the sandbox cannot see or signal other processes
CLONE_NEWNET = 0x40000000     # net:    no interface but loopback; egress must be mediated

# All seven. The user namespace is what makes this possible without privilege: it is created
# first, the kernel grants the caller full capabilities *inside* it, and the other six are
# then created with those capabilities rather than with any the supervisor started with.
SANDBOX_NAMESPACES = (CLONE_NEWUSER | CLONE_NEWNS | CLONE_NEWPID | CLONE_NEWNET
                      | CLONE_NEWIPC | CLONE_NEWUTS | CLONE_NEWCGROUP)

_libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)


def unshare(flags: int) -> None:
    """Detach the calling process into new namespaces, or raise OSError saying why not."""
    if _libc.unshare(ctypes.c_int(flags)) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), "unshare")


def write_identity_maps(outer_uid: int, outer_gid: int) -> None:
    """Map the sandbox's uid 0 to the supervisor's own uid, inside the new user namespace.

    A user namespace with no map is nearly unusable: every id appears as `nobody`. Mapping one
    is the minimum, and mapping the supervisor's own is what keeps a sandbox's files belonging
    to a real user on the outside.

    **The two arguments are required, and that is the whole point of this function's shape.**
    An unprivileged process may write only a single-line map, and only one whose outer id is
    the id it already had; the kernel compares it against the credentials the `/proc` file was
    opened with. After `unshare(CLONE_NEWUSER)` the caller's own `getuid()` already answers
    `nobody`, so a function that read the id itself would faithfully write `0 65534 1` and be
    refused with `EPERM` — which is precisely what an earlier version of this file did. The
    identity has to be captured before the namespace that hides it exists, which is the same
    ordering §6.3.4 records for the socket and for the sandbox's identity hash.

    `setgroups` must be denied before `gid_map` can be written unprivileged. That is a
    deliberate kernel restriction — otherwise a process could drop out of a group a file's
    permissions rely on — and it costs nothing here, because a sandbox has no use for
    supplementary groups.
    """
    with open("/proc/self/setgroups", "w") as f:
        f.write("deny")
    with open("/proc/self/uid_map", "w") as f:
        f.write(f"0 {outer_uid} 1")
    with open("/proc/self/gid_map", "w") as f:
        f.write(f"0 {outer_gid} 1")


# Bringing an interface up is an ioctl on any socket. `ip link set lo up` would do the same
# thing and would put util-linux and iproute2 in the sandbox's dependency list, which §6.4.6's
# argument about checks applies to equally: the supervisor should make the syscall it means.
SIOCGIFFLAGS = 0x8913
SIOCSIFFLAGS = 0x8914
IFF_UP = 0x1


def bring_loopback_up() -> None:
    """Raise `lo` inside the calling process's network namespace.

    A freshly created network namespace contains a loopback interface and it is **down**.
    §5.7.3 describes the namespace as giving "no route to anywhere", which is accurate and
    incomplete: it also gives no working loopback, and that is a different thing. Home
    Assistant's HTTP server binds a socket, and on a namespace with no enabled address the
    bind fails — which presented as `async_setup_component(hass, "http", {})` returning False
    with nothing but a warning about source-address detection.

    The grant is narrow by construction: the interface exists only inside this namespace, so
    the sandbox gains the ability to talk to itself and nothing else. Nothing routes out; that
    is still the mediator's job (§5.11.1).

    Requires `CAP_NET_ADMIN`, which the sandbox holds *over its own namespace* by virtue of
    having created it — the same property that makes the other six unshares unprivileged.
    """
    import fcntl
    import socket as _socket
    import struct

    with _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM) as sock:
        request = struct.pack("16sh14s", b"lo", 0, b"")
        current = struct.unpack("16sh14s", fcntl.ioctl(sock, SIOCGIFFLAGS, request))[1]
        fcntl.ioctl(sock, SIOCSIFFLAGS,
                    struct.pack("16sh14s", b"lo", current | IFF_UP, b""))


def probe() -> tuple[bool, str]:
    """Can this process actually create the sandbox's namespaces, right now?

    Done in a forked child, because a process cannot leave a namespace once it has entered
    one and the supervisor must not confine itself while testing whether it can confine.
    """
    outer_uid, outer_gid = os.getuid(), os.getgid()  # before the namespace hides them
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        # Child. Nothing here may allocate or take a lock the fork did not duplicate cleanly,
        # so reporting is done with os.write and the exit with os._exit. The stage is reported
        # alongside the error: "Operation not permitted" from a probe that does four things is
        # not a diagnosis.
        os.close(read_fd)
        stage = "unshare"
        try:
            unshare(SANDBOX_NAMESPACES)
            stage = "uid map"
            write_identity_maps(outer_uid, outer_gid)
            os.write(write_fd, f"ok uid {os.getuid()} in the new namespace".encode())
        except OSError as err:
            os.write(write_fd, f"fail {stage}: {err.strerror or err}".encode()[:200])
        except Exception as err:  # noqa: BLE001 — a failed probe is a result
            os.write(write_fd, f"fail {stage}: {err}".encode()[:200])
        os._exit(0)

    os.close(write_fd)
    with os.fdopen(read_fd, "rb") as f:
        message = f.read().decode(errors="replace")
    os.waitpid(pid, 0)
    if message.startswith("ok "):
        return True, message[3:]
    return False, message.removeprefix("fail ") or "no report from the child"
