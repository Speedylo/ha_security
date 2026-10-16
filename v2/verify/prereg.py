#!/usr/bin/env python3
"""Verification 4.8: was every prediction committed before its results, and left alone after?

For each `notes/*prediction*.md`:
  order     the commit that added the note is an ancestor of, and older than, the first commit
            holding any of its results. Results are found by the paths the note names, or, for a
            note that names none, by the commit recorded in RESULTS below (read from the log, and
            each checked by hand against the Pi's file times where the gap was short).
  untouched every line the note had just before its results were committed is still in it, word
            for word. Adding text after results (outcomes, dated corrections) is allowed; changing
            or deleting a line that was there is not. Each changed line is printed with the
            commit that changed it, for a reader to judge.

Run from v2/:  python3 verify/prereg.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

#: Notes that name no result path: the commit that first committed their results.
RESULTS = {
    "ch7_31_compat_rerun": "54e97e4", "ch7_31_egress_shape_rerun": "1f63011",
    "ch7_31_endtoend": "5239f9f", "ch7_31_remaining_rerun": "7b8f4d2",
    "ch7_uniform": "dea5ffe", "item12_footprint_rerun": "e9ec2b1",
    "t3_credentialed": "5773839", "t4_auditlog_wiring": "04a31db",
    "t5_api_surface_uniform": "c38244b",
    # Its results directory also holds the fuzz output that *found* F33, committed before the
    # note on purpose: that is the evidence the note is about, not a result it predicts. The
    # first result it predicts is F34's failing-first run.
    "review_fixes": "1733e0c",
    # Its §0 cites the 2026-10-03 rerun's results as the evidence it starts from, which the path
    # search took for its own (a result five days before the note). Its first result is the
    # recorded run at retest-2026-10-e2e.
    "e2e_functional_retest": "bd81f9c",
    # The same: it cites F54's regression as the run that found it.
    "f56_port": "a7943de",
    # Added 2026-10-15 (notes/prereg_coverage_prediction.md): notes that name no result path and
    # were reported UNCHECKED, or that the old glob missed. Each is the first commit after the note
    # touching experiments/*/results, its message read to confirm it reports that note's work.
    "f08_t06": "7271291", "minor_findings": "aa072c2", "final_pass": "d739e77",
    "f48_f49": "b22c306",
    # Added 2026-10-16 after the final rerun's step 13: each cites an older results path (the bare
    # verify results directory; item12_20261003/depth.sh, re-issued by step 11), which the path
    # search took for its own. Their first results are step 1's run and F61's laptop run.
    "final_rerun": "0c771fa", "f61_fault_harness_approval": "c41eafd",
}
#: The checks registered without results of their own yet, or registered for this campaign.
SKIP = {"integrity_consistency"}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def first_commit(path: str) -> str | None:
    out = git("log", "--format=%H", "--diff-filter=A", "--", path).split()
    return out[-1] if out else None


def first_result(paths: list[str]) -> str | None:
    commits = []
    for p in paths:
        out = git("log", "--format=%H %ct", "--", p).split("\n")
        commits += [line.split() for line in out if line]
    if not commits:
        return None
    return min(commits, key=lambda c: int(c[1]))[0]


def main() -> int:
    bad = 0
    # The glob also takes notes with a date after "prediction" (f48_f49_prediction_20261007.md).
    for note in sorted(Path("notes").glob("*prediction*.md")):
        name = note.name.split("_prediction")[0]
        if name in SKIP:
            continue
        added = first_commit(str(note))
        paths = sorted({p.rstrip("/.") for p in re.findall(r"experiments/[A-Za-z0-9_./-]+",
                                                            note.read_text())
                        if "results" in p})
        result = RESULTS.get(name) or first_result(paths)
        if result is None:
            print(f"UNCHECKED  {name}: no result path named and none recorded")
            continue
        result = git("rev-parse", result).strip()
        ordered = added != result and subprocess.run(
            ["git", "merge-base", "--is-ancestor", added, result]).returncode == 0
        t_added, t_result = (int(git("log", "-1", "--format=%ct", c)) for c in (added, result))
        before = git("show", f"{result}^:v2/{note}") if ordered else ""
        now = note.read_text().splitlines()
        missing = [line for line in before.splitlines() if line.strip() and line not in now]
        verdict = "ok" if ordered and not missing else "CHECK"
        bad += verdict != "ok"
        print(f"{verdict:<10} {name}: note {added[:7]} → results {result[:7]} "
              f"(+{(t_result - t_added) / 60:.0f} min); {len(missing)} prediction line(s) "
              f"changed after")
        for line in missing[:6]:
            changer = git("log", "--format=%h %cs", "-S", line[:60], "--", str(note)).split("\n")[0]
            print(f"           - {line[:110]}  [last touched {changer}]")
    print(f"\n{bad} note(s) to look at")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
