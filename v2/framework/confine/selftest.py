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

from .cgroup import Delegation, ResourceLimits, SandboxCgroup
from .preflight import require_ready
from .sandbox import SandboxSpec
from .spawn import become_subreaper, start

SECRET = "api_key: THIS-STRING-MUST-NOT-BE-READABLE"

# Runs inside the sandbox. Deliberately dependency-free and deliberately reporting facts
# rather than verdicts: the assertions belong out here, where they can be read next to the
# claims they check.
INSIDE = r"""
import ctypes, ctypes.util, json, os, socket, ssl
from pathlib import Path

libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)

# Make one syscall the filter should refuse, and report what came back.
def attempt(fn):
    ctypes.set_errno(0)
    return "allowed" if fn() == 0 else os.strerror(ctypes.get_errno())

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
    # Verification 4.7, F34: what /dev holds, and whether this process has a controlling
    # terminal. `tty_nr` is field 7 of /proc/self/stat, counted after the parenthesised name;
    # 0 means none.
    "dev": sorted(os.listdir("/dev")),
    "tty_nr": int(Path("/proc/self/stat").read_text().rpartition(")")[2].split()[4]),
    "interfaces": sorted(
        line.split(":")[0].strip()
        for line in Path("/proc/net/dev").read_text().splitlines()[2:] if ":" in line
    ),
    "paths": {p: probe(p) for p in PATHS},
    # What the configuration root looks like from in here. It exists — binding a declared
    # path necessarily creates the directories above it — so the question worth asking is
    # not whether it is there but whether anything is in it.
    # Made from inside the real sandbox, not a test harness: the filter is installed
    # immediately before this interpreter was executed. chroot and unshare both succeed
    # inside a user namespace, so refusal here is evidence of seccomp and not of the
    # namespace that surrounds it.
    "syscalls": {
        "chroot": attempt(lambda: libc.chroot(b"/")),
        "unshare": attempt(lambda: libc.unshare(0x10000000)),
        "ptrace": attempt(lambda: libc.ptrace(0, 0, 0, 0)),
    },
    "config_root_listing": (sorted(os.listdir(CONFIG_ROOT))
                            if Path(CONFIG_ROOT).is_dir() else None),
    # §7.31.4. What the interpreter's default TLS context will trust. `capath` certificates are
    # loaded lazily, so the count that matters is the readable files there, not
    # `cert_store_stats()`, which reads 0 for a populated capath until something verifies.
    "tls": (lambda capath: {
        "capath": capath,
        "readable": sum(1 for f in Path(capath).iterdir() if f.is_file())
                    if capath and Path(capath).is_dir() else 0,
        "capath_probe": probe(capath) if capath else {"present": False},
        "etc": sorted(os.listdir("/etc")) if Path("/etc").is_dir() else None,
        "etc_ssl": sorted(os.listdir("/etc/ssl")) if Path("/etc/ssl").is_dir() else None,
        "private_present": Path("/etc/ssl/private").exists(),
    })(ssl.get_default_verify_paths().capath),
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
        script = (f"PATHS = {json.dumps(list(watched.values()))}\n"
                  f"CONFIG_ROOT = {json.dumps(str(root))}\n" + INSIDE)
        spec = SandboxSpec(
            domain="demo_a",
            own_dir=str(layout["own"]),
            data_dir=str(layout["data"]),
            argv=[sys.executable, "-c", script],
            files_ro=[str(layout["shared"])],
        )

        delegation = Delegation.discover()
        with SandboxCgroup.create(delegation, "confine-selftest",
                                  ResourceLimits(memory_mb=256)) as cgroup:
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
        # Present, and that is not a failure: a bind mount creates the directories above its
        # target, so granting one path inside the configuration directory makes the
        # directory itself exist. What matters is that it is a skeleton — see below.
        ("the configuration root",    True,  None),
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

    listing = report["config_root_listing"]
    granted_only = listing == ["shared"]
    print(f"  {'ok  ' if granted_only else 'FAIL'}  {'…and it holds only':<{width}}  "
          f"{listing}")
    if not granted_only:
        failures.append(f"the configuration root holds {listing}, expected only ['shared']")

    print()
    for call, outcome in sorted(report["syscalls"].items()):
        denied = outcome == "Operation not permitted"
        print(f"  {'ok  ' if denied else 'FAIL'}  {call + '(2)':<{width}}  {outcome}")
        if not denied:
            failures.append(f"{call} was {outcome} inside the sandbox")

    # §7.31.4: the sandbox once held **zero** trust anchors, so any TLS client not built on
    # `certifi` failed verification *after* the mediator had granted and connected it. The
    # fix exposes one public directory read-only, and this asserts both halves — that it is
    # there, and that nothing beside it is.
    tls = report["tls"]
    tls_checks = [
        (tls["readable"] > 0, "the default TLS context has CA certificates to trust",
         f"{tls['readable']} readable in {tls['capath']}"),
        (tls["capath_probe"].get("writable") is False, "…and cannot add one",
         "absent" if not tls["capath_probe"].get("present")
         else "read-only" if tls["capath_probe"].get("writable") is False else "WRITABLE"),
        (tls["etc"] == ["ssl"] and tls["etc_ssl"] == ["certs"],
         "/etc holds ssl/certs and nothing else", f"/etc={tls['etc']} /etc/ssl={tls['etc_ssl']}"),
        (not tls["private_present"], "/etc/ssl/private is absent", "absent"
         if not tls["private_present"] else "PRESENT"),
    ]
    print()
    for ok, label, detail in tls_checks:
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<{width}}  {detail}")
        if not ok:
            failures.append(label)

    # F34: a sandbox that shares the supervisor's terminal can write into it, and a terminal is
    # not something the mediator sees. No terminal device in /dev, and no controlling terminal.
    # Run from a terminal to make the second check mean anything (`script -qc` supplies one).
    terminal = [
        ("tty" not in report["dev"], "/dev holds no terminal", f"{report['dev']}"),
        (report["tty_nr"] == 0, "no controlling terminal",
         "none" if report["tty_nr"] == 0 else f"tty_nr {report['tty_nr']}"
         + ("" if sys.stdin.isatty() else " (this run has no terminal: proves nothing)")),
    ]
    print()
    for ok, label, detail in terminal:
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<{width}}  {detail}")
        if not ok:
            failures.append(label)
    if not sys.stdin.isatty():
        print(f"  note  {'':<{width}}  no terminal attached to this run, so the second row "
              f"cannot fail")

    if len(report["processes"]) != 1:
        failures.append("the PID namespace shows more than the sandbox itself")
    if report["interfaces"] != ["lo"]:
        failures.append(f"the network namespace has {report['interfaces']}, expected only lo")

    print()
    if failures:
        print(f"FAILED: {'; '.join(failures)}")
        return 1
    print("PASS — every claim §5.6.2 and §5.10.2 make about the sandbox's filesystem held.")
    print("       The absent rows are absent rather than refused, and the configuration")
    print("       root exists only as the skeleton one granted path requires.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
