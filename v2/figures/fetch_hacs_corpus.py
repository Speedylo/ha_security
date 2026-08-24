#!/usr/bin/env python3
"""Fetch a corpus of community integrations, for the API-surface measurement.

`api_surface.py` measured the integrations shipped with Home Assistant. Those are not the
population this project targets — §5.6.1 and §5.9.1 both carry that limitation explicitly.
This script assembles the corpus that removes it.

**Sampling.** Community integrations are sampled by *install count*, not at random. The
argument §5.10 needs is about what confinement would break in practice, and breaking an
integration on 40,000 installations is not equivalent to breaking one on twelve. §1.3
records a long tail whose median integration has 20 installs; a uniform sample would be
dominated by it and would describe a population almost nobody runs. Both views matter and
the limitation of this one is stated in the write-up.

**Sources.**
  - `https://data-v2.hacs.xyz/integration/data.json` — HACS's own index: 3,000+ repositories
    with their GitHub `full_name` and declared `domain`.
  - `custom_integrations.json` — Home Assistant's opt-in analytics, already used by
    `ecosystem_scale.py` for every install figure in Chapter 1.

Matching the two on `domain` gives repositories ordered by how many people actually run them.

**Reproducibility.** Every repository fetched is recorded in the output manifest with its
resolved commit, so the corpus can be rebuilt exactly. The source itself is not committed:
it is several hundred megabytes of third-party code, and the manifest plus this script is
what makes the measurement checkable.

Run:  python3 fetch_hacs_corpus.py --top 150 --out /path/to/corpus
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import io
import json
import shutil
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


def candidates(top: int) -> list[dict]:
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
    rows.sort(key=lambda r: (r["installs"], r["hacs_downloads"]), reverse=True)
    return rows[:top]


def fetch_one(row: dict, out: Path) -> dict:
    """Download a repository tarball and extract just its integration directory."""
    repo = row["repo"]
    for ref in ("HEAD", "main", "master"):
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
        return {**row, "ok": True, "ref": ref, "layout": layout, "py_files": py}
    return {**row, "ok": False, "reason": "could not download any ref"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=150)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=HERE / "hacs_corpus_manifest.json")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rows = candidates(args.top)
    print(f"selected {len(rows)} community integrations by install count")

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
        "selection": "top by Home Assistant analytics install count, HACS downloads as tiebreak",
        "requested": args.top,
        "fetched": len(ok),
        "repositories": done,
    }, indent=2) + "\n")
    print(f"wrote {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
