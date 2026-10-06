"""How a result was produced, written beside it (verification finding F14).

A result file records what was measured and not the command that measured it. The campaign had to
reconstruct invocations from memory and notes, and once reconstructed one wrongly: the compatibility
baseline without `--platform-deps`. So every measurement harness, after writing its JSON, calls
`record_run(path)`, which writes `<path>.run.json` beside it. That file holds the command line, the
working directory, the interpreter, the host, the time, the git commit of the checkout and whether
its tree had uncommitted changes, and the moment installs resolve against. The result file itself
keeps its structure, because `verify/compare.py` and `verify/recompute.py` read it.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

#: Every requirements install resolves only packages uploaded before this moment
#: (`uv pip install --exclude-newer`), so a re-run tests the versions the original run did. Until
#: 2026-10-06 installs took whatever was newest, and between two runs `aiohttp` moved from 3.14.3
#: to 3.14.4 under an unchanged declaration (verification finding F13). The moment is the
#: campaign's freeze day. `CONFINE_RESOLVE_BEFORE` moves it on purpose, and both the install result
#: and the run record carry the value used.
RESOLVE_BEFORE = os.environ.get("CONFINE_RESOLVE_BEFORE", "2026-10-06T00:00:00Z")


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(Path(__file__).resolve().parent), *args],
                              check=True, capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None


def run_record() -> dict:
    commit = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain", "--untracked-files=no") if commit else None
    return {
        "argv": sys.argv,
        "cwd": os.getcwd(),
        "executable": sys.executable,
        "python": platform.python_version(),
        "host": platform.node(),
        "machine": platform.machine(),
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "commit": commit or "not a git checkout",
        "uncommitted_changes": bool(status) if commit else None,
        "resolve_before": RESOLVE_BEFORE,
    }


def record_run(result: Path | str) -> Path:
    """Write `<result>.run.json`, the run record for a result just written. Returns its path."""
    path = Path(str(result) + ".run.json")
    path.write_text(json.dumps(run_record(), indent=2) + "\n")
    return path
