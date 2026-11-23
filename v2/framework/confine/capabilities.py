"""Drop every capability before the integration starts.

**Why the sandbox holds any.** It is built as uid 0 in a user namespace of its own, and the
creator of a user namespace holds every capability over it. That is what lets it bring up its
loopback, mount its file view and `pivot_root` without any privilege on the host. And uid 0 keeps
a full set across `execve`, so unless something drops them, the integration itself starts with
them all. They act only on the sandbox's own namespaces, but they put capability-gated kernel code
within its reach for no purpose: `CAP_NET_ADMIN` opens netfilter, the code behind the well-known
user-namespace escalations. Found 2026-11-22: the framework dropped none.

**What is dropped, and why that is enough.** For uid 0, `execve` gives a permitted set of
(inheritable ∩ the file's inheritable) ∪ (the file's permitted ∩ the bounding set) ∪ ambient,
where the file's sets count as full because the caller is root. So emptying the bounding set, the
ambient set and the inheritable set leaves nothing to give, and `no_new_privs`, already set by the
seccomp filter, stops a file capability from adding one back. The current sets are cleared too,
so the process holds nothing even before `execve`.

**Why seccomp still matters.** Making a new user namespace needs no capability and would hand a
full set back. The filter's refusal of `unshare`, `setns`, and `clone` and `clone3` with namespace
flags is what makes the drop stick. The two layers are complementary: neither is enough alone.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import os

_libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)

PR_CAPBSET_READ = 23
PR_CAPBSET_DROP = 24
PR_CAP_AMBIENT = 47
PR_CAP_AMBIENT_CLEAR_ALL = 4

# `capset` version 3: 64-bit sets, passed as two 32-bit halves.
_LINUX_CAPABILITY_VERSION_3 = 0x20080522


class _CapHeader(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]


class _CapData(ctypes.Structure):
    _fields_ = [("effective", ctypes.c_uint32), ("permitted", ctypes.c_uint32),
                ("inheritable", ctypes.c_uint32)]


def _fail(what: str) -> OSError:
    err = ctypes.get_errno()
    return OSError(err, os.strerror(err), what)


def drop_all() -> int:
    """Empty every capability set of the calling process. Returns how many were in the bounding set.

    The bounding set goes first, because dropping from it needs `CAP_SETPCAP`, which the final
    `capset` removes. The kernel says how many capabilities it has by refusing a number past the
    last, so no list is hard-coded that a newer kernel could outgrow.
    """
    count = 0
    while _libc.prctl(PR_CAPBSET_READ, count, 0, 0, 0) >= 0:
        if _libc.prctl(PR_CAPBSET_DROP, count, 0, 0, 0) != 0:
            raise _fail(f"PR_CAPBSET_DROP {count}")
        count += 1
    if ctypes.get_errno() != errno.EINVAL or count == 0:
        raise _fail("PR_CAPBSET_READ")

    if _libc.prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL, 0, 0, 0) != 0:
        raise _fail("PR_CAP_AMBIENT_CLEAR_ALL")

    header = _CapHeader(_LINUX_CAPABILITY_VERSION_3, 0)
    data = (_CapData * 2)()
    if _libc.capset(ctypes.byref(header), data) != 0:
        raise _fail("capset")

    # Checked rather than trusted, as the seccomp numbers are.
    held = held_sets()
    if any(held.values()):
        raise OSError(errno.EPERM, f"capabilities still held after the drop: {held}")
    return count


def held_sets() -> dict[str, int]:
    """The calling process's five capability sets, as the kernel reports them."""
    with open("/proc/self/status") as status:
        return {line.split(":")[0]: int(line.split()[1], 16) for line in status
                if line.startswith(("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"))}
