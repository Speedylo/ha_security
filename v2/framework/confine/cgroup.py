"""Putting a sandbox in a cgroup, from a supervisor that is not root.

§5.7.4 chose cgroup v2 to satisfy S9, and §6.4.1 measured what an unprivileged process is
actually permitted to do with it. The result decides the shape of this module, so it is worth
restating rather than referring to:

  - Creating a cgroup directory succeeds from almost anywhere. It is not evidence of
    anything. Placement is the operation that can fail, and it fails *after* everything the
    supervisor would naturally check has succeeded.
  - Placement — migrating a process in, having it migrate itself, or creating it inside with
    `clone3(CLONE_INTO_CGROUP)` — all require write access to the **common ancestor** of the
    source and destination cgroups. All three fail identically without it.
  - The common ancestor is user-owned only when the supervisor is already inside the subtree
    its user's manager has been delegated. On a systemd host that means running as a systemd
    *user unit*; a login shell or an ssh session is outside it.

So this module does two things and refuses to guess at either: it locates the delegated
subtree by *checking ownership* rather than by assuming a path, and it places the sandbox by
having the sandbox place itself between `fork` and `exec`.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

CGROUP_FS = Path("/sys/fs/cgroup")

# systemd puts a user's own units under app.slice. Sandboxes belong there rather than at the
# delegated root, so that the supervisor's own limits and a sandbox's are siblings and the
# common ancestor of the two is a cgroup this user owns.
PREFERRED_PARENT = "app.slice"


def _text(path: Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def own_cgroup() -> Path | None:
    """The cgroup this process is in.

    cgroup v2 gives a process exactly one line, `0::<path>`. A v1 or hybrid host produces
    several numbered lines instead, and this returns None there rather than picking one —
    everything below assumes the unified hierarchy, and §6.4.2's preflight says so out loud.
    """
    for line in _text(Path("/proc/self/cgroup")).splitlines():
        if line.startswith("0::"):
            return CGROUP_FS / line[3:].lstrip("/")
    return None


def delegated_root(uid: int | None = None) -> Path | None:
    """The root of the cgroup subtree this user's manager may write in, if there is one.

    Delegation is not a path convention, it is an ownership fact: systemd chowns
    `cgroup.subtree_control` to the user for the subtree it hands over. That file is therefore
    what gets tested. The conventional location is tried first only because searching the
    whole of cgroupfs to confirm what is almost always true would be silly.
    """
    uid = os.getuid() if uid is None else uid
    conventional = CGROUP_FS / "user.slice" / f"user-{uid}.slice" / f"user@{uid}.service"
    candidates = [conventional] if conventional.is_dir() else \
        [p for p in CGROUP_FS.glob(f"**/user@{uid}.service") if p.is_dir()]
    for candidate in candidates:
        control = candidate / "cgroup.subtree_control"
        try:
            if control.stat().st_uid == uid:
                return candidate
        except OSError:
            continue
    return None


def common_ancestor(a: Path, b: Path) -> Path:
    """The deepest cgroup that contains both — the one the kernel checks on placement."""
    shared = 0
    while (shared < min(len(a.parts), len(b.parts))
           and a.parts[shared] == b.parts[shared]):
        shared += 1
    return Path(*a.parts[:shared])


@dataclass(frozen=True)
class Delegation:
    """Where this process sits in the cgroup tree, and whether it may place a sandbox."""

    own: Path | None
    root: Path | None
    parent: Path | None
    unavailable: str | None

    @property
    def available(self) -> bool:
        return self.unavailable is None

    @classmethod
    def discover(cls, uid: int | None = None) -> Delegation:
        uid = os.getuid() if uid is None else uid
        own = own_cgroup()
        if own is None:
            return cls(None, None, None,
                       "this host does not use the unified cgroup v2 hierarchy")

        root = delegated_root(uid)
        if root is None:
            return cls(own, None, None,
                       f"no cgroup subtree is delegated to uid {uid}")

        if root != own and root not in own.parents:
            return cls(own, root, None,
                       f"the supervisor is in {own.relative_to(CGROUP_FS)}, which is outside "
                       f"the delegated subtree {root.relative_to(CGROUP_FS)}")

        parent = root / PREFERRED_PARENT if (root / PREFERRED_PARENT).is_dir() else root
        if "memory" not in _text(parent / "cgroup.controllers").split():
            return cls(own, root, parent,
                       f"the memory controller is not available in "
                       f"{parent.relative_to(CGROUP_FS)}")
        return cls(own, root, parent, None)

    def describe(self) -> str:
        """One line naming where we are, for a refusal message that can be acted on."""
        here = self.own.relative_to(CGROUP_FS) if self.own else "?"
        there = self.root.relative_to(CGROUP_FS) if self.root else "none"
        return f"supervisor in {here}; delegated subtree {there}"


# The period `cpu.max` is expressed against. 100 ms is the kernel's own default and the
# smallest unit of accounting that does not make a bursty process look throttled when it is
# not; `cpu_percent` is converted into a quota against it.
CPU_PERIOD_US = 100_000


@dataclass(frozen=True)
class ResourceLimits:
    """S9's bound on one sandbox, as four numbers rather than as four hard-coded constants.

    This type exists because of what §7.21.1 found: every caller was passing its own
    `memory_max` and `pids_max` literals, `cpu_percent` was validated and rendered to the user
    and enforced nowhere, and disk was absent entirely. A manifest clause that does not reach
    an enforcement path is the exact failure §5.10 legislates against one level up, so the
    clause and the enforcement now share one type and there is no second way to reach `create`.

    **Disk is narrower than §4.10.1's wording, and the narrowing is measured rather than
    assumed.** cgroup v2's `io` controller is not delegated to a user manager on the target
    (`experiments/resource_limits/`): writing `+io` to the delegated subtree's
    `cgroup.subtree_control` fails with `ENOENT` and `io.max` never appears in a child cgroup,
    while `cpu`, `memory` and `pids` all arrive. That is §6.4.1's distinction — a controller
    being *present* on the host is not this supervisor being *permitted* to use it — one layer
    down. So `disk_mb` bounds the space a sandbox can consume in its own private `/tmp`, which
    is enforceable unprivileged as a tmpfs `size=`, and I/O *bandwidth* is not bounded at all.
    §7.22 states the narrowing and what stays uncovered.
    """

    memory_mb: int = 640
    cpu_percent: int | None = None
    max_processes: int = 64
    disk_mb: int = 64

    @property
    def memory_max(self) -> int:
        return self.memory_mb * 1024 ** 2

    def cpu_quota(self) -> str | None:
        """`cpu.max`'s two fields, or None when nothing was declared.

        `cpu_percent` is a percentage of **one** processor, which is how §6.7.1 renders it to
        the user, so 200 is a legitimate declaration on a multi-core host and is not clamped.
        """
        if self.cpu_percent is None:
            return None
        return f"{self.cpu_percent * CPU_PERIOD_US // 100} {CPU_PERIOD_US}"


class SandboxCgroup:
    """One sandbox's cgroup: created by the supervisor, entered by the sandbox itself."""

    def __init__(self, path: Path) -> None:
        self.path = path
        # What `create` actually put into the kernel's files, so that a caller — and
        # `selftest_resources` — can assert on the limits in force rather than on the ones
        # that were requested. The two were the same thing until §7.21.1 found they were not.
        self.applied: ResourceLimits | None = None

    # -- supervisor side ---------------------------------------------------------------

    @classmethod
    def create(cls, delegation: Delegation, name: str,
               limits: ResourceLimits | None = None) -> SandboxCgroup:
        """Create the cgroup and apply every limit in `limits`, or refuse and say which.

        `limits` is not optional in the sense that matters — omitting it applies
        `ResourceLimits()`'s defaults rather than applying nothing. There is deliberately no
        way to reach this method with a limit that is declared and then quietly dropped, which
        is what §7.21.1 found the previous signature permitting.
        """
        limits = ResourceLimits() if limits is None else limits
        if not delegation.available:
            raise PlacementUnavailable(delegation.unavailable or "placement unavailable")
        assert delegation.parent is not None

        # A controller only reaches children if the parent has delegated it downward. This is
        # ours to write, and writing it is idempotent, so it is done rather than required.
        # `cpu` joins `memory` and `pids` only when something asked for it, so a host that
        # delegates the other two stays usable by every manifest that declares no CPU bound.
        needed = ["memory", "pids"] + (["cpu"] if limits.cpu_percent is not None else [])
        enabled = _text(delegation.parent / "cgroup.subtree_control").split()
        wanted = [c for c in needed if c not in enabled]
        if wanted:
            try:
                (delegation.parent / "cgroup.subtree_control").write_text(
                    " ".join(f"+{c}" for c in wanted))
            except OSError as err:
                raise PlacementUnavailable(
                    f"cannot enable {' '.join(wanted)} in "
                    f"{delegation.parent.relative_to(CGROUP_FS)}: {err.strerror}. The "
                    f"controller is present on this host but not delegated to uid "
                    f"{os.getuid()}") from err

        path = delegation.parent / name
        path.mkdir(exist_ok=True)
        cgroup = cls(path)
        cgroup.limit_memory(limits.memory_max)
        cgroup._write("pids.max", str(limits.max_processes), "max_processes")
        quota = limits.cpu_quota()
        if quota is not None:
            cgroup._write("cpu.max", quota, "cpu_percent")
        cgroup.applied = limits
        return cgroup

    def _write(self, filename: str, value: str, clause: str) -> None:
        """Write one limit, and refuse the sandbox if the kernel will not take it.

        N3, in the form §6.4.2 argued for: a framework that could not apply a declared limit
        and started the sandbox anyway would leave T16 uncontrolled while implying protection,
        and §6.7.1 would meanwhile be telling the user the limit is in force. Failing here
        makes an unenforceable declaration a refusal that names the clause instead.
        """
        try:
            (self.path / filename).write_text(value)
        except OSError as err:
            raise PlacementUnavailable(
                f"declared resources.{clause} cannot be enforced: writing {filename} in "
                f"{self.path.name} failed with {err.strerror}") from err

    def limit_memory(self, limit_bytes: int) -> None:
        """Apply S9's memory bound.

        Swap is capped at zero as well. Without that the cgroup's memory limit is a limit on
        *resident* memory only, and a sandbox that exceeds it gets slowly swapped instead of
        stopped — which satisfies the file and not the requirement.
        """
        self._write("memory.max", str(limit_bytes), "memory_mb")
        try:
            (self.path / "memory.swap.max").write_text("0")
        except OSError:
            pass  # absent when the kernel is built without swap accounting

    # -- sandbox side ------------------------------------------------------------------

    def place_self(self) -> None:
        """Move the calling process into this cgroup.

        Called in the child between `fork` and `exec`. That timing is the point: the parent
        could migrate the child afterwards, but between the fork and that write the sandbox
        runs with no limit at all, and T16 is exactly a sandbox consuming memory. Doing it
        here means nothing of the sandbox has executed before its limit applies.
        """
        (self.path / "cgroup.procs").write_text(str(os.getpid()))

    # -- observation -------------------------------------------------------------------

    @property
    def pids(self) -> list[int]:
        return [int(p) for p in _text(self.path / "cgroup.procs").split()]

    def event_count(self, name: str) -> int:
        """One counter from `memory.events` — `oom_kill` is the one that answers S9."""
        for line in _text(self.path / "memory.events").splitlines():
            key, _, value = line.partition(" ")
            if key == name:
                return int(value)
        return 0

    def peak_memory(self) -> int:
        return int(_text(self.path / "memory.peak") or 0)

    def cpu_usage_us(self) -> int:
        """Total CPU time charged to this cgroup, in microseconds.

        `cpu.stat`'s `usage_usec`. This is what makes a CPU limit checkable by behaviour
        rather than by reading back the file that was just written — the distinction
        §6.4.2's preflight is built around, and §6.4.6 applied to the seccomp filter.
        """
        for line in _text(self.path / "cpu.stat").splitlines():
            key, _, value = line.partition(" ")
            if key == "usage_usec":
                return int(value)
        return 0

    def throttled_us(self) -> int:
        """Time this cgroup spent throttled by `cpu.max`, from `cpu.stat`."""
        for line in _text(self.path / "cpu.stat").splitlines():
            key, _, value = line.partition(" ")
            if key == "throttled_usec":
                return int(value)
        return 0

    def kill(self) -> None:
        """Kill everything in the cgroup and in every cgroup beneath it.

        `cgroup.kill` (Linux 5.14) does it in the kernel, all at once, so a process that forks
        while this runs cannot leave a child behind. Reading `cgroup.procs` and killing each pid,
        the fallback where the file is absent, races with `fork` and misses nested cgroups
        (verification 4.7, F35 R4).
        """
        if not self.path.exists():
            return
        try:
            (self.path / "cgroup.kill").write_text("1")
            return
        except OSError:
            pass
        for child in self.path.iterdir():
            if child.is_dir():
                SandboxCgroup(child).kill()
        for pid in self.pids:
            try:
                os.kill(pid, 9)
            except ProcessLookupError:
                pass

    def remove(self) -> None:
        """Delete the cgroup. Only an empty cgroup can be removed, so it is emptied first."""
        self.kill()
        self._rmdir_tree()

    def _rmdir_tree(self) -> None:
        if not self.path.exists():
            return
        for child in self.path.iterdir():
            if child.is_dir():
                SandboxCgroup(child)._rmdir_tree()
        try:
            self.path.rmdir()
        except OSError:
            pass  # a cgroup that will not go away is the supervisor's problem, not a crash

    def gone(self, wait: float = 5.0) -> bool:
        """Kill, wait for the cgroup to empty, remove it, and say whether it is gone."""
        self.kill()
        deadline = time.monotonic() + wait
        while self.path.exists() and time.monotonic() < deadline:
            if _text(self.path / "cgroup.events").find("populated 0") >= 0:
                self._rmdir_tree()
            if self.path.exists():
                time.sleep(0.1)
        self._rmdir_tree()
        return not self.path.exists()

    def __enter__(self) -> SandboxCgroup:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.remove()


class PlacementUnavailable(RuntimeError):
    """The host will not let this supervisor confine anything, and says why.

    N3 requires a stated failure mode. This carries the statement, so that the refusal in
    §6.4.2's preflight can name the position the supervisor is actually in rather than
    reporting that something went wrong.
    """


def spawn_confined(cmd: list[str], cgroup: SandboxCgroup, **kwargs) -> subprocess.Popen:
    """Start a process that is already inside `cgroup` by the time it executes.

    `preexec_fn` runs in the child after `fork` and before `exec`, which is the only window in
    which the sandbox can place itself. It is documented as unsafe in the presence of threads;
    the supervisor is single-threaded for this reason, and §6.4.2 records that as a constraint
    on the supervisor rather than as a property of this function.
    """
    return subprocess.Popen(cmd, preexec_fn=cgroup.place_self, **kwargs)  # noqa: PLW1509
