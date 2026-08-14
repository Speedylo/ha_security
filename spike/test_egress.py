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

import egress as egress_module
from egress import MAX_RESPONSE_BYTES, Egress, EgressDenied, forbidden_reason
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
        elif self.path == "/host":
            # Echo the Host header so a pinned connection can prove it still
            # presents the declared name rather than the address it dialled.
            self._send(200, self.headers.get("Host", "").encode())
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

    # ------------------------------------------------------------------
    # THREAT_MODEL.md T14/T15 — the manifest names hosts, the author owns the
    # DNS. These cases are the reason the allowlist is not the whole control.
    # ------------------------------------------------------------------
    print("\ndestinations, not just names — T14")

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal failures
        if condition:
            print(f"  {PASS}  {label:<46} {detail}")
        else:
            failures += 1
            print(f"  {FAIL}  {label:<46} {detail}")

    # Classification is a pure function, so test it as one: no network, no
    # timing, and every range that matters in one table.
    for address, want_blocked in (
        ("8.8.8.8", False),
        ("93.184.216.34", False),
        ("2606:4700::1111", False),
        ("127.0.0.1", True),  # the supervisor's own services
        ("192.168.1.1", True),  # the router
        ("10.0.0.5", True),
        ("172.16.4.4", True),
        ("169.254.169.254", True),  # cloud metadata, the classic SSRF target
        ("224.0.0.1", True),
        ("0.0.0.0", True),
        ("::1", True),
        ("fd00::1", True),
        ("::ffff:192.168.1.1", True),  # RFC 1918 wearing an IPv6 hat
    ):
        reason = forbidden_reason(address)
        check(
            f"classify {address}",
            (reason is not None) == want_blocked,
            reason or "public — allowed",
        )

    class ScriptedEgress(Egress):
        """An Egress whose DNS answers are written by the attacker, not by DNS.

        Rebinding is a *difference between two resolutions*, which cannot be
        demonstrated against a resolver you do not control. This plays the part
        of a zone the integration author owns.
        """

        def __init__(self, *args: object, answers: list[list[str]], **kwargs: object) -> None:
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]
            self.answers = answers
            self.calls = 0

        def resolve(self, host: str, port: int) -> list[str]:  # noqa: ARG002
            answer = self.answers[min(self.calls, len(self.answers) - 1)]
            self.calls += 1
            return answer

    declared = Manifest({"name": "t", "network": ["vendor.example"]})

    # A declared host is not a safe host. Each of these is a manifest entry that
    # would survive review — the abuse is entirely in the DNS record.
    for label, answer in (
        ("declared host resolving to the router", ["192.168.1.1"]),
        ("declared host resolving to loopback", ["127.0.0.1"]),
        ("declared host resolving to metadata", ["169.254.169.254"]),
        # One good answer and one bad one is not a host reachable two ways. It
        # is an attempt to have the check read one and the connection use the
        # other, so it must be refused on the strength of the bad one alone.
        ("declared host with one poisoned answer", ["93.184.216.34", "192.168.1.1"]),
    ):
        scripted = ScriptedEgress(declared, answers=[answer])
        try:
            scripted.fetch({"url": "http://vendor.example/data"})
            check(label, False, "was ALLOWED and should not have been")
        except EgressDenied as err:
            check(label, True, str(err))

    # Pinning. With the destination check stubbed out so the request can
    # proceed at all, does the connection go to the address that was *checked*,
    # or to whatever DNS says at connect time? The scripted zone answers with
    # the stub on the first call and a different address afterwards; the name
    # itself does not resolve at all in real DNS, so a second lookup could not
    # succeed even if it were attempted.
    scripted = ScriptedEgress(
        declared, answers=[["127.0.0.1"], ["192.0.2.99"]]
    )
    original = egress_module.forbidden_reason
    egress_module.forbidden_reason = lambda address: None  # allow loopback, this test only
    try:
        reply = scripted.fetch({"url": f"http://vendor.example:{port}/host"})
        body = base64.b64decode(reply["body"]).decode()
        check("pinned connection reaches the checked address", reply["status"] == 200, f"status={reply['status']}")
        check("resolved exactly once, so rebinding has no second chance", scripted.calls == 1, f"{scripted.calls} lookup(s)")
        check(
            "Host: header still carries the declared name",
            body.startswith("vendor.example"),
            f"server saw Host: {body}",
        )
        check(
            "audit trail records the address, not only the name",
            reply["hops"] == [f"vendor.example[127.0.0.1]"],
            f"hops={reply['hops']}",
        )
    except EgressDenied as err:
        check("pinned connection reaches the checked address", False, f"denied: {err}")
    finally:
        egress_module.forbidden_reason = original

    server.shutdown()
    print()
    if failures:
        print(f"{failures} failure(s)")
        return 1
    print("all egress policy tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
