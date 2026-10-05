#!/usr/bin/env python3
"""Pull candidate claims out of the report, for the claim register (verification plan §3).

A candidate is a sentence or a table row that states a figure, carries a verdict mark, or makes a
universal statement ("every", "never", "all", "no …"). Each one is tagged with its file, the
nearest heading, and its line, so a person can accept, merge or discard it with the source in view.
This finds candidates; it decides nothing. Deciding is the register's job.

Run from v2/:  python3 verify/extract_claims.py [--json verify/candidates.jsonl]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPORT = Path(__file__).resolve().parent.parent / "report"
FILES = ["00_front_matter.md", "05_architecture.md", "06_implementation.md", "07_evaluation.md",
         "08_conclusions.md"]

FIGURE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|µs|ms|s\b|MB|GB|×|x\b|/\d+)|\b\d+\s+of\s+\d+\b"
                    r"|\b\d+/\d+\b|\b\d{2,}\b")
VERDICT = re.compile(r"[✅⚠✗⊘◐]|\b(?:Met|Demonstrated|Paired|Held|Wrong|Partial|Retained)\b")
UNIVERSAL = re.compile(r"\b(?:every|never|all|none|no)\b", re.I)
#: Lines that are history, not claims: dated pointers and struck-through text are tracked by the
#: claim they qualify, not as claims of their own.
SKIP = re.compile(r"^\s*(?:>|\*\(|<!--)|~~")
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z*(])")


def kinds(text: str) -> list[str]:
    found = []
    if FIGURE.search(text):
        found.append("figure")
    if VERDICT.search(text):
        found.append("verdict")
    if UNIVERSAL.search(text):
        found.append("universal")
    return found


def candidates(path: Path):
    heading = ""
    in_code = False
    paragraph: list[tuple[int, str]] = []

    def flush():
        if not paragraph:
            return
        start = paragraph[0][0]
        text = " ".join(t.strip() for _, t in paragraph)
        for sentence in SENTENCE.split(text):
            if len(sentence) > 25 and (k := kinds(sentence)):
                yield {"file": path.name, "section": heading, "line": start,
                       "text": sentence.strip(), "kinds": k, "form": "prose"}
        paragraph.clear()

    for number, line in enumerate(path.read_text().splitlines(), 1):
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.startswith("#"):
            yield from flush()
            heading = line.lstrip("#").strip()
            continue
        if line.startswith("|"):
            yield from flush()
            if set(line) <= set("|-: ") or SKIP.search(line):
                continue
            if k := kinds(line):
                yield {"file": path.name, "section": heading, "line": number,
                       "text": line.strip(), "kinds": k, "form": "table"}
            continue
        if not line.strip():
            yield from flush()
            continue
        if SKIP.search(line):
            continue
        paragraph.append((number, line))
    yield from flush()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    rows = []
    for name in FILES:
        path = REPORT / name
        if path.exists():
            rows.extend(candidates(path))
    for index, row in enumerate(rows, 1):
        row["id"] = f"K{index:04d}"
    by_file: dict[str, int] = {}
    for row in rows:
        by_file[row["file"]] = by_file.get(row["file"], 0) + 1
    for name, count in by_file.items():
        print(f"  {name:<24} {count:>5}")
    print(f"  {'total':<24} {len(rows):>5}")
    if args.json:
        args.json.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
