"""Keep one confined integration running against the house's Home Assistant, (A).

Every other entry point in this package is an experiment: it starts a sandbox, measures, and
exits. The refusal flood's way back needs something that stays: when the mediator cuts an
integration off, the sandbox must be killed, and when a member of the household confirms the
Repairs issue, it must be started again (`notes/flood_cutoff_prediction.md` §3). This is that
supervisor, for **one** integration, kept as small as the job allows:

  - **The mediator decides; this only acts on what it decided.** A cut-off arrives through
    `Mediator.on_cut_off` and is answered by killing the sandbox through its cgroup. A restart
    arrives through `on_reinstate`, after the mediator has written its record, and is answered by
    starting a new sandbox, which registers under the same manifest, re-read at registration.
  - **A sandbox that exits on its own is not restarted.** Only a reinstatement restarts one, so
    a crashing integration cannot turn this into a respawn loop.
  - **The durable log is kept**, in `--audit-dir`, so the cut-off and the reinstatement can be
    read back after the run, unlike the experiments' logs, which are summarised and removed.

Run (on the Pi, with (A) up), from `~/r2exp/v2/framework`:

    systemd-run --user --scope -q python3 -u -m confine.supervise \\
        --component ../experiments/flood/demo_flood --python ~/r2exp/ha314/bin/python
"""

from __future__ import annotations

import argparse
import json
import os
import selectors
import shutil
import signal
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

from .audit import AuditLog
from .cgroup import Delegation, SandboxCgroup
from .channel import Channel
from .compat import DEPS, PLATFORM_DEPS
from .manifest import Manifest
from .mediator import CutOff, Mediator
from .platform import acting_policy
from .preflight import require_ready
from .real_platform import RealPlatform
from .sandbox import SandboxSpec
from .selftest_bridge import interpreter_trees
from .spawn import Sandbox, become_subreaper, start

HERE = Path(__file__).resolve().parent


class Supervisor:
    def __init__(self, component: Path, permissions: dict, python: Path, audit_dir: Path,
                 hours: float) -> None:
        self.domain = component.name
        self.python = python
        self.hours = hours
        self.delegation = Delegation.discover()
        self.root = Path(tempfile.mkdtemp(prefix=f"supervise-{self.domain}-"))
        self.own = self.root / "custom_components" / self.domain
        shutil.copytree(component, self.own, ignore=shutil.ignore_patterns("__pycache__"))
        # Beside the integration, never inside its manifest.json (§5.9.4).
        (self.own.parent / f"{self.domain}.permissions.json").write_text(json.dumps(permissions))
        self.deps = self.root / "deps"
        self.deps.mkdir()

        self.platform = RealPlatform()
        audit_dir.mkdir(parents=True, exist_ok=True)
        self.audit_dir = audit_dir
        self.mediator = Mediator(log=AuditLog(path=audit_dir / "decisions.jsonl"))
        self.manifest = Manifest.load(self.own, self.root)
        self.mediator.policy = acting_policy({self.domain: self.manifest}, self.platform)
        self.mediator.attach_platform(self.platform)
        self.mediator.on_cut_off.append(self.cut_off)
        self.mediator.on_reinstate.append(self.reinstated)

        self.sandbox: Sandbox | None = None
        self.cgroup: SandboxCgroup | None = None
        self.wanted = True
        self.starts = 0

    # ---------------------------------------------------------------- what the mediator says

    def cut_off(self, identity: str) -> None:
        say(f"{identity} cut off by the mediator; killing its sandbox")
        self.stop()

    def reinstated(self, identity: str) -> None:
        say(f"{identity} reinstated (recorded); starting it again")
        self.wanted = True

    # ---------------------------------------------------------------- sandboxes

    def launch(self) -> None:
        self.wanted = False
        # A fresh data directory for every start, as every experiment harness gives one. Found on
        # the Pi (2026-10-05): with the first start's directory reused, the private instance finds
        # the integration's config entry already stored, the config flow aborts as
        # `already_configured`, and flow mode never sets the stored entry up — so the restarted
        # integration ran and published nothing. Keeping `/sandbox/data` across starts, which an
        # OAuth integration needs to stay logged in (§7.42), is therefore not supported yet.
        data = self.root / ".confine" / f"{self.domain}-start{self.starts + 1}"
        data.mkdir(parents=True)
        spec_file = self.root / "spec.json"
        spec_file.write_text(json.dumps({
            "domain": self.domain, "mode": "flow", "auth": True,
            "entities": [], "services": [], "setup_components": [],
            "egress": True, "record_egress": True, "push": True,
            "settle_seconds": self.hours * 3600, "flow_input": {}, "menu_choice": {}}))
        mediator_end, sandbox_end = Channel.pair()
        try:
            self.mediator.register(self.domain, Channel(mediator_end), component=self.own)
        except CutOff as err:
            say(f"not started: {err}")
            mediator_end.close()
            sandbox_end.close()
            return
        spec = SandboxSpec(
            domain=self.domain, own_dir=str(self.own), data_dir=str(data),
            argv=[str(self.python), "/sandbox/runtime.py"],
            runtime_files={str(HERE / "sandbox_runtime.py"): "/sandbox/runtime.py",
                           # `"egress": True` imports it inside the sandbox (`endtoend_egress`).
                           str(HERE / "egress_shim.py"): "/sandbox/egress_shim.py",
                           str(spec_file): "/sandbox/spec.json", str(self.deps): DEPS},
            env={"PYTHONPATH": DEPS})
        platform_deps = Path.home() / "r2exp/platform-deps"
        if platform_deps.is_dir():
            spec.runtime_files[str(platform_deps)] = PLATFORM_DEPS
            spec.env["PYTHONPATH"] = f"{DEPS}:{PLATFORM_DEPS}"
        for tree in (*interpreter_trees(self.python), sys.base_prefix):
            if tree and tree not in spec.runtime_paths:
                spec.runtime_paths.append(tree)
        limits = replace(self.manifest.resources,
                         memory_mb=max(self.manifest.resources.memory_mb, 640))
        spec.tmp_size_mb = limits.disk_mb
        self.starts += 1
        self.cgroup = SandboxCgroup.create(self.delegation, f"sup-{self.domain}-{self.starts}",
                                           limits)
        # The sandbox's report (stdout, JSON) and its Home Assistant log (stderr), one pair per
        # start, beside the audit log. A setup failure is reported on stdout, as `"fatal"`.
        base = self.audit_dir / f"{self.domain}-run{self.starts}"
        with open(f"{base}.json", "wb") as stdout, open(f"{base}.log", "wb") as stderr:
            self.sandbox = start(spec, self.cgroup, stdout=stdout.fileno(),
                                 stderr=stderr.fileno(), channel_end=sandbox_end.fileno())
        sandbox_end.detach()
        say(f"{self.domain} started (run {self.starts}, pid {self.sandbox.pid})")

    def stop(self) -> None:
        if self.sandbox is None:
            return
        assert self.cgroup is not None
        self.cgroup.remove()                      # kills everything in it
        try:
            os.waitpid(self.sandbox.pid, 0)
        except ChildProcessError:
            pass
        self.cgroup.remove()                      # now empty, so the directory goes too
        self.sandbox, self.cgroup = None, None

    def reap(self) -> None:
        """A sandbox that exited by itself is reported, and not restarted."""
        if self.sandbox is None:
            return
        pid, status = os.waitpid(self.sandbox.pid, os.WNOHANG)
        if pid:
            say(f"{self.domain} exited by itself (status {status}); not restarting it")
            assert self.cgroup is not None
            self.cgroup.remove()
            self.sandbox, self.cgroup = None, None

    # ---------------------------------------------------------------- the loop

    def run(self) -> None:
        idle = selectors.DefaultSelector()
        idle.register(self.platform, selectors.EVENT_READ)
        try:
            while True:
                if self.wanted and self.sandbox is None:
                    self.launch()
                if self.mediator.open_channels:
                    self.mediator.serve(timeout=0.5, until=time.monotonic() + 0.5)
                else:
                    # Nothing to serve, but the house can still ask for a restart.
                    if idle.select(0.5):
                        self.platform.pump()
                    self.platform.dispatch()
                self.reap()
        finally:
            self.stop()
            self.platform.close()
            shutil.rmtree(self.root, ignore_errors=True)


def say(text: str) -> None:
    print(f"{time.strftime('%H:%M:%S')}  {text}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--component", type=Path, required=True,
                    help="the integration's directory; its name is the domain")
    ap.add_argument("--permissions", default='{"schema_version": 1}',
                    help="the authority manifest, as JSON (default: nothing declared)")
    ap.add_argument("--python", type=Path, required=True)
    ap.add_argument("--audit-dir", type=Path,
                    default=Path.home() / "r2exp" / "supervise-audit")
    ap.add_argument("--hours", type=float, default=8.0, help="how long one sandbox may run")
    args = ap.parse_args()

    require_ready(deep=False)
    become_subreaper()

    # Stop cleanly on SIGTERM, which is what systemd and `kill` send. Started in the background
    # from a non-interactive shell, this process inherits SIGINT as ignored, so Ctrl-C's signal
    # alone cannot stop it — found when three supervisors outlived `pkill -INT` (2026-10-05).
    def terminate(_signum, _frame) -> None:
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    supervisor = Supervisor(args.component.resolve(), json.loads(args.permissions),
                            args.python, args.audit_dir, args.hours)
    say(f"supervising {supervisor.domain}; durable log in {args.audit_dir}; Ctrl-C to stop")
    try:
        supervisor.run()
    except KeyboardInterrupt:
        say("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
