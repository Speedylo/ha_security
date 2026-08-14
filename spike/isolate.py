#!/usr/bin/env python3
"""Filesystem and process isolation for the sandboxed integration.

Runs *inside* a fresh set of namespaces (created by `unshare`, see
`isolation_launch.py`) and does three things before handing control to the real
command:

  1. builds a new root filesystem containing only an explicit allowlist of paths,
  2. pivots into it, so everything not on the list ceases to exist,
  3. mounts a private /proc, so the sandbox cannot see any other process.

The design mirrors the manifest: the integration declares what it needs, and it
gets that and nothing else. A blocklist ("hide /home, hide secrets.yaml") would
be weaker and would need updating every time the host layout changed; an
allowlist fails closed.

Usage (normally via isolation_launch.py, which supplies the unshare wrapper):

    unshare --user --map-root-user --pid --fork --mount \
        python3 isolate.py -- python3 runner.py
"""

from __future__ import annotations

import ctypes
import os
import platform
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Kernel plumbing
# ---------------------------------------------------------------------------
# mount(2) flags. Values are fixed by the kernel ABI, not by us.
MS_RDONLY = 1
MS_NOSUID = 2
MS_NODEV = 4
MS_NOEXEC = 8
MS_REMOUNT = 32
MS_BIND = 4096
MS_REC = 16384
MNT_DETACH = 2

# pivot_root(2) has no glibc wrapper, so it is called by syscall number, which
# differs per architecture. The Pi 5 target is aarch64; dev machines are x86_64.
PIVOT_ROOT_SYSCALL = {"x86_64": 155, "aarch64": 41, "armv7l": 218}

_libc = ctypes.CDLL("libc.so.6", use_errno=True)


def _check(result: int, what: str) -> None:
    if result != 0:
        err = ctypes.get_errno()
        raise OSError(err, f"{what} failed: {os.strerror(err)}")


def mount(source: str, target: str, fstype: str | None, flags: int, data: str | None = None) -> None:
    _check(
        _libc.mount(
            source.encode(),
            target.encode(),
            fstype.encode() if fstype else None,
            ctypes.c_ulong(flags),
            data.encode() if data else None,
        ),
        f"mount({source} -> {target})",
    )


def pivot_root(new_root: str, put_old: str) -> None:
    machine = platform.machine()
    number = PIVOT_ROOT_SYSCALL.get(machine)
    if number is None:
        raise RuntimeError(f"pivot_root syscall number unknown for architecture {machine!r}")
    _check(_libc.syscall(number, new_root.encode(), put_old.encode()), "pivot_root")


def umount(target: str, flags: int = 0) -> None:
    _check(_libc.umount2(target.encode(), flags), f"umount({target})")


# ---------------------------------------------------------------------------
# The allowlist
# ---------------------------------------------------------------------------
def allowlist() -> tuple[list[Path], list[Path]]:
    """Return (read_only, read_write) host paths the sandbox may see.

    Everything here is justified by something the integration genuinely needs.
    Anything not returned here will not exist inside the sandbox.
    """
    read_only: list[Path] = [
        # The interpreter, its standard library, shared libraries, and the CA
        # bundle for TLS. On a usr-merged system (Debian/Ubuntu) /bin, /sbin,
        # /lib and /lib64 are all symlinks into /usr, so this one entry covers
        # them once the symlinks are recreated below.
        Path("/usr"),
    ]

    # If we are running inside a virtualenv, its interpreter and site-packages
    # live outside /usr and must be added explicitly, or exec fails with ENOENT.
    for prefix in {sys.prefix, sys.base_prefix}:
        path = Path(prefix)
        if not str(path).startswith("/usr"):
            read_only.append(path)

    here = Path(__file__).resolve().parent
    # The runner and the shim it imports. Note this is deliberately *not* the
    # whole spike directory: audit/ stays invisible, which is what stops the
    # sandbox rewriting its own decision log.
    for name in ("runner.py", "probe.py", "shim", "isolate.py", "syscall_filter.py"):
        candidate = here / name
        if candidate.exists():
            read_only.append(candidate)

    # The integration under test, mounted at its real path so imports resolve.
    integration = os.environ.get("HACS_INTEGRATION_DIR")
    if integration:
        # Parent of custom_components/, as runner.py puts it on sys.path.
        read_only.append(Path(integration).resolve().parent.parent)

    # DNS resolution. resolv.conf is often a symlink; bind what it points at.
    resolv = Path("/etc/resolv.conf")
    if resolv.exists():
        read_only.append(resolv.resolve())

    # The dynamic linker's cache. Without it ctypes.util.find_library() cannot
    # resolve a soname to a path — it shells out to `ldconfig -p`, which reads
    # this file — and any library loaded that way (libseccomp, for one) fails
    # even though the .so itself is present under /usr.
    cache = Path("/etc/ld.so.cache")
    if cache.exists():
        read_only.append(cache)

    read_write: list[Path] = []
    # The bridge socket the supervisor is listening on. Without this the
    # sandbox cannot ask permission for anything, which would be secure but
    # useless. It is the *only* writable window onto the host.
    sandbox_dir = os.environ.get("HACS_SANDBOX_DIR")
    if sandbox_dir:
        read_write.append(Path(sandbox_dir))

    return read_only, read_write


# ---------------------------------------------------------------------------
# Building the new root
# ---------------------------------------------------------------------------
def bind(source: Path, new_root: Path, read_only: bool) -> None:
    """Bind one host path into the new root at the same location."""
    target = new_root / source.relative_to("/")
    if source.is_dir():
        target.mkdir(parents=True, exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()

    mount(str(source), str(target), None, MS_BIND | MS_REC)
    if read_only:
        # A read-only bind needs a second call: the kernel ignores MS_RDONLY on
        # the initial MS_BIND and only applies it on a remount.
        mount(
            "none",
            str(target),
            None,
            MS_BIND | MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV,
        )


def build_root() -> Path:
    """Construct the sandbox root and pivot into it."""
    new_root = Path("/tmp/.sandbox-root")
    new_root.mkdir(parents=True, exist_ok=True)

    # pivot_root requires the new root to be a mount point in its own right.
    mount("none", str(new_root), "tmpfs", MS_NOSUID | MS_NODEV, "size=16m")

    # Order matters: the scratch tmpfs mounts go down *first*, because the
    # allowlist can contain paths underneath them (the bridge socket lives in a
    # mkdtemp under /tmp). Mounting a fresh tmpfs over /tmp afterwards would
    # shadow that bind and the sandbox would lose its only route to the
    # supervisor.
    for scratch in ("tmp", "run"):
        directory = new_root / scratch
        directory.mkdir(exist_ok=True)
        mount("none", str(directory), "tmpfs", MS_NOSUID | MS_NODEV, "size=64m")

    # A private /proc. This is what removes /proc/<supervisor>/environ and
    # /proc/<supervisor>/cmdline — the two token-leak routes that cannot be
    # closed from inside supervisor.py.
    (new_root / "proc").mkdir(exist_ok=True)
    mount("proc", str(new_root / "proc"), "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC)

    # Minimal /dev. urandom is needed by Python's hashing and by TLS.
    (new_root / "dev").mkdir(exist_ok=True)
    mount("none", str(new_root / "dev"), "tmpfs", MS_NOSUID, "size=1m")
    for device in ("null", "zero", "urandom", "random"):
        target = new_root / "dev" / device
        target.touch()
        mount(f"/dev/{device}", str(target), None, MS_BIND)

    ro_paths, rw_paths = allowlist()
    for path in ro_paths:
        bind(path, new_root, read_only=True)
    for path in rw_paths:
        bind(path, new_root, read_only=False)

    # Recreate the usr-merge symlinks so /bin/python3 and the dynamic loader at
    # /lib64/ld-linux-*.so resolve exactly as they do on the host.
    for link in ("bin", "sbin", "lib", "lib64"):
        host = Path("/") / link
        if host.is_symlink():
            (new_root / link).symlink_to(os.readlink(host))

    # Pivot. After this the old root is reachable only at /.oldroot, and the
    # next two lines detach even that.
    old_root = new_root / ".oldroot"
    old_root.mkdir(exist_ok=True)
    os.chdir(str(new_root))
    pivot_root(str(new_root), str(old_root))
    os.chdir("/")
    umount("/.oldroot", MNT_DETACH)
    os.rmdir("/.oldroot")
    return new_root


# ---------------------------------------------------------------------------
# Launcher side — used by supervisor.py, runs on the *host*
# ---------------------------------------------------------------------------
# --user            : a new user namespace, so no host privileges are needed
# --map-root-user   : be root *inside* only, which is what permits the mounts
# --pid --fork      : a new process table; the sandbox becomes pid 1 and cannot
#                     see the supervisor, closing token routes 2 and 3
# --mount           : a private mount table, so the pivot below is invisible
#                     to the host
# --propagation private : do not leak our mounts back to the host
UNSHARE_FLAGS = [
    "--user",
    "--map-root-user",
    "--pid",
    "--fork",
    "--mount",
    "--propagation",
    "private",
]


def wrap(command: list[str]) -> list[str]:
    """Wrap a command so it runs inside the namespaces built above."""
    return [
        "unshare",
        *UNSHARE_FLAGS,
        sys.executable,
        str(Path(__file__).resolve()),
        "--",
        *command,
    ]


def available() -> tuple[bool, str]:
    """Can this host actually do unprivileged isolation? Checked before use."""
    import shutil
    import subprocess

    if shutil.which("unshare") is None:
        return False, "unshare(1) not found — install util-linux"
    probe = subprocess.run(
        ["unshare", "--user", "--map-root-user", "--mount", "true"],
        capture_output=True,
    )
    if probe.returncode != 0:
        detail = probe.stderr.decode(errors="replace").strip() or "unknown error"
        return False, f"unprivileged user namespaces unavailable: {detail}"
    return True, f"unprivileged user + mount + pid namespaces available on {platform.machine()}"


def main() -> int:
    if "--" not in sys.argv:
        print("isolate.py: expected `-- <command>`", file=sys.stderr)
        return 2
    command = sys.argv[sys.argv.index("--") + 1 :]
    if not command:
        print("isolate.py: no command given after --", file=sys.stderr)
        return 2

    build_root()

    # Working directory must exist inside the new root.
    workdir = os.environ.get("HACS_SANDBOX_DIR", "/tmp")
    os.chdir(workdir if Path(workdir).is_dir() else "/tmp")

    # Syscall filter last, so it constrains the integration but not the mount
    # work above (the policy denies mount/pivot_root/unshare, among others).
    # A seccomp filter survives execve, which is what makes this ordering work.
    if os.environ.get("HACS_SECCOMP", "1") != "0":
        import syscall_filter

        # AF_INET is denied by default. The sandbox has no legitimate need for
        # an IP socket: its HTTP goes to the supervisor over AF_UNIX, which is
        # what makes the manifest's `network:` allowlist enforcing rather than
        # advisory. HACS_ALLOW_INET=1 restores the old behaviour so the
        # before/after stays reproducible for the evaluation chapter.
        syscall_filter.apply(
            deny_inet=os.environ.get("HACS_ALLOW_INET") != "1",
            verbose=True,
        )

    os.execvp(command[0], command)
    return 1  # only reached if exec fails


if __name__ == "__main__":
    sys.exit(main())
