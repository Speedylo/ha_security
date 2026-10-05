"""CS09 / F10 probe: what a sandbox sees of the user's home when the configuration lives there.

A real installation keeps its configuration under the user's home (`~/.homeassistant`), unlike
every suite run before 2026-10-05, which built its configuration in /tmp. This builds the same
dangerous configuration `confine.selftest` builds, but under `~/r2exp/disktmp`, and reports every
path the sandbox can see under /home, with what each is: so the question "is it names, or more?"
is answered by listing, not by inference.

Run on the Pi from the frozen tree's framework/:
    systemd-run --user --scope -q python3 ../verify/probes/home_visibility.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from confine.cgroup import Delegation, ResourceLimits, SandboxCgroup  # noqa: E402
from confine.preflight import require_ready  # noqa: E402
from confine.sandbox import SandboxSpec  # noqa: E402
from confine.selftest import build_config, run_inside  # noqa: E402
from confine.spawn import become_subreaper  # noqa: E402

INSIDE = r"""
import json, os
seen = []
for top, dirs, files in os.walk("/home"):
    for name in sorted(dirs):
        p = os.path.join(top, name)
        seen.append({"path": p, "kind": "dir", "entries": len(os.listdir(p)) if os.access(p, os.R_OK) else None})
    for name in sorted(files):
        p = os.path.join(top, name)
        seen.append({"path": p, "kind": "file", "readable": os.access(p, os.R_OK)})
mountinfo = [l.split()[3:5] for l in open("/proc/self/mountinfo")]
print(json.dumps({"home": seen, "mountinfo_root_and_point": mountinfo}))
"""


def main() -> int:
    require_ready(deep=False)
    become_subreaper()
    base = Path.home() / "r2exp" / "disktmp"
    root = Path(tempfile.mkdtemp(prefix="home-probe-", dir=base))
    try:
        layout = build_config(root)
        spec = SandboxSpec(domain="demo_a", own_dir=str(layout["own"]), data_dir=str(layout["data"]),
                           argv=[sys.executable, "-c", INSIDE], files_ro=[str(layout["shared"])])
        with SandboxCgroup.create(Delegation.discover(), "home-probe", ResourceLimits()) as cgroup:
            report = run_inside(spec, cgroup)
        report["configuration_root_on_host"] = str(root)
        print(json.dumps(report, indent=2))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
