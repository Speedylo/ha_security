"""The commands the mediator forwards from the household to a confined integration, per type.

Bridge step 2 (`notes/bridge_types_step2_prediction_20261025.md`). A user operating a confined
integration's entity in (A) becomes a command the mediator decides: the entity must be the
integration's own, the service one listed for the entity's type, and the data **exactly** the
listed keys with values of the listed kind. Anything else is refused, recorded, and never pushed.
This suite needs no (A): it drives `Mediator.command` with a stand-in that owns one entity of each
type, as `selftest_audit`'s F3 check does.

    K1   each listed command, with exactly its data, is pushed to the owning sandbox as it was
    K2   a service not listed for the entity's type is refused under COMMAND_SERVICES
    K3   data that is not exactly the listed keys, of the listed kind, is refused under COMMAND_DATA
    K4   a refused value is recorded by its type and length, never itself

Run:  python3 -m confine.selftest_commands
"""

from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path

from .audit import AuditLog
from .channel import Channel, ProtocolError
from .mediator import AMBIENT, COMMAND_SERVICES, Mediator, deny_everything
from .selftest_push import component

try:
    from .mediator import COMMAND_DATA
except ImportError:  # before step 2 there is no such rule; every K3 case then fails, as predicted
    COMMAND_DATA = "(no COMMAND_DATA rule)"

results: list[bool] = []
OWNED = {"switch.demo_power": "demo", "button.demo_report": "demo", "text.demo_note": "demo",
         "select.demo_mode": "demo", "number.demo_target": "demo"}


def check(claim: str, condition: bool, detail: str = "") -> None:
    results.append(bool(condition))
    print(f"{'  ok  ' if condition else '  FAIL'}  {claim}{f'  — {detail}' if detail else ''}")


class House:
    """Enough of a platform for `Mediator.command`: who owns what, and what it was told."""

    def __init__(self) -> None:
        self.owners = dict(OWNED)
        self.results: list[tuple] = []

    def command_result(self, command: int, ok: bool, error: str | None = None) -> None:
        self.results.append((command, ok, error))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mediator = Mediator(policy=deny_everything, log=AuditLog(path=root / "commands.jsonl"))
        mediator._platform = House()  # type: ignore[assignment]
        mine, theirs = Channel.pair()
        mediator.register("demo", Channel(mine), component=component(root, "demo", []))
        sandbox = Channel(theirs)
        sandbox.sock.settimeout(0.5)
        ids = iter(range(1, 1000))

        def send(entity: str, service: str, data: dict | None = None) -> tuple[dict, dict | None]:
            """One user's command; the decision recorded for it, and what the sandbox received."""
            before = len(mediator.log.records())
            command = {"command": next(ids), "integration": "demo", "entity_id": entity,
                       "service": service}
            if data is not None:
                command["data"] = data
            mediator.command(command)
            records = [r for r in mediator.log.records()[before:]
                       if r.get("kind") == "decision" and r.get("op") == "entity.command"]
            try:
                pushed = sandbox.recv()
            except (TimeoutError, OSError, ProtocolError):
                pushed = None
            return (records[0] if records else {}), pushed

        print("\nK1 — each listed command is forwarded with exactly its data\n")
        for entity, service, data in (
                ("switch.demo_power", "turn_on", None),
                ("switch.demo_power", "turn_off", {}),
                ("button.demo_report", "press", None),
                ("text.demo_note", "set_value", {"value": "*.tmp; rm -rf /"}),
                ("select.demo_mode", "select_option", {"option": "away"}),
                ("number.demo_target", "set_value", {"value": 22}),
                ("number.demo_target", "set_value", {"value": 19.5})):
            record, pushed = send(entity, service, data)
            check(f"K1 {entity.partition('.')[0]}.{service} {data or ''}: allowed and pushed as sent",
                  record.get("allowed") is True and record.get("clause") == AMBIENT
                  and pushed is not None and pushed.get("entity") == entity
                  and pushed.get("service") == service and pushed.get("data") == (data or {}),
                  f"{record.get('clause')} {pushed}")

        print("\nK2 — a service not listed for the entity's type\n")
        for entity, service in (("number.demo_target", "turn_on"), ("switch.demo_power", "press"),
                                ("switch.demo_power", "unlock"), ("select.demo_mode", "set_value")):
            record, pushed = send(entity, service, None)
            check(f"K2 {entity.partition('.')[0]}.{service}: refused under COMMAND_SERVICES, "
                  "not pushed",
                  record.get("allowed") is False and record.get("clause") == COMMAND_SERVICES
                  and pushed is None, f"{record.get('clause')} {pushed}")

        print("\nK3 — data that is not exactly the listed keys, of the listed kind\n")
        for label, entity, service, data in (
                ("switch turn_on with any data", "switch.demo_power", "turn_on", {"brightness": 1}),
                ("text set_value redirected with entity_id", "text.demo_note", "set_value",
                 {"value": "x", "entity_id": "text.someone_else"}),
                ("text set_value with no value", "text.demo_note", "set_value", {}),
                ("text set_value with a dict", "text.demo_note", "set_value",
                 {"value": {"__class__": "x"}}),
                ("text set_value with 256 characters", "text.demo_note", "set_value",
                 {"value": "x" * 256}),
                ("number set_value with a string", "number.demo_target", "set_value",
                 {"value": "22"}),
                ("number set_value with a boolean", "number.demo_target", "set_value",
                 {"value": True}),
                ("number set_value with NaN", "number.demo_target", "set_value",
                 {"value": math.nan}),
                ("number set_value with infinity", "number.demo_target", "set_value",
                 {"value": math.inf}),
                ("select select_option with a list", "select.demo_mode", "select_option",
                 {"option": ["away"]})):
            record, pushed = send(entity, service, data)
            check(f"K3 {label}: refused under COMMAND_DATA, not pushed",
                  record.get("allowed") is False and record.get("clause") == COMMAND_DATA
                  and pushed is None, f"{record.get('clause')} {pushed}")

        print("\nK4 — a refused value is recorded by its kind, never itself\n")
        hostile = "A" * 10_000
        record, pushed = send("text.demo_note", "set_value", {"value": hostile})
        log_text = (root / "commands.jsonl").read_text()
        check("K4 a 10,000-character value is refused under COMMAND_DATA",
              record.get("allowed") is False and record.get("clause") == COMMAND_DATA
              and pushed is None, str(record.get("clause")))
        check("K4 and the durable record holds its type and length, not the value",
              hostile not in log_text and "10000" in str(record.get("requested")),
              str(record.get("requested"))[:120])
        check("every chain verifies", mediator.log.verify() == [])

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
