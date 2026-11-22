"""Installing an integration's dependencies: a package built from source, with and without a sandbox.

A dependency that ships only as source (no wheel) is *built* when it is installed, and building
runs the package's own code: its `setup.py`, or the build backend it names. That code belongs to
whoever published the package, exactly like the integration's own code, so it must not run with
the user's authority on the host. A wheel is different: installing one only unpacks files, and
none of the package's code runs.

The probe is a source-only package whose build script tries three things, the same three an
integration's own code would try (§2): write a file outside, read a planted secret, and connect
to a listener on the host's loopback. It records what it managed into the package it builds, so
the installed files say what the build could do.

    unconfined   the install as it was before this test existed: `uv pip install` on the host,
                 which builds the source package in the user's own environment. The probe must
                 SUCCEED here, or the confined arm proves nothing.
    confined     `compat.install_requirements`: wheels only on the host; anything that needs
                 building is built inside a sandbox with no network. The probe must fail at all
                 three, AND the package must still install, or the fix has only broken installs.

Run:  systemd-run --user --scope -q python3 -m confine.selftest_install --python <ha-interpreter>
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import os
import shutil
import socket
import sys
import tarfile
import tempfile
import threading
from pathlib import Path

from .compat import install_requirements
from .preflight import require_ready
from .provenance import RESOLVE_BEFORE
from .spawn import become_subreaper

PROBE = "confine-buildprobe"
PROBE_DIR = "confine_buildprobe"
CANARY = "CANARY-BUILDPROBE-3d91c07e5a2b48f6-DO-NOT-DISCLOSE"

SETUP_PY = '''
import json, os, pathlib, socket
seen = {{}}
try:
    pathlib.Path({marker!r}).write_text("the build ran here")
    seen["wrote_outside"] = True
except OSError:
    seen["wrote_outside"] = False
try:
    seen["read_secret"] = pathlib.Path({secret!r}).read_text()
except OSError:
    seen["read_secret"] = None
try:
    s = socket.create_connection(("127.0.0.1", {port}), timeout=3)
    s.sendall(b"probe")
    s.close()
    seen["reached_host_listener"] = True
except OSError:
    seen["reached_host_listener"] = False
seen["host_dir_visible"] = os.path.exists({host_dir!r})
pkg = pathlib.Path("confine_buildprobe")
pkg.mkdir(exist_ok=True)
(pkg / "__init__.py").write_text("SEEN = " + repr(json.dumps(seen)) + "\\n")
from setuptools import setup
setup(name="confine-buildprobe", version="0.1", packages=["confine_buildprobe"])
'''

PKG_INFO = "Metadata-Version: 2.1\nName: confine-buildprobe\nVersion: 0.1\n"


class Listener:
    """A TCP listener on the host's loopback that counts who reached it."""

    def __init__(self) -> None:
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(8)
        self.port = self.sock.getsockname()[1]
        self.hits = 0
        self._stop = False
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        self.sock.settimeout(0.5)
        while not self._stop:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                continue
            self.hits += 1
            conn.close()

    def close(self) -> None:
        self._stop = True
        self.sock.close()


def make_probe(where: Path, marker: Path, secret: Path, port: int, host_dir: Path) -> Path:
    """A source distribution, and only that: no wheel exists for it anywhere."""
    sdist = where / "confine_buildprobe-0.1.tar.gz"
    setup = SETUP_PY.format(marker=str(marker), secret=str(secret), port=port,
                            host_dir=str(host_dir))
    with tarfile.open(sdist, "w:gz") as tar:
        for name, text in (("setup.py", setup), ("PKG-INFO", PKG_INFO)):
            data = text.encode()
            info = tarfile.TarInfo(f"confine_buildprobe-0.1/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return sdist


def seen_by_build(target: Path) -> dict | None:
    """What the build recorded, read as text: the installed probe is never imported here."""
    init = target / PROBE_DIR / "__init__.py"
    if not init.exists():
        return None
    text = init.read_text().strip()
    return json.loads(ast.literal_eval(text.partition("=")[2].strip()))


def arm_unconfined(uv: str, python: Path, target: Path, env: dict) -> dict:
    """The install exactly as `install_requirements` ran it before: on the host."""
    import subprocess
    proc = subprocess.run(
        [uv, "pip", "install", "--quiet", "--python", str(python), "--target", str(target),
         "--exclude-newer", RESOLVE_BEFORE, PROBE],
        capture_output=True, text=True, timeout=600, env=env)
    return {"ok": proc.returncode == 0, "error": (proc.stderr or "").strip()[-300:],
            "seen": seen_by_build(target)}


def arm_confined(uv: str, python: Path, target: Path) -> dict:
    result = install_requirements([PROBE], target, python, uv, timeout=600)
    return {"ok": bool(result.get("ok")), "error": result.get("error", ""),
            "built_in_sandbox": result.get("built_in_sandbox"), "seen": seen_by_build(target)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", required=True, help="an interpreter with homeassistant")
    ap.add_argument("--uv", default=shutil.which("uv") or str(Path.home() / ".local/bin/uv"))
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    require_ready(deep=False)
    become_subreaper()
    python = Path(args.python)

    root = Path(tempfile.mkdtemp(prefix="confine-install-test-"))
    listener = Listener()
    try:
        outside = root / "outside"
        outside.mkdir()
        secret = outside / "secret.txt"
        secret.write_text(CANARY)
        marker = outside / "marker.txt"
        links = root / "links"
        links.mkdir()
        make_probe(links, marker, secret, listener.port, outside)

        # The probe is found through `find-links`, as a local index would serve it. The cache
        # is off so that each arm really builds, rather than reusing the other arm's wheel.
        os.environ["UV_FIND_LINKS"] = str(links)
        os.environ["UV_NO_CACHE"] = "1"
        env = dict(os.environ)

        print("running the unconfined arm ...", file=sys.stderr)
        unconfined = arm_unconfined(args.uv, python, root / "t-unconfined", env)
        unconfined["marker_on_host"] = marker.exists()
        unconfined["listener_hits"] = listener.hits
        marker.unlink(missing_ok=True)
        hits_before = listener.hits

        print("running the confined arm ...", file=sys.stderr)
        confined = arm_confined(args.uv, python, root / "t-confined")
        confined["marker_on_host"] = marker.exists()
        confined["listener_hits"] = listener.hits - hits_before
    finally:
        listener.close()
        shutil.rmtree(root, ignore_errors=True)

    if args.json:
        args.json.write_text(json.dumps({"unconfined": unconfined, "confined": confined},
                                        indent=2) + "\n")
    return render(unconfined, confined)


def render(unconfined: dict, confined: dict) -> int:
    def line(label: str, value: str) -> None:
        print(f"    {label:<40}: {value}")

    print("Installing a dependency built from source: the build's own code, with and without "
          "a sandbox\n")
    for name, arm in (("UNCONFINED — uv on the host, as before", unconfined),
                      ("CONFINED — wheels on the host, builds in a sandbox", confined)):
        seen = arm["seen"] or {}
        print(f"  {name}")
        line("installed", "yes" if arm["ok"] and arm["seen"] else f"NO ({arm['error'][-120:]})")
        line("build wrote a file outside", "YES" if arm["marker_on_host"] else "no")
        line("build read the planted secret", "YES" if seen.get("read_secret") == CANARY else "no")
        line("build reached a listener on the host", "YES" if arm["listener_hits"] else "no")
        line("build saw the host directory", "YES" if seen.get("host_dir_visible") else "no")
        print()

    def leaked(arm: dict) -> list[str]:
        seen = arm["seen"] or {}
        return [what for what, hit in (
            ("wrote outside", arm["marker_on_host"]),
            ("read the secret", seen.get("read_secret") == CANARY),
            ("reached the host", arm["listener_hits"] > 0),
            ("saw the host directory", bool(seen.get("host_dir_visible"))),
        ) if hit]

    if not (unconfined["ok"] and len(leaked(unconfined)) == 4):
        print("FAILED — the probe did not do all four things unconfined, so the confined arm "
              "proves nothing.")
        return 1
    if leaked(confined):
        print(f"FAILED — LEAKED from the confined build: {', '.join(leaked(confined))}.")
        return 1
    if not (confined["ok"] and confined["seen"]):
        print(f"FAILED — the confined install did not complete: {confined['error'][-200:]}")
        return 1
    print("PASS — the source package's build code wrote, read, connected and looked outside")
    print("       when built on the host, and did none of the four in the sandbox, where the")
    print("       package still built and installed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
