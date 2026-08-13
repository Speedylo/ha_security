#!/usr/bin/env python3
"""Stub of the Andrews & Arnold CHAOS API.

Stands in for the vendor cloud so the unmodified integration can be exercised
without real credentials. It lives outside the sandbox and is reached only after
the supervisor has approved the request against the manifest's network
allowlist; the redirection to this host happens after that check, never instead
of it.

Quota falls between polls so a second refresh produces a visibly different state.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

LINE_ID = "12345@a.1"
MONTHLY_QUOTA = 1_000_000_000_000  # 1 TB, in bytes, as the real API reports it

_state = {"remaining": 532_000_000_000, "requests": 0}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)  # credentials arrive here; deliberately not logged

        if not self.path.endswith("/quota"):
            self.send_error(404)
            return

        _state["requests"] += 1
        if _state["requests"] > 1:
            _state["remaining"] -= 3_000_000_000

        payload = {
            "quota": [
                {
                    "ID": LINE_ID,
                    "quota_monthly": str(MONTHLY_QUOTA),
                    "quota_remaining": str(_state["remaining"]),
                }
            ]
        }
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
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), Handler)
    print(f"fake A&A CHAOS API on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
