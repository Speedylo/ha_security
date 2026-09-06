"""Did the integration's own source survive the run? C1, counted rather than argued.

§7.4.1 stated that *"C1 is verified mechanically, not asserted — zero source lines changed,
counted by diffing each integration's tree against the fetched original after the run"*, and
§8.3 repeated it. Stage 5's second pass found that **no such count existed anywhere in the
project** and C1 was downgraded from *counted* to *argued* (§7.28). This module is §8.7 #4,
and running it is what converts the word the report's title rests on back into a count.

**The two arms need different things checked, and this is the part §7.28 says the criterion as
originally worded got wrong.**

    confined   `compat.py` runs a `shutil.copytree` of the integration, and `sandbox.py`
               bind-mounts that copy read-only. Diffing the *fetched original* afterwards
               therefore compares a tree nothing ever opened. What must be hashed is **the
               copy**, and a mismatch there is not a C1 finding at all — it is a containment
               failure, because a read-only mount held nothing.
    baseline   the fetched tree itself is passed by path into a full in-process Home Assistant
               with no copy and no mount (`compat.py`'s `component_dir`). **This is the arm
               that needs the check**, and it is the arm every compatibility figure in the
               report is measured against.

**Identity is not recomputed here, it is reused.** `audit.Identity.compute` is §5.12.1's
three-part tuple, already built to answer "did this integration's code change" for T12. Using
it for C1 as well means the report has one mechanism answering one question in two places,
rather than two mechanisms that could disagree. `changes_from` then says *which* of source,
manifest and requirements moved, which a single composite could not.

**`__pycache__` is reported, not ignored, and the distinction is the honest part.** The
baseline arm imports the integration from a tree it can write to, so CPython will drop
bytecode caches beside the source. That *is* a modification to the directory and it is *not* a
modification to the integration's source, so this module counts the two separately and names
both. `Identity.compute` already excludes `__pycache__` from the source hash — that exclusion
was a §5.12 decision, and stating it here is what stops it looking like one made to get a
convenient answer.

Run:  python3 -m confine.selftest_integrity
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path

from .audit import Identity, sha256_file

# Files whose presence or absence is a bytecode-cache artifact rather than a source change.
CACHE_PARTS = ("__pycache__",)


def _is_cache(relpath: str) -> bool:
    return any(part in CACHE_PARTS for part in Path(relpath).parts)


@dataclass(frozen=True)
class TreeState:
    """Everything needed to answer "did this change" and, if it did, "where".

    `identity` is the verdict and `files` is the diagnosis. Both are captured because a hash
    that says *something moved* and cannot say *what* is not enough to report a C1 violation
    against — and not enough to dismiss one either.
    """

    root: str
    identity: Identity
    files: dict[str, str] = field(default_factory=dict)
    content: dict[str, bytes] | None = None

    @classmethod
    def capture(cls, component_dir: Path, retain: bool = False) -> TreeState:
        """`retain` keeps the pre-run bytes so that a mismatch can be counted in lines.

        It is needed whenever the tree is compared against **itself after being written to**,
        which is the baseline arm: by the time the comparison runs, the original bytes are
        gone and no amount of re-reading recovers them. The confined arm compares a copy
        against a still-existing original and does not need it. Peak cost is one integration
        tree — 32 MB for the largest member of the head corpus, held for the length of one run.
        """
        component_dir = Path(component_dir)
        paths = sorted(p for p in component_dir.rglob("*") if p.is_file())
        files = {str(p.relative_to(component_dir)): sha256_file(p) for p in paths}
        content = None
        if retain:
            content = {}
            for path in paths:
                relpath = str(path.relative_to(component_dir))
                if not _is_cache(relpath):
                    content[relpath] = path.read_bytes()
        return cls(str(component_dir), Identity.compute(component_dir), files, content)


@dataclass(frozen=True)
class Comparison:
    """What moved between two captures, classified so that the verdict is not a judgement call.

    `source_changed` is the only field that bears on C1. The others exist so that a run which
    is *not* a violation cannot be reported as a clean one by silence — a tree that gained
    forty bytecode files is unmodified in C1's sense and it is not untouched, and the report
    should be able to say both.
    """

    modified: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    cache_added: list[str] = field(default_factory=list)
    cache_removed: list[str] = field(default_factory=list)
    components_changed: list[str] = field(default_factory=list)
    diff_lines: int = 0
    # Files whose hash moved and whose line count could not be established because the
    # pre-run bytes were neither retained nor still on disk. **Reported rather than counted
    # as zero** — §6.4.5 records that three defects in this project presented as an absence,
    # and a line count silently reading 0 because it had nothing to compare would be a fourth.
    lines_unknown: list[str] = field(default_factory=list)

    @property
    def source_changed(self) -> bool:
        """C1's verdict for one integration. Bytecode caches deliberately do not count."""
        return bool(self.modified or self.removed or self.added
                    or self.components_changed)

    def as_dict(self) -> dict:
        return {"source_changed": self.source_changed, "modified": self.modified,
                "removed": self.removed, "added": self.added,
                "cache_added": len(self.cache_added),
                "cache_removed": len(self.cache_removed),
                "components_changed": self.components_changed,
                "diff_lines": self.diff_lines, "lines_unknown": self.lines_unknown}


def compare(before: TreeState, after: TreeState, count_lines: bool = True) -> Comparison:
    """Classify the difference between two captures of the same tree.

    `count_lines` re-reads any file whose hash moved so that §7.5's criterion — a **zero-line**
    diff — is answered in the units it asks for rather than in hashes. It is only ever paid on
    a mismatch, which is expected to be never.
    """
    modified, removed, added, cache_added, cache_removed = [], [], [], [], []

    for relpath, digest in before.files.items():
        if relpath not in after.files:
            (cache_removed if _is_cache(relpath) else removed).append(relpath)
        elif after.files[relpath] != digest and not _is_cache(relpath):
            modified.append(relpath)
    for relpath in after.files:
        if relpath not in before.files:
            (cache_added if _is_cache(relpath) else added).append(relpath)

    diff_lines, lines_unknown = 0, []
    if count_lines:
        for relpath in modified:
            old = _before_bytes(before, after, relpath)
            new = _read(Path(after.root) / relpath)
            if old is None or new is None:
                lines_unknown.append(relpath)
            else:
                diff_lines += _line_delta(old, new)

    return Comparison(sorted(modified), sorted(removed), sorted(added),
                      sorted(cache_added), sorted(cache_removed),
                      after.identity.changes_from(before.identity), diff_lines,
                      sorted(lines_unknown))


def _before_bytes(before: TreeState, after: TreeState, relpath: str) -> bytes | None:
    """The pre-run bytes, if they can be had honestly.

    Retained content first; failing that, the original file — but **only when the two captures
    are of different directories**. When they are the same directory the file on disk is the
    post-run version, and reading it would compare a file against itself and report a
    reassuring zero.
    """
    if before.content is not None and relpath in before.content:
        return before.content[relpath]
    if before.root != after.root:
        return _read(Path(before.root) / relpath)
    return None


def _read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def _line_delta(before: bytes, after: bytes) -> int:
    """Lines a unified diff would show as added or removed. Undecodable files count as one."""
    try:
        old = before.decode().splitlines(keepends=True)
        new = after.decode().splitlines(keepends=True)
    except UnicodeDecodeError:
        return 1
    # `n=0` drops context, so every remaining +/- line is a changed one. The `+++`/`---`
    # file headers are the only other lines that start with those characters.
    return sum(1 for line in difflib.unified_diff(old, new, n=0)
               if line[:1] in "+-" and line[:3] not in ("+++", "---"))


def summarise(results: list[dict]) -> dict:
    """The count §7.5's C1 row asks for, over a whole run."""
    checked = [r for r in results if r.get("integrity")]
    violations = [r for r in checked if r["integrity"]["source_changed"]]
    return {
        "integrations_checked": len(checked),
        "source_changed": len(violations),
        "total_diff_lines": sum(r["integrity"]["diff_lines"] for r in checked),
        "lines_unknown": sum(len(r["integrity"]["lines_unknown"]) for r in checked),
        "trees_gaining_bytecode": sum(1 for r in checked
                                      if r["integrity"]["cache_added"]),
        "domains_with_changes": sorted(r["domain"] for r in violations),
    }
