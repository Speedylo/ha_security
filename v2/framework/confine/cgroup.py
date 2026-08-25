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


class SandboxCgroup:
    """One sandbox's cgroup: created by the supervisor, entered by the sandbox itself."""

    def __init__(self, path: Path) -> None:
        self.path = path

    # -- supervisor side ---------------------------------------------------------------

    @classmethod
    def create(cls, delegation: Delegation, name: str, *,
               memory_max: int | None = None, pids_max: int | None = None) -> SandboxCgroup:
        if not delegation.available:
            raise PlacementUnavailable(delegation.unavailable or "placement unavailable")
        assert delegation.parent is not None

        # A controller only reaches children if the parent has delegated it downward. This is
        # ours to write, and writing it is idempotent, so it is done rather than required.
        enabled = _text(delegation.parent / "cgroup.subtree_control").split()
        wanted = [c for c in ("memory", "pids") if c not in enabled]
        if wanted:
            try:
                (delegation.parent / "cgroup.subtree_control").write_text(
                    " ".join(f"+{c}" for c in wanted))
            except OSError as err:
                raise PlacementUnavailable(
                    f"cannot enable {' '.join(wanted)} in "
                    f"{delegation.parent.relative_to(CGROUP_FS)}: {err.strerror}") from err

        path = delegation.parent / name
        path.mkdir(exist_ok=True)
        cgroup = cls(path)
        if memory_max is not None:
            cgroup.limit_memory(memory_max)
        if pids_max is not None:
            (path / "pids.max").write_text(str(pids_max))
        return cgroup

    def limit_memory(self, limit_bytes: int) -> None:
        """Apply S9's memory bound.

        Swap is capped at zero as well. Without that the cgroup's memory limit is a limit on
        *resident* memory only, and a sandbox that exceeds it gets slowly swapped instead of
        stopped — which satisfies the file and not the requirement.
        """
        (self.path / "memory.max").write_text(str(limit_bytes))
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

    def remove(self) -> None:
        """Delete the cgroup. Only an empty cgroup can be removed, so it is emptied first."""
        for pid in self.pids:
            try:
                os.kill(pid, 9)
            except ProcessLookupError:
                pass
        try:
            self.path.rmdir()
        except OSError:
            pass  # a cgroup that will not go away is the supervisor's problem, not a crash

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
