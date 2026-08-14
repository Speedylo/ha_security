#!/usr/bin/env python3
"""Policy tests for egress.py — the supervisor's outbound HTTP.

`egress.py` is trusted code that acts on attacker-controlled input, so its
limits are the ones most worth testing directly rather than only end-to-end.
Each case below corresponds to something a malicious integration could
otherwise make the *supervisor* do on its behalf.

    python3 test_egress.py

Runs against a local stub server; no external traffic.
"""

from __future__ import annotations

import base64
import http.server
import socketserver
import sys
import threading

from egress import MAX_RESPONSE_BYTES, Egress, EgressDenied
from supervisor import Manifest

PASS, FAIL = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m"


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code: int, body: bytes = b"ok", headers: dict | None = None) -> None:
        self.send_response(code)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/offsite":
            self._send(302, b"", {"Location": "http://evil.example.net/steal"})
        elif self.path == "/onsite":
            self._send(302, b"", {"Location": "/final"})
        elif self.path == "/final":
            self._send(200, b"arrived")
        elif self.path == "/loop":
            self._send(302, b"", {"Location": "/loop"})
        elif self.path == "/big":
            self._send(200, b"x" * (MAX_RESPONSE_BYTES + 1024))
        elif self.path == "/401":
            self._send(401, b"unauthorised")
        elif self.path == "/500":
            self._send(500, b"server error")
        else:
            self._send(200, b"ok")

    do_POST = do_GET

    def log_message(self, *args: object) -> None:
        return


def main() -> int:
    server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    server.allow_reuse_address = True
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    manifest = Manifest({"name": "t", "network": ["declared.example"]})
    egress = Egress(
        manifest,
        rewrites={"declared.example": f"http://127.0.0.1:{port}"},
        blocked_hosts=["homeassistant.local"],
    )

    failures = 0

    def expect_allowed(label: str, status: int | None = None, **message: object) -> None:
        nonlocal failures
        try:
            reply = egress.fetch(message)
        except EgressDenied as err:
            failures += 1
            print(f"  {FAIL}  {label:<46} unexpectedly denied: {err}")
            return
        if status is not None and reply["status"] != status:
            failures += 1
            print(f"  {FAIL}  {label:<46} status {reply['status']}, wanted {status}")
            return
        print(f"  {PASS}  {label:<46} status={reply['status']} hops={reply['hops']}")

    def expect_denied(label: str, **message: object) -> None:
        nonlocal failures
        try:
            egress.fetch(message)
        except EgressDenied as err:
            print(f"  {PASS}  {label:<46} {err}")
            return
        failures += 1
        print(f"  {FAIL}  {label:<46} was ALLOWED and should not have been")

    print("\nreachability — the manifest decides, not the sandbox")
    expect_allowed("declared host", 200, url="http://declared.example/ok")
    expect_denied("undeclared host", url="http://evil.example.net/steal")
    expect_denied("undeclared LAN device by IP", url="http://192.0.2.10/unlock")
    expect_denied("undeclared LAN device, no scheme host", url="http://10.0.0.5:8080/")

    print("\nthe supervisor is not a general-purpose fetcher")
    expect_denied("file:// scheme", url="file:///etc/passwd")
    expect_denied("ftp:// scheme", url="ftp://declared.example/x")
    expect_denied("no host in URL", url="http:///justapath")
    expect_denied("Home Assistant itself", url="http://homeassistant.local:8123/api/states")

    print("\nredirects are re-authorised per hop, not followed blindly")
    expect_allowed("redirect within the allowlist", 200, url="http://declared.example/onsite")
    expect_denied("redirect off the allowlist", url="http://declared.example/offsite")
    expect_denied("redirect loop", url="http://declared.example/loop")

    print("\nresource limits on the trusted side")
    expect_denied("oversized response", url="http://declared.example/big")
    expect_denied(
        "header count",
        url="http://declared.example/ok",
        headers={f"X-{n}": "v" for n in range(64)},
    )
    expect_denied(
        "CRLF injection in a header value",
        url="http://declared.example/ok",
        headers={"X-Evil": "a\r\nX-Injected: yes"},
    )

    print("\nupstream errors reach the integration rather than being swallowed")
    expect_allowed("401 passes through", 401, url="http://declared.example/401")
    expect_allowed("500 passes through", 500, url="http://declared.example/500")

    print("\nrequest bodies survive the round trip")
    expect_allowed(
        "POST with a body",
        200,
        method="POST",
        url="http://declared.example/ok",
        body=base64.b64encode(b"user=x&pass=y").decode(),
    )

    server.shutdown()
    print()
    if failures:
        print(f"{failures} failure(s)")
        return 1
    print("all egress policy tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
