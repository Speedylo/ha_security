#!/usr/bin/env python3
"""F16, last step: assemble the rebuilt sample with the matched commits, parse it, and compare.

After `rebuild_top150.py` (the selection and a commit per repository) and
`rebuild_top150_match.py` (the five integrations whose first rebuild differed), this fetches every
repository in the sample at its final commit into `corpus_final/`, and parses it with
`api_surface.py` as of 671795d under the interpreter running this script, which must be Python 3.14,
as the original parse was. It then compares the result with the committed one, field for field,
and writes the manifest with, for each repository, how its commit was decided.

A repository is in the sample when its fetch succeeded. Where two repositories declare one domain,
the one whose parse matched is in the sample and the other is not, as one directory can hold only
one of them.

Run on the Pi from a checkout's v2/:  ~/r2exp/ha314/bin/python verify/rebuild_top150_finish.py --work ~/r2exp/f16
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2 / "figures"))
import fetch_hacs_corpus as fetcher  # noqa: E402

BY_DATE = "the default branch's last commit before the result was committed"
BY_PARSE = ("the commit whose parse equals the committed entry exactly; why the original fetch "
            "took it is not established")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    args = ap.parse_args()
    if sys.version_info[:2] != (3, 14):
        sys.exit("run under Python 3.14, as the original parse was")
    work = args.work
    manifest = json.loads((work / "hacs_top150_manifest.json").read_text())
    matched = json.loads((work / "matched.json").read_text())
    final = work / "corpus_final"
    if final.exists():
        shutil.rmtree(final)
    final.mkdir()

    rows = []
    for row in manifest["repositories"]:
        domain = row["domain"]
        if not row.get("ok"):
            reason = row.get("reason") or "not fetched"
            rows.append({**row, "in_sample": False, "pinned_by": f"not in the sample: {reason}"})
        elif domain in matched and matched[domain]["repo"] != row["repo"]:
            rows.append({**row, "in_sample": False,
                         "pinned_by": "domain collision: the other repository declaring this "
                                      "domain is the one measured"})
        elif domain in matched:
            rows.append({**row, "commit": matched[domain]["commit"], "in_sample": True,
                         "pinned_by": BY_PARSE})
        else:
            rows.append({**row, "in_sample": True, "pinned_by": BY_DATE})
    for row in rows:
        if row["in_sample"]:
            result = fetcher.fetch_one({k: row[k] for k in ("domain", "repo", "commit")}, final)
            if not result["ok"]:
                sys.exit(f"{row['domain']}: {result.get('reason')}")
    in_sample = [r for r in rows if r["in_sample"]]
    print(f"in the sample: {len(in_sample)}, {len({r['domain'] for r in in_sample})} domains")

    out = work / "rebuilt_final.json"
    subprocess.run([sys.executable, str(work / "api_surface_671795d.py"), "--root", str(final),
                    "--label", "hacs-top150", "--json", str(out)], check=True,
                   capture_output=True)
    committed = json.loads(subprocess.run(
        ["git", "-C", str(V2), "show", "671795d:v2/figures/api_surface_hacs.json"],
        check=True, capture_output=True, text=True).stdout)
    rebuilt = json.loads(out.read_text())
    same = committed == rebuilt
    print("IDENTICAL" if same else
          f"DIFFERENT in {[k for k in committed if committed[k] != rebuilt.get(k)]}")

    manifest.update({
        "repositories": rows,
        "fetched": len(in_sample),
        "commits": f"{sum(r.get('pinned_by') == BY_DATE for r in rows)} at each default branch's "
                   f"last commit before 2026-08-24 20:53:36 +01:00; "
                   f"{sum(r.get('pinned_by') == BY_PARSE for r in rows)} by exact parse equality "
                   f"(verify/rebuild_top150_match.py)",
        "parsed_with": "figures/api_surface.py at 671795d under Python 3.14, Home Assistant "
                       "2026.8's interpreter (under 3.13, 41 files do not parse)",
        "check": ("the rebuilt sample's parse equals figures/api_surface_hacs.json at 671795d, "
                  "field for field") if same else "NOT equal",
    })
    (work / "hacs_top150_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
