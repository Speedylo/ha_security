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
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import house_a
from .audit import AuditLog
from .cgroup import Delegation

HERE = Path(__file__).resolve().parent
FRAMEWORK = HERE.parent
DEMO = FRAMEWORK.parent / "experiments" / "flood" / "demo_flood"
DOMAIN = "demo_flood"
SWITCH_UNIQUE = f"{DOMAIN}:switch.demo_flood_misbehave"
ISSUE = f"cut_off_{DOMAIN}"

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

    def __init__(self, python: Path, audit: Path, log: Path) -> None:
        self.log, self.audit = log, audit
        self.out = open(log, "wb")
        self.proc = subprocess.Popen(
            [sys.executable, "-u", "-m", "confine.supervise", "--component", str(DEMO),
             "--python", str(python), "--audit-dir", str(audit)],
            cwd=FRAMEWORK, stdout=self.out, stderr=subprocess.STDOUT)

    def text(self) -> str:
        return self.log.read_text(errors="replace")

    def says(self, words: str, seconds: float) -> bool:
        return wait(lambda: words in self.text(), seconds)

    def sandbox(self, run: int, seconds: float = 60) -> int | None:
        """The pid the supervisor printed for its `run`th sandbox."""
        pattern = re.compile(rf"{DOMAIN} started \(run {run}, pid (\d+)\)")
        found: list[int] = []
        wait(lambda: bool(found or found.extend(int(m) for m in pattern.findall(self.text()))),
             seconds)
        return found[0] if found else None

    def cgroup(self, run: int) -> Path | None:
        parent = Delegation.discover().parent
        return None if parent is None else parent / f"sup-{DOMAIN}-{self.proc.pid}-{run}"

    def records(self) -> list[dict]:
        newest = max(self.audit.glob("decisions-*.jsonl"), key=lambda p: p.stat().st_mtime)
        return AuditLog(path=newest).records()

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


def issue() -> dict:
    listed = admin({"type": "repairs/list_issues"}) or {}
    return next((i for i in listed.get("issues", [])
                 if i["domain"] == "confine_bridge" and i["issue_id"] == ISSUE), {})


def steps(python: Path, work: Path, runs: list[Run]) -> None:
    print("\n1 — it starts\n")
    first = Run(python, work / "audit_a", work / "supervisor_a.log")
    runs.append(first)
    pid1 = first.sandbox(1)
    check("run 1's sandbox started", pid1 is not None and alive(pid1), f"pid {pid1}")
    group1 = first.cgroup(1)
    check("in its own cgroup", group1 is not None and group1.is_dir(), str(group1))
    switch = None

    def find_switch() -> bool:
        nonlocal switch
        switch = next((e["entity_id"] for e in admin({"type": "config/entity_registry/list"})
                       or [] if e.get("unique_id") == SWITCH_UNIQUE), None)
        return switch is not None
    check("its switch is in (A)", wait(find_switch, 60), str(switch))

    print("\n2 — the mediator cuts it off, and the sandbox is killed (M31)\n")
    user = house_a.User()
    user.press(switch, "turn_on").join(timeout=15)
    user.close()
    check("the supervisor is told", first.says("cut off by the mediator", 15))
    check("the sandbox's process is gone", wait(lambda: not alive(pid1), 15), f"pid {pid1}")
    check("and so is its cgroup", wait(lambda: not group1.exists(), 15), str(group1))
    check("the house sees a Repairs issue", wait(lambda: bool(issue()), 10))

    print("\n3 — a person submits the Repairs issue, and it runs again (M32)\n")
    token = house_a.TOKEN_FILE.read_text().strip()
    flow = house_a.request("POST", "/api/repairs/issues/fix",
                           {"handler": "confine_bridge", "issue_id": ISSUE}, token=token)
    done = house_a.request("POST", f"/api/repairs/issues/fix/{flow['flow_id']}", {}, token=token)
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
    for run in runs:
        for path in sorted(run.audit.glob("decisions-*.jsonl")):
            # Read from outside the mediator, so without its key: every MAC "fails", as it must
            # (§6.8.4). Every other kind of break (sequence, link, hash) is checkable and counted.
            breaks = [b for b in AuditLog(path=path).verify(key=b"") if b.kind != "mac"]
            check(f"{path.name}: no sequence, link or hash break", not breaks,
                  "; ".join(str(b) for b in breaks[:2]))


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
