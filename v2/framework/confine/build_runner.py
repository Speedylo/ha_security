"""Runs inside a build sandbox, and only there: read or build one source distribution.

    python build_runner.py requires SDIST          prints {"requires": [...]}
    python build_runner.py build SDIST BUILDENV     prints {"wheel": name} or {"need": [...]}

The source distribution is unpacked into the sandbox's private /tmp and built with the standard
build interface (PEP 517): import the build backend the package names, ask it for any further
build requirements, then ask it for a wheel. That is what `pip` and `uv` do, minus the network:
the build tools arrive read-only in BUILDENV, installed on the host from wheels, because the
sandbox has no network at all.

Standard library only. This file is the one piece of the framework that runs next to the
package's own build code, so it imports nothing the build could have replaced.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import os
import re
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

# PEP 517: a package with no [build-system] table is built with setuptools' legacy backend.
DEFAULT_REQUIRES = ["setuptools>=40.8.0"]
DEFAULT_BACKEND = "setuptools.build_meta:__legacy__"
OUT = Path("/sandbox/data/out")
WORK = Path("/tmp/build")


def _name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    return re.sub(r"[-_.]+", "-", match.group(1)).lower() if match else requirement


def unpack(sdist: Path) -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    if sdist.name.endswith(".zip"):
        with zipfile.ZipFile(sdist) as archive:
            archive.extractall(WORK)
    else:
        with tarfile.open(sdist) as archive:
            archive.extractall(WORK, filter="data")
    entries = list(WORK.iterdir())
    return entries[0] if len(entries) == 1 and entries[0].is_dir() else WORK


def build_system(source: Path) -> tuple[list[str], str, list[str]]:
    pyproject = source / "pyproject.toml"
    table = tomllib.loads(pyproject.read_text()).get("build-system", {}) \
        if pyproject.exists() else {}
    if not table:
        return DEFAULT_REQUIRES + ["wheel"], DEFAULT_BACKEND, []
    return (list(table.get("requires", DEFAULT_REQUIRES)),
            table.get("build-backend", DEFAULT_BACKEND), list(table.get("backend-path", [])))


def load_backend(spec: str):
    module, _, attribute = spec.partition(":")
    backend = importlib.import_module(module)
    for part in filter(None, attribute.split(".")):
        backend = getattr(backend, part)
    return backend


def main() -> int:
    mode, sdist = sys.argv[1], Path(sys.argv[2])
    source = unpack(sdist)
    requires, backend_spec, backend_path = build_system(source)
    if mode == "requires":
        print(json.dumps({"requires": requires}))
        return 0

    buildenv = sys.argv[3]
    paths = [buildenv] + [str(source / p) for p in backend_path]
    sys.path[:0] = paths
    # Some backends run `setup.py` in a second interpreter (poetry-core does), which inherits the
    # environment but not this process's `sys.path`, so the build tools must be on PYTHONPATH too.
    os.environ["PYTHONPATH"] = os.pathsep.join(paths)
    os.chdir(source)
    backend = load_backend(backend_spec)
    extra = getattr(backend, "get_requires_for_build_wheel", lambda _settings=None: [])({})
    have = {_name(d.metadata["Name"]) for d in importlib.metadata.distributions(path=[buildenv])}
    need = [r for r in extra if _name(r) not in have]
    if need:
        print(json.dumps({"need": need}))
        return 3
    OUT.mkdir(parents=True, exist_ok=True)
    print(json.dumps({"wheel": backend.build_wheel(str(OUT))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
