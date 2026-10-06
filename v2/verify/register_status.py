#!/usr/bin/env python3
"""Write the campaign's outcome into the claim register: one status per row (exit criterion 1).

The statuses live in one table here, so that each is a reviewable line with its evidence. Tier A rows
already have a Status cell, which is overwritten; the Tier B, C and CS tables gain one. Running it
twice gives the same file.

Run from v2/:  python3 verify/register_status.py STATUSES.py
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

REGISTER = Path("verify/claims_register.md")


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def row(values: list[str]) -> str:
    return "| " + " | ".join(values) + " |"


def main() -> int:
    table = runpy.run_path(sys.argv[1])
    a, b, c, cs = table["A"], table["B"], table["C"], table["CS"]
    lines = REGISTER.read_text().split("\n")
    out, header, status_at, adding, done = [], None, None, False, set()
    for line in lines:
        if not line.startswith("|"):
            header, status_at, adding = None, None, False
            out.append(line)
            continue
        parts = cells(line)
        if header is None:
            header = parts
            status_at = header.index("Status") if "Status" in header else None
            first = parts[0]
            adding = status_at is None and (
                (first == "§" and "Claim (headline)" in parts)
                or (first == "Group" and "What its claims say" in parts)
                or (first == "ID" and "Claim" in parts and "Where" in parts))
            out.append(row(parts + ["Status"]) if adding else line)
            continue
        if set(line.replace("|", "").strip()) <= {"-", " "}:
            out.append(row(parts + ["---"]) if adding else line)
            continue
        key = parts[0]
        if status_at is not None and key in a:
            parts[status_at] = a[key]
            done.add(key)
            out.append(row(parts))
        elif adding:
            value = (b if header[0] == "§" else c if header[0] == "Group" else cs).get(key)
            if value is None and key in parts[-1:]:
                value = None
            if value is not None:
                done.add(key)
            # re-runs: if the row already ends with a status cell from a previous run, replace it
            out.append(row(parts + [value or "—"]))
        else:
            out.append(line)
    REGISTER.write_text("\n".join(out))
    missing = sorted((set(a) | set(b) | set(c) | set(cs)) - done)
    print(f"{len(done)} rows given a status; not found: {sorted(missing)}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
