#!/usr/bin/env python3
"""Tier C: give every extracted candidate a disposition (verification plan §3).

Rules, applied in order; the first that matches decides:

  structure  front matter that describes the report, not the work (contents, tables, glossary)
  history    a dated past state the report keeps on purpose: "Original text", "Run 2026-…",
             "until 2026-…", "was … corrected", and §7.21/§7.26/§7.28's read-through narrative
  B §7.n     a Chapter 7 candidate is covered by the Tier B row for its own section: re-running
             that measurement and re-deriving its numbers (plan §7.1) tests every figure in it
  ref §x     a candidate outside Chapter 7 that cites a §7.n section is covered by that row
  review     everything else: read by a person, and either mapped, made a Tier C row, or dropped

Run from v2/:  python3 verify/triage_claims.py   (reads verify/candidates.jsonl)
"""

from __future__ import annotations

import collections
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TIER_B = {f"7.{n}" for n in range(12, 45)}
READING = {"7.21", "7.26", "7.28"}
STRUCTURE = re.compile(r"^(Contents|Tables|Figures|Abbreviations|Declaration|Outstanding|"
                       r"Acknowledg|A Declared-Authority)", re.I)
HISTORY = re.compile(r"Original text|\bRun 2026-|\buntil 2026-|\bwas (?:wrong|false|corrected)|"
                     r"\bwithdrawn\b|\bsuperseded\b|\bbefore the fix\b|\bstale\b", re.I)
SECTION = re.compile(r"§\s?(7\.\d+)")


#: Second pass, after reading (2026-10-05): every subsection outside Chapter 7's results goes to the
#: Tier A row or Tier C group that tests it. Design rationale no test can check is "argued", checked
#: only for wording (plan §7.9).
GROUPS = {
    "Abstract": "A1", "The artifact": "C16",
    "5.1": "argued", "5.2": "argued", "5.3": "argued", "5.4": "argued", "5.5": "argued",
    "5.8": "argued", "5.6": "C01", "5.7": "C02", "5.9": "C03", "5.10": "C03", "5.11": "C04",
    "5.12": "C05", "5.13": "C06", "5.14": "C07", "5.15": "C08",
    "6.1": "argued", "6.2": "argued", "6.3": "C02", "6.4": "C02", "6.5": "C04", "6.6": "C03",
    "6.7": "C03", "6.8": "C05", "6.9": "C06", "6.10": "C09", "6.11": "C13", "6.12": "C10",
    "6.13": "C11", "6.14": "C11",
    "7.1": "C12", "7.2": "C12", "7.3": "C12", "7.4": "C12", "7.5": "A2", "7.6": "A1.32",
    "7.7": "A5", "7.8": "C12", "7.9": "C12", "7.10": "C12", "7.11": "C12",
    "8.1": "argued", "8.2": "A5", "8.3": "A5", "8.4": "A1.32", "8.5": "C14", "8.6": "C13",
    "8.7": "C13", "8.8": "C15", "8.9": "A5",
}
#: Claims from Chapters 5 and 6 that get a row of their own (`claims_register.md`, Tier C), by id.
SINGLE = {
    "K0262": "CS01", "K0266": "CS02", "K0289": "CS02", "K0498": "CS02", "K0499": "CS02",
    "K0273": "CS03", "K0484": "CS03", "K0277": "CS04", "K0283": "CS05", "K0290": "CS06",
    "K0291": "CS07", "K0292": "CS07", "K0294": "CS08", "K0539": "CS08", "K0458": "CS09",
    "K0465": "CS10", "K0467": "CS11", "K0488": "CS12", "K0533": "CS13", "K0535": "CS13",
    "K0564": "CS14", "K0421": "CS15", "K0431": "CS16", "K0432": "CS16",
}


def disposition(row: dict) -> str:
    if row["id"] in SINGLE:
        return SINGLE[row["id"]]
    first = _first_pass(row)
    if first != "review":
        return first
    m = re.match(r"(\d\.\d+)", row["section"])
    key = m.group(1) if m else row["section"]
    if key in GROUPS:
        return GROUPS[key]
    # Unnumbered sub-headings inside Chapter 7's results belong to the section around them.
    return "B context" if row["file"] == "07_evaluation.md" else "review"


def _first_pass(row: dict) -> str:
    section, text = row["section"], row["text"]
    if row["file"] == "00_front_matter.md" and STRUCTURE.match(section):
        return "structure"
    top = re.match(r"(7\.\d+)", section)
    if HISTORY.search(text):
        return "history"
    if row["file"] == "07_evaluation.md" and top:
        if top.group(1) in READING:
            return "history"
        if top.group(1) in TIER_B:
            return f"B {top.group(1)}"
    cited = [s for s in SECTION.findall(text) if s in TIER_B]
    if cited:
        return f"ref {cited[0]}"
    return "review"


def main() -> int:
    rows = [json.loads(line) for line in (HERE / "candidates.jsonl").read_text().splitlines()]
    tally = collections.Counter()
    by_file = collections.defaultdict(collections.Counter)
    for row in rows:
        row["disposition"] = d = disposition(row)
        kind = d.split()[0] if d.startswith(("B ", "ref ")) else d.split(".")[0] if d.startswith("A") else d
        tally[kind] += 1
        by_file[row["file"]][kind] += 1
    (HERE / "triage.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    print(f"{len(rows)} candidates: " + ", ".join(f"{k} {v}" for k, v in tally.most_common()))
    for name, counts in by_file.items():
        print(f"  {name:<24} " + ", ".join(f"{k} {v}" for k, v in counts.most_common()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
