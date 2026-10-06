#!/usr/bin/env python3
"""Fetch a corpus of community integrations, for the API-surface measurement.

`api_surface.py` measured the integrations shipped with Home Assistant. Those are not the
population this project targets — §5.6.1 and §5.9.1 both carry that limitation explicitly.
This script assembles the corpus that removes it.

**Sampling, and there are two of them.** By default community integrations are sampled by
*install count*. The argument §5.10 needs is about what confinement would break in practice,
and breaking an integration on 40,000 installations is not equivalent to breaking one on
twelve. §1.3 records a long tail whose median integration has 20 installs; an install-weighted
sample answers **"what do most installations run?"**

That is one question and not the only one. `--uniform SEED` draws instead from the whole index
with equal probability, which answers **"what do most integrations do?"** — the population a
claim about the *ecosystem* is really about. §7.9 records the install-weighted corpus as a
threat to external validity for exactly this reason, and §7.23 is the arm that measures it
rather than continuing to caveat it.

The seed is required rather than defaulted, and it is recorded in the manifest, because a
sample nobody can redraw is not reproducible and a seed chosen after seeing a result is not a
sample.

**Sources.**
  - `https://data-v2.hacs.xyz/integration/data.json` — HACS's own index: 3,000+ repositories
    with their GitHub `full_name` and declared `domain`.
  - `custom_integrations.json` — Home Assistant's opt-in analytics, already used by
    `ecosystem_scale.py` for every install figure in Chapter 1.

Matching the two on `domain` gives repositories ordered by how many people actually run them.

**Reproducibility.** Every repository fetched is recorded in the output manifest with the
commit it was fetched at, and `--rebuild` fetches a manifest's repositories at those commits, so
the corpus can be rebuilt exactly. The source itself is not committed: it is several hundred
megabytes of third-party code, and the manifest plus this script is what makes the measurement
checkable.

*Until 2026-10-06 this paragraph said the same and was false (finding F21): the manifest recorded
`"ref": "HEAD"`, the name and not the commit it resolved to. The two corpora Chapter 7 measured were
pinned afterwards by matching the Pi's copies against each repository's history
(`verify/pin_corpus.py`). A fetch now resolves the commit first and downloads that commit.*

Run:  python3 fetch_hacs_corpus.py --top 150 --out /path/to/corpus
      python3 fetch_hacs_corpus.py --rebuild MANIFEST --out /path/to/corpus
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import io
import json
import random
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
HACS_INDEX = "https://data-v2.hacs.xyz/integration/data.json"
ANALYTICS = HERE / "custom_integrations.json"
UA = {"User-Agent": "capstone-api-surface-measurement/1.0"}


def get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def candidates(top: int, uniform_seed: int | None = None) -> list[dict]:
    index = json.loads(get(HACS_INDEX))
    # Same shape ecosystem_scale.py reads: {domain: {"total": n, "versions": {...}}}.
    installs = {domain: entry.get("total", 0)
                for domain, entry in json.loads(ANALYTICS.read_text()).items()}

    rows = []
    for entry in index.values():
        domain, full = entry.get("domain"), entry.get("full_name")
        if not domain or not full:
            continue
        rows.append({
            "domain": domain,
            "repo": full,
            # Analytics install count where the domain is reported; HACS's own download
            # count otherwise, marked so the two are never silently mixed.
            "installs": installs.get(domain, 0),
            "hacs_downloads": entry.get("downloads", 0),
            "source": "analytics" if domain in installs else "hacs_downloads",
        })
    if uniform_seed is not None:
        # Every integration in the index has the same chance of selection, whatever anyone
        # runs. Sorting first makes the draw depend on the seed alone rather than on the
        # order the index happened to arrive in, which is not stable between fetches.
        rows.sort(key=lambda r: r["domain"])
        return random.Random(uniform_seed).sample(rows, min(top, len(rows)))
    rows.sort(key=lambda r: (r["installs"], r["hacs_downloads"]), reverse=True)
    return rows[:top]


def resolve(repo: str) -> str | None:
    """The commit the repository's default branch points at now, or None."""
    try:
        out = subprocess.run(["git", "ls-remote", f"https://github.com/{repo}.git", "HEAD"],
                             check=True, capture_output=True, text=True, timeout=60).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return out.split()[0] if out.strip() else None


def fetch_one(row: dict, out: Path) -> dict:
    """Download a repository tarball at one commit and extract just its integration directory.

    The commit is `row["commit"]` when rebuilding, and otherwise the default branch's, resolved
    before the download so that what is recorded is what was fetched.
    """
    repo = row["repo"]
    commit = row.get("commit") or resolve(repo)
    if commit is None:
        return {**row, "ok": False, "reason": "could not resolve the default branch"}
    for ref in (commit,):
        url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
        try:
            blob = get(url, timeout=120)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            continue
        try:
            tf = tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz")
        except tarfile.TarError:
            continue

        # The integration lives at <root>/custom_components/<domain>/ in the common
        # layout; some repositories put it at the top level instead.
        names = tf.getnames()
        root = names[0].split("/")[0] if names else ""
        wanted = f"{root}/custom_components/{row['domain']}/"
        members = [m for m in tf.getmembers() if m.name.startswith(wanted)]
        layout = "custom_components"
        if not members:
            wanted = f"{root}/{row['domain']}/"
            members = [m for m in tf.getmembers() if m.name.startswith(wanted)]
            layout = "toplevel"
        if not members:
            return {**row, "ok": False, "reason": "integration directory not found"}

        dest = out / row["domain"]
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        py = 0
        for m in members:
            if not m.isfile():
                continue
            rel = Path(m.name[len(wanted):])
            if rel.is_absolute() or ".." in rel.parts:   # never trust a tar path
                continue
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            extracted = tf.extractfile(m)
            if extracted is None:
                continue
            target.write_bytes(extracted.read())
            py += rel.suffix == ".py"
        return {**row, "ok": True, "commit": commit, "layout": layout, "py_files": py}
    return {**row, "ok": False, "reason": "could not download any ref"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=150)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=HERE / "hacs_corpus_manifest.json")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--uniform", type=int, default=None, metavar="SEED",
                    help="draw uniformly from the whole HACS index with this seed, instead "
                         "of taking the top by install count (§7.23). The seed is recorded "
                         "in the manifest so the sample can be redrawn exactly")
    ap.add_argument("--rebuild", type=Path, default=None, metavar="MANIFEST",
                    help="fetch exactly the repositories a manifest lists, at the commits it "
                         "records, into --out; writes no manifest")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    if args.rebuild is not None:
        listed = json.loads(args.rebuild.read_text())["repositories"]
        rows = [r for r in listed if r.get("commit")]
        print(f"rebuilding {len(rows)} of {len(listed)} repositories at their recorded commits")
        failed = 0
        for row in rows:
            res = fetch_one({k: row[k] for k in ("domain", "repo", "commit")}, args.out)
            failed += not res["ok"]
            print(f"  {'ok ' if res['ok'] else 'FAIL'} {row['domain']:<28} {row['commit'][:12]}")
        return 1 if failed else 0
    rows = candidates(args.top, args.uniform)
    if args.uniform is None:
        print(f"selected {len(rows)} community integrations by install count")
    else:
        median = sorted(r["installs"] for r in rows)[len(rows) // 2]
        print(f"selected {len(rows)} community integrations uniformly at random, "
              f"seed {args.uniform}")
        print(f"  median install count of the draw: {median}")

    done: list[dict] = []
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, res in enumerate(pool.map(lambda r: fetch_one(r, args.out), rows), 1):
            done.append(res)
            flag = "ok " if res["ok"] else "FAIL"
            print(f"  [{i:>3}/{len(rows)}] {flag} {res['domain']:<28} "
                  f"{res['repo']:<44} {res.get('py_files', res.get('reason', ''))}")

    ok = [d for d in done if d["ok"]]
    print(f"\nfetched {len(ok)}/{len(done)}; {sum(d['py_files'] for d in ok)} python files")
    args.manifest.write_text(json.dumps({
        "source_index": HACS_INDEX,
        "selection": ("top by Home Assistant analytics install count, HACS downloads as "
                      "tiebreak") if args.uniform is None else
                     f"uniform random draw from the whole index, seed {args.uniform}",
        "uniform_seed": args.uniform,
        "requested": args.top,
        "fetched": len(ok),
        "repositories": done,
    }, indent=2) + "\n")
    print(f"wrote {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
