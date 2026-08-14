#!/usr/bin/env python3
"""Seccomp policy for the sandboxed integration.

Namespaces decide *what the sandbox can see*. Seccomp decides *what it can ask
the kernel to do*. They address different risks, and the second one exists
largely because of the first: unprivileged user namespaces hand the sandbox a
much wider reachable kernel surface than an ordinary process has, and that
surface has a long history of local privilege-escalation bugs. Denying the
syscalls a polling integration provably never needs shrinks it back.

The policy is a *denylist over a default-allow*, which is the opposite of the
manifest's approach and deserves justification. A default-deny allowlist is
stronger, but CPython, aiohttp and OpenSSL between them issue a wide and
version-dependent syscall set, so an allowlist that is wrong fails by crashing
the integration in ways that look like bugs. The denylist below is chosen so
that every entry is something no integration has any legitimate reason to call,
which makes it safe to enforce and easy to defend. Tightening this to a true
allowlist is future work, and should be driven by tracing rather than guesswork.

Applied after the mounts in isolate.py and immediately before exec, so the
filter is inherited by the integration but does not obstruct sandbox setup.
"""

from __future__ import annotations

import errno
import socket
import sys

# Every entry is (syscall, why a polling integration never needs it).
DENIED = [
    # Reading or controlling other processes.
    ("ptrace", "attach to and control another process"),
    ("process_vm_readv", "read another process's memory directly"),
    ("process_vm_writev", "write another process's memory directly"),
    # Kernel programmability — the highest-value escape surface.
    ("bpf", "load BPF programs into the kernel"),
    ("perf_event_open", "kernel performance counters; a recurring LPE source"),
    ("init_module", "load a kernel module"),
    ("finit_module", "load a kernel module from a file descriptor"),
    ("delete_module", "unload a kernel module"),
    ("kexec_load", "load a replacement kernel"),
    ("kexec_file_load", "load a replacement kernel from a file"),
    # Namespace manipulation. Ours are already built; nesting only helps an
    # attacker looking for a confused-deputy path back out.
    ("unshare", "create further namespaces"),
    ("setns", "join an existing namespace"),
    # Filesystem topology. isolate.py has finished mounting by the time this
    # filter is installed, so nothing legitimate calls these again.
    ("mount", "change the mount table"),
    ("umount2", "unmount a filesystem"),
    ("pivot_root", "change the root filesystem"),
    ("chroot", "change the apparent root directory"),
    ("open_by_handle_at", "open a file by handle; a known container-escape primitive"),
    # Kernel keyring — credential storage the integration has no business in.
    ("keyctl", "manipulate the kernel keyring"),
    ("add_key", "add a key to the kernel keyring"),
    ("request_key", "request a key from the kernel keyring"),
    # Memory and I/O primitives that appear in exploit chains far more often
    # than in application code.
    ("userfaultfd", "handle page faults in userspace; common in exploit chains"),
    ("io_uring_setup", "asynchronous I/O rings; a recent LPE source"),
    # Host-level actions.
    ("reboot", "reboot the machine"),
    ("swapon", "enable swap"),
    ("swapoff", "disable swap"),
]


def apply(deny_inet: bool = False, verbose: bool = False) -> tuple[int, int]:
    """Install the filter. Returns (rules applied, rules skipped).

    Skipped rules are syscalls this kernel or architecture does not know about,
    which is not an error — there is nothing to deny.
    """
    try:
        from pyseccomp import EQ, ERRNO, Arg, SyscallFilter
    except ImportError as err:  # pragma: no cover
        raise RuntimeError(
            "pyseccomp is not installed; run `pip install pyseccomp` "
            "(needs libseccomp on the host)"
        ) from err

    # Default ALLOW: see the module docstring for why this is a denylist.
    syscall_filter = SyscallFilter(defaction=ALLOW_ACTION())

    applied = skipped = 0
    for name, _reason in DENIED:
        try:
            syscall_filter.add_rule(ERRNO(errno.EPERM), name)
            applied += 1
        except (ValueError, OSError, RuntimeError):
            # Unknown on this kernel/arch — nothing to block.
            skipped += 1

    if deny_inet:
        # Argument filtering: allow AF_UNIX (the bridge socket) and deny IP.
        # This is what would *force* all egress through the supervisor rather
        # than merely asking the integration to route it there — see
        # ANALYSIS_2026-08-14_isolation_coverage.md, category B. It breaks any
        # integration that talks to its vendor cloud directly, which is the
        # point: it demonstrates the proxy architecture is enforceable.
        for family in (socket.AF_INET, socket.AF_INET6):
            syscall_filter.add_rule(
                ERRNO(errno.EAFNOSUPPORT), "socket", Arg(0, EQ, int(family))
            )
            applied += 1

    syscall_filter.load()
    if verbose:
        print(
            f"  sandbox: seccomp filter loaded — {applied} rules"
            + (f", {skipped} unsupported on this kernel" if skipped else "")
            + (", AF_INET denied" if deny_inet else ""),
            file=sys.stderr,
        )
    return applied, skipped


def ALLOW_ACTION():  # noqa: N802 - named to read as a constant at the call site
    from pyseccomp import ALLOW

    return ALLOW


if __name__ == "__main__":
    # Self-test: install the filter, then prove one denied syscall is denied.
    apply(verbose=True)
    import ctypes

    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    # PTRACE_TRACEME on ourselves: harmless, and must now fail with EPERM.
    result = libc.ptrace(0, 0, 0, 0)
    code = ctypes.get_errno()
    print(f"ptrace returned {result}, errno={code} ({errno.errorcode.get(code)})")
    print("PASS" if code == errno.EPERM else "FAIL — filter not enforcing")
