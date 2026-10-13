"""T06's subscription half, paired: both arms on the same host and Home Assistant release.

Appendix C's T06 row compared §7.14's unconfined 4 of 4 (real Home Assistant, four entities) with
§7.36's confined 0 of 3 (the stand-in platform, three other entities): two experiments, not two
arms of one. This harness runs both arms against Home Assistant 2026.8.3 on the Pi, with the same
three undeclared entities changed by the same state write. Predictions:
`notes/t06_true_pair_prediction.md`.

    unconfined  `pair_unconfined.py` under 3.14: a listener on EVENT_STATE_CHANGED. (A) must be
                down (F56: the unconfined arms run with (A) down)
    confined    the real `Mediator` and `RealPlatform` against (A), `selftest_push`'s `Sandbox`
                on the far end of the channel, subscribed to the declared entity only
    control     the filter bypassed in the harness, as `selftest_push` does for M10, at both of
                its layers: (A)'s watched set and the mediator's subscription table

Run:  experiments/pair_subscriptions/run.sh, which runs both arms in order.
"""

from __future__ import annotations

import argparse
import json
import platform as host
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import house_a
from .audit import AuditLog
from .mediator import Mediator
from .platform import ActingPolicy
from .real_platform import RealPlatform
from .selftest_push import Sandbox, component

HERE = Path(__file__).resolve().parent
DECLARED = "sensor.pair_declared"
UNDECLARED = ["sensor.bedroom_occupancy", "lock.front_door", "person.younes"]


def arm_unconfined(python: Path) -> dict:
    if house_a.running():
        return {"arm": "unconfined", "fatal": "(A) is running: stop it first (F56)"}
    root = Path(tempfile.mkdtemp(prefix="pair-unconfined-"))
    try:
        (root / "config").mkdir()
        for name in ("sandbox_runtime.py", "pair_unconfined.py"):
            shutil.copy2(HERE / name, root / name)
        spec = root / "spec.json"
        spec.write_text(json.dumps({"config_dir": str(root / "config")}))
        proc = subprocess.run([str(python), str(root / "pair_unconfined.py"), str(spec)],
                              capture_output=True, text=True, timeout=600, cwd=str(root))
        lines = (proc.stdout or "").strip().splitlines()
        if not lines:
            tail = (proc.stderr or "").strip().splitlines()
            return {"arm": "unconfined", "fatal": tail[-1][:300] if tail else "no output"}
        return json.loads(lines[-1])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def set_state(token: str, entity_id: str, state: str) -> None:
    """The platform's own state write, over (A)'s REST API, as the house's owner."""
    house_a.request("POST", f"/api/states/{entity_id}", {"state": state}, token=token)


def wait_for(mediator: Mediator, sandbox: Sandbox, condition, seconds: float = 5) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and not condition():
        mediator.serve(timeout=0.05)
        sandbox.drain()
    return condition()


def arm_confined() -> dict:
    if not house_a.running():
        return {"arm": "confined", "fatal": "(A) is not running: python3 -m confine.house_a up --fresh"}
    token = house_a.TOKEN_FILE.read_text().strip()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        platform = RealPlatform()
        log = AuditLog(path=root / "audit" / "decisions.jsonl")
        mediator = Mediator(policy=ActingPolicy({}, platform), log=log)
        mediator.attach_platform(platform)
        reader = Sandbox(mediator, "pair", component(root, "pair", [DECLARED]))

        for entity_id in [DECLARED, *UNDECLARED]:
            set_state(token, entity_id, "0")
        granted = reader.ask({"op": "entity.subscribe", "entity": DECLARED})
        reader.received.clear()

        def seen(state: str) -> set[str]:
            return {m["entity"] for m in reader.received if m.get("state") == state}

        # The measurement. The declared change is made last, so once it has arrived every
        # undeclared change before it has had its chance to arrive too; then one more second.
        for entity_id in [*UNDECLARED, DECLARED]:
            set_state(token, entity_id, "on")
        declared_delivered = wait_for(mediator, reader, lambda: DECLARED in seen("on"))
        wait_for(mediator, reader, lambda: False, seconds=1)
        undeclared_delivered = sorted(seen("on") & set(UNDECLARED))
        decisions = [r for r in log.records() if r["kind"] == "decision"]

        # The control: past both layers of the filter, the same observer must see all three.
        for entity_id in UNDECLARED:
            platform.watch(entity_id)
        for entities in mediator._subscriptions.values():  # noqa: SLF001 — the bypass is the point
            entities.update(UNDECLARED)
        for entity_id in UNDECLARED:
            set_state(token, entity_id, "leaked")
        wait_for(mediator, reader, lambda: seen("leaked") >= set(UNDECLARED))

        result = {"arm": "confined", "ha_version": platform.call({"type": "get_config"})["version"],
                  "host": host.node(), "subscription_granted": granted.get("ok") is True,
                  "declared_delivered": declared_delivered,
                  "undeclared_delivered": undeclared_delivered, "undeclared": UNDECLARED,
                  "control_seen": sorted(seen("leaked") & set(UNDECLARED)),
                  "decisions": len(decisions),
                  "decisions_allowed": sum(r["allowed"] for r in decisions),
                  "decisions_after_control": len([r for r in log.records()
                                                  if r["kind"] == "decision"]),
                  "chain_breaks": len(log.verify())}
        platform.close()
        return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["unconfined", "confined"], required=True)
    ap.add_argument("--python", type=Path, default=Path.home() / "r2exp/ha314/bin/python",
                    help="the 3.14 interpreter with Home Assistant, for the unconfined arm")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    result = arm_unconfined(args.python) if args.arm == "unconfined" else arm_confined()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 1 if "fatal" in result else 0


if __name__ == "__main__":
    sys.exit(main())
