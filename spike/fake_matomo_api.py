#!/usr/bin/env python3
"""Stub of the Matomo Reporting API.

Same role as fake_aa_api.py for the second target: it stands outside the sandbox
so the unmodified integration can be exercised without a real Matomo instance or
a real token. The supervisor authorises the request against the manifest's
network allowlist before any redirection to this stub happens.

Visits climb between polls so a second refresh produces a visibly different
state, the same way the A&A stub drains quota.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

# Matomo reports per-period counters; only the day figures move between polls.
# Counted off the day-period VisitsSummary call, which the coordinator makes
# exactly once per refresh, so "second poll" is unambiguous.
_state = {"polls": 0}

_BASE = {
    "day": {"nb_uniq_visitors": 412, "nb_visits": 530, "nb_actions": 1480},
    "week": {"nb_uniq_visitors": 2711, "nb_visits": 3902, "nb_actions": 11043},
    "month": {"nb_uniq_visitors": 10233, "nb_visits": 15871, "nb_actions": 46220},
}
_PAGEVIEWS = {"day": 1180, "week": 8702, "month": 35110}


def _visit_summary(period: str) -> dict:
    data = dict(_BASE.get(period, _BASE["day"]))
    if period == "day" and _state["polls"] > 1:
        # Traffic arriving between the two polls.
        data["nb_uniq_visitors"] += 17
        data["nb_visits"] += 23
        data["nb_actions"] += 64
    return data


def _actions(period: str) -> dict:
    views = _PAGEVIEWS.get(period, _PAGEVIEWS["day"])
    if period == "day" and _state["polls"] > 1:
        views += 51
    return {"nb_pageviews": views, "nb_downloads": 12, "nb_outlinks": 33}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        length = int(self.headers.get("Content-Length", 0))
        body_raw = self.rfile.read(length).decode("utf-8", "replace")
        # token_auth arrives in this body and is deliberately never logged.
        body = parse_qs(body_raw)

        query = parse_qs(urlparse(self.path).query)
        method = (query.get("method") or [""])[0]
        # module/method/format ride in the query string; everything else,
        # including period and the token, is form-encoded in the body.
        period = (body.get("period") or ["day"])[0]

        if method == "VisitsSummary.get":
            if period == "day":
                _state["polls"] += 1
            payload = _visit_summary(period)
        elif method == "Actions.get":
            payload = _actions(period)
        elif method == "Live.getCounters":
            payload = [{"visitors": 7, "visits": 9, "actions": 21}]
        elif method == "API.getMatomoVersion":
            payload = {"value": "5.1.2"}
        elif method == "SitesManager.getSitesWithAtLeastViewAccess":
            payload = [{"idsite": "1", "name": "example.org"}]
        else:
            payload = {"result": "error", "message": f"unsupported method {method}"}

        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"  [vendor cloud] {fmt % args}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1",
                        help="bind address; use 0.0.0.0 to reach it from a container")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), Handler)
    print(f"fake Matomo Reporting API on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
