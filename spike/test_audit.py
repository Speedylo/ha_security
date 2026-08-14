#!/usr/bin/env python3
"""Tests for AuditLog — what the hash chain does, and what it provably does not.

Three of these encode findings rather than requirements, which is deliberate: a
limit that is written down but not tested tends to quietly stop being true, and
a limit that is *asserted* in a test cannot be mistaken for a fixed bug later.

    python3 test_audit.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

from supervisor import AuditLog

PASS, FAIL = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m"
_failures = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global _failures
    if condition:
        print(f"  {PASS}  {label}" + (f" — {detail}" if detail else ""))
    else:
        _failures += 1
        print(f"  {FAIL}  {label}" + (f" — {detail}" if detail else ""))


def write_log(path: Path, count: int) -> AuditLog:
    log = AuditLog(path)
    for n in range(count):
        log.append("t", "set_state", {"entity_id": f"sensor.x{n}"}, True, "ok")
    log.close()
    return log


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        print("\nthe chain verifies, and detects a naive edit")
        good = root / "good.jsonl"
        write_log(good, 5)
        ok, detail = AuditLog.verify(good)
        check("intact chain verifies", ok, detail)

        rows = [json.loads(line) for line in good.open()]
        # Must be a real change: the records were written with allowed=True, so
        # setting decision to "allow" is a no-op and the chain correctly still
        # verifies. That mistake made this test pass-by-accident on first write.
        assert rows[2]["decision"] == "allow"
        rows[2]["decision"] = "DENY"
        edited = root / "edited.jsonl"
        edited.write_text("".join(json.dumps(r) + "\n" for r in rows))
        ok, detail = AuditLog.verify(edited)
        check("single-record edit is detected", not ok, detail)

        print("\ntwo runs cannot silently share a log file")
        # Regression test. AuditLog used to open in append mode, and run ids were
        # second-resolution, so two runs starting in the same second wrote into
        # one file. The second restarted seq at 0 and prev at the zero anchor, so
        # verify() reported "chain broken" — a FALSE tamper report. Exclusive
        # create makes the collision impossible to mistake for tampering.
        collided = False
        try:
            AuditLog(good)
        except FileExistsError:
            collided = True
        check("reopening an existing log raises", collided, "exclusive create, not append")

        merged = root / "merged.jsonl"
        merged.write_text(good.read_text() + good.read_text())
        ok, detail = AuditLog.verify(merged)
        check(
            "two concatenated runs would fail verification",
            not ok,
            f"{detail} — which is why the collision must be prevented, not detected",
        )

        print("\nKNOWN LIMIT: an unkeyed chain can be rebuilt wholesale")
        # Not a bug report — an asserted limit. FINDINGS_2026-08-14_token_leak.md
        # part 6.9. _digest is plain sha256 with no secret, so anyone who can
        # write the file can recompute a consistent chain. An HMAC would close
        # this; until one exists, this test documents that it does not.
        rows = [json.loads(line) for line in good.open()]
        rows[2]["decision"] = "DENY"
        prev = "0" * 64
        for row in rows:
            row.pop("hash", None)
            row["prev"] = prev
            payload = json.dumps(
                {k: v for k, v in row.items() if k != "hash"},
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            row["hash"] = hashlib.sha256((prev + payload).encode()).hexdigest()
            prev = row["hash"]
        rebuilt = root / "rebuilt.jsonl"
        rebuilt.write_text("".join(json.dumps(r) + "\n" for r in rows))
        ok, _ = AuditLog.verify(rebuilt)
        check(
            "rebuilt chain still verifies (limit, not a pass)",
            ok,
            "unkeyed digest — an HMAC would close this",
        )

    print()
    if _failures:
        print(f"{_failures} failure(s)")
        return 1
    print("all audit log tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
