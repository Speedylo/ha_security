#!/usr/bin/env python3
"""Golden-result comparison: a re-run against the committed result it must reproduce (plan §5, L4).

Nobody judges a re-run by eye. Both files are normalised the same way, then compared field by
field, and every difference is classified:

  exact     a string, boolean, entity, decision or verdict changed — a finding unless explained
  numeric   a number changed — reported with its relative size, judged against the register's
            criterion (E, T, M or L) for that row
  added / removed   a field present on one side only

**Normalised away, and why.** Fields that cannot repeat by design: timings and timestamps (judged
by the T criterion from their own measurement, not here), process and run identifiers, hash and
MAC chain values, sequence numbers, and temporary paths. Lists are compared as multisets, so a
change of order is not a difference; a change of content is.

Run from v2/:  python3 verify/compare.py OLD.json NEW.json [--json out.json]
Exit status: 0 if no exact difference, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

#: Keys whose values cannot repeat between runs. Matched against the key alone, case-insensitive.
VOLATILE = re.compile(
    r"(^|_)(seconds|secs|ms|us|ns|time|times|elapsed|latency|median|mean|p\d\d|max_ms|min_ms|"
    r"duration|started|finished|recorded|when|timestamp|t|pid|pids|run|run_id|hash|mac|prev_hash|"
    r"prev_mac|seq|key|nonce|token|expires|expires_at|created_at|port_ephemeral|inode)$", re.I)
#: Temporary paths differ every run; what is compared is that a path was there.
TMP = re.compile(r"(/tmp/|/home/[^/]+/r2exp/disktmp/)[^\s\"',;)]*")


def normalise(value):
    if isinstance(value, dict):
        return {k: normalise(v) for k, v in value.items() if not VOLATILE.search(str(k))}
    if isinstance(value, list):
        items = [normalise(v) for v in value]
        return sorted(items, key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False))
    if isinstance(value, str):
        return TMP.sub("<tmp>", value)
    return value


def compare(old, new, path: str, out: list[dict]) -> None:
    if isinstance(old, dict) and isinstance(new, dict):
        for key in sorted(set(old) | set(new)):
            sub = f"{path}.{key}" if path else str(key)
            if key not in new:
                out.append({"kind": "removed", "path": sub, "old": _short(old[key])})
            elif key not in old:
                out.append({"kind": "added", "path": sub, "new": _short(new[key])})
            else:
                compare(old[key], new[key], sub, out)
        return
    if isinstance(old, list) and isinstance(new, list):
        if all(not isinstance(v, (dict, list)) for v in old + new):
            gone = [v for v in old if v not in new]
            came = [v for v in new if v not in old]
            if gone or came or len(old) != len(new):
                out.append({"kind": "exact", "path": path, "old": _short(gone or len(old)),
                            "new": _short(came or len(new)), "note": "list content"})
            return
        key = _identity_key(old, new)
        if key:
            # Pair objects by what they are, not by where sorting put them: a subject whose
            # content changed must still be compared with itself.
            left = {str(v.get(key)): v for v in old}
            right = {str(v.get(key)): v for v in new}
            for name in sorted(set(left) | set(right)):
                sub = f"{path}[{key}={name}]"
                if name not in right:
                    out.append({"kind": "removed", "path": sub, "old": "present"})
                elif name not in left:
                    out.append({"kind": "added", "path": sub, "new": "present"})
                else:
                    compare(left[name], right[name], sub, out)
        elif len(old) == len(new):
            for index, (a, b) in enumerate(zip(old, new)):
                compare(a, b, f"{path}[{index}]", out)
        else:
            out.append({"kind": "exact", "path": path, "old": f"{len(old)} items",
                        "new": f"{len(new)} items", "note": "list length"})
        return
    if old == new:
        return
    numbers = (int, float)
    if isinstance(old, numbers) and isinstance(new, numbers) and not isinstance(old, bool) \
            and not isinstance(new, bool):
        base = abs(old) if old else 1.0
        out.append({"kind": "numeric", "path": path, "old": old, "new": new,
                    "relative": round((new - old) / base, 4)})
        return
    out.append({"kind": "exact", "path": path, "old": _short(old), "new": _short(new)})


def _identity_key(old: list, new: list) -> str | None:
    """The field that names each object, if every object has one and it is unique on each side.

    Unique *within* each file, so that two objects sharing a name can never be collapsed into
    one and a difference hidden; otherwise the list is compared by position after sorting.
    """
    items = old + new
    if not items or not all(isinstance(v, dict) for v in items):
        return None
    for key in ("domain", "integration", "subject", "entity", "entity_id", "id", "name"):
        if all(key in v for v in items) and all(
                len({str(v[key]) for v in side}) == len(side) for side in (old, new)):
            return key
    return None


def _short(value, limit: int = 160) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= limit else text[:limit] + "…"


def run(old_path: Path, new_path: Path) -> list[dict]:
    old = normalise(json.loads(old_path.read_text()))
    new = normalise(json.loads(new_path.read_text()))
    out: list[dict] = []
    compare(old, new, "", out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old", type=Path)
    ap.add_argument("new", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--quiet", action="store_true", help="the counts only")
    args = ap.parse_args()
    diffs = run(args.old, args.new)
    counts = {k: sum(1 for d in diffs if d["kind"] == k)
              for k in ("exact", "numeric", "added", "removed")}
    print(f"{args.new.name} against {args.old.name}: "
          + ", ".join(f"{k} {v}" for k, v in counts.items()))
    if not args.quiet:
        for d in diffs:
            extra = f"  ({d['relative']:+.1%})" if "relative" in d else ""
            print(f"  {d['kind']:<8} {d['path']}: {d.get('old', '')} → {d.get('new', '')}{extra}")
    if args.json:
        args.json.write_text(json.dumps({"old": str(args.old), "new": str(args.new),
                                         "counts": counts, "differences": diffs}, indent=2))
    return 1 if counts["exact"] else 0


if __name__ == "__main__":
    sys.exit(main())
