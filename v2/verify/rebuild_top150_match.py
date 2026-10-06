#!/usr/bin/env python3
"""F16, second step: for the integrations whose rebuild did not reproduce the committed result,
find the commit that does.

`rebuild_top150.py` took each repository at its last commit before the result was committed. For
139 of 144 that reproduced the committed per-integration entry exactly (once parsed with Python 3.14,
as the original was). For the rest the fetch evidently happened earlier, or the domain is declared
by two repositories and the original fetch kept the other. So each candidate repository's commits
before the bound that touched the integration are tried, newest first, and the first whose parse
equals the committed entry, field for field, is the match. No match is reported as no match.

Run on the Pi from a checkout's v2/, after rebuild_top150.py:
    ~/r2exp/ha314/bin/python verify/rebuild_top150_match.py --work ~/r2exp/f16
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

V2 = Path(__file__).resolve().parent.parent
BEFORE = "2026-08-24T20:53:36+01:00"
#: The domains to search, and every repository in the HACS index that declares each one.
CANDIDATES = {
    "chime_tts": ["nimroddolev/chime_tts"],
    "dwains_dashboard": ["dwainscheeren/dwains-lovelace-dashboard"],
    "f1_sensor": ["Nicxe/f1_sensor"],
    "solaredge_modbus_multi": ["WillCodeForCats/solaredge-modbus-multi"],
    "govee": ["LaggAt/hacs-govee", "lasswellt/govee-homeassistant"],
}


def git(clone: Path, *args: str, binary: bool = False):
    return subprocess.run(["git", "-C", str(clone), *args], check=True, capture_output=True,
                          text=not binary, timeout=600).stdout


def parse(parser: Path, directory: Path, domain: str) -> dict | None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "root"
        (root / domain).parent.mkdir(parents=True)
        subprocess.run(["cp", "-r", str(directory), str(root / domain)], check=True)
        out = Path(tmp) / "out.json"
        subprocess.run([sys.executable, str(parser), "--root", str(root), "--label", "x",
                        "--json", str(out)], check=True, capture_output=True)
        entries = json.loads(out.read_text())["per_integration"]
        return entries[0] if entries else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--only", nargs="*", help="search these domains only")
    ap.add_argument("--limit", type=int, default=60, help="commits tried per repository")
    args = ap.parse_args()
    parser = args.work / "api_surface_671795d.py"
    committed = {e["domain"]: e for e in json.loads(subprocess.run(
        ["git", "-C", str(V2), "show", "671795d:v2/figures/api_surface_hacs.json"],
        check=True, capture_output=True, text=True).stdout)["per_integration"]}
    found = {}
    for domain, repos in CANDIDATES.items():
        if args.only and domain not in args.only:
            continue
        found[domain] = None
        for repo in repos:
            clone = args.work / "clones" / repo.replace("/", "__")
            if not clone.exists():
                subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none",
                                f"https://github.com/{repo}.git", str(clone)], check=True,
                               capture_output=True, timeout=600)
            for prefix in (f"custom_components/{domain}", domain):
                commits = git(clone, "log", "--format=%H", f"--before={BEFORE}", "HEAD",
                              "--", prefix).split()
                if commits:
                    break
            tried = 0
            for commit in commits[:args.limit]:
                tried += 1
                blob = git(clone, "archive", "--format=tar", commit, prefix, binary=True)
                with tempfile.TemporaryDirectory() as tmp:
                    # Regular files only, as `fetch_hacs_corpus.fetch_one` kept, so a link in the
                    # repository is neither followed nor extracted.
                    archive = tarfile.open(fileobj=io.BytesIO(blob))
                    archive.extractall(tmp, members=[m for m in archive.getmembers()
                                                     if m.isfile()], filter="data")
                    entry = parse(parser, Path(tmp) / prefix, domain)
                if entry == committed[domain]:
                    found[domain] = {"repo": repo, "commit": commit, "layout": (
                        "custom_components" if prefix.startswith("custom_components") else
                        "toplevel"), "tried": tried}
                    break
            print(f"  {domain:<24} {repo:<44} "
                  f"{('MATCH ' + found[domain]['commit'][:12]) if found[domain] and found[domain]['repo'] == repo else 'no match'} "
                  f"after {tried} of {len(commits)} commits")
            if found[domain]:
                break
    path = args.work / "matched.json"
    previous = json.loads(path.read_text()) if path.exists() else {}
    path.write_text(json.dumps({**previous, **{d: f for d, f in found.items()
                                                if f or d not in previous}}, indent=2) + "\n")
    missing = [d for d, f in found.items() if not f]
    print(f"{len(found) - len(missing)} of {len(found)} matched; unmatched: {missing}")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
