"""F59: what an integration stores survives a restart, and nothing it could run from does.

Until F59 (2026-10-11) the supervisor gave every start a fresh data directory, so a restarted
integration lost its configuration entry and everything else it stored, an OAuth token included.
Keeping the whole directory would have been worse: it is the sandbox's Home Assistant
configuration directory, and the integration could replace the link to its approved code there
with code of its own, which the next start would load past F57's gate. So only `.storage` is
kept, the start that finds an entry sets it up as Home Assistant's own start-up does, the kept
folder is held to `disk_mb`, and each start's throwaway folder is deleted once its sandbox is
gone (`notes/f59_kept_storage_prediction.md`).

`experiments/keep/demo_keep` is the integration: each setup turns its stored token `refresh-<n>`
into `refresh-<n+1>` and shows it in a sensor, plants code in place of its link, and makes a
directory nobody may read. Everything here acts as an operator or an administrator does, against
the house's Home Assistant, (A). Each step stops the suite if it fails.

Needs (A) up (`python3 -m confine.house_a up`).
Run:  systemd-run --user --scope -q python3 -m confine.selftest_keep [--python PATH]
"""

from __future__ import annotations

import argparse
import os
import re
import signal
import sys
import tempfile
import time
from pathlib import Path

from . import house_a
from .manifest import Manifest
from .selftest_supervise import (FRAMEWORK, Run, Stop, admin, check, not_started, open_screen,
                                 results, wait)

KEEP = FRAMEWORK.parent / "experiments" / "keep" / "demo_keep"
DOMAIN = KEEP.name
UNIQUE = f"{DOMAIN}:sensor.demo_keep_token"


def token() -> tuple[str | None, dict]:
    """The sensor's state in (A) and its attributes, or (None, {}) before it exists."""
    entity = next((e["entity_id"] for e in admin({"type": "config/entity_registry/list"}) or []
                   if e.get("unique_id") == UNIQUE), None)
    if entity is None:
        return None, {}
    state = next((s for s in admin({"type": "get_states"}) or [] if s["entity_id"] == entity), None)
    return (state["state"], state.get("attributes") or {}) if state else (None, {})


def reads(value: str, seconds: float = 90) -> bool:
    """Wait for the sensor to read `value`, asking (A) once a second rather than ten times."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if token()[0] == value:
            return True
        time.sleep(1)
    return token()[0] == value


def holds_entry(kept: Path) -> bool:
    """Whether Home Assistant's entries file under `kept` names the integration.

    Looked for anywhere under the folder, not only at its top, so that a design keeping the
    whole configuration directory (M45) passes this step and is caught where it matters, by
    the code it lets the integration plant.
    """
    try:
        return any(f'"domain":"{DOMAIN}"' in path.read_text().replace(" ", "")
                   for path in kept.rglob("core.config_entries"))
    except OSError:
        return False


def folder(run: Run, n: int) -> Path | None:
    """The throwaway folder the supervisor printed for its `n`th start."""
    found = re.findall(rf"{DOMAIN} run {n} folder (\S+)", run.text())
    return Path(found[0]) if found else None


def submit(issue_id: str) -> dict:
    screen = open_screen(issue_id)
    return house_a.request("POST", f"/api/repairs/issues/fix/{screen['flow_id']}", {},
                           token=house_a.TOKEN_FILE.read_text().strip())


def steps(python: Path, work: Path, runs: list[Run]) -> None:
    kept = work / "kept"
    print("\n1 — the first start logs in, and the kept folder holds its entry\n")
    first = Run(python, work / "audit_a", work / "supervisor_a.log", KEEP, keep=kept)
    runs.append(first)
    check("1. the sensor reads refresh-1", reads("refresh-1"), str(token()[0]))
    check("2. the integration planted code in place of its link, so step 6 means something",
          wait(lambda: token()[1].get("plant") == "done", 30), str(token()[1].get("plant")))
    check("3. the kept folder holds its configuration entry", wait(lambda: holds_entry(kept), 15),
          str(sorted(p.name for p in kept.iterdir()) if kept.is_dir() else "no folder"))
    time.sleep(3)                           # past Home Assistant's one-second save delay
    first.end(signal.SIGTERM)

    print("\n2 — a new supervisor: the entry is set up, not asked for again (M45, M47)\n")
    second = Run(python, work / "audit_b", work / "supervisor_b.log", KEEP, keep=kept)
    runs.append(second)
    check("4. the sensor reads refresh-2: the stored token was read back", reads("refresh-2"),
          str(token()[0]))
    logs = sorted(second.audit.glob(f"{DOMAIN}-*-run1.log"))
    text = logs[0].read_text(errors="replace") if logs else ""
    check("5. the run's log says it set up 1 stored entry, and ran no setup dialog",
          "set up 1 stored entry" in text, logs[0].name if logs else "no run log")
    time.sleep(5)
    check("6. the planted code was not loaded", token()[0] == "refresh-2", str(token()[0]))
    time.sleep(3)
    second.end(signal.SIGTERM)

    print("\n3 — too much stored: not started, and Try again grants nothing (M46)\n")
    limit = Manifest.load(KEEP, KEEP.parent.parent).resources.disk_mb
    big = kept / "too_much"
    with open(big, "wb") as f:              # sparse: its size is counted, nothing is written
        f.truncate((limit + 1) * 1024 * 1024)
    third = Run(python, work / "audit_c", work / "supervisor_c.log", KEEP, keep=kept)
    runs.append(third)
    check("7. the supervisor says it did not start it, and no sandbox started",
          third.says("not started", 60) and "started (run 1" not in third.text())
    found = {}
    check("8. (A) shows a `not_started` issue: too much data, fixable",
          wait(lambda: bool(found.update(not_started(DOMAIN)) or found), 15)
          and found.get("translation_key") == "too_much_data" and found.get("is_fixable") is True,
          str({k: found.get(k) for k in ("translation_key", "is_fixable")}))
    done = submit(f"not_started_{DOMAIN}")
    check("9. Try again with it still there: still not started, and the issue is back",
          done.get("type") == "create_entry" and third.says("asked to try again", 15)
          and wait(lambda: third.text().count("not started") >= 2, 15)
          and wait(lambda: bool(not_started(DOMAIN)), 15) and "started (run 1" not in third.text())
    big.unlink()
    submit(f"not_started_{DOMAIN}")
    check("10. the file removed, Try again: it starts, and the sensor reads refresh-3",
          third.sandbox(1, 60) is not None and reads("refresh-3"), str(token()[0]))
    check("11. and the issue is gone", wait(lambda: not not_started(DOMAIN), 15))

    print("\n4 — a restart inside one supervisor: the throwaway folder goes, the entry stays (M48, M49)\n")
    wait(lambda: token()[1].get("locked") == "done", 30)
    locked = token()[1].get("locked")
    run1 = folder(third, 1)
    time.sleep(3)
    house_a.stop(house_a.DEFAULT_CONFIG)
    house_a.start(house_a.DEFAULT_CONFIG)
    house_a.wait_until_running()
    check("    the supervisor saw (A) go and come back",
          third.says("went away", 30) and third.says("is back; starting", 90))
    pid2 = third.sandbox(2, 60)
    check("12. while it still runs, run 1's throwaway folder is gone, its locked directory with it, "
          "and the kept folder still holds the entry",
          pid2 is not None and run1 is not None and locked == "done" and not run1.exists()
          and holds_entry(kept),
          f"folder {run1} exists={run1.exists() if run1 else None}, locked {locked}")
    check("13. and run 2's sensor reads refresh-4", reads("refresh-4"), str(token()[0]))
    third.end(signal.SIGTERM)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", type=Path, default=Path.home() / "r2exp" / "ha314" / "bin" / "python")
    args = ap.parse_args()
    if not house_a.running():
        print("  FAIL  (A) is not up: run `python3 -m confine.house_a up` first")
        return 1
    runs: list[Run] = []
    work = Path(tempfile.mkdtemp(prefix="selftest-keep-"))
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
