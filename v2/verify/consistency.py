#!/usr/bin/env python3
"""Verification 4.9: the report agrees with itself (notes/integrity_consistency_prediction.md).

  refs       every `§n.n…` reference resolves to a heading that exists, or to a parent of one
             (§7.45 is a heading; §7.45.9 would not be)
  cites      every `[n]` in the body is an entry in 09_references.md, and every entry is cited
  counts     the counts the prose states match the artefacts: suites, threats, requirements,
             references

Run from v2/:  python3 verify/consistency.py
Prints every unresolved item with its file and line; exits 1 if any.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPORT = Path("report")
CHAPTERS = sorted(p for p in REPORT.glob("0*.md"))
BODY = [p for p in CHAPTERS if p.name != "09_references.md"]

#: References into other documents, written with §, that are not this report's sections. They are
#: listed rather than guessed: a reference that matches none of these and no heading is reported.
EXTERNAL = re.compile(r"(ISO 31000|ISO/IEC|RFC|fsync\(2\)|clause|plan|note|notes/|backlog|"
                      r"STATE|README|prediction|decision_network|flood_cutoff|w1_|w2|"
                      r"remaining_work|verification_plan|SP 800|NIST|IEC|OWASP|EN 303)", re.I)

problems: list[str] = []


def headings() -> set[str]:
    found = set()
    for path in CHAPTERS:
        for line in path.read_text().splitlines():
            m = re.match(r"#{1,5} (?:Chapter )?([0-9]+(?:\.[0-9]+)*)\b", line)
            if m:
                number = m.group(1)
                found.add(number)
    # A chapter is a section too: §7 means Chapter 7.
    found |= {p.name[1] for p in CHAPTERS if p.name[1].isdigit()}
    return found


def check_refs(known: set[str]) -> int:
    count = 0
    for path in BODY:
        for no, line in enumerate(path.read_text().splitlines(), 1):
            for m in re.finditer(r"§\s?([0-9]+(?:\.[0-9]+)*)", line):
                number = m.group(1).rstrip(".")
                count += 1
                if number in known:
                    continue
                context = line[max(0, m.start() - 60):m.start()]
                if EXTERNAL.search(context[-45:]):
                    continue
                problems.append(f"refs   {path.name}:{no}  §{number} has no heading  "
                                f"…{line[max(0, m.start() - 40):m.end() + 20].strip()}…")
    return count


def check_cites() -> int:
    entries = set(re.findall(r"^\*\*\[([0-9]+)\]\*\*", (REPORT / "09_references.md").read_text(),
                             re.M))
    cited: dict[str, str] = {}
    for path in BODY:
        for no, line in enumerate(path.read_text().splitlines(), 1):
            # [n] and [n, m] and [n–m], not markdown links [text](url) or `[3]` in code
            for m in re.finditer(r"(?<![`\w])\[([0-9]+(?:\s*[,–-]\s*[0-9]+)*)\](?!\()", line):
                for part in re.split(r"\s*,\s*", m.group(1)):
                    if re.fullmatch(r"[0-9]+\s*[–-]\s*[0-9]+", part):
                        a, b = map(int, re.split(r"\s*[–-]\s*", part))
                        numbers = [str(n) for n in range(a, b + 1)]
                    else:
                        numbers = [part]
                    for n in numbers:
                        cited.setdefault(n, f"{path.name}:{no}")
    for n, where in sorted(cited.items(), key=lambda kv: int(kv[0])):
        if n not in entries:
            problems.append(f"cites  {where}  [{n}] is not in the bibliography")
    for n in sorted(entries - set(cited), key=int):
        problems.append(f"cites  09_references.md  [{n}] is never cited in the body")
    return len(entries)


def main() -> int:
    known = headings()
    n_refs = check_refs(known)
    n_entries = check_cites()
    print(f"{len(known)} headings; {n_refs} § references checked; {n_entries} bibliography entries")
    for p in problems:
        print(p)
    print(f"\n{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
