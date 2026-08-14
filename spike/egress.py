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

That was not a hypothetical worry. Writing THREAT_MODEL.md found T14 here on
2026-08-14: this module checked the host *name* against the manifest and never
resolved it, so an author could declare a plausible vendor host, point its A
record at 192.168.1.1, and have the supervisor — trusted, and not subject to the
sandbox's seccomp AF_INET denial — fetch it for them. The control that closed
lateral movement had reopened it one layer up, through the deputy created to
close it. Fixed by resolving here, refusing every non-public address, and
connecting to the checked address rather than re-resolving the name. Measured by
probe checks 9 and 10.
"""

from __future__ import annotations

import base64
import functools
import gzip
import http.client
import ipaddress
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


def forbidden_reason(address: str) -> str | None:
    """Why this address is not a legitimate egress destination, or None.

    THREAT_MODEL.md T14/T15. The manifest names *hosts*, but the author of the
    manifest also controls the DNS records those names point at, so a name
    allowlist on its own says nothing about where a request actually goes. This
    is the check that turns a name allowlist into a destination allowlist.

    Everything not on the public internet is refused. That is broader than "no
    LAN devices" on purpose — link-local covers cloud metadata services
    (169.254.169.254), loopback covers anything the supervisor itself is
    listening on, and the IANA special-purpose ranges cover the rest. Being
    broad costs nothing here: an integration's declared vendor host lives on the
    public internet by definition, so nothing legitimate is inside these ranges.

    Note Python treats the RFC 5737 documentation ranges (192.0.2.0/24 and
    friends) as private, which is why the probe can use them as stand-ins for
    real LAN devices without ever addressing a real one.
    """
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return f"{address!r} is not an IP address"
    # ::ffff:192.168.1.1 is 192.168.1.1 wearing a hat. Unwrap it so the reason
    # names the address that matters rather than its IPv6 spelling.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    # Ordered most specific first, so the reason is the informative one:
    # is_private is also true for loopback and link-local.
    for label, matched in (
        ("loopback", ip.is_loopback),
        ("link-local", ip.is_link_local),
        ("multicast", ip.is_multicast),
        ("unspecified", ip.is_unspecified),
        ("reserved", ip.is_reserved),
        ("private", ip.is_private),
    ):
        if matched:
            return f"{ip} is {label}, not a public destination"
    return None


# ---------------------------------------------------------------------------
# Address pinning
#
# ⚠️ ADVANCED — this is the one part of the module that is not ordinary Python,
# and it exists for one narrow reason. Checking an address and then handing the
# *name* to urlopen means two separate DNS lookups: the one that was checked,
# and the one that is used. An attacker who controls the zone can answer
# differently the second time (a short TTL is enough), so the check passes on a
# public address and the connection lands on 192.168.1.1. That is DNS rebinding,
# and it is a time-of-check-to-time-of-use bug.
#
# The fix is to connect to the exact address that was checked. http.client
# resolves `self.host` inside connect(), so overriding connect() to use the
# pinned address is the whole change. `self.host` is left alone, so the Host:
# header and the TLS certificate check still use the declared name — pinning
# changes *where* the connection goes, never *who* it claims to be talking to.
#
# No proxy handling here: build_opener installs ProxyHandler({}) below, so
# CONNECT tunnels never occur and _tunnel_host is always None.
# ---------------------------------------------------------------------------
class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, *, pinned: str, **kwargs: object) -> None:
        super().__init__(host, **kwargs)  # type: ignore[arg-type]
        self._pinned = pinned

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._pinned, self.port), self.timeout, self.source_address
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, *, pinned: str, **kwargs: object) -> None:
        super().__init__(host, **kwargs)  # type: ignore[arg-type]
        self._pinned = pinned

    def connect(self) -> None:
        sock = socket.create_connection(
            (self._pinned, self.port), self.timeout, self.source_address
        )
        # server_hostname stays the declared name: pinning must not weaken
        # certificate validation, or it would trade one hole for a worse one.
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class _PinnedHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, pinned: str) -> None:
        super().__init__()
        self._pinned = pinned

    def http_open(self, req):  # noqa: ANN001, ANN201, D102
        return self.do_open(functools.partial(_PinnedHTTPConnection, pinned=self._pinned), req)


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, pinned: str) -> None:
        super().__init__()
        self._pinned = pinned

    def https_open(self, req):  # noqa: ANN001, ANN201, D102
        return self.do_open(
            functools.partial(_PinnedHTTPSConnection, pinned=self._pinned),
            req,
            context=self._context,
        )


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
    def resolve(self, host: str, port: int) -> list[str]:
        """Every address this name currently answers with.

        Split out as a method for one reason: DNS rebinding is a *difference
        between two resolutions*, and that cannot be demonstrated against a
        resolver you do not control. Tests substitute this to play the part of
        an attacker-controlled zone. See test_egress.py.
        """
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError as err:
            raise EgressDenied(f"cannot resolve {host}: {err}") from err
        return [info[4][0] for info in infos]

    # ------------------------------------------------------------------
    def _authorise(self, url: str) -> tuple[str, str, str | None]:
        """Check one URL. Returns (host, url to fetch, address to pin to).

        Two questions, and they are genuinely different: *may this integration
        talk to this name* (the manifest), and *where does that name actually
        go* (the resolution). Answering only the first was T14 — see
        forbidden_reason() above.
        """
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
            # Test-harness redirection to a local stub, configured by the
            # supervisor's own command line and never by the sandbox. The
            # destination check is skipped because the answer is known and
            # deliberate: the stub *is* on loopback. Nothing the sandbox can say
            # reaches this branch, so skipping is safe — but it does mean the
            # stub-house scenarios exercise the manifest check and not the
            # address check, which is why the address check is measured by the
            # probe and by test_egress.py instead.
            target = urllib.parse.urlparse(self.rewrites[host])
            parsed = parsed._replace(scheme=target.scheme or parsed.scheme, netloc=target.netloc)
            return host, urllib.parse.urlunparse(parsed), None

        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = self.resolve(host, port)
        if not addresses:
            raise EgressDenied(f"{host} resolves to nothing")
        # Refuse if *any* answer is forbidden, not merely the one that would be
        # used. A resolver returning [93.184.216.34, 192.168.1.1] is not a host
        # that happens to be reachable two ways; it is an attempt to have the
        # check look at one answer and the connection use another.
        for address in addresses:
            reason = forbidden_reason(address)
            if reason:
                raise EgressDenied(f"{host} resolves to {reason}")
        return host, url, addresses[0]

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
            host, target, pinned = self._authorise(url)
            # Record the address, not just the name. A request to a declared
            # host was previously logged as "allowed to a declared host" and
            # said nothing about where it went — which is exactly what made T14
            # invisible in an audit log that was otherwise complete and intact.
            hops.append(host if pinned is None else f"{host}[{pinned}]")

            request = urllib.request.Request(target, data=body, method=method)
            for name, value in headers.items():
                request.add_header(str(name), str(value))

            # build_opener with no ProxyHandler: ignore http_proxy from the
            # environment, so egress cannot be redirected by ambient config.
            handlers: list[urllib.request.BaseHandler] = [
                _NoRedirects,  # type: ignore[list-item]
                urllib.request.ProxyHandler({}),
            ]
            if pinned is not None:
                # Connect to the address that was just checked, rather than
                # letting urlopen resolve the name a second time. Without this
                # the check and the connection can see different answers.
                handlers += [_PinnedHTTPHandler(pinned), _PinnedHTTPSHandler(pinned)]
            opener = urllib.request.build_opener(*handlers)
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
