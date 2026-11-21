"""What a sandbox can see of the filesystem, and how that view is built.

§5.6.2 argues that under R2 default denial is *structural* rather than procedural: an
integration reading `secrets.yaml` is not refused by a check, because the file is not in its
mount namespace and there is nothing there to refuse. §5.10.2 makes the same point about the
sandbox's own directory. This module is where those sentences become a filesystem.

The construction is the standard one — a private mount namespace, a fresh tmpfs root, bind
mounts for what is allowed, then `pivot_root` — and three details in it are load-bearing:

  - **Mount propagation is made private first.** This mount namespace belongs to a new user
    namespace, so the kernel has already reduced the copied shared mounts to slave mounts, and
    nothing mounted here propagates back to the host. A slave mount still receives the host's
    mounts, though: without this step, something the host mounted later could appear inside
    the sandbox. Making the whole tree private fixes the view at construction.
  - **`pivot_root`, not `chroot`.** A process inside a user namespace holds `CAP_SYS_CHROOT`
    over that namespace, and a `chroot` is escapable by anything holding it. Using `chroot`
    here would produce a boundary that looks identical from the inside and is not one.
  - **Paths are resolved before they are bound.** §5.10.5's resolve-then-pin, applied to the
    filesystem: a symbolic link or a `..` in a declared path must not be able to name
    something the declaration did not.

**What the sandbox sees that is not "its own directory and nothing else".** It also gets a
read-only copy of the interpreter and libraries it runs on, because R2 runs a real Python
against a real Home Assistant and neither can execute out of nothing. §5.10.2's phrasing is
about *declared* resources; the runtime is ambient, and saying so is better than implying a
sandbox is emptier than it is.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import json
import os
import platform
from dataclasses import dataclass, field
from pathlib import Path

_libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)

MS_RDONLY = 1
MS_NOSUID = 2
MS_NODEV = 4
MS_NOEXEC = 8
MS_REMOUNT = 32
MS_BIND = 4096
MS_REC = 16384
MS_PRIVATE = 1 << 18
MNT_DETACH = 2

# glibc has never exported pivot_root as a function on every platform this might run on, so
# the syscall is issued directly. The number is per-architecture, which is itself a portability
# finding worth recording rather than hiding: isolation code of this kind couples to the
# machine, and a framework claiming to run "on Linux" should say which Linux it was run on.
_PIVOT_ROOT_NR = {"aarch64": 41, "x86_64": 155, "armv7l": 218, "armv6l": 218}


def _check(result: int, what: str) -> None:
    if result != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), what)


def mount(source: str | None, target: str, fstype: str | None,
          flags: int = 0, data: str | None = None) -> None:
    _check(_libc.mount(
        source.encode() if source else None,
        target.encode(), fstype.encode() if fstype else None,
        ctypes.c_ulong(flags), data.encode() if data else None), target)


def umount2(target: str, flags: int = 0) -> None:
    _check(_libc.umount2(target.encode(), ctypes.c_int(flags)), target)


def pivot_root(new_root: str, put_old: str) -> None:
    if hasattr(_libc, "pivot_root"):
        _check(_libc.pivot_root(new_root.encode(), put_old.encode()), "pivot_root")
        return
    machine = platform.machine()
    number = _PIVOT_ROOT_NR.get(machine)
    if number is None:
        raise OSError(f"no pivot_root syscall number known for {machine}; "
                      f"add it to _PIVOT_ROOT_NR after checking the kernel's unistd.h")
    _check(_libc.syscall(ctypes.c_long(number), new_root.encode(), put_old.encode()),
           "pivot_root")


# Everything a Unix program assumes exists. `/dev/full` is included because writing to it is
# how well-behaved code discovers it has run out of space; the rest are the usual four.
# `/dev/tty` was a sixth until 2026-10-06: it is the process's controlling terminal, which for
# a supervisor started from a shell was that shell's (verification 4.7, finding F34).
DEV_NODES = ("null", "zero", "full", "random", "urandom")

# The interpreter and its libraries. Bound read-only, and enumerated rather than inherited so
# that adding to the list is a visible decision.
#
# **`/etc/ssl/certs` was added by §7.31, and it is the directory, not `/etc/ssl`** — Debian
# keeps private keys in `/etc/ssl/private`, beside it. Without it, `ssl.create_default_context()`
# inside a sandbox held **zero** CA certificates, so any TLS client not built on `certifi` —
# a bare `aiohttp.ClientSession()`, `urllib` — failed verification after the mediator had
# granted and connected it. `regensburg_transport` caught the error and showed `unavailable`
# behind three granted connections. `requests`, `httpx` and the platform's own helper session
# all use `certifi`, which is why nothing before §7.31 noticed. The contents are public trust
# anchors, and read-only, so a sandbox can use the host's roots and cannot add one.
DEFAULT_RUNTIME_PATHS = ("/usr", "/lib", "/lib64", "/bin", "/sbin", "/etc/ssl/certs")


class GrantRefused(ValueError):
    """A declared path that the manifest schema forbids (§5.10.5)."""


@dataclass
class SandboxSpec:
    """Everything the supervisor decides about one sandbox's filesystem.

    Serialised to JSON and handed to the child, because the child is a fresh process: it is
    the supervisor that reads the manifest, and the sandbox never sees the manifest itself.
    """

    domain: str
    own_dir: str                      # the integration's own directory, mounted read-only
    data_dir: str                     # its private writable directory
    argv: list[str]
    runtime_paths: list[str] = field(default_factory=lambda: list(DEFAULT_RUNTIME_PATHS))
    files_ro: list[str] = field(default_factory=list)
    files_rw: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    # The descriptor the sandbox's end of the mediator channel arrives on. The supervisor
    # chooses it, because `pass_fds` preserves a descriptor's number rather than letting the
    # child pick (§6.4.5 is the version of that lesson learned expensively).
    channel_fd: int | None = None
    # Framework files bound read-only at fixed paths inside the sandbox: the runtime itself
    # and the spec it reads. Kept separate from `files_ro`, which is the manifest's `files`
    # clause and appears at host paths.
    runtime_files: dict[str, str] = field(default_factory=dict)
    # S9's disk bound, in megabytes, applied as the private /tmp's tmpfs `size=`. It is on the
    # spec rather than on the cgroup because cgroup v2's `io` controller is not delegated to a
    # user manager on the target (§7.22), so the only disk resource this framework can bound
    # unprivileged is the space a sandbox writes into its own scratch. The supervisor takes the
    # number from `resources.disk_mb`; the default is the framework's, not the integration's.
    tmp_size_mb: int = 64
    # F59: a host folder bound read-write at `DATA/.storage`, where Home Assistant keeps its
    # configuration entries and registries, so that they outlive one start. Only that folder:
    # `DATA` itself is still fresh every start, because it is the configuration directory the
    # integration's code is loaded from, and an integration that could keep it could replace its
    # own approved code there (`notes/f59_kept_storage_prediction.md` §0). None keeps nothing.
    kept_dir: str | None = None

    # Inside the sandbox, an integration's own things are always in the same two places,
    # whatever they were called outside. A fixed layout means the sandbox runner needs no
    # configuration and the integration cannot learn its own path on the host.
    COMPONENT = "/sandbox/component"
    DATA = "/sandbox/data"
    KEPT = "/sandbox/data/.storage"

    def to_json(self) -> str:
        return json.dumps({k: v for k, v in self.__dict__.items()})

    @classmethod
    def from_json(cls, text: str) -> SandboxSpec:
        return cls(**json.loads(text))


def reject_forbidden(path: Path, config_root: Path) -> None:
    """Refuse a declared path that reaches what no grant may reach (§5.10.5).

    The manifest parser is where this belongs and where a user gets a useful error. It is
    repeated here because this is the last point before the grant becomes a mount, and a
    check that only exists in the parser is one bug away from not existing — §5.13's layering,
    at the smallest possible scale.
    """
    resolved = path.resolve()
    root = config_root.resolve()
    forbidden = (root, root / ".storage", root / "secrets.yaml")
    for f in forbidden:
        if resolved == f or f in resolved.parents or resolved in f.parents:
            raise GrantRefused(
                f"{path} resolves to {resolved}, which reaches {f} — the configuration root, "
                f"its storage or its secrets are not grantable (§5.10.5)")


def _bind(source: str, target: str, *, read_only: bool) -> None:
    """Bind one host path into the sandbox's root, creating the mount point for it."""
    src = Path(source)
    dst = Path(target)
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.touch(exist_ok=True)

    mount(source, target, None, MS_BIND | MS_REC)
    if read_only:
        # A bind mount does not take its flags from the original call: read-only has to be
        # applied by remounting. Silently skipping this step is how a "read-only" bind ends up
        # writable, which is a failure that looks exactly like success.
        mount(None, target, None,
              MS_REMOUNT | MS_BIND | MS_REC | MS_RDONLY | MS_NOSUID | MS_NODEV)


def build_root(spec: SandboxSpec, scratch: str = "/tmp/.confine-root") -> None:
    """Construct the sandbox's filesystem view and pivot into it.

    Runs in the sandboxed process itself, after `unshare` and after the fork that puts it in
    the new PID namespace, and immediately before `exec`. Everything it does is invisible
    outside this mount namespace.
    """
    # 1. Detach this namespace's propagation from the host's. The kernel has already made the
    #    copied mounts slaves (the namespace belongs to a new user namespace), so nothing here
    #    reaches the host; making them private also stops the host's later mounts reaching in.
    mount(None, "/", None, MS_REC | MS_PRIVATE)

    # 2. A new root that starts genuinely empty. Small on purpose: it holds mount points and
    #    nothing the sandbox writes, so a sandbox filling it is not a way to fill the host.
    Path(scratch).mkdir(parents=True, exist_ok=True)
    mount("tmpfs", scratch, "tmpfs", MS_NOSUID | MS_NODEV, "mode=755,size=4m")

    def inside(path: str) -> str:
        return str(Path(scratch) / path.lstrip("/"))

    # 3. The interpreter and its libraries, read-only. A path that is a symbolic link on this
    #    distribution — /bin and /lib are, on Debian — is recreated as the same link rather
    #    than bound, so that the layout the interpreter expects still resolves.
    for path in spec.runtime_paths:
        source = Path(path)
        if not source.exists():
            continue
        if source.is_symlink():
            link = Path(inside(path))
            link.parent.mkdir(parents=True, exist_ok=True)
            if not link.exists():
                link.symlink_to(os.readlink(source))
            continue
        _bind(path, inside(path), read_only=True)

    # 4. The integration's own two directories, at fixed locations.
    _bind(spec.own_dir, inside(SandboxSpec.COMPONENT), read_only=True)
    _bind(spec.data_dir, inside(SandboxSpec.DATA), read_only=False)
    if spec.kept_dir is not None:
        # Into a data directory the host has just made and nothing has run in, so the mount point
        # cannot be a link the integration planted. Checked anyway: anything already there means
        # the directory is not the fresh one this assumes.
        kept = Path(inside(SandboxSpec.KEPT))
        if kept.exists() or kept.is_symlink():
            raise FileExistsError(f"{SandboxSpec.KEPT} already exists in a fresh data directory")
        _bind(spec.kept_dir, str(kept), read_only=False)

    # 5. /proc, which is a view of *this* PID namespace and therefore lists only the sandbox.
    Path(inside("/proc")).mkdir(parents=True, exist_ok=True)
    mount("proc", inside("/proc"), "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC)

    # 6. A /dev holding five device nodes and no devices. Bound from the host rather than
    #    created, because creating a device node needs privilege the sandbox must not have.
    dev = inside("/dev")
    Path(dev).mkdir(parents=True, exist_ok=True)
    mount("tmpfs", dev, "tmpfs", MS_NOSUID, "mode=755,size=64k")
    for node in DEV_NODES:
        source = f"/dev/{node}"
        if Path(source).exists():
            _bind(source, f"{dev}/{node}", read_only=False)

    # 7. A private /tmp. Whatever the sandbox writes there is its own and disappears with it.
    tmp = inside("/tmp")
    Path(tmp).mkdir(parents=True, exist_ok=True)
    mount("tmpfs", tmp, "tmpfs", MS_NOSUID | MS_NODEV,
          f"mode=1777,size={spec.tmp_size_mb}m")

    # 8a. The framework's own files, at fixed paths. Read-only: the sandbox executes this
    #     code, and code a sandbox can rewrite is not a boundary.
    for source, target in spec.runtime_files.items():
        _bind(source, inside(target), read_only=True)

    # 8b. Whatever the manifest declared, at the paths it declared. Resolution happened when
    #    the supervisor built the spec, so these are already the real paths.
    #
    #    **These are bound last, and the order is the fix for a real defect.** A mount made
    #    later covers one made earlier, so a declared path that happens to fall under one of
    #    the sandbox's own synthetic filesystems — /tmp above all — is shadowed by it if the
    #    synthetic mount comes second. The file is then simply not there, with no error
    #    anywhere: the sandbox sees an absence, and an absence is what this design uses to
    #    mean "not granted". A silently unhonoured grant is therefore indistinguishable from
    #    a refused one, which is the same class of failure as §6.3.3's.
    for path in spec.files_ro:
        _bind(path, inside(path), read_only=True)
    for path in spec.files_rw:
        _bind(path, inside(path), read_only=False)

    # 9. Ordering alone is not a guarantee, so the grants are checked rather than assumed.
    #    Every declared path must be reachable in the new root before the sandbox is allowed
    #    to run in it — the same argument as §6.4.2's preflight, at the scale of one sandbox.
    missing = [p for p in (*spec.files_ro, *spec.files_rw)
               if not Path(inside(p)).exists()]
    if missing:
        raise GrantRefused(
            "declared paths did not survive the mount construction and would have been "
            f"invisible to the sandbox: {', '.join(missing)}")

    # 10. Pivot. The old root is moved to a directory inside the new one and then detached, so
    #    that no path from inside names anything outside. `chdir` first, because pivot_root
    #    leaves the working directory where it was and a process whose cwd is outside the new
    #    root has kept a way back in.
    old = Path(inside("/oldroot"))
    old.mkdir(parents=True, exist_ok=True)
    os.chdir(scratch)
    pivot_root(scratch, str(old))
    os.chdir("/")
    umount2("/oldroot", MNT_DETACH)
    Path("/oldroot").rmdir()
