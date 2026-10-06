#!/usr/bin/env python3
"""F07's check: every Chapter 7 results section is named by some experiment README.

A results section is a `## 7.n` heading from §7.12 on (§7.1–§7.11 are the plan, written before any
result). A README names it with `§7.n`. Sections that report no data of their own are listed in
NOT_RESULTS with the reason, so the exemption is visible rather than silent.

Run from v2/:  python3 verify/readme_coverage.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

NOT_RESULTS = {
    "7.21": "a reading pass, the chapter against Chapter 6; what it found, §7.22 measured",
    "7.26": "a read-through scoring the two registers against earlier sections",
    "7.28": "the whole-report read-through; the requirement it found unmeasured, §7.29 measures",
}


def main() -> int:
    chapter = Path("report/07_evaluation.md").read_text()
    sections = [m.group(1) for m in re.finditer(r"^## (7\.(\d+))\b", chapter, re.M)
                if int(m.group(2)) >= 12]
    named = set()
    for readme in Path("experiments").rglob("README.md"):
        named |= set(re.findall(r"§(7\.\d+)(?![\d])", readme.read_text()))
    missing = [s for s in sections if s not in named and s not in NOT_RESULTS]
    for s in sections:
        mark = "ok  " if s in named else ("n/a " if s in NOT_RESULTS else "MISS")
        print(f"  {mark} §{s}  {NOT_RESULTS.get(s, '')}")
    print(f"\n{len(sections)} results sections; {len(missing)} named by no README: {missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
