#!/usr/bin/env python3
"""Supervisor-side HTTP egress. The sandbox has no network of its own.

Before this existed, `network:` in the manifest was *advisory*: the shim asked
the supervisor for permission and then the sandbox opened the connection itself,
so a raw `socket.create_connection(...)` never consulted the manifest at all.
Two probe checks measured that — reaching an undeclared LAN device, and
exfiltrating to an undeclared internet host — and both were ALLOWED even with
namespaces and seccomp enabled.

Now the sandbox cannot open an IP socket at all (seccomp denies `socket(AF_INET)`
and `AF_INET6`), and every request travels to the supervisor over the existing
Unix socket. The supervisor checks the manifest and makes the connection. The
allowlist is therefore *enforcing* rather than advisory, and the difference is
not a stronger promise about the sandbox's behaviour — it is that the sandbox is
no longer the party making the decision.

**This module is new attack surface, and that is the trade.** The supervisor now
parses attacker-controlled URLs, headers and bodies, and issues requests on the
attacker's behalf — a confused deputy by construction. Every limit below exists
because of that, and each one should be read as "a thing the sandbox would
otherwise be able to make the trusted process do".
"""

from __future__ import annotations

import base64
import gzip
import socket
import urllib.error
import urllib.parse
import urllib.request
import zlib

# Limits. Each is a bound on what a malicious integration can make the
# *supervisor* do, which is a different question from what it can reach.
ALLOWED_SCHEMES = ("http", "https")  # no file://, ftp://, gopher://, data://
MAX_REDIRECTS = 5  # each hop is re-checked against the manifest
MAX_RESPONSE_BYTES = 8 * 1024 * 1024  # a response big enough to exhaust the supervisor
MAX_TIMEOUT_SECONDS = 30.0  # a request that never returns holds a thread
MAX_HEADER_COUNT = 32
MAX_HEADER_BYTES = 4096


class EgressDenied(Exception):
    """Refused before any connection was attempted."""


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """Stop urllib following redirects silently.

    Automatic redirect following was the mechanism behind the gap the shim's own
    docstring recorded: only the first URL was ever checked, so a declared host
    answering `302 Location: https://evil.example` moved the request off the
    allowlist without anything noticing. Handling hops here means each one is
    re-authorised against the manifest.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102, ANN001
        return None


def _decode_body(raw: bytes, encoding: str) -> bytes:
    if encoding == "gzip":
        return gzip.decompress(raw)
    if encoding == "deflate":
        return zlib.decompress(raw)
    return raw


class Egress:
    """Performs outbound HTTP for one sandboxed integration."""

    def __init__(self, manifest, rewrites: dict[str, str] | None = None, blocked_hosts=()) -> None:
        self.manifest = manifest
        # Test-harness redirection (declared host -> local stub). Applied *after*
        # the manifest check, so a rewrite can never widen what is reachable.
        self.rewrites = rewrites or {}
        # Hosts the sandbox may not reach even if its manifest declares them.
        # Home Assistant itself belongs here: the sandbox holds no token, but an
        # allowlist that can name the thing the framework is protecting is a
        # weaker allowlist than one that cannot.
        self.blocked_hosts = {host.lower() for host in blocked_hosts if host}

    # ------------------------------------------------------------------
    def _authorise(self, url: str) -> tuple[str, str]:
        """Check one URL against the manifest. Returns (host, url to fetch)."""
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ALLOWED_SCHEMES:
            raise EgressDenied(f"scheme {parsed.scheme!r} not permitted")
        host = (parsed.hostname or "").lower()
        if not host:
            raise EgressDenied("no host in URL")
        if host in self.blocked_hosts:
            raise EgressDenied(f"{host} is reserved to the supervisor")
        if not self.manifest.may_connect(host):
            raise EgressDenied(f"{host} not in manifest network allowlist")

        if host in self.rewrites:
            target = urllib.parse.urlparse(self.rewrites[host])
            parsed = parsed._replace(scheme=target.scheme or parsed.scheme, netloc=target.netloc)
            return host, urllib.parse.urlunparse(parsed)
        return host, url

    def fetch(self, message: dict) -> dict:
        """Perform one request. Raises EgressDenied if policy refuses it."""
        method = str(message.get("method", "GET")).upper()
        url = str(message.get("url", ""))
        headers = message.get("headers") or {}
        timeout = min(float(message.get("timeout") or 10.0), MAX_TIMEOUT_SECONDS)

        if len(headers) > MAX_HEADER_COUNT:
            raise EgressDenied(f"too many headers ({len(headers)} > {MAX_HEADER_COUNT})")
        for name, value in headers.items():
            if len(str(name)) + len(str(value)) > MAX_HEADER_BYTES:
                raise EgressDenied(f"header {name!r} too long")
            # A newline in a header value splits the request. urllib catches
            # most of this, but refusing early is clearer than relying on it.
            if "\n" in str(value) or "\r" in str(value):
                raise EgressDenied(f"header {name!r} contains a line break")

        body = base64.b64decode(message["body"]) if message.get("body") else None

        hops: list[str] = []
        for _ in range(MAX_REDIRECTS + 1):
            host, target = self._authorise(url)
            hops.append(host)

            request = urllib.request.Request(target, data=body, method=method)
            for name, value in headers.items():
                request.add_header(str(name), str(value))

            # build_opener with no ProxyHandler: ignore http_proxy from the
            # environment, so egress cannot be redirected by ambient config.
            opener = urllib.request.build_opener(_NoRedirects, urllib.request.ProxyHandler({}))
            try:
                with opener.open(request, timeout=timeout) as response:
                    raw = response.read(MAX_RESPONSE_BYTES + 1)
                    status = response.status
                    response_headers = dict(response.headers)
            except urllib.error.HTTPError as err:
                # 3xx arrives here because redirects are disabled above.
                raw = err.read(MAX_RESPONSE_BYTES + 1)
                status = err.code
                response_headers = dict(err.headers or {})
            except urllib.error.URLError as err:
                raise EgressDenied(f"transport failure: {err.reason}") from err
            except (TimeoutError, socket.timeout) as err:
                raise EgressDenied("upstream timed out") from err

            if len(raw) > MAX_RESPONSE_BYTES:
                raise EgressDenied(f"response exceeds {MAX_RESPONSE_BYTES} bytes")

            if status in (301, 302, 303, 307, 308) and response_headers.get("Location"):
                # Re-enter the loop so the new host is checked like the first.
                #
                # Resolve against the *logical* url, not the rewritten `target`.
                # A relative `Location: /next` from a declared host must stay on
                # that host; resolving it against the rewrite target would
                # rewrite the identity too, and the hop would then be checked
                # against the stub's address rather than the declared one.
                url = urllib.parse.urljoin(url, response_headers["Location"])
                if status == 303 or (status == 302 and method == "POST"):
                    method, body = "GET", None
                continue

            raw = _decode_body(raw, response_headers.get("Content-Encoding", "").lower())
            return {
                "status": status,
                "headers": response_headers,
                "body": base64.b64encode(raw).decode("ascii"),
                "hops": hops,
            }

        raise EgressDenied(f"more than {MAX_REDIRECTS} redirects")
