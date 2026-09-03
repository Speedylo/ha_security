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
IFF_MULTICAST = 0x1000


def bring_loopback_up() -> None:
    """Raise `lo` inside the calling process's network namespace, and mark it multicast-capable.

    A freshly created network namespace contains a loopback interface and it is **down**.
    §5.7.3 describes the namespace as giving "no route to anywhere", which is accurate and
    incomplete: it also gives no working loopback, and that is a different thing. Home
    Assistant's HTTP server binds a socket, and on a namespace with no enabled address the
    bind fails — which presented as `async_setup_component(hass, "http", {})` returning False
    with nothing but a warning about source-address detection.

    **`IFF_MULTICAST` is set for the same reason, and the evidence for it arrived later.**
    A fresh namespace's `lo` carries no multicast flag, so `IP_ADD_MEMBERSHIP` fails with
    `ENODEV` — and Home Assistant constructs a resolver that joins the mDNS group *at client
    session construction*:

        aiohttp_client._async_make_resolver(hass)
            -> HassAsyncDNSResolver(async_zeroconf=zeroconf.async_get_async_zeroconf(hass))

    So `async_get_clientsession(hass)` — the platform's own documented way for an integration
    to make an HTTP request, and the way a real one does it — could not be *constructed* inside
    the sandbox at all, before any name was resolved or any connection attempted. §7.27 is the
    measurement that found it, on `nordpool`, and it is why that section exists.

    **The grant is vacuous by construction, which is what makes it the right answer rather than
    a concession.** The namespace holds `lo` and nothing else, so a group joined on it can
    carry only what this sandbox sends to itself: no datagram reaches another host, no device
    is discovered, and nothing is learned about the home network. This is §5.6.2's structural
    denial rather than a permission — the same shape as the loopback grant above, which lets
    the sandbox talk to itself and to nobody else. Discovery that is *meant* to reach the real
    network stays mediated, behind the `discover` clause of
    `notes/decision_network_capability.md`.

    The cost is stated rather than absorbed: an integration that genuinely depends on mDNS
    discovery finds no devices here. That is a real limit and a far smaller one than being
    unable to build an HTTP client.

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
                    struct.pack("16sh14s", b"lo", current | IFF_UP | IFF_MULTICAST, b""))


SIOCADDRT = 0x890B
RTF_UP = 0x0001


def route_multicast_to_loopback() -> None:
    """Route 224.0.0.0/4 to `lo` inside the calling process's network namespace.

    The `IFF_MULTICAST` flag alone is not enough, and the reason is worth recording because it
    was found by measurement rather than by reading. A join through a **specific** interface
    address succeeds once the flag is set; a join through `INADDR_ANY` — which is what
    `zeroconf` issues — still fails with `ENODEV`, because the kernel resolves the interface
    for an unbound join from the routing table, and a fresh namespace has no route for the
    multicast range at all:

        lo flags 0x1049 (UP|LOOPBACK|RUNNING|MULTICAST)
            join via 127.0.0.1 : OK
            join via 0.0.0.0   : [Errno 19] No such device      <- before this route
            join via 0.0.0.0   : OK                             <- after it

    **This grants no reach and the arithmetic is the argument.** The route's device is `lo`, so
    every multicast datagram the sandbox sends is delivered to the sandbox. There is no other
    interface in the namespace for the kernel to choose and none can be added without
    `CAP_NET_ADMIN` over a namespace the sandbox does not own. §5.6.2's structural denial, in a
    routing table: the capability is present and vacuous rather than absent and fatal.

    `SIOCADDRT` rather than `ip route add`, on §6.4.6's rule that the supervisor should make the
    syscall it means instead of shelling out to a tool it would then have to put in the
    sandbox's mount namespace.
    """
    import ctypes
    import fcntl
    import socket as _socket
    import struct

    class _SockAddr(ctypes.Structure):
        _fields_ = [("sa_family", ctypes.c_ushort), ("sa_data", ctypes.c_char * 14)]

    class _RtEntry(ctypes.Structure):
        _fields_ = [("rt_pad1", ctypes.c_ulong), ("rt_dst", _SockAddr),
                    ("rt_gateway", _SockAddr), ("rt_genmask", _SockAddr),
                    ("rt_flags", ctypes.c_ushort), ("rt_pad2", ctypes.c_short),
                    ("rt_pad3", ctypes.c_ulong), ("rt_tos", ctypes.c_ubyte),
                    ("rt_class", ctypes.c_ubyte), ("rt_pad4", ctypes.c_short * 3),
                    ("rt_metric", ctypes.c_short), ("rt_dev", ctypes.c_char_p),
                    ("rt_mtu", ctypes.c_ulong), ("rt_window", ctypes.c_ulong),
                    ("rt_irtt", ctypes.c_ushort)]

    def address(text: str) -> _SockAddr:
        out = _SockAddr()
        out.sa_family = _socket.AF_INET
        out.sa_data = struct.pack("!H", 0) + _socket.inet_aton(text) + b"\x00" * 8
        return out

    route = _RtEntry()
    route.rt_dst = address("224.0.0.0")
    route.rt_genmask = address("240.0.0.0")
    route.rt_gateway = address("0.0.0.0")
    route.rt_flags = RTF_UP
    route.rt_dev = b"lo"
    with _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM) as sock:
        fcntl.ioctl(sock, SIOCADDRT, route)


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
