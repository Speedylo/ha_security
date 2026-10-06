#!/usr/bin/env python3
"""F16: rebuild the 144-integration `hacs-top150` sample behind contribution 1's head figures.

Its manifest was overwritten the next day by the 40-integration head corpus, which used the same
default path, so nothing records which repositories, at which commits, were parsed. This rebuilds
the sample the way it was drawn, and then checks the rebuild against the result it must reproduce:

  selection  `fetch_hacs_corpus.candidates(150)`: the committed analytics snapshot of 2026-08-21
             (F37, the file the fetcher read) ranked against today's HACS index
  commits    each repository's default branch at its last commit before 2026-08-24 20:53:36
             +01:00, the commit (`bd3ee7b`) that first committed the result, from a blobless clone
  parse      `api_surface.py` as of `671795d`, the commit that wrote the final
             `figures/api_surface_hacs.json`, run on the rebuilt sample
  check      the rebuilt result against that committed file, field by field. Equal means the
             sample is recovered and its manifest can be committed; anything else is reported.

Run on the Pi from a checkout's v2/:  python3 verify/rebuild_top150.py --work ~/r2exp/f16
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import subprocess
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2 / "figures"))
import fetch_hacs_corpus as fetcher  # noqa: E402

BEFORE = "2026-08-24T20:53:36+01:00"
PARSER_COMMIT = "671795d"


def commit_before(row: dict, clones: Path) -> dict:
    clone = clones / row["repo"].replace("/", "__")
    try:
        if not clone.exists():
            subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none",
                            f"https://github.com/{row['repo']}.git", str(clone)],
                           check=True, capture_output=True, timeout=600)
        out = subprocess.run(["git", "-C", str(clone), "rev-list", "-1", f"--before={BEFORE}",
                              "HEAD"], check=True, capture_output=True, text=True,
                             timeout=120).stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as err:
        return {**row, "commit": None, "reason": f"{type(err).__name__}"}
    return {**row, "commit": out or None,
            **({} if out else {"reason": "no commit before the fetch"})}


def git_show(rev_path: str) -> str:
    return subprocess.run(["git", "-C", str(V2), "show", rev_path], check=True,
                          capture_output=True, text=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    args = ap.parse_args()
    clones, corpus = args.work / "clones", args.work / "corpus"
    clones.mkdir(parents=True, exist_ok=True)
    corpus.mkdir(parents=True, exist_ok=True)

    rows = fetcher.candidates(150)
    print(f"selected {len(rows)}")
    with futures.ThreadPoolExecutor(max_workers=8) as pool:
        pinned = list(pool.map(lambda r: commit_before(r, clones), rows))
    fetched = []
    for row in pinned:
        if not row.get("commit"):
            fetched.append({**row, "ok": False})
            continue
        fetched.append(fetcher.fetch_one({k: row[k] for k in ("domain", "repo", "commit")},
                                         corpus) | {"installs": row["installs"],
                                                    "hacs_downloads": row["hacs_downloads"]})
    ok = [f for f in fetched if f.get("ok")]
    print(f"fetched {len(ok)} of {len(fetched)} at their commits before {BEFORE}")
    manifest = {
        "source_index": fetcher.HACS_INDEX,
        "selection": "top 150 by Home Assistant analytics install count (snapshot 2026-08-21), "
                     "HACS downloads as tiebreak; the index as of the rebuild",
        "commits": f"each default branch's last commit before {BEFORE}",
        "rebuilt": "2026-10-06 by verify/rebuild_top150.py (finding F16)",
        "requested": 150, "fetched": len(ok), "repositories": fetched,
    }
    (args.work / "hacs_top150_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    parser = args.work / "api_surface_671795d.py"
    parser.write_text(git_show(f"{PARSER_COMMIT}:v2/figures/api_surface.py"))
    out = args.work / "api_surface_hacs_rebuilt.json"
    subprocess.run([sys.executable, str(parser), "--root", str(corpus), "--label", "hacs-top150",
                    "--json", str(out)], check=True, capture_output=True)
    committed = json.loads(git_show(f"{PARSER_COMMIT}:v2/figures/api_surface_hacs.json"))
    rebuilt = json.loads(out.read_text())
    differing = [k for k in sorted(set(committed) | set(rebuilt))
                 if committed.get(k) != rebuilt.get(k)]
    print(f"committed n={committed.get('n')} files={committed.get('files')}; "
          f"rebuilt n={rebuilt.get('n')} files={rebuilt.get('files')}")
    print("IDENTICAL" if not differing else f"DIFFERENT in {differing}")
    return 0 if not differing else 1


if __name__ == "__main__":
    sys.exit(main())
