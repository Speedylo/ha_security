"""The manual test, driven by a script: what a person in the house does, step by step.

Run on the Pi while `confine.supervise` is running `demo_flood` against (A):

    cd ~/r2exp/v2/framework && python3 ../experiments/flood/drive_demo.py SUPERVISOR_LOG AUDIT_DIR

Each step does what the interface does, over the same APIs: the switch is pressed over the
WebSocket API from a user's own connection, and the Repairs issue is opened and submitted over the
HTTP endpoints the Repairs panel calls. Prints a JSON summary of what happened, with timings.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from confine import house_a
from confine.house_a import User
from confine.ws import WebSocket

SWITCH_UNIQUE = "demo_flood:switch.demo_flood_misbehave"
ISSUE = "cut_off_demo_flood"


class Viewer:
    """A person's own connection to (A), for reading what the interface would show.

    Deliberately not a `RealPlatform`: that subscribes to the bridge's command stream, which has
    one subscriber, the newest. A second `RealPlatform` takes the stream from the supervisor's
    mediator, and the press then reaches this script instead of the sandbox — what the first
    run of this script did (2026-10-05).
    """

    def __init__(self, token: str) -> None:
        self.ws = WebSocket(house_a.HOST, house_a.PORT, timeout=30)
        self.ws.receive()
        self.ws.send({"type": "auth", "access_token": token})
        self.ws.receive()
        self.next = 1

    def call(self, message: dict) -> object:
        ident, self.next = self.next, self.next + 1
        self.ws.send({"id": ident, **message})
        while True:
            for answer in self.ws.receive():
                if answer.get("id") == ident and answer.get("type") == "result":
                    return answer.get("result")

    def read(self, entity_id: str) -> str | None:
        return next((s["state"] for s in self.call({"type": "get_states"})
                     if s["entity_id"] == entity_id), None)

    def close(self) -> None:
        self.ws.close()


def wait(condition, seconds: float) -> float | None:
    """Seconds until `condition()` holds, or None if it never did."""
    started = time.perf_counter()
    while time.perf_counter() - started < seconds:
        if condition():
            return time.perf_counter() - started
        time.sleep(0.02)
    return None


def main() -> int:
    # The supervisor writes one log per start (F31); the one being written is the newest.
    log = Path(sys.argv[1])
    audit = max(Path(sys.argv[2]).glob("decisions*.jsonl"), key=lambda p: p.stat().st_mtime)
    token = house_a.TOKEN_FILE.read_text().strip()
    platform = Viewer(token)

    def entity() -> str | None:
        return next((e["entity_id"] for e in platform.call({"type": "config/entity_registry/list"})
                     if e.get("unique_id") == SWITCH_UNIQUE), None)

    def issue() -> dict:
        return next((i for i in platform.call({"type": "repairs/list_issues"})["issues"]
                     if i["domain"] == "confine_bridge" and i["issue_id"] == ISSUE), {})

    def kinds() -> list[str]:
        return [json.loads(line)["kind"] for line in audit.read_text().splitlines() if line]

    summary: dict = {}
    switch = entity()
    summary["switch_in_A"] = switch
    if switch is None:
        print(json.dumps(summary))
        return 1
    before = len(kinds())

    user = User()
    pressed_at = time.perf_counter()
    user.press(switch, "turn_on").join(timeout=15)
    summary["press"] = user.outcome
    summary["cut_off_after_s"] = wait(lambda: "cutoff" in kinds()[before:], 15)
    summary["issue_after_s"] = wait(lambda: bool(issue()), 5)
    summary["press_to_issue_s"] = time.perf_counter() - pressed_at
    raised = issue()
    summary["issue"] = {k: raised.get(k) for k in ("severity", "is_fixable", "translation_key",
                                                   "translation_placeholders")}
    summary["supervisor_after_cut_off"] = [l for l in log.read_text().splitlines()
                                           if "cut off" in l]
    new = kinds()[before:]
    summary["records_during_flood"] = {k: new.count(k) for k in sorted(set(new))}

    flow = house_a.request("POST", "/api/repairs/issues/fix",
                           {"handler": "confine_bridge", "issue_id": ISSUE}, token=token)
    done = house_a.request("POST", f"/api/repairs/issues/fix/{flow['flow_id']}", {}, token=token)
    summary["fix_flow"] = [flow.get("step_id"), done.get("type")]
    starts = log.read_text().count(" started (run ")
    summary["restarted_after_s"] = wait(lambda: log.read_text().count(" started (run ") > starts, 15)
    summary["issue_gone"] = wait(lambda: not issue(), 5) is not None
    # Back in (A): the integration publishes its switch again, off, from its new sandbox.
    summary["switch_back_off_after_s"] = wait(lambda: platform.read(switch) == "off", 60)
    tail = kinds()[before:]
    summary["records_total"] = {k: tail.count(k) for k in sorted(set(tail))}
    user.close()
    platform.close()
    print(json.dumps(summary, indent=2))
    # Until 2026-10-07 this returned 0 whatever the summary said, and the regressions recorded
    # that 0 as a pass (verification 4.12, F48). It now fails unless every value is the one the
    # demo exists to show.
    expected = {
        "the press was accepted": (summary["press"] or {}).get("success") is True,
        "it was cut off": summary["cut_off_after_s"] is not None,
        "the house was told": summary["issue_after_s"] is not None,
        "the fix flow completed": summary["fix_flow"] == ["confirm", "create_entry"],
        "it was started again": summary["restarted_after_s"] is not None,
        "the issue is gone": summary["issue_gone"] is True,
        "its switch is back": summary["switch_back_off_after_s"] is not None,
        "one cut-off and one reinstatement recorded":
            summary["records_total"].get("cutoff") == 1
            and summary["records_total"].get("reinstate") == 1,
    }
    for claim, held in expected.items():
        print(f"{'  ok  ' if held else '  FAIL'}  {claim}")
    return 0 if all(expected.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
