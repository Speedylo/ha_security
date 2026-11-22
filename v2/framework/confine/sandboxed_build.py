"""Build a source-only dependency inside a sandbox, so its build code never runs on the host.

`compat.install_requirements` installs wheels only on the host: installing a wheel unpacks files
and runs none of the package's code. When a requirement has no wheel, uv says which package it
is, and this module builds that one package into a wheel *inside a sandbox* (the same sandbox an
integration runs in: every namespace, the file view, seccomp, a cgroup), then hands the wheel back
for the wheels-only install to use.

Three steps, and only the middle one touches the package's code:

    1. host     fetch the source file (PyPI, or a local find-links directory) and check its hash.
                Downloading bytes runs nothing.
    2. sandbox  read its build requirements; the host installs them from wheels into a build
                environment; the sandbox then builds the wheel, with that environment read-only,
                no network, and only its own private /tmp and output folder writable.
    3. host     check the wheel's file name and move it into the wheelhouse. Unpacking it later
                runs nothing.

What the build can see is what an integration's sandbox sees (the interpreter and system
libraries, read-only) plus the source and the build tools. The host's home, other integrations,
the configuration and the network are absent.

**Choosing the same versions as an unrestricted install.** uv's wheels-only resolution treats a
version that has no wheel as unavailable, so where another version does have one, uv quietly
chooses it (an older release, or a pre-release) instead of failing. An unrestricted install would
have built the newer source file. So after each wheels-only resolution, `newer_source_only` asks
PyPI, for every package chosen, whether a newer stable release exists that has no usable wheel;
each one found is built in the sandbox too, and the resolution is repeated until nothing changes.
Constraints still decide: a built wheel that the requirements exclude is simply not chosen.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from .cgroup import Delegation, ResourceLimits, SandboxCgroup
from .sandbox import SandboxSpec
from .selftest_bridge import interpreter_trees
from .spawn import SandboxFailed, become_subreaper, start

HERE = Path(__file__).resolve().parent
RUNNER = "build_runner.py"

# uv's words when a wheels-only resolution needs a package built. Whitespace is collapsed first,
# because uv wraps its explanation across lines.
NEEDS_SOURCE = re.compile(
    r"Because (?:all versions of )?([A-Za-z0-9][A-Za-z0-9._-]*?)(?:==([^\s,]+))?"
    r"(?:[<>=!~][^\s]*)? (?:has|have) no (?:usable )?wheels")
HINT = re.compile(r"Wheels are required for `([A-Za-z0-9][A-Za-z0-9._-]*)`")
WHEEL_NAME = re.compile(r"^([A-Za-z0-9_.]+)-[^-]+(-[^-]+)?-[^-]+-[^-]+-[^-]+\.whl$")
RELEASE = re.compile(r"^\d+(\.\d+)*(\.post\d+)?$")

# More than this many source packages for one integration is treated as a failure, not a loop.
MAX_BUILDS = 8

BUILD_LIMITS = ResourceLimits(memory_mb=1024, max_processes=128, disk_mb=512)


class BuildFailed(RuntimeError):
    """A source package could not be built in the sandbox, and says why."""


def normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def needs_source(uv_error: str) -> tuple[str, str | None] | None:
    """The package uv could not install without building, and its version if uv named one.

    uv's hint line names the package whatever route led to it ("Wheels are required for `X`");
    the explanation above it names the version only sometimes, and in wording that depends on
    whether the package was asked for directly or reached through another one's dependencies.
    """
    text = " ".join(uv_error.split())
    hint = HINT.search(text)
    if hint is None:
        match = NEEDS_SOURCE.search(text)
        return (match.group(1), match.group(2)) if match else None
    name = hint.group(1)
    pinned = re.search(re.escape(name) + r"==([^\s,]+) (?:has|have) no (?:usable )?wheels", text,
                       re.IGNORECASE)
    return name, pinned.group(1) if pinned else None


def _version_key(version: str):
    try:
        from packaging.version import Version
        return Version(version)
    except ImportError:  # release-only versions, compared as numbers
        return tuple(int(x) for x in re.findall(r"\d+", version))


def _is_prerelease(version: str) -> bool:
    return not RELEASE.match(version)


_RELEASES: dict[str, dict] = {}


def _pypi_releases(name: str) -> dict:
    key = normalise(name)
    if key not in _RELEASES:
        try:
            with urllib.request.urlopen(f"https://pypi.org/pypi/{key}/json", timeout=60) as reply:
                _RELEASES[key] = json.load(reply)["releases"]
        except OSError:
            _RELEASES[key] = {}
    return _RELEASES[key]


def latest_stable(name: str, before: str) -> str | None:
    """The newest stable release with a file uploaded before `before`, by PyPI's record."""
    stable = [v for v, files in _pypi_releases(name).items()
              if RELEASE.match(v) and any(not f.get("yanked")
                                          and f.get("upload_time_iso_8601", "9999") <= before
                                          for f in files)]
    return max(stable, key=_version_key) if stable else None


def resolve(uv: str, python: Path, requirements: list[str], links: list[Path], before: str,
            timeout: int) -> tuple[dict[str, str] | None, str]:
    """A wheels-only dry run: the versions uv would install, or None and uv's error."""
    with tempfile.TemporaryDirectory(prefix="confine-resolve-") as scratch:
        proc = subprocess.run(
            [uv, "pip", "install", "--dry-run", "--python", str(python), "--target", scratch,
             "--exclude-newer", before, "--only-binary", ":all:",
             *[arg for link in links for arg in ("--find-links", str(link))], *requirements],
            capture_output=True, text=True, timeout=timeout)
    text = (proc.stderr or "") + (proc.stdout or "")
    if proc.returncode != 0:
        return None, text.strip()
    chosen = dict(re.findall(r"^ \+ ([A-Za-z0-9._-]+)==(\S+)$", text, re.MULTILINE))
    return {normalise(k): v for k, v in chosen.items()}, text


def newer_source_only(chosen: dict[str, str], uv: str, python: Path, links: list[Path],
                      before: str, timeout: int) -> list[tuple[str, str]]:
    """Packages for which an unrestricted install would have built a newer stable release."""
    pending = []
    for name, version in sorted(chosen.items()):
        latest = latest_stable(name, before)
        if latest is None or latest == version:
            continue
        if not _is_prerelease(version) and _version_key(latest) <= _version_key(version):
            continue
        # Could that release be installed wheels-only, with its own dependencies? uv answers. If
        # it can, the requirements, not a missing wheel, kept uv from choosing it, and nothing
        # needs building. If it cannot, uv names the package that needs building: the release
        # itself, or one of its dependencies (python-miio 0.5.12 has a wheel; netifaces, which
        # it needs, does not).
        alone, message = resolve(uv, python, [f"{name}=={latest}"], links, before, timeout)
        if alone is None:
            source = needs_source(message)
            if source is not None and source not in pending:
                pending.append(source)
    return pending


def find_links() -> list[Path]:
    value = os.environ.get("UV_FIND_LINKS", "")
    return [Path(p) for p in re.split(r"[\s,]+", value) if p]


def fetch_sdist(name: str, version: str | None, before: str, into: Path) -> Path:
    """Step 1: the source file, from a local find-links directory or from PyPI."""
    wanted = normalise(name)
    for folder in find_links():
        for candidate in sorted(folder.glob("*.tar.gz")) + sorted(folder.glob("*.zip")):
            stem = re.sub(r"\.(tar\.gz|zip)$", "", candidate.name)
            dist, _, dist_version = stem.rpartition("-")
            if normalise(dist) == wanted and (version is None or dist_version == version):
                return Path(shutil.copy2(candidate, into / candidate.name))

    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=60) as reply:
        releases = json.load(reply)["releases"]
    choices = []
    for release, files in releases.items():
        if version is not None and release != version:
            continue
        if version is None and not RELEASE.match(release):
            continue
        for f in files:
            if (f.get("packagetype") == "sdist" and not f.get("yanked")
                    and f.get("upload_time_iso_8601", "9999") <= before):
                choices.append((f["upload_time_iso_8601"], f))
    if not choices:
        raise BuildFailed(f"{name}{'==' + version if version else ''}: no source file on PyPI "
                          f"uploaded before {before}")
    chosen = max(choices, key=lambda c: c[0])[1]
    target = into / Path(chosen["filename"]).name
    with urllib.request.urlopen(chosen["url"], timeout=120) as reply:
        target.write_bytes(reply.read())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if digest != chosen["digests"]["sha256"]:
        raise BuildFailed(f"{chosen['filename']}: hash does not match PyPI's")
    return target


def _run_sandboxed(argv: list[str], own: Path, data: Path, python: Path, files_ro: list[str],
                   label: str, timeout: int) -> tuple[int, str, str]:
    spec = SandboxSpec(domain=f"build-{label}", own_dir=str(own), data_dir=str(data),
                       argv=argv, files_ro=files_ro, tmp_size_mb=BUILD_LIMITS.disk_mb)
    # `/etc/alternatives` holds the links that name the system's compiler (`cc` -> gcc on
    # Debian). A package with a C extension cannot build without it; it is read-only, like every
    # runtime path, and only build sandboxes get it.
    for extra in (*interpreter_trees(python), sys.base_prefix, "/etc/alternatives"):
        if extra and extra not in spec.runtime_paths:
            spec.runtime_paths.append(extra)
    out = tempfile.TemporaryFile()
    err = tempfile.TemporaryFile()
    name = f"confine-build-{os.getpid()}-{normalise(label)}"
    with SandboxCgroup.create(Delegation.discover(), name, BUILD_LIMITS) as cgroup:
        sandbox = start(spec, cgroup, stdout=out.fileno(), stderr=err.fileno())
        try:
            status = sandbox.wait(timeout=timeout)
        except TimeoutError:
            sandbox.kill()
            raise BuildFailed(f"{label}: build still running after {timeout}s") from None
    out.seek(0)
    err.seek(0)
    return (os.waitstatus_to_exitcode(status), out.read().decode(errors="replace"),
            err.read().decode(errors="replace"))


def _last_json(text: str) -> dict:
    for line in reversed(text.strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return {}


def _install_wheels(uv: str, python: Path, target: Path, requirements: list[str], before: str,
                    timeout: int) -> None:
    proc = subprocess.run(
        [uv, "pip", "install", "--quiet", "--python", str(python), "--target", str(target),
         "--exclude-newer", before, "--only-binary", ":all:", *requirements],
        capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()
        raise BuildFailed("build requirements need building themselves, which is not done: "
                          + (tail[-1][:200] if tail else "install failed"))


def build(name: str, version: str | None, python: Path, uv: str, wheelhouse: Path,
          before: str, timeout: int = 600) -> str:
    """Build one source package in a sandbox and put its wheel into `wheelhouse`."""
    become_subreaper()
    root = Path(tempfile.mkdtemp(prefix="confine-build-"))
    try:
        own, data, buildenv = root / "in", root / "data", root / "buildenv"
        for folder in (own, data, buildenv):
            folder.mkdir()
        sdist = fetch_sdist(name, version, before, own)
        shutil.copy2(HERE / RUNNER, own / RUNNER)
        runner = [str(python), f"{SandboxSpec.COMPONENT}/{RUNNER}"]
        inside = f"{SandboxSpec.COMPONENT}/{sdist.name}"

        code, out, err = _run_sandboxed(runner + ["requires", inside], own, data, python, [],
                                        name, timeout)
        requires = _last_json(out).get("requires")
        if code != 0 or requires is None:
            raise BuildFailed(f"{sdist.name}: reading its build requirements failed: "
                              f"{(err.strip().splitlines() or ['no output'])[-1][:200]}")

        for _ in range(3):
            _install_wheels(uv, python, buildenv, requires, before, timeout)
            code, out, err = _run_sandboxed(runner + ["build", inside, str(buildenv)], own, data,
                                            python, [str(buildenv)], name, timeout)
            report = _last_json(out)
            if code == 3 and report.get("need"):
                requires = list(report["need"])
                continue
            break
        wheel = report.get("wheel")
        if code != 0 or not wheel:
            raise BuildFailed(f"{sdist.name}: the build failed in the sandbox: "
                              f"{(err.strip().splitlines() or ['no output'])[-1][:200]}")

        built = data / "out" / Path(wheel).name
        match = WHEEL_NAME.match(built.name)
        if not built.is_file() or not match or normalise(match.group(1)) != normalise(name):
            raise BuildFailed(f"{sdist.name}: the sandbox returned {wheel!r}, not a wheel of "
                              f"{name}")
        shutil.move(str(built), wheelhouse / built.name)
        return built.name
    except SandboxFailed as err:
        raise BuildFailed(f"{name}: the build sandbox did not start: {err}") from err
    finally:
        shutil.rmtree(root, ignore_errors=True)
