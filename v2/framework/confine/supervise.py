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
from pathlib import Path

from .audit import DEFAULT_LOG, AuditLog, Identity, grant_digest
from .cgroup import Delegation, SandboxCgroup
from .channel import Channel
from .compat import DEPS, PLATFORM_DEPS
from .describe import approve_shown, changes_since_approval, describe_markdown
from .manifest import Manifest, ManifestRejected, NotApproved
from .mediator import CutOff, Mediator
from .platform import acting_policy
from .preflight import require_ready
from .real_platform import PlatformLost, RealPlatform
from .sandbox import SandboxSpec
from .selftest_bridge import interpreter_trees
from .spawn import Sandbox, become_subreaper, start

HERE = Path(__file__).resolve().parent
#: Where an integration's `.storage` is kept between starts, under its configuration root (F59).
KEPT_ROOT = Path("confine/kept")
MB = 1024 * 1024
#: Who an approval from the Repairs screen is recorded as given by. Home Assistant does not tell
#: a Repairs flow which administrator opened it (F57c §1, rule 4).
ALLOWED_BY = "an administrator, from the Repairs panel"


class Supervisor:
    def __init__(self, component: Path, permissions: dict, python: Path, audit_dir: Path,
                 hours: float, approvals: Path | None = None, keep: Path | None = None) -> None:
        self.domain = component.name
        # F57: the integration runs from a copy in a temporary directory, whose own configuration
        # root holds no approvals, so the approvals are read from the original's root, where
        # `describe --approve` writes them, unless another file is named.
        self.approvals = approvals or component.parent.parent / DEFAULT_LOG
        # F59: what the integration stores in `.storage` is kept here between starts, beside the
        # approvals by default, so it outlives this supervisor and a restart of the machine.
        self.keep = keep or component.parent.parent / KEPT_ROOT / self.domain
        self.keep.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.data: Path | None = None
        self.python = python
        self.hours = hours
        self.delegation = Delegation.discover()
        self.cleared = self._clear_predecessors()
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
        # One file per supervisor start (verification 4.5, finding F31). A restarted mediator
        # begins a new chain from genesis, with a new key, and appended to the previous run's
        # file it made `verify` report breaks that look exactly like deleted records.
        self.stem = f"{time.strftime('%Y%m%dT%H%M%S')}-{os.getpid()}"
        self.log_path = audit_dir / f"decisions-{self.stem}.jsonl"
        self.mediator = Mediator(log=AuditLog(path=self.log_path))
        self.manifest = Manifest.load(self.own, self.root)
        self.mediator.policy = acting_policy({self.domain: self.manifest}, self.platform,
                                             approvals=self.approvals)
        self.mediator.attach_platform(self.platform)
        self.mediator.on_cut_off.append(self.cut_off)
        self.mediator.on_reinstate.append(self.reinstated)
        self._listen(self.platform)

        self.sandbox: Sandbox | None = None
        self.cgroup: SandboxCgroup | None = None
        self.wanted = True
        self.starts = 0

    def _clear_predecessors(self) -> int:
        """Kill every sandbox an earlier supervisor of this integration left running.

        A supervisor killed with SIGKILL cannot stop its sandbox, which then runs on with no
        mediator, and this supervisor's first sandbox was placed in the same cgroup beside it
        (verification 4.5, finding F30). The sandbox now ends its own run when its channel
        closes, but that is inside the sandbox, so the guarantee is here: nothing named for this
        integration is left in the delegated subtree when a new one starts.

        Three corrections from the review of that fix (verification 4.7, F35). A cgroup is
        counted as cleared only once it is gone, and one that will not go stops this supervisor
        from starting, since its next sandbox would otherwise run beside what is left (R3). The
        kill is the kernel's `cgroup.kill`, which a fork cannot outrun (R4). And each
        supervisor's cgroups carry its pid, so a supervisor that is still running is left alone
        rather than having its sandbox killed under it (R10).
        """
        if self.delegation.parent is None:
            return 0
        cleared, stuck = 0, []
        for path in sorted(self.delegation.parent.glob(f"sup-{self.domain}-*")):
            owner = _owner(path.name, self.domain)
            if owner is not None and _is_supervisor(owner):
                continue
            if SandboxCgroup(path).gone():
                cleared += 1
            else:
                stuck.append(path.name)
        if stuck:
            raise PredecessorsRemain(
                f"an earlier supervisor's sandbox could not be removed ({', '.join(stuck)}); "
                f"not starting {self.domain} beside it")
        return cleared

    # ---------------------------------------------------------------- what the mediator says

    def cut_off(self, identity: str) -> None:
        say(f"{identity} cut off by the mediator; killing its sandbox")
        self.stop()

    def reinstated(self, identity: str) -> None:
        say(f"{identity} reinstated (recorded); starting it again")
        self.wanted = True

    # ---------------------------------------------------------------- what the house says (F57c)

    def _listen(self, platform: RealPlatform) -> None:
        platform.approve_handlers.append(self.allowed)
        platform.retry_handlers.append(self.retry)

    def allowed(self, request: dict) -> None:
        """An administrator chose Allow and start on the Repairs screen.

        Recorded only if the screen showed what is on disk now (`approve_shown`). Either way the
        integration is then started, which registers it through the gate: approved, it runs and
        its issue goes; not, it stays stopped and the house is shown the current screen.
        """
        if request.get("approve") != self.domain or self.sandbox is not None:
            return
        try:
            approve_shown(self.own, self.approvals, Manifest.load(self.own, self.root),
                          str(request.get("identity", "")), str(request.get("grant", "")),
                          by=ALLOWED_BY)
            say(f"{self.domain} allowed by an administrator, from the Repairs panel")
        except ManifestRejected as err:
            say(f"not allowed: {err}")
        self.wanted = True

    def retry(self, identity: str) -> None:
        """Someone asked to try a not-started integration again. Nothing is granted by asking."""
        if identity == self.domain and self.sandbox is None:
            say(f"{self.domain}: asked to try again")
            self.wanted = True

    def _tell(self, what: str, *args, **kwargs) -> None:
        """Tell (A); if it cannot be told, say so, and change nothing else (F57c rule 7)."""
        try:
            getattr(self.platform, what)(*args, **kwargs)
        except PlatformLost:
            raise
        except Exception as err:  # noqa: BLE001 — the house not hearing it stops nothing
            say(f"could not tell the house's Home Assistant ({what}): {err}")

    def _not_approved(self) -> None:
        """The `not_started` issue, with the screen an administrator decides from."""
        manifest = Manifest.load(self.own, self.root)
        _, code, permissions = changes_since_approval(self.own, manifest, self.approvals)
        self._tell("not_started", self.domain, "not_approved",
                   details=describe_markdown(manifest, code_changed=code,
                                             permissions_changed=permissions),
                   shown_identity=Identity.compute(self.own).composite,
                   grant=grant_digest(manifest.provenance.value, manifest.permissions))

    # ---------------------------------------------------------------- sandboxes

    def launch(self) -> None:
        self.wanted = False
        # F59 rule 4: the kept folder is held to `disk_mb`, as `/tmp` is, and checked before
        # the start, since nothing bounds it while a run writes to it.
        limit = self.manifest.resources.disk_mb
        size = kept_size(self.keep)
        if size > limit * MB:
            say(f"not started: {self.domain} has stored {size / MB:.0f} MB, more than the "
                f"{limit} MB it may keep ({self.keep})")
            self._tell("not_started", self.domain, "too_much_data",
                       detail=f"{size / MB:.0f} MB stored, {limit} MB allowed")
            return
        spec_file = self.root / "spec.json"
        spec_file.write_text(json.dumps({
            "domain": self.domain, "mode": "flow", "auth": True,
            "entities": [], "services": [], "setup_components": [],
            "egress": True, "record_egress": True, "push": True,
            "settle_seconds": self.hours * 3600, "flow_input": {}, "menu_choice": {}}))
        mediator_end, sandbox_end = Channel.pair()
        try:
            self.mediator.register(self.domain, Channel(mediator_end), component=self.own,
                                   installed=self.deps)
        except (CutOff, NotApproved) as err:
            # Not approved (F57) is answered as a cut-off is: the supervisor stays up and says
            # why. Since F57c the house is told too, and an administrator can allow it there; a
            # cut-off has its own issue already.
            say(f"not started: {err}")
            mediator_end.close()
            sandbox_end.close()
            if isinstance(err, NotApproved):
                self._not_approved()
            return
        # A fresh data directory for every start, as every experiment harness gives one. Found on
        # the Pi (2026-10-05): with the first start's directory reused, the private instance finds
        # the integration's config entry already stored, the config flow aborts as
        # `already_configured`, and flow mode never sets the stored entry up — so the restarted
        # integration ran and published nothing. Keeping `/sandbox/data` across starts, which an
        # OAuth integration needs to stay logged in (§7.42), is therefore not supported yet.
        #
        # Made only once the start is registered. Made before, a refused start left this run's
        # directory behind, and the next attempt, after an administrator allowed it, failed on
        # it with `FileExistsError` (F57c's C2, 2026-10-11): `starts` counts only real starts.
        data = self.root / ".confine" / f"{self.domain}-start{self.starts + 1}"
        data.mkdir(parents=True)
        self.data = data
        spec = SandboxSpec(
            domain=self.domain, own_dir=str(self.own), data_dir=str(data),
            kept_dir=str(self.keep),
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
        limits = self.manifest.resources
        spec.tmp_size_mb = limits.disk_mb
        self.starts += 1
        self.cgroup = SandboxCgroup.create(
            self.delegation, f"sup-{self.domain}-{os.getpid()}-{self.starts}", limits)
        # The sandbox's report (stdout, JSON) and its Home Assistant log (stderr), one pair per
        # start, beside the audit log. A setup failure is reported on stdout, as `"fatal"`.
        # Named for this supervisor's start, like the audit log, so that a restarted supervisor
        # does not overwrite what the previous one's sandbox reported (F35 R2).
        base = self.audit_dir / f"{self.domain}-{self.stem}-run{self.starts}"
        with open(f"{base}.json", "wb") as stdout, open(f"{base}.log", "wb") as stderr:
            self.sandbox = start(spec, self.cgroup, stdout=stdout.fileno(),
                                 stderr=stderr.fileno(), channel_end=sandbox_end.fileno())
        sandbox_end.detach()
        say(f"{self.domain} started (run {self.starts}, pid {self.sandbox.pid})")
        say(f"{self.domain} run {self.starts} folder {data}")
        self._tell("started", self.domain)

    def stop(self) -> None:
        if self.sandbox is None:
            return
        assert self.cgroup is not None
        # Its channel goes now, not when the selector next notices it closed: a user's command
        # in between went down the dead channel and failed (F35 R5).
        self.mediator.drop(self.domain)
        self.cgroup.remove()                      # kills everything in it
        try:
            os.waitpid(self.sandbox.pid, 0)
        except ChildProcessError:
            pass
        self.cgroup.remove()                      # now empty, so the directory goes too
        self.sandbox, self.cgroup = None, None
        self._remove_start_dir()

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
            self._remove_start_dir()

    def _remove_start_dir(self) -> None:
        """F59 rule 5: the start's throwaway folder goes once nothing of its sandbox runs.

        Called only after the cgroup is killed and the sandbox waited for. On the Pi `/tmp` is
        memory, and until F59 every start's folder stayed there until the supervisor exited.
        """
        if self.data is None:
            return
        left = remove_folder(self.data)
        if left:
            say(f"could not remove all of {self.data}: {left}")
        self.data = None

    # ---------------------------------------------------------------- the loop

    def platform_lost(self, err: Exception) -> None:
        """(A) went away: stop the integration, wait for (A), then start it again.

        Until 2026-10-06 the `PlatformLost` left `run` as a traceback, the supervisor exited, and
        nothing started the integration again when (A) came back (verification 4.5, finding F29).
        Stopping it is still the first thing done, because with (A) gone nothing the integration
        asks for could be acted on or shown. Nobody in the house is asked to do anything: while
        (A) is down nothing can be shown in it, and once it is back the integration is running
        again, as it was.
        """
        was_running = self.sandbox is not None or self.wanted
        say(f"the house's Home Assistant went away ({err}); {self.domain} is stopped until it "
            f"is back")
        self.stop()
        self.mediator.detach_platform()
        try:
            self.platform.close()
        except Exception:  # noqa: BLE001 — it is already gone
            pass
        # Retried every 5 s, whatever the reason, because each can clear: (A) finishes starting,
        # a token is replaced. But each new reason is said once, in a plain line, so a refused
        # token is not a supervisor waiting forever in silence (F35 R8).
        last = ""
        while True:
            time.sleep(5)
            try:
                platform = RealPlatform()
            except Exception as failure:  # noqa: BLE001 — not up yet, in any of the ways (A) can be down
                reason = _plain(failure)
                if reason != last:
                    say(f"still waiting for the house's Home Assistant: {reason}")
                    last = reason
                continue
            break
        self.platform = platform
        self.mediator.policy = acting_policy({self.domain: self.manifest}, platform,
                                             approvals=self.approvals)
        self.mediator.attach_platform(platform)
        self._listen(platform)
        self.wanted = was_running
        say(f"the house's Home Assistant is back; "
            f"{'starting ' + self.domain + ' again' if was_running else self.domain + ' was not running'}")

    def run(self) -> None:
        try:
            while True:
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
                except PlatformLost as err:
                    idle.close()
                    self.platform_lost(err)
        finally:
            self.stop()
            self.platform.close()
            remove_folder(self.root)


def kept_size(folder: Path) -> int:
    """The apparent size of every file under `folder`, following no link (F59 rule 4).

    Apparent rather than allocated, so that a sparse file counts at the size it claims: it can
    be filled later. A directory the integration made unreadable is opened up to be counted, or
    whatever it holds would not be.
    """
    total, stack = 0, [folder]
    while stack:
        directory = stack.pop()
        try:
            entries = list(os.scandir(directory))
        except FileNotFoundError:
            continue
        except PermissionError:
            try:
                os.chmod(directory, 0o700)
                entries = list(os.scandir(directory))
            except OSError:
                return sys.maxsize          # what cannot be counted is not under the limit
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                stack.append(Path(entry.path))
            else:
                total += entry.stat(follow_symlinks=False).st_size
    return total


def remove_folder(folder: Path) -> str:
    """Delete a folder a sandbox wrote in; what could not be deleted, or "" (F59 rule 5).

    `shutil.rmtree` removes a link without following it on Linux
    (`rmtree.avoids_symlink_attacks`), so a link planted towards the host's files removes only
    the link. A directory the integration made unreadable stops it, so after a first attempt
    every directory left is given back its owner's permissions, without following links, and
    the deletion is tried once more.
    """
    if not folder.exists():
        return ""
    shutil.rmtree(folder, ignore_errors=True)
    if not folder.exists():
        return ""
    stack = [folder]
    while stack:
        directory = stack.pop()
        try:
            os.chmod(directory, 0o700)
            stack += [Path(e.path) for e in os.scandir(directory) if e.is_dir(follow_symlinks=False)]
        except OSError:
            continue
    shutil.rmtree(folder, ignore_errors=True)
    if not folder.exists():
        return ""
    left = sorted(str(p) for p in folder.rglob("*"))
    return ", ".join(left[:3]) or str(folder)


class PredecessorsRemain(RuntimeError):
    """An earlier supervisor's cgroup would not go, so this one does not start beside it."""


def _owner(name: str, domain: str) -> int | None:
    """The supervisor pid in `sup-<domain>-<pid>-<n>`; None for the older `sup-<domain>-<n>`."""
    parts = name.removeprefix(f"sup-{domain}-").split("-")
    return int(parts[0]) if len(parts) == 2 and all(p.isdigit() for p in parts) else None


def _is_supervisor(pid: int) -> bool:
    """Whether `pid` is a running supervisor other than this one (its cgroups are its own)."""
    if pid == os.getpid():
        return False
    try:
        return b"confine.supervise" in Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return False


def _plain(failure: Exception) -> str:
    """Why (A) could not be reached, in one line, without a traceback."""
    if isinstance(failure, FileNotFoundError):
        return f"the mediator's token file is missing ({failure.filename or failure})"
    if isinstance(failure, ConnectionRefusedError):
        return "nothing is answering on its port"
    return str(failure) or type(failure).__name__


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
    ap.add_argument("--approvals", type=Path,
                    help=f"where `describe --approve` recorded approvals (default: "
                         f"<the component's config root>/{DEFAULT_LOG})")
    ap.add_argument("--keep-dir", type=Path,
                    help=f"where what the integration stores is kept between starts (F59; "
                         f"default: <the component's config root>/{KEPT_ROOT}/<domain>)")
    args = ap.parse_args()

    require_ready(deep=False)
    become_subreaper()

    # Stop cleanly on SIGTERM, which is what systemd and `kill` send. Started in the background
    # from a non-interactive shell, this process inherits SIGINT as ignored, so Ctrl-C's signal
    # alone cannot stop it — found when three supervisors outlived `pkill -INT` (2026-10-05).
    def terminate(_signum, _frame) -> None:
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    try:
        supervisor = Supervisor(args.component.resolve(), json.loads(args.permissions),
                                args.python, args.audit_dir, args.hours, args.approvals,
                                args.keep_dir)
    except PredecessorsRemain as err:
        say(str(err))
        return 1
    if supervisor.cleared:
        say(f"cleared {supervisor.cleared} sandbox cgroup(s) an earlier supervisor left behind")
    say(f"supervising {supervisor.domain}; durable log {supervisor.log_path}; Ctrl-C to stop")
    try:
        supervisor.run()
    except KeyboardInterrupt:
        say("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
