#!/usr/bin/env python3
"""Where must the supervisor run, for it to put a sandbox in a cgroup?

§5.7.4 recorded a finding: an unprivileged process could not create a cgroup and then move an
existing process into it, because migration needs write access to the *common ancestor* of
source and destination and that is root-owned. From that one failure it drew a design rule —
**the sandbox must be placed in its cgroup at creation** — which §6.3.4 now lists alongside
three other ordering constraints.

The rule was inferred from a single failed command, and it contains an assumption the command
could not test: that placement at creation is permitted where migration is not. This
experiment tests it, because §6.4 has to implement whichever is true and the two lead to very
different supervisors — one that needs `clone3(CLONE_INTO_CGROUP)` and therefore C, or one
that needs only to be started in the right place.

Four operations, each attempted from two positions:

    mkdir            create the sandbox's cgroup under the delegated subtree
    migrate other    write a running child's pid into it
    migrate self     have the child write its own pid into it
    clone3           create the child directly inside it, via CLONE_INTO_CGROUP

The two positions are the interesting variable:

    as launched      an ssh session lands in user-<uid>.slice/session-N.scope, which is
                     *outside* the subtree systemd delegates to the user
    --user --scope   systemd-run relocates into user@<uid>.service/app.slice/..., inside it

Run:  ./place.py [--json results/out.json]     # the driver: both positions, all operations
      ./place.py --probe                       # one position only, as currently placed
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import pwd
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CGROUP_FS = Path("/sys/fs/cgroup")
HELPER_SRC = HERE / "clone_into_cgroup.c"
HELPER_BIN = HERE / "clone_into_cgroup"


def own_cgroup() -> Path:
    """The cgroup this process is in, as a path under the cgroup2 mount."""
    rel = Path("/proc/self/cgroup").read_text().strip().split("::", 1)[1]
    return CGROUP_FS / rel.lstrip("/")


def delegated_root(uid: int) -> Path | None:
    """The root of the subtree systemd hands to this user, if there is one.

    systemd delegates the whole of `user@<uid>.service` to the user's own manager. That is
    the boundary this experiment is about, so it is located rather than assumed: the test is
    ownership of `cgroup.subtree_control`, which is what delegation actually grants.
    """
    conventional = (CGROUP_FS / "user.slice" / f"user-{uid}.slice" / f"user@{uid}.service")
    candidates = [conventional] if conventional.is_dir() else []
    if not candidates:
        candidates = [p for p in CGROUP_FS.glob(f"**/user@{uid}.service") if p.is_dir()]
    for c in candidates:
        ctl = c / "cgroup.subtree_control"
        if ctl.exists() and ctl.stat().st_uid == uid:
            return c
    return None


def common_ancestor(a: Path, b: Path) -> Path:
    """The deepest directory that is a prefix of both — the cgroup the kernel checks."""
    parts_a, parts_b = a.parts, b.parts
    n = 0
    while n < min(len(parts_a), len(parts_b)) and parts_a[n] == parts_b[n]:
        n += 1
    return Path(*parts_a[:n])


class Refused(Exception):
    """An operation the kernel declined, carrying what it said rather than a stack trace."""

    def split(self) -> tuple[str, str]:
        text = str(self)
        head, _, rest = text.partition(" ")
        return (head, rest) if rest else ("REFUSED", text)


def attempt(fn) -> dict:
    """Run one operation and record what the kernel said, rather than only whether it worked."""
    try:
        detail = fn()
        return {"ok": True, "detail": detail or ""}
    except Refused as err:
        code, detail = err.split()
        return {"ok": False, "errno": code, "detail": detail}
    except OSError as err:
        return {"ok": False, "errno": errno_name(err), "detail": err.strerror or str(err)}
    except Exception as err:  # noqa: BLE001 — a failed probe is a result, not a crash
        return {"ok": False, "errno": type(err).__name__, "detail": str(err)}


def errno_name(err: OSError) -> str:
    import errno as e
    return e.errorcode.get(err.errno, str(err.errno))


def spawn_sleeper() -> subprocess.Popen:
    return subprocess.Popen(["sleep", "30"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


def cgroup_of(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/cgroup").read_text().strip().split("::", 1)[1]
    except OSError:
        return "<gone>"


def build_helper() -> bool:
    if HELPER_BIN.exists() and HELPER_BIN.stat().st_mtime >= HELPER_SRC.stat().st_mtime:
        return True
    cc = shutil.which("cc") or shutil.which("gcc")
    if not cc:
        return False
    r = subprocess.run([cc, "-O2", "-Wall", "-o", str(HELPER_BIN), str(HELPER_SRC)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        return False
    return True


def probe() -> dict:
    uid = os.getuid()
    here = own_cgroup()
    root = delegated_root(uid)
    out: dict = {
        "uid": uid,
        "user": pwd.getpwuid(uid).pw_name,
        "own_cgroup": str(here.relative_to(CGROUP_FS)),
        "delegated_root": str(root.relative_to(CGROUP_FS)) if root else None,
        "inside_delegated_subtree": bool(root) and (root == here or root in here.parents),
        "ops": {},
    }
    if root is None:
        out["ops"]["mkdir"] = {"ok": False, "errno": "NODELEGATION",
                               "detail": "no delegated subtree found for this uid"}
        return out

    # Sandboxes go under app.slice when it exists — that is where systemd puts a user's own
    # units, and it already has `memory` enabled in cgroup.subtree_control.
    parent = root / "app.slice" if (root / "app.slice").is_dir() else root
    dest = parent / f"capstone-place-{os.getpid()}"
    out["destination"] = str(dest.relative_to(CGROUP_FS))
    out["common_ancestor"] = str(common_ancestor(here, dest).relative_to(CGROUP_FS))
    try:
        anc = common_ancestor(here, dest)
        out["common_ancestor_owner"] = pwd.getpwuid(anc.stat().st_uid).pw_name
    except (OSError, KeyError):
        out["common_ancestor_owner"] = "?"

    procs = dest / "cgroup.procs"

    def do_mkdir() -> str:
        dest.mkdir()
        return f"controllers: {(dest / 'cgroup.controllers').read_text().strip()}"

    out["ops"]["mkdir"] = attempt(do_mkdir)
    if not out["ops"]["mkdir"]["ok"]:
        return out

    try:
        # 1. migrate a process that is already running — what §5.7.4 tried.
        child = spawn_sleeper()

        def do_migrate_other() -> str:
            procs.write_text(str(child.pid))
            return f"child now in {cgroup_of(child.pid)}"

        out["ops"]["migrate_other"] = attempt(do_migrate_other)
        child.terminate()
        child.wait(timeout=5)

        # 2. the child moves itself. The kernel's rule names the writer, not the subject, so
        # this should behave identically — but "should" is what this experiment is replacing.
        def do_migrate_self() -> str:
            r = subprocess.run([sys.executable, str(HERE / "place.py"),
                                "--self-migrate", str(dest)],
                               capture_output=True, text=True, timeout=30)
            line = (r.stdout or r.stderr).strip()
            if r.returncode != 0:
                raise Refused(line.removeprefix("FAIL ") or "self-migrate failed")
            return line

        out["ops"]["migrate_self"] = attempt(do_migrate_self)

        # 3. placement at creation — the mechanism §5.7.4's rule presumes is available.
        if build_helper():
            def do_clone3() -> str:
                r = subprocess.run([str(HELPER_BIN), str(dest)],
                                   capture_output=True, text=True, timeout=30)
                line = (r.stdout or r.stderr).strip()
                if not line.startswith("OK"):
                    raise Refused(line.removeprefix("FAIL ").strip())
                return line[3:]

            out["ops"]["clone3_into_cgroup"] = attempt(do_clone3)
        else:
            out["ops"]["clone3_into_cgroup"] = {"ok": False, "errno": "NOCC",
                                                "detail": "no C compiler available"}

        # 4. whichever placement worked, does the limit then actually bite? Presence is not
        #    enforcement — the distinction host_isolation_probe/README.md insists on.
        out["ops"]["cap_enforced"] = attempt(lambda: check_cap(dest))
    finally:
        for pid in dest.joinpath("cgroup.procs").read_text().split():
            try:
                (CGROUP_FS / "cgroup.procs").write_text(pid)
            except OSError:
                pass
        try:
            dest.rmdir()
        except OSError as err:
            out["cleanup"] = f"{dest}: {err}"
    return out


def check_cap(dest: Path) -> str:
    """Set a 64 MB cap, ask a child inside the cgroup for 192 MB, and see who wins."""
    (dest / "memory.max").write_text(str(64 * 1024 * 1024))
    try:
        (dest / "memory.swap.max").write_text("0")
    except OSError:
        pass
    r = subprocess.run(
        [sys.executable, str(HERE / "place.py"), "--allocate", str(dest)],
        capture_output=True, text=True, timeout=120)
    if r.returncode == 0 and r.stdout.strip().startswith("PLACED"):
        return "ALLOCATED 192 MB against a 64 MB cap — NOT enforced"
    if "NOTPLACED" in r.stdout:
        raise Refused("UNTESTED the child could not enter the cgroup, so nothing was tested")
    return f"killed (rc={r.returncode}) — cap enforced"


def self_migrate(dest: str) -> int:
    """Helper: try to move *this* process in, and report the errno rather than a traceback."""
    try:
        Path(dest, "cgroup.procs").write_text(str(os.getpid()))
    except OSError as err:
        print(f"FAIL {errno_name(err)} {err.strerror}")
        return 1
    print(f"self now in {cgroup_of(os.getpid())}")
    return 0


def allocate(dest: str) -> int:
    """Enter the cgroup, then ask for far more than its cap allows."""
    try:
        Path(dest, "cgroup.procs").write_text(str(os.getpid()))
    except OSError as err:
        print(f"NOTPLACED {errno_name(err)} {err.strerror}")
        return 3
    time.sleep(0.2)
    _ = bytearray(192 * 1024 * 1024)
    print("PLACED and allocated")
    return 0


def run_position(label: str, argv: list[str]) -> dict:
    r = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    for line in r.stdout.splitlines():
        if line.startswith("PROBE "):
            return {"position": label, **json.loads(line[len("PROBE "):])}
    return {"position": label, "error": (r.stdout + r.stderr)[-500:]}


def render(res: dict) -> None:
    print(f"  own cgroup        {res.get('own_cgroup')}")
    print(f"  delegated root    {res.get('delegated_root')}")
    print(f"  inside it         {res.get('inside_delegated_subtree')}")
    print(f"  common ancestor   {res.get('common_ancestor')} "
          f"(owned by {res.get('common_ancestor_owner')})")
    for op, r in res.get("ops", {}).items():
        mark = "OK  " if r["ok"] else "FAIL"
        extra = r["detail"] if r["ok"] else f"{r.get('errno')} — {r['detail']}"
        print(f"    {op:<20} {mark}  {extra}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="one position, as currently placed")
    ap.add_argument("--self-migrate", metavar="CGROUP")
    ap.add_argument("--allocate", metavar="CGROUP")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    if args.self_migrate:
        return self_migrate(args.self_migrate)
    if args.allocate:
        return allocate(args.allocate)
    if args.probe:
        print("PROBE " + json.dumps(probe()))
        return 0

    me = [sys.executable, str(HERE / "place.py"), "--probe"]
    positions = [("as launched", me)]
    if shutil.which("systemd-run"):
        positions.append(("systemd-run --user --scope",
                          ["systemd-run", "--user", "--scope", "-q", *me]))

    print(f"cgroup placement — {platform.machine()}, kernel {platform.release()}, "
          f"uid {os.getuid()}\n")
    results = []
    for label, argv in positions:
        print(f"--- {label} " + "-" * max(0, 56 - len(label)))
        res = run_position(label, argv)
        results.append(res)
        if "error" in res:
            print(f"  could not run: {res['error']}")
        else:
            render(res)
        print()

    if args.json:
        args.json.write_text(json.dumps(
            {"host": {"machine": platform.machine(), "kernel": platform.release(),
                      "node": platform.node()},
             "positions": results}, indent=2) + "\n")
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
