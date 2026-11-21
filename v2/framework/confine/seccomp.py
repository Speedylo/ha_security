"""The seccomp-BPF filter, built by hand.

§5.7.3 gives seccomp one job: "denies syscalls outside the set an integration needs". Taken
literally that is an allow-list, and an allow-list for a real CPython running a real Home
Assistant is several hundred entries that change with the interpreter's version. What is
implemented instead is narrower and is worth stating as a deliberate narrowing rather than
presented as the same thing:

    **The other six namespaces have already removed most of what a syscall could reach.**
    There is no network to open, no other process to signal, no host filesystem to name. What
    is left for seccomp is the set of calls that are dangerous *in themselves*, whatever
    namespace they are made from — the ones that attack the kernel, or that rearrange or leave
    the boundary the other six mechanisms just built.

That set is small, which is why a deny-list is defensible here and would not be elsewhere.
§6.4.6 records the residual risk this accepts.

**Denial is `EPERM`, not death.** A killed sandbox is indistinguishable from a crashed one,
and §6.4.5 has already established what this design pays for making failures look like
absences. An errno leaves the sandbox alive to be observed, keeps the failure attributable, and
lets the audit record say what was attempted.

**The syscall numbers are per-architecture and are hard-coded.** There is no portable way to
ask Python for them. A wrong number silently denies the wrong call, so the numbers are not
trusted: `probe()` installs the filter in a throwaway child and *makes* the calls, and the
self-test asserts on what actually happened.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import os
import platform
import struct

_libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)

PR_SET_NO_NEW_PRIVS = 38
PR_SET_SECCOMP = 22
SECCOMP_MODE_FILTER = 2

SECCOMP_RET_ALLOW = 0x7FFF0000
SECCOMP_RET_ERRNO = 0x00050000
SECCOMP_RET_KILL_PROCESS = 0x80000000

AUDIT_ARCH = {"aarch64": 0xC00000B7, "x86_64": 0xC000003E}

# Classic BPF, the only kind seccomp accepts.
BPF_LD_W_ABS = 0x20
BPF_JEQ_K = 0x15
BPF_RET_K = 0x06

BPF_JSET_K = 0x45
BPF_JGE_K = 0x35

# On x86_64 a second calling convention, x32, reports the same architecture value and marks its
# calls by setting this bit in the number, so a list of plain numbers matches none of them and
# the whole deny-list is bypassed (`man 2 seccomp`). Found 2026-11-21. No ordinary x86_64
# program uses x32, so every number at or above the bit is refused. aarch64 has no x32 and no
# number this high, so there the check never fires.
X32_SYSCALL_BIT = 0x40000000

# Offsets into `struct seccomp_data`: nr at 0, arch at 4, then the instruction pointer, then the
# six arguments. 16 is the low word of the first argument on a little-endian machine, which both
# supported architectures are.
OFF_NR = 0
OFF_ARCH = 4
OFF_ARG0_LO = 16

# `unshare` and `setns` are not the only ways to make a namespace: `clone` takes the same
# CLONE_NEW* flags, and `clone3` takes them inside a structure in memory, which a seccomp filter
# cannot read. Found 2026-11-20: with only `unshare` denied, `clone(CLONE_NEWUSER)` and `clone3`
# still gave the sandbox a fresh user namespace holding every capability. So `clone` is refused
# when its flags ask for any new namespace (the flags are its first argument on both
# architectures, and all the CLONE_NEW* bits `clone` accepts are in the low word), and `clone3`
# is answered "not implemented", so that the C library falls back to `clone` and is checked there.
# CLONE_NEWTIME is absent on purpose: `clone` cannot take it (that bit is part of the exit
# signal there), and `clone3`, the only clone that can, is already refused.
CLONE_NAMESPACE_FLAGS = (0x00020000 | 0x02000000 | 0x04000000 | 0x08000000
                         | 0x10000000 | 0x20000000 | 0x40000000)
#                        NEWNS        NEWCGROUP    NEWUTS       NEWIPC
#                        NEWUSER      NEWPID       NEWNET
CLONE_NR = {"aarch64": 220, "x86_64": 56}
CLONE3_NR = 435   # the same on both: it is in the table the architectures share from 424 on

# What is denied, grouped by why. Every entry is here because it attacks the kernel or the
# boundary itself, not because an integration is unlikely to need it.
DENIED_BY_REASON: dict[str, tuple[str, ...]] = {
    "leaving or rearranging the sandbox": (
        "mount", "umount2", "pivot_root", "chroot", "unshare", "setns",
        "open_tree", "move_mount", "fsopen", "fsconfig", "fsmount", "fspick",
        "mount_setattr",
    ),
    "reaching into another process": (
        "ptrace", "process_vm_readv", "process_vm_writev",
    ),
    "attacking or reconfiguring the kernel": (
        "bpf", "perf_event_open", "kexec_load", "init_module", "finit_module",
        "delete_module", "reboot", "swapon", "swapoff", "acct", "syslog",
    ),
    "the kernel keyring, and handles that bypass path resolution": (
        "add_key", "request_key", "keyctl", "name_to_handle_at", "open_by_handle_at",
    ),
    # io_uring performs reads, writes, opens and connects from a ring in shared memory, so the
    # operations never pass this filter one by one. None of them leaves the boundary, but the
    # code behind them is large and young, a frequent source of kernel exploits (2026-11-21).
    "operations the filter would never see one by one": (
        "io_uring_setup", "io_uring_enter", "io_uring_register",
    ),
}

# Numbers, per architecture. aarch64 uses the asm-generic table; x86_64 has its own.
SYSCALLS: dict[str, dict[str, int]] = {
    "aarch64": {
        "umount2": 39, "mount": 40, "pivot_root": 41, "chroot": 51, "acct": 89,
        "unshare": 97, "kexec_load": 104, "init_module": 105, "delete_module": 106,
        "syslog": 116, "ptrace": 117, "reboot": 142, "add_key": 217, "request_key": 218,
        "keyctl": 219, "swapon": 224, "swapoff": 225, "perf_event_open": 241,
        "name_to_handle_at": 264, "open_by_handle_at": 265, "setns": 268,
        "process_vm_readv": 270, "process_vm_writev": 271, "finit_module": 273,
        "bpf": 280, "io_uring_setup": 425, "io_uring_enter": 426,
        "io_uring_register": 427, "open_tree": 428, "move_mount": 429, "fsopen": 430,
        "fsconfig": 431, "fsmount": 432, "fspick": 433, "mount_setattr": 442,
    },
    "x86_64": {
        "ptrace": 101, "syslog": 103, "pivot_root": 155, "chroot": 161, "acct": 163,
        "mount": 165, "umount2": 166, "swapon": 167, "swapoff": 168, "reboot": 169,
        "init_module": 175, "delete_module": 176, "kexec_load": 246, "add_key": 248,
        "request_key": 249, "keyctl": 250, "unshare": 272, "perf_event_open": 298,
        "name_to_handle_at": 303, "open_by_handle_at": 304, "setns": 308,
        "process_vm_readv": 310, "process_vm_writev": 311, "finit_module": 313,
        "bpf": 321, "io_uring_setup": 425, "io_uring_enter": 426,
        "io_uring_register": 427, "open_tree": 428, "move_mount": 429, "fsopen": 430,
        "fsconfig": 431, "fsmount": 432, "fspick": 433, "mount_setattr": 442,
    },
}


class Unsupported(RuntimeError):
    """This architecture has no syscall table here, and guessing one is not an option."""


def denied_names() -> tuple[str, ...]:
    return tuple(name for group in DENIED_BY_REASON.values() for name in group)


def _instruction(code: int, jt: int, jf: int, k: int) -> bytes:
    return struct.pack("=HBBI", code, jt, jf, k)


def build_filter(machine: str | None = None) -> tuple[bytes, list[str]]:
    """Assemble the BPF program, and report which syscalls it actually covers.

    Returning the covered names matters: a syscall this kernel's table does not list is
    skipped rather than silently mapped to zero, and the caller can then say what it did not
    manage to deny instead of implying it denied everything.
    """
    machine = machine or platform.machine()
    arch = AUDIT_ARCH.get(machine)
    table = SYSCALLS.get(machine)
    if arch is None or table is None:
        raise Unsupported(
            f"no seccomp syscall table for {machine}; add one after checking that "
            f"architecture's unistd.h rather than assuming it matches another")

    covered = [name for name in denied_names() if name in table]

    program = [
        # Refuse anything not built for this architecture outright. Without this check a
        # 32-bit call could carry a number that means something else entirely in the table
        # above, which is the classic way a seccomp filter is bypassed.
        _instruction(BPF_LD_W_ABS, 0, 0, OFF_ARCH),
        _instruction(BPF_JEQ_K, 1, 0, arch),
        _instruction(BPF_RET_K, 0, 0, SECCOMP_RET_KILL_PROCESS),
        _instruction(BPF_LD_W_ABS, 0, 0, OFF_NR),
        # x32 numbers: refused whatever call they name.
        _instruction(BPF_JGE_K, 0, 1, X32_SYSCALL_BIT),
        _instruction(BPF_RET_K, 0, 0, SECCOMP_RET_ERRNO | (errno.EPERM & 0xFFFF)),
        # clone3: "not implemented", so the C library retries with clone (checked next).
        _instruction(BPF_JEQ_K, 0, 1, CLONE3_NR),
        _instruction(BPF_RET_K, 0, 0, SECCOMP_RET_ERRNO | (errno.ENOSYS & 0xFFFF)),
        # clone: allowed for a thread or a process, refused for a new namespace. A miss skips
        # the four instructions of this check, with the call number still loaded.
        _instruction(BPF_JEQ_K, 0, 4, CLONE_NR[machine]),
        _instruction(BPF_LD_W_ABS, 0, 0, OFF_ARG0_LO),
        _instruction(BPF_JSET_K, 0, 1, CLONE_NAMESPACE_FLAGS),
        _instruction(BPF_RET_K, 0, 0, SECCOMP_RET_ERRNO | (errno.EPERM & 0xFFFF)),
        _instruction(BPF_RET_K, 0, 0, SECCOMP_RET_ALLOW),
    ]
    n = len(covered)
    for i, name in enumerate(covered):
        # On a match, jump past the remaining comparisons and past the ALLOW, to the DENY.
        program.append(_instruction(BPF_JEQ_K, n - i, 0, table[name]))
    program.append(_instruction(BPF_RET_K, 0, 0, SECCOMP_RET_ALLOW))
    program.append(_instruction(BPF_RET_K, 0, 0,
                                SECCOMP_RET_ERRNO | (errno.EPERM & 0xFFFF)))
    return b"".join(program), covered


class _SockFprog(ctypes.Structure):
    _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.c_void_p)]


def install(machine: str | None = None) -> list[str]:
    """Install the filter on the calling process. Irreversible, and inherited across exec."""
    program, covered = build_filter(machine)
    if _libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), "PR_SET_NO_NEW_PRIVS")

    buffer = ctypes.create_string_buffer(program, len(program))
    fprog = _SockFprog(len(program) // 8, ctypes.cast(buffer, ctypes.c_void_p))
    if _libc.prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ctypes.byref(fprog), 0, 0) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), "PR_SET_SECCOMP")
    return covered


# Calls the probe makes to check the filter *behaves*, rather than trusting the table. Each is
# harmless, and each would succeed without the filter — `chroot` and `unshare` in particular
# succeed inside a user namespace, which is exactly why they are worth denying.
def _try_chroot() -> int:
    return 0 if _libc.chroot(b"/") == 0 else ctypes.get_errno()


def _try_unshare() -> int:
    return 0 if _libc.unshare(ctypes.c_int(0x10000000)) == 0 else ctypes.get_errno()


def _try_ptrace() -> int:
    return 0 if _libc.ptrace(0, 0, 0, 0) == 0 else ctypes.get_errno()


def _try_keyctl() -> int:
    return 0 if _libc.syscall(ctypes.c_long(SYSCALLS[platform.machine()]["keyctl"]),
                              0, 0, 0, 0, 0) >= 0 else ctypes.get_errno()


def _try_clone(nr: int, *args) -> int:
    """Make a new user namespace through a clone call; the child, if one is born, leaves at once."""
    _libc.syscall.restype = ctypes.c_long
    pid = _libc.syscall(ctypes.c_long(nr), *args)
    if pid == 0:
        os._exit(0)
    if pid < 0:
        return ctypes.get_errno()
    os.waitpid(pid, 0)
    return 0


def _try_clone_newuser() -> int:
    return _try_clone(CLONE_NR[platform.machine()], ctypes.c_ulong(0x10000000 | 17), 0, 0, 0, 0)


def _try_clone3_newuser() -> int:
    # struct clone_args: flags, pidfd, child_tid, parent_tid, exit_signal, then six more fields.
    args = struct.pack("=11Q", 0x10000000, 0, 0, 0, 17, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(args, len(args))
    code = _try_clone(CLONE3_NR, buf, ctypes.c_size_t(len(args)))
    # ENOSYS is this filter's answer for clone3; anything else that is not success is too.
    return errno.EPERM if code == errno.ENOSYS else code


def _try_x32_unshare() -> int:
    """`unshare(CLONE_NEWUSER)` through its x32 number, in a child that leaves at once."""
    pid = os.fork()
    if pid == 0:
        _libc.syscall.restype = ctypes.c_long
        r = _libc.syscall(ctypes.c_long(X32_SYSCALL_BIT | 272), ctypes.c_ulong(0x10000000))
        os._exit(0 if r == 0 else (ctypes.get_errno() or 1))
    _, status = os.waitpid(pid, 0)
    code = os.waitstatus_to_exitcode(status)
    # A kernel built without x32 answers ENOSYS: the door does not exist there, which is as good.
    return errno.EPERM if code == errno.ENOSYS else code


def _try_io_uring() -> int:
    _libc.syscall.restype = ctypes.c_long
    params = ctypes.create_string_buffer(120)   # struct io_uring_params, zeroed
    fd = _libc.syscall(ctypes.c_long(425), 4, params)
    if fd < 0:
        return ctypes.get_errno()
    os.close(fd)
    return 0


# The clone probes qualify for the same reason as `unshare`: an ordinary user may make a user
# namespace, so the call succeeds without the filter and its refusal is evidence of the filter.
BEHAVIOURAL = {"chroot": _try_chroot, "unshare": _try_unshare,
               "clone(CLONE_NEWUSER)": _try_clone_newuser,
               "clone3(CLONE_NEWUSER)": _try_clone3_newuser,
               "ptrace": _try_ptrace, "keyctl": _try_keyctl,
               "io_uring_setup": _try_io_uring}
if platform.machine() == "x86_64":
    BEHAVIOURAL["x32:unshare(CLONE_NEWUSER)"] = _try_x32_unshare


def probe() -> dict[str, str]:
    """Install the filter in a throwaway child and make the calls it claims to deny."""
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        try:
            install()
            results = {name: fn() for name, fn in BEHAVIOURAL.items()}
            # A call that still works is the failure worth catching: it means this
            # architecture's number for it is wrong, or the filter never loaded.
            report = " ".join(
                f"{name}={'DENIED' if code == errno.EPERM else 'ALLOWED' if code == 0 else os.strerror(code)}"
                for name, code in results.items())
            os.write(write_fd, report.encode()[:400])
        except OSError as err:
            os.write(write_fd, f"error {err.strerror or err}".encode()[:400])
        except Unsupported as err:
            os.write(write_fd, f"error {err}".encode()[:400])
        os._exit(0)

    os.close(write_fd)
    with os.fdopen(read_fd, "rb") as f:
        message = f.read().decode(errors="replace")
    _, status = os.waitpid(pid, 0)
    if os.WIFSIGNALED(status):
        return {"_error": f"the probe child was killed by signal {os.WTERMSIG(status)}"}
    if message.startswith("error "):
        return {"_error": message[6:]}
    return dict(item.split("=", 1) for item in message.split() if "=" in item)
