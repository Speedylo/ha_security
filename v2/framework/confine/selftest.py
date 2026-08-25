"""Build one sandbox around a deliberately dangerous configuration directory, and look inside.

§5.6.2 claims that under R2 default denial is structural: an integration reading `secrets.yaml`
is not refused, the file is simply not there. §5.10.2 claims a sandbox's filesystem holds "its
own directory and nothing else". §5.10.5 says the configuration root and `.storage/` are not
grantable at all. Those are testable claims and this is the test.

The configuration directory it builds contains exactly what an attacker would want — a secrets
file, the config-entry store, and a second integration's source — and then a sandbox is built
for one integration and asked to report what it can see. The interesting rows are the ones
that come back absent.

Run:  systemd-run --user --scope -q python3 -m confine.selftest
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .cgroup import Delegation, SandboxCgroup
from .preflight import require_ready
from .sandbox import SandboxSpec
from .spawn import become_subreaper, start

SECRET = "api_key: THIS-STRING-MUST-NOT-BE-READABLE"

# Runs inside the sandbox. Deliberately dependency-free and deliberately reporting facts
# rather than verdicts: the assertions belong out here, where they can be read next to the
# claims they check.
INSIDE = r"""
import json, os, socket
from pathlib import Path

def probe(p):
    path = Path(p)
    if not path.exists():
        return {"present": False}
    out = {"present": True, "is_dir": path.is_dir()}
    target = path / ".confine-write-probe" if path.is_dir() else path
    try:
        if path.is_dir():
            target.write_text("x"); target.unlink()
        else:
            with open(path, "a"):
                pass
        out["writable"] = True
    except OSError as err:
        out["writable"] = False
        out["write_error"] = err.strerror
    return out

report = {
    "uid": os.getuid(),
    "hostname": socket.gethostname(),
    "pid": os.getpid(),
    "processes": sorted(p for p in os.listdir("/proc") if p.isdigit()),
    "root_entries": sorted(os.listdir("/")),
    "interfaces": sorted(
        line.split(":")[0].strip()
        for line in Path("/proc/net/dev").read_text().splitlines()[2:] if ":" in line
    ),
    "paths": {p: probe(p) for p in PATHS},
}
print(json.dumps(report))
"""


def build_config(root: Path) -> dict[str, Path]:
    """A configuration directory holding everything a hostile integration would go looking for."""
    layout = {
        "secrets": root / "secrets.yaml",
        "storage": root / ".storage",
        "own": root / "custom_components" / "demo_a",
        "other": root / "custom_components" / "demo_b",
        "shared": root / "shared" / "readable.txt",
        "data": root / ".confine" / "demo_a",
    }
    layout["storage"].mkdir(parents=True)
    (layout["storage"] / "core.config_entries").write_text('{"entries": ["a token"]}')
    layout["secrets"].write_text(SECRET)
    for component in ("own", "other"):
        layout[component].mkdir(parents=True)
        (layout[component] / "__init__.py").write_text("# nothing\n")
        (layout[component] / "manifest.json").write_text(
            json.dumps({"domain": layout[component].name, "name": layout[component].name}))
    layout["shared"].parent.mkdir(parents=True)
    layout["shared"].write_text("a file the manifest declares\n")
    layout["data"].mkdir(parents=True)
    return layout


def run_inside(spec: SandboxSpec, cgroup: SandboxCgroup) -> dict:
    with tempfile.NamedTemporaryFile(prefix="confine-selftest-", suffix=".json") as out:
        with open(out.name, "wb") as stdout:
            sandbox = start(spec, cgroup, stdout=stdout.fileno(),
                            stderr=subprocess.DEVNULL)
            sandbox.wait(timeout=60)
        text = Path(out.name).read_text().strip()
    if not text:
        raise RuntimeError("the sandbox produced no report")
    return json.loads(text)


def main() -> int:
    require_ready(deep=False)
    become_subreaper()

    root = Path(tempfile.mkdtemp(prefix="confine-selftest-"))
    try:
        layout = build_config(root)
        watched = {
            "its own directory": SandboxSpec.COMPONENT,
            "its own data directory": SandboxSpec.DATA,
            "the declared file": str(layout["shared"]),
            "secrets.yaml": str(layout["secrets"]),
            "the .storage directory": str(layout["storage"]),
            "another integration": str(layout["other"]),
            "the configuration root": str(root),
            "the user's home directory": os.path.expanduser("~"),
        }
        script = f"PATHS = {json.dumps(list(watched.values()))}\n" + INSIDE
        spec = SandboxSpec(
            domain="demo_a",
            own_dir=str(layout["own"]),
            data_dir=str(layout["data"]),
            argv=[sys.executable, "-c", script],
            files_ro=[str(layout["shared"])],
        )

        delegation = Delegation.discover()
        with SandboxCgroup.create(delegation, "confine-selftest",
                                  memory_max=256 * 1024**2, pids_max=64) as cgroup:
            report = run_inside(spec, cgroup)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    return render(report, watched)


def render(report: dict, watched: dict[str, str]) -> int:
    print("sandbox self-test — what one integration can see\n")
    print(f"  uid inside              {report['uid']}  (outside: {os.getuid()})")
    print(f"  hostname                {report['hostname']}")
    print(f"  pid                     {report['pid']}")
    print(f"  processes visible       {len(report['processes'])}  {report['processes']}")
    print(f"  network interfaces      {report['interfaces']}")
    print(f"  entries at /            {report['root_entries']}")
    print()

    expectations = [
        # label,                      must be present, must be writable (None = don't care)
        ("its own directory",         True,  False),
        ("its own data directory",    True,  True),
        ("the declared file",         True,  False),
        ("secrets.yaml",              False, None),
        ("the .storage directory",    False, None),
        ("another integration",       False, None),
        ("the configuration root",    False, None),
        ("the user's home directory", False, None),
    ]
    failures = []
    width = max(len(label) for label, _, _ in expectations)
    for label, want_present, want_writable in expectations:
        seen = report["paths"][watched[label]]
        present = seen["present"]
        ok = present == want_present
        detail = "present" if present else "ABSENT"
        if present and want_writable is not None:
            ok = ok and seen.get("writable") is want_writable
            detail += ", writable" if seen.get("writable") else ", read-only"
        if not ok:
            failures.append(label)
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<{width}}  {detail}")

    if len(report["processes"]) != 1:
        failures.append("the PID namespace shows more than the sandbox itself")
    if report["interfaces"] != ["lo"]:
        failures.append(f"the network namespace has {report['interfaces']}, expected only lo")

    print()
    if failures:
        print(f"FAILED: {'; '.join(failures)}")
        return 1
    print("PASS — every claim §5.6.2 and §5.10.2 make about the sandbox's filesystem held,")
    print("       and the two absent rows are absent rather than refused.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
