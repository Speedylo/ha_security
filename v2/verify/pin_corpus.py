#!/usr/bin/env python3
"""F21: recover the commit each corpus integration was fetched at, by matching file contents.

`figures/fetch_hacs_corpus.py` recorded `"ref": "HEAD"` for every repository, not the commit HEAD
resolved to, so neither corpus can be rebuilt from its manifest. The copies on the Pi are the only
record. This finds, for each repository, the commit whose integration directory holds exactly the
same files with exactly the same contents as the Pi's copy.

**How a match is decided.** The fetcher kept regular files only and wrote them without their modes,
so a git *tree* hash cannot match. File contents can: for every file the Pi holds, its git blob hash
(`sha1("blob <size>\\0" + bytes)`), keyed by path. For each commit that changed the integration's
directory, `git ls-tree -r` lists the same pairs without downloading any file, from a blobless clone.
A match is the two sets being equal. Nothing is approximated: a near miss is reported as a miss,
with its counts. `__pycache__` is excluded on the Pi's side, because earlier runs wrote it there and
no repository in either corpus ships one.

Run on the Pi:
    python3 pin_corpus.py --manifest hacs_corpus_manifest.json --corpus ~/r2exp/corpus \
        --work ~/r2exp/f21/clones --json pinned_head.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def on_disk(directory: Path) -> dict[str, str]:
    """{relative path: blob hash} for every regular file, `__pycache__` excluded."""
    files = {}
    for path in sorted(directory.rglob("*")):
        rel = path.relative_to(directory)
        if "__pycache__" in rel.parts or not path.is_file() or path.is_symlink():
            continue
        files[rel.as_posix()] = blob_sha(path.read_bytes())
    return files


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


def at_commit(repo: Path, commit: str, prefix: str) -> dict[str, str]:
    """{path relative to prefix: blob hash} for the regular files under prefix at commit."""
    files = {}
    for line in git(repo, "ls-tree", "-r", commit, "--", prefix + "/").splitlines():
        meta, path = line.split("\t", 1)
        mode, kind, sha = meta.split()
        if kind == "blob" and mode in ("100644", "100755"):
            files[path[len(prefix) + 1:]] = sha
    return files


def pin(row: dict, corpus: Path, work: Path) -> dict:
    repo, domain = row["repo"], row["domain"]
    result = {"domain": domain, "repo": repo}
    directory = corpus / domain
    if not directory.is_dir():
        return {**result, "status": "not on disk"}
    disk = on_disk(directory)
    clone = work / repo.replace("/", "__")
    if not clone.exists():
        try:
            subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none",
                            f"https://github.com/{repo}.git", str(clone)],
                           check=True, capture_output=True, text=True, timeout=600)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as err:
            return {**result, "status": "clone failed", "detail": str(err)[:300]}
    prefix = f"custom_components/{domain}" if row.get("layout") != "toplevel" else domain
    commits = git(clone, "rev-list", "--format=%H %cI", "--no-commit-header", "HEAD",
                  "--", prefix + "/").split()
    pairs = list(zip(commits[0::2], commits[1::2]))
    matches, nearest = [], None
    for commit, date in pairs:
        there = at_commit(clone, commit, prefix)
        if there == disk:
            matches.append({"commit": commit, "date": date})
            continue
        missing = sorted(set(there) - set(disk))
        extra = sorted(set(disk) - set(there))
        changed = sorted(p for p in set(disk) & set(there) if disk[p] != there[p])
        score = len(missing) + len(extra) + len(changed)
        if nearest is None or score < nearest["differences"]:
            nearest = {"commit": commit, "date": date, "differences": score,
                       "missing_on_disk": missing[:10], "extra_on_disk": extra[:10],
                       "changed": changed[:10]}
    result.update(files=len(disk), commits_examined=len(pairs))
    if matches:
        return {**result, "status": "pinned", "matches": matches}
    return {**result, "status": "no exact match", "nearest": nearest}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--json", type=Path, required=True)
    args = ap.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(args.manifest.read_text())
    rows = [r for r in manifest["repositories"] if r.get("ok")]
    results = []
    for row in rows:
        r = pin(row, args.corpus, args.work)
        results.append(r)
        print(f"{r['status']:<15} {r['domain']:<28} {r['repo']}", flush=True)
    summary = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    args.json.write_text(json.dumps({"manifest": args.manifest.name, "corpus": str(args.corpus),
                                     "summary": summary, "results": results}, indent=1))
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
