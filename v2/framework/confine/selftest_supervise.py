"""The supervisor, run as an installation runs it, against the house's Home Assistant, (A).

Until 2026-10-07 no suite ran `supervise.py`. Branch coverage of the suites found it at 0%
(verification 4.12, finding F48): the cut-off that kills a sandbox, the Repairs restart, the
return after (A) restarts (F29), the clearing of a dead supervisor's sandbox (F30) and the rule
that a sandbox which exits by itself is not restarted were exercised only by `drive_demo.py`,
which could not fail, and by the fault scripts, outside the suites by which a mutant is judged.
Predictions and the mutant for each step: `notes/f48_f49_prediction_20261007.md`.

The supervisor is a separate process, started as `REPRODUCE.md` starts it, and everything here
acts as a person or an operator does: the switch is pressed from a user's connection, the Repairs
issue is submitted through the panel's HTTP endpoints, (A) is restarted, processes are signalled
by the pid the supervisor printed. Each step stops the suite if it fails, so a mutant ends it
at the step it breaks rather than at the runner's time limit.

Needs (A) up (`python3 -m confine.house_a up`).
Run:  systemd-run --user --scope -q python3 -m confine.selftest_supervise [--python PATH]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
from pathlib import Path

from .describe import record_approval
from .manifest import Manifest, Provenance
from . import house_a
from .audit import AuditLog, last_record
from .cgroup import Delegation

HERE = Path(__file__).resolve().parent
FRAMEWORK = HERE.parent
DEMO = FRAMEWORK.parent / "experiments" / "flood" / "demo_flood"
#: `demo_flood` that blocks its own event loop, so it cannot stop itself after a cut-off (M31).
STUBBORN = DEMO.with_name("demo_stubborn")
DOMAIN = "demo_flood"

results: list[bool] = []


class Stop(Exception):
    """A step failed; the rest depend on it."""


def check(claim: str, condition: bool, detail: str = "", *, fatal: bool = True) -> None:
    results.append(condition)
    print(f"{'  ok  ' if condition else '  FAIL'}  {claim}{f'  — {detail}' if detail else ''}",
          flush=True)
    if not condition and fatal:
        raise Stop(claim)


def wait(condition, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.1)
    return bool(condition())


def alive(pid: int) -> bool:
    """Running, and not a zombie waiting for its parent (a reaped sandbox's pid is gone)."""
    try:
        status = Path(f"/proc/{pid}/status").read_text()
    except OSError:
        return False
    return "\nState:\tZ" not in status


class Run:
    """One supervisor process, its printed lines and its audit directory."""

    def __init__(self, python: Path, audit: Path, log: Path, component: Path = DEMO, *,
                 approve: bool = True, permissions: dict | None = None,
                 approvals: Path | None = None) -> None:
        self.log, self.audit, self.domain = log, audit, component.name
        # F57: the supervisor registers nothing unapproved. The test approves the grant the
        # supervisor will load, by default a derived manifest that declares nothing, and keeps
        # the approval beside its own logs rather than in the repository. F57c's steps start
        # some supervisors unapproved, and some with a wider grant.
        self.permissions = permissions or {"schema_version": 1}
        self.approvals = approvals or audit.parent / f"approvals-{audit.name}.jsonl"
        if approve:
            record_approval(component, self.approvals,
                            Manifest(component.name, Provenance.DERIVED, self.permissions))
        self.out = open(log, "wb")
        self.proc = subprocess.Popen(
            [sys.executable, "-u", "-m", "confine.supervise", "--component", str(component),
             "--python", str(python), "--audit-dir", str(audit),
             "--approvals", str(self.approvals), "--permissions", json.dumps(self.permissions)],
            cwd=FRAMEWORK, stdout=self.out, stderr=subprocess.STDOUT)

    def text(self) -> str:
        return self.log.read_text(errors="replace")

    def says(self, words: str, seconds: float) -> bool:
        return wait(lambda: words in self.text(), seconds)

    def sandbox(self, run: int, seconds: float = 60) -> int | None:
        """The pid the supervisor printed for its `run`th sandbox."""
        pattern = re.compile(rf"{self.domain} started \(run {run}, pid (\d+)\)")
        found: list[int] = []
        wait(lambda: bool(found or found.extend(int(m) for m in pattern.findall(self.text()))),
             seconds)
        return found[0] if found else None

    def cgroup(self, run: int) -> Path | None:
        parent = Delegation.discover().parent
        return None if parent is None else parent / f"sup-{self.domain}-{self.proc.pid}-{run}"

    def records(self) -> list[dict]:
        newest = max(self.audit.glob("decisions-*.jsonl"), key=lambda p: p.stat().st_mtime)
        return AuditLog(path=newest).records()

    def published(self, times: int, seconds: float = 90) -> bool:
        """Wait until the integration has published its switch `times` times in this log.

        The switch's registry entry outlives every run, so finding it in (A) says nothing about
        whether the integration inside the sandbox is up. Its own `entity.publish` decision does.
        Found on the first run of this suite (2026-10-07): a press 0.2 s after the start was
        recorded and then had no effect, because the integration published its switch at 0.9 s.
        """
        return wait(lambda: sum(1 for r in self.records() if r.get("op") == "entity.publish"
                                and r.get("allowed")) >= times, seconds)

    def end(self, sig: int) -> None:
        if self.proc.poll() is None:
            self.proc.send_signal(sig)
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=10)
        self.out.close()


def admin(message: dict) -> object:
    return house_a._ws_call(house_a.TOKEN_FILE.read_text().strip(), message).get("result")


def issue(domain: str = DOMAIN) -> dict:
    listed = admin({"type": "repairs/list_issues"}) or {}
    return next((i for i in listed.get("issues", [])
                 if i["domain"] == "confine_bridge" and i["issue_id"] == f"cut_off_{domain}"), {})


def switch_of(domain: str) -> str | None:
    """The entity id (A) gave the integration's switch, from its registry."""
    unique = f"{domain}:switch.{domain}_misbehave"
    return next((e["entity_id"] for e in admin({"type": "config/entity_registry/list"}) or []
                 if e.get("unique_id") == unique), None)


def not_started(domain: str = DOMAIN) -> dict:
    """The integration's `not_started` Repairs issue in (A), or {} (F57c)."""
    listed = admin({"type": "repairs/list_issues"}) or {}
    return next((i for i in listed.get("issues", [])
                 if i["domain"] == "confine_bridge"
                 and i["issue_id"] == f"not_started_{domain}"), {})


def open_screen(issue_id: str, token: str | None = None) -> dict:
    """Open a Repairs issue's screen as the panel does: the flow's first answer."""
    token = token or house_a.TOKEN_FILE.read_text().strip()
    return house_a.request("POST", "/api/repairs/issues/fix",
                           {"handler": "confine_bridge", "issue_id": issue_id}, token=token)


def screen_text(screen: dict) -> str:
    return " ".join(str(v) for v in (screen.get("description_placeholders") or {}).values())


def repair(domain: str) -> dict:
    """Submit the integration's Repairs issue as the panel does; the flow's last answer."""
    token = house_a.TOKEN_FILE.read_text().strip()
    flow = house_a.request("POST", "/api/repairs/issues/fix",
                           {"handler": "confine_bridge", "issue_id": f"cut_off_{domain}"},
                           token=token)
    return house_a.request("POST", f"/api/repairs/issues/fix/{flow['flow_id']}", {}, token=token)


def steps(python: Path, work: Path, runs: list[Run]) -> None:
    print("\n1 — it starts\n")
    first = Run(python, work / "audit_a", work / "supervisor_a.log")
    runs.append(first)
    pid1 = first.sandbox(1)
    check("run 1's sandbox started", pid1 is not None and alive(pid1), f"pid {pid1}")
    group1 = first.cgroup(1)
    check("in its own cgroup", group1 is not None and group1.is_dir(), str(group1))
    check("its switch is in (A)", wait(lambda: switch_of(DOMAIN) is not None, 60))
    switch = switch_of(DOMAIN)
    check("and the integration inside has published it", first.published(1))

    print("\n2 — the mediator cuts it off, and the sandbox is killed (M31)\n")
    user = house_a.User()
    user.press(switch, "turn_on").join(timeout=15)
    user.close()
    check("the supervisor is told", first.says("cut off by the mediator", 15))
    check("the sandbox's process is gone", wait(lambda: not alive(pid1), 15), f"pid {pid1}")
    check("and so is its cgroup", wait(lambda: not group1.exists(), 15), str(group1))
    check("the house sees a Repairs issue", wait(lambda: bool(issue()), 10))

    print("\n3 — a person submits the Repairs issue, and it runs again (M32)\n")
    done = repair(DOMAIN)
    check("the fix flow completes", done.get("type") == "create_entry", str(done.get("type")))
    pid2 = first.sandbox(2, 30)
    check("run 2 started, a new process", pid2 is not None and pid2 != pid1 and alive(pid2),
          f"pid {pid2}")
    kinds = [r["kind"] for r in first.records()]
    check("the durable log holds one cut-off and one reinstatement",
          kinds.count("cutoff") == 1 and kinds.count("reinstate") == 1,
          f"cutoff {kinds.count('cutoff')}, reinstate {kinds.count('reinstate')}")
    check("and the issue is gone", wait(lambda: not issue(), 10))

    print("\n4 — (A) restarts, and the integration comes back (F29, M33)\n")
    house_a.stop(house_a.DEFAULT_CONFIG)
    house_a.start(house_a.DEFAULT_CONFIG)
    house_a.wait_until_running()
    check("the supervisor saw (A) go", first.says("went away", 30))
    check("and come back", first.says("is back; starting", 90))
    pid3 = first.sandbox(3, 30)
    check("run 3 started", pid3 is not None and alive(pid3), f"pid {pid3}")

    print("\n5 — a supervisor killed outright; the next one clears what it left (F30, M34)\n")
    left = [first.cgroup(n) for n in (1, 2, 3)]
    first.end(signal.SIGKILL)
    check("the first supervisor is gone", first.proc.poll() is not None)
    second = Run(python, work / "audit_b", work / "supervisor_b.log")
    runs.append(second)
    check("the second reports clearing what the first left",
          second.says("cleared 1 sandbox cgroup", 60),
          (re.findall(r"cleared \d+ sandbox cgroup\S*", second.text()) or ["nothing cleared"])[0])
    check("run 3 of the first is not running", wait(lambda: not alive(pid3), 15), f"pid {pid3}")
    check("and none of the first's cgroups remains",
          not any(g is not None and g.exists() for g in left))
    pid_b = second.sandbox(1)
    check("the second's own sandbox started", pid_b is not None and alive(pid_b), f"pid {pid_b}")

    print("\n6 — a sandbox that exits by itself is not restarted (M35)\n")
    os.kill(pid_b, signal.SIGKILL)
    check("the supervisor reports it", second.says("exited by itself", 15))
    time.sleep(10)
    check("and starts nothing in its place", "started (run 2" not in second.text())

    print("\n7 — it stops cleanly\n")
    second.end(signal.SIGTERM)
    check("it says it stopped", second.text().rstrip().endswith("stopped"))
    parent = Delegation.discover().parent
    remaining = sorted(p.name for p in parent.glob(f"sup-{DOMAIN}-*")) if parent else []
    check("no demo_flood cgroup is left", not remaining, ", ".join(remaining))

    print("\n8 — an integration that will not stop by itself is killed (M31)\n")
    # `demo_flood` stops by itself once the mediator closes its channel, so steps 2 and 3 pass
    # whether or not the supervisor kills anything: mutant M31 survived them (2026-10-07). This
    # integration blocks its own event loop, so only the kill through its cgroup can end it.
    third = Run(python, work / "audit_c", work / "supervisor_c.log", STUBBORN)
    runs.append(third)
    pid_c = third.sandbox(1)
    check("demo_stubborn's sandbox started", pid_c is not None and alive(pid_c), f"pid {pid_c}")
    check("its switch is in (A)", wait(lambda: switch_of(STUBBORN.name) is not None, 60))
    check("and the integration inside has published it", third.published(1))
    user = house_a.User()
    user.press(switch_of(STUBBORN.name), "turn_on").join(timeout=15)
    user.close()
    check("it is cut off", third.says("cut off by the mediator", 30))
    group_c = third.cgroup(1)
    check("its sandbox's process is gone", wait(lambda: not alive(pid_c), 15), f"pid {pid_c}")
    check("and so is its cgroup", wait(lambda: not group_c.exists(), 15), str(group_c))
    check("not by stopping itself", "exited by itself" not in third.text())
    # Leave (A) as it was found: the Repairs issue submitted, then this supervisor stopped.
    check("its Repairs issue is cleared", wait(lambda: bool(issue(STUBBORN.name)), 10)
          and repair(STUBBORN.name).get("type") == "create_entry")
    third.end(signal.SIGTERM)
    left_c = sorted(p.name for p in parent.glob(f"sup-{STUBBORN.name}-*")) if parent else []
    check("no demo_stubborn cgroup is left", not left_c, ", ".join(left_c))
    not_approved_steps(python, work, runs)
    for run in runs:
        for path in sorted(run.audit.glob("decisions-*.jsonl")):
            # Read from outside the mediator, so without its key: every MAC "fails", as it must
            # (§6.8.4). Every other kind of break (sequence, link, hash) is checkable and counted.
            breaks = [b for b in AuditLog(path=path).verify(key=b"") if b.kind != "mac"]
            check(f"{path.name}: no sequence, link or hash break", not breaks,
                  "; ".join(str(b) for b in breaks[:2]))


def not_approved_steps(python: Path, work: Path, runs: list[Run]) -> None:
    """F57c: the house is told, and an administrator can allow it, when an integration is not
    approved (`notes/f57c_not_started_issue_prediction.md` §3, steps 1–8)."""
    print("\n9 — not approved: the house is told, and can allow it (F57c, M41–M42)\n")
    fourth = Run(python, work / "audit_d", work / "supervisor_d.log", approve=False)
    runs.append(fourth)
    check("1. with no approval on record, the supervisor says it did not start it",
          fourth.says("not started", 60))
    check("   and no sandbox started", "started (run 1" not in fourth.text())
    found = {}
    check("2. (A) shows a `not_started` issue: not approved, and fixable",
          wait(lambda: bool(found.update(not_started()) or found), 15)
          and found.get("translation_key") == "not_approved" and found.get("is_fixable") is True,
          str({k: found.get(k) for k in ("translation_key", "is_fixable")}))
    screen = open_screen(f"not_started_{DOMAIN}")
    text = screen_text(screen)
    check("3. its screen shows `describe`'s lines", screen.get("type") == "form"
          and "It will NOT be allowed to" in text and "control anything" in text, text[:120])
    try:
        open_screen(f"not_started_{DOMAIN}", house_a.MEDIATOR_TOKEN_FILE.read_text().strip())
        status = 200
    except urllib.error.HTTPError as err:
        status = err.code
    check("4. the mediator's non-admin login cannot open it", status == 401, f"HTTP {status}")
    done = house_a.request("POST", f"/api/repairs/issues/fix/{screen['flow_id']}", {},
                           token=house_a.TOKEN_FILE.read_text().strip())
    pid = fourth.sandbox(1, 60)
    check("5. Allow and start: a sandbox starts", done.get("type") == "create_entry"
          and pid is not None and alive(pid), f"{done.get('type')}, pid {pid}")
    check("   and the integration publishes its switch", fourth.published(1))
    record = last_record(fourth.approvals, DOMAIN) or {}
    check("6. the issue is gone, and the approval says who gave it",
          wait(lambda: not not_started(), 10)
          and record.get("by") == "an administrator, from the Repairs panel", str(record.get("by")))
    fourth.end(signal.SIGTERM)

    wider = {"schema_version": 1, "services": {"call": ["light.turn_on"]}}
    fifth = Run(python, work / "audit_e", work / "supervisor_e.log", approve=False,
                permissions=wider, approvals=fourth.approvals)
    runs.append(fifth)
    check("7. its permissions widened, it is not started again",
          fifth.says("not started", 60) and "started (run 1" not in fifth.text())
    text = ""
    if wait(lambda: bool(not_started()), 15):
        text = screen_text(open_screen(f"not_started_{DOMAIN}"))
    check("   and its screen says what it is allowed to do has changed",
          "allowed to do has changed" in text, text[:120])
    fifth.end(signal.SIGTERM)
    sixth = Run(python, work / "audit_f", work / "supervisor_f.log", permissions=wider,
                approvals=fourth.approvals)
    runs.append(sixth)
    pid = sixth.sandbox(1, 60)
    check("8. approved by the operator instead, a new supervisor starts it",
          pid is not None and alive(pid), f"pid {pid}")
    check("   and the issue is gone, though no screen was submitted",
          wait(lambda: not not_started(), 15))
    sixth.end(signal.SIGTERM)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", type=Path, default=Path.home() / "r2exp" / "ha314" / "bin" / "python")
    args = ap.parse_args()
    if not house_a.running():
        print("  FAIL  (A) is not up: run `python3 -m confine.house_a up` first")
        return 1
    runs: list[Run] = []
    work = Path(tempfile.mkdtemp(prefix="selftest-supervise-"))
    try:
        steps(args.python, work, runs)
    except Stop as stopped:
        print(f"\n  stopped at: {stopped}")
    finally:
        for run in runs:
            run.end(signal.SIGTERM)
        print(f"\n  logs: {work}")
    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if results and all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
