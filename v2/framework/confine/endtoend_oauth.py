"""W2 (d): an OAuth token refreshed inside a sandbox, and where the new one goes.

`trakt_tv`, unmodified, refreshes through Home Assistant's `OAuth2Session`. Trakt's refresh tokens
are single-use, so the refreshed pair the integration writes with `async_update_entry`, which
lands in (B)'s storage in the sandbox's data directory, is the only valid credential afterwards.
Predictions: `notes/w2d_token_refresh_prediction.md`.

    1  the stored token, marked expired          a token expiring while the sandbox runs
    2  the same original token, now spent         a respawn without a persistent data directory
    3  the token run 1's sandbox stored in (B)    a respawn with one
    C  as 3, with no egress declared              the control

**The credentials.** `~/.config/capstone/trakt.json` (mode 600) holds the client id and the token.
After every run that refreshed, the newest token is saved back there at once, so the account is
never left holding only a spent token. Nothing this harness prints or writes contains the client
id or any token: every report is scrubbed of each one seen.

Run:  systemd-run --user --scope -q python3 -u -m confine.endtoend_oauth \\
          --corpus ~/r2exp/corpus_uniform --python ~/r2exp/ha314/bin/python --json out.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from .cgroup import Delegation
from .endtoend_egress import run_confined
from .preflight import require_ready
from .spawn import become_subreaper
from .provenance import record_run

TOKENS = Path.home() / ".config" / "capstone" / "trakt.json"
SUBJECT = {
    "flow_input": {}, "settle": 0,
    # One source, fetched through the integration's authenticated `request()`, so the first poll
    # needs a valid token. Trakt's anticipated movies, a public list: the first runs used the
    # user's stats, which Trakt answers with 204 and no body for an account that has watched
    # nothing, and `trakt_tv` cannot decode an empty body (`runs_stats_source.json`).
    "component_config": {"trakt_tv": {"sensors": {"anticipated": {"movie": {"max_medias": 3}}}}},
}
# `api.tmdb.org:80` was **not** in the first declaration, which was written from reading the source.
# The second set of runs found it: after the Trakt request, `trakt_tv` fetches poster metadata from
# TMDB over plain HTTP, the mediator refused it six times with its clause, and setup never finished
# (`runs_tmdb_undeclared.json`). Added from that measurement, and said so, the way §7.31.5 treated
# `dwd_weather`'s missed host.
DECLARED = {"schema_version": 1, "network": {"egress": ["api.trakt.tv:443", "api.tmdb.org:80"]}}
NOTHING = {"schema_version": 1}


def load() -> dict:
    if TOKENS.stat().st_mode & 0o077:
        raise SystemExit(f"{TOKENS} is readable by others; chmod 600 it first")
    return json.loads(TOKENS.read_text())


def save(config: dict) -> None:
    tmp = TOKENS.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, indent=2))
    os.chmod(tmp, 0o600)
    tmp.replace(TOKENS)


def entry_for(config: dict, token: dict) -> dict:
    # An empty secret: Trakt issues public clients now, and the helper omits an empty one.
    # `expires_at` in the past, so the first request refreshes.
    return {"auth_implementation": "trakt_tv", "client_id": config["client_id"],
            "client_secret": "", "token": {**token, "expires_at": time.time() - 60}}


def inspector(given: dict, carried: dict):
    """Read (B)'s stored entry; keep the token in `carried`; return only facts about it."""
    def inspect(data_dir: Path) -> dict:
        stored = data_dir / ".storage" / "core.config_entries"
        if not stored.exists():
            return {"stored_entry": False}
        entries = json.loads(stored.read_text()).get("data", {}).get("entries", [])
        mine = [e for e in entries if e.get("domain") == "trakt_tv"]
        token = ((mine[0].get("data") or {}).get("token") or {}) if mine else {}
        carried.clear()
        carried.update(token)
        return {"stored_entry": bool(mine),
                "where": str(stored.relative_to(data_dir.parent.parent)),
                "refresh_token_changed": bool(token.get("refresh_token"))
                and token.get("refresh_token") != given.get("refresh_token"),
                "access_token_changed": bool(token.get("access_token"))
                and token.get("access_token") != given.get("access_token"),
                "valid_for_hours": round((token.get("expires_at", 0) - time.time()) / 3600, 1)}
    return inspect


def scrub(value: object, secrets: set[str]) -> object:
    text = json.dumps(value, default=str)
    for secret in sorted((s for s in secrets if s and len(s) >= 8), key=len, reverse=True):
        text = text.replace(secret, "<redacted>")
    return json.loads(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--python", type=Path, required=True)
    ap.add_argument("--uv", default=str(Path.home() / ".local/bin/uv"))
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    require_ready(deep=False)
    become_subreaper()
    delegation = Delegation.discover()
    uv = args.uv if Path(args.uv).exists() else None
    platform_deps = Path.home() / "r2exp/platform-deps"
    platform_deps = platform_deps if platform_deps.is_dir() else None
    component = args.corpus / "trakt_tv"

    config = load()
    original = dict(config["token"])
    secrets = {config["client_id"], original.get("access_token", ""),
               original.get("refresh_token", "")}
    latest = dict(original)
    results = []

    def run(name: str, token: dict, permissions: dict) -> dict:
        nonlocal latest
        carried: dict = {}
        report = run_confined(component, "trakt_tv", SUBJECT, name, permissions, args.python,
                              delegation, uv, platform_deps, max_seconds=300,
                              entry_data=entry_for(config, token),
                              inspect_data=inspector(token, carried))
        if carried.get("refresh_token") and carried["refresh_token"] != token["refresh_token"]:
            # Refreshed: this is now the only valid token. Saved at once.
            secrets.update({carried.get("access_token", ""), carried["refresh_token"]})
            latest = {k: v for k, v in carried.items()}
            config["token"] = latest
            save(config)
        egress = [{"target": d.get("target"), "allowed": d.get("allowed"),
                   "clause": d.get("clause")} for d in report.get("logged") or []
                  if d.get("op") == "network.egress"]
        summary = scrub({"run": name, "loaded": report.get("loaded"),
                         "entry_state": report.get("entry_state"),
                         "entry_reason": report.get("entry_reason"),
                         "setup_error": report.get("setup_error"),
                         "setup_log": report.get("setup_log"),
                         "level": report.get("level"), "error": report.get("error"),
                         "egress": egress, "inspection": report.get("data_inspection"),
                         "published": [p.get("entity") for p in report.get("published") or []],
                         "audit_breaks": report.get("audit_breaks"),
                         "reconcile": report.get("reconcile")}, secrets)
        results.append(summary)
        print(f"  {name:<22} loaded={summary['loaded']}  state={summary['entry_state']}  "
              f"reason={summary['entry_reason']}  egress={len(egress)} "
              f"({sum(1 for e in egress if e['allowed'])} allowed)  "
              f"inspection={summary['inspection']}", flush=True)
        for line in (summary.get("setup_log") or [])[:6]:
            print(f"      {line}", flush=True)
        if args.json:
            args.json.write_text(json.dumps(results, indent=2) + "\n")
            record_run(args.json)  # F14: how this result was produced, beside it
        return summary

    run("1_expiring", original, DECLARED)
    run("2_respawn_spent", original, DECLARED)
    run("3_respawn_carried", latest, DECLARED)
    run("C_nothing_declared", latest, NOTHING)
    return 0


if __name__ == "__main__":
    sys.exit(main())
