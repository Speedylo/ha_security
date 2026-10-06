#!/usr/bin/env python3
"""Verification 4.7, the supervisor's half of F35 (notes/review_fixes_prediction.md), case by case.

Each case drives one method of `confine.supervise.Supervisor` directly, on an object built without
its constructor, so that no Home Assistant and no sandbox is needed. The cgroup cases need the Pi's
delegated subtree. Run there, from v2/framework, inside a user scope:

    systemd-run --user --scope -q python3 ../verify/review_units.py

U1  R3/R4  a predecessor's process inside a nested cgroup is killed, and the cgroup removed
U2  R3     a predecessor's cgroup that will not go is refused, not counted as cleared
U3  R10    a cgroup belonging to a supervisor that is still running is left alone
U4  R8     while (A) refuses the token, the reconnect loop says why, once per reason
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "framework"))

from confine import supervise                                  # noqa: E402
from confine.cgroup import Delegation, SandboxCgroup, spawn_confined  # noqa: E402
from confine.real_platform import PlatformError                # noqa: E402

DOMAIN = "review_probe"
results: list[bool] = []


def check(claim: str, ok: bool, detail: str = "") -> None:
    results.append(ok)
    print(f"  {'ok  ' if ok else 'FAIL'}  {claim}{f'  — {detail}' if detail else ''}")


def bare_supervisor() -> supervise.Supervisor:
    sup = object.__new__(supervise.Supervisor)
    sup.domain = DOMAIN
    sup.delegation = Delegation.discover()
    return sup


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # A zombie is dead for this purpose; this script is its parent and has not reaped it.
    return Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()[0] != "Z"


def sleeper(cgroup: SandboxCgroup, *extra: str) -> subprocess.Popen:
    return spawn_confined([sys.executable, "-c", "import time; time.sleep(600)", *extra], cgroup,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def plant(name: str) -> SandboxCgroup:
    return SandboxCgroup.create(Delegation.discover(), name)


def clear(sup: supervise.Supervisor) -> tuple[object, str]:
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            got = sup._clear_predecessors()
    except Exception as err:  # noqa: BLE001 — a refusal is one of the outcomes
        got = err
    return got, out.getvalue().strip()


def tidy(*cgroups: SandboxCgroup) -> None:
    for cg in cgroups:
        for child in sorted(cg.path.glob("*/"), reverse=True):
            if (child / "cgroup.procs").exists():
                SandboxCgroup(child).remove()
        cg.remove()
        time.sleep(0.3)
        cg.remove()


def u1() -> None:
    print("\nU1 (R3, R4) — a predecessor's process in a nested cgroup")
    outer = plant(f"sup-{DOMAIN}-1")
    inner = SandboxCgroup(outer.path / "inner")
    inner.path.mkdir()
    proc = sleeper(inner)
    time.sleep(0.3)
    got, _ = clear(bare_supervisor())
    time.sleep(0.5)
    check("the process is killed", not alive(proc.pid), f"pid {proc.pid}; cleared → {got!r}")
    check("and the cgroup is gone", not outer.path.exists(), str(outer.path.name))
    proc.kill(); proc.wait()
    tidy(outer)


def u2() -> None:
    print("\nU2 (R3) — a predecessor's cgroup that will not go")
    stale = plant(f"sup-{DOMAIN}-2")
    real_rmdir = pathlib.Path.rmdir

    def stuck(self: pathlib.Path) -> None:
        if self == stale.path:
            raise OSError(16, "Device or resource busy")
        real_rmdir(self)
    pathlib.Path.rmdir = stuck   # type: ignore[method-assign]
    try:
        got, said = clear(bare_supervisor())
    finally:
        pathlib.Path.rmdir = real_rmdir   # type: ignore[method-assign]
    refused = isinstance(got, Exception)
    check("the supervisor refuses to start, and says which cgroup", refused
          and stale.path.name in str(got), f"{type(got).__name__}: {got}")
    tidy(stale)


def u3() -> None:
    print("\nU3 (R10) — a cgroup belonging to a supervisor that is still running")
    # A stand-in for a live supervisor: a process whose command line names confine.supervise.
    live = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)",
                             "-m", "confine.supervise"])
    theirs = plant(f"sup-{DOMAIN}-{live.pid}-1")
    proc = sleeper(theirs)
    time.sleep(0.3)
    got, _ = clear(bare_supervisor())
    check("its sandbox is still running", alive(proc.pid), f"cleared → {got!r}")
    check("and its cgroup is still there", theirs.path.exists(), theirs.path.name)
    live.kill(); live.wait()
    proc.kill(); proc.wait()
    tidy(theirs)


class _Mediator:
    def detach_platform(self) -> None:
        pass

    def attach_platform(self, platform: object) -> None:
        pass


class _Platform:
    listeners: list = []

    def close(self) -> None:
        pass


def u4() -> None:
    print("\nU4 (R8) — (A) answers but refuses the token, then accepts it")
    attempts = iter([ConnectionRefusedError(111, "Connection refused"),
                     PlatformError("(A) refused the mediator's token: auth_invalid"),
                     PlatformError("(A) refused the mediator's token: auth_invalid"),
                     FileNotFoundError(2, "No such file or directory"),
                     None])

    def connect(*_a, **_k):
        step = next(attempts)
        if step is not None:
            raise step
        return _Platform()

    sup = object.__new__(supervise.Supervisor)
    sup.domain, sup.sandbox, sup.wanted = DOMAIN, None, True
    sup.mediator, sup.platform, sup.manifest = _Mediator(), _Platform(), None
    sup.stop = lambda: None
    saved = (supervise.RealPlatform, supervise.time.sleep, supervise.acting_policy)
    supervise.RealPlatform, supervise.time.sleep = connect, lambda _s: None
    supervise.acting_policy = lambda *_a, **_k: None
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            sup.platform_lost(ConnectionError("gone"))
    finally:
        supervise.RealPlatform, supervise.time.sleep, supervise.acting_policy = saved
    said = out.getvalue()
    check("the refused token is named", "refused the mediator's token" in said, said.strip()[-300:])
    check("once, though it was refused twice", said.count("refused the mediator's token") == 1)
    check("the missing token file is named", "No such file" in said)


def main() -> int:
    for case in (u1, u2, u3, u4):
        try:
            case()
        except Exception as err:  # noqa: BLE001 — a case that cannot run is a failure, said so
            check(f"{case.__name__} ran", False, f"{type(err).__name__}: {err}")
    print(f"\n{sum(results)}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
