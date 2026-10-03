"""The whole egress loop, driven by unmodified HTTP clients.

The previous two suites test the halves: `selftest_egress` that the manifest gates a destination,
`selftest_fdpass` that a descriptor crosses intact. This one joins them and puts a real client on
top, because the claim F2 makes is not "the mediator decides correctly" — it is *"an integration
polling a declared remote API completes successfully while confined"*, and only an unmodified
client library can show that.

  1  `urllib.request` reaches a declared host and gets its body back — nothing patched in it,
     nothing it was told, no proxy variable set
  2  the sandbox never holds a real address: the name resolves to 240.0.0.0/4 throughout
  3  an undeclared host fails the way a network failure fails, not with a framework exception
     escaping into integration code that has never heard of this project
  4  `aiohttp` reaches a declared host — the platform's own seam, which four of six integrations'
     API names use (§7.31.11), and the one §5.10.3's design would have missed entirely
  5  a connection to a real address is **not** intercepted, and is left to fail

Case 5 is the design's dividing line rather than a gap in it: security is the network namespace,
which has no route anywhere; the shim is compatibility. An integration that avoids the shim gets
nothing rather than getting out, so the shim's coverage bounds how many *honest* integrations work
and never how far a *hostile* one reaches.

**No network is required** and none is used: destinations are local listeners and the mediator's
resolver is substituted, so what is measured is the path rather than the internet.

Run: `python3 -m confine.selftest_egress_shim`
"""

from __future__ import annotations

import http.server
import json
import socket
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

try:
    from .egress import EgressBroker, EgressRefused
    from .egress_shim import PLACEHOLDER_NET, EgressDenied, EgressShim
    from .manifest import Manifest, policy_for
except ImportError:  # run as a plain script
    from egress import EgressBroker, EgressRefused
    from egress_shim import PLACEHOLDER_NET, EgressDenied, EgressShim
    from manifest import Manifest, policy_for

import ipaddress

PASS, FAIL, SKIP = "  ok  ", " FAIL ", " skip "
_results: list[tuple[bool, str]] = []


def check(condition: bool, name: str, detail: str = "") -> None:
    _results.append((bool(condition), name))
    print(f"[{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def skip(name: str, why: str) -> None:
    print(f"[{SKIP}] {name} — {why}")


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = b'{"temperature": 12.5}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        pass


def api_server() -> tuple[http.server.HTTPServer, int]:
    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def wire(root: Path, domain: str, declared: list[str]) -> tuple[EgressShim, EgressBroker, list]:
    """A shim whose `connect_via` runs the real decision path against a real manifest.

    The mediator is a function call rather than a process here. That is the deliberate seam
    §7.24's design left: `EgressShim` takes `connect_via` injected, so the policy, the broker
    and the shim can be exercised together without a sandbox, a channel or a second process —
    and what is under test stays the *loop*, not the plumbing that carries it.
    """
    directory = root / "custom_components" / domain
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "__init__.py").write_text("# nothing\n")
    (directory / "manifest.json").write_text(json.dumps(
        {"domain": domain, "name": domain, "version": "1.0.0",
         "permissions": {"schema_version": 1, "network": {"egress": declared}}}))
    manifest = Manifest.load(directory, root)
    policy = policy_for({domain: manifest})
    # `resolver` is set by each case once the mediator's DNS is in place and *before* the shim
    # is installed over the global one. In deployment the ordering is automatic — the mediator
    # is a different process — and having to sequence it by hand here is itself the clearest
    # statement of which side of the boundary each resolver belongs to.
    broker = EgressBroker()
    decisions: list = []

    def connect_via(host: str, port: int) -> int:
        request = {"op": "network.egress", "host": host, "port": port}
        decision = policy(domain, request)
        decisions.append(decision)
        try:
            # `allow_private=True` here is a **harness** decision — this suite's declared
            # destinations are loopback listeners for determinism, and T10 itself is exercised
            # against a resolved address in `selftest_egress` case 4, not here. The request
            # dict carries no such field, because a sandbox setting it on its own request was
            # exactly the bug `egress.py` documents fixing.
            fd, _record = broker.open(domain, request, decision, allow_private=True)
        except EgressRefused as err:
            raise EgressDenied(err.reason, err.clause) from err
        return fd

    return EgressShim(connect_via), broker, decisions


class _MediatorResolver:
    """DNS for the mediator only. The sandbox's resolution is the shim's job and is what is
    under test; this stands in for the real world the mediator resolves against."""

    def __init__(self, table: dict[str, str]) -> None:
        self.table = table

    def __enter__(self) -> _MediatorResolver:
        self.real = socket.getaddrinfo

        def getaddrinfo(host, port, *args, **kwargs):
            if host in self.table:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (self.table[host], port))]
            return self.real(host, port, *args, **kwargs)

        self._patched = getaddrinfo
        socket.getaddrinfo = getaddrinfo
        return self

    def __exit__(self, *_exc) -> None:
        # The shim installs *over* this, so restore only if nothing else has since replaced it.
        if socket.getaddrinfo is self._patched:
            socket.getaddrinfo = self.real


# -- 1-3: the synchronous path, with an unmodified client -------------------------------

def case_urllib(root: Path) -> None:
    server, port = api_server()
    shim, broker, decisions = wire(root, "demo_weather", [f"api.weather.invalid:{port}"])
    real_getaddrinfo = socket.getaddrinfo

    try:
        with _MediatorResolver({"api.weather.invalid": "127.0.0.1"}):
            broker.resolver = socket.getaddrinfo      # the mediator's side of the boundary
            shim.install()                            # the sandbox's side goes on top

            # Nothing below this line knows the framework exists.
            body = urllib.request.urlopen(
                f"http://api.weather.invalid:{port}/forecast", timeout=10).read()
            check(body == b'{"temperature": 12.5}',
                  "1. **F2** — urllib reaches a declared host and gets its body back",
                  body.decode(errors="replace"))
            check(decisions and decisions[0].allowed
                  and decisions[0].clause == "/permissions/network/egress/0",
                  "1b. and the connection was permitted by a named clause (F3)",
                  str(decisions[0].clause) if decisions else "no decision")

            # What the *sandbox* saw when it resolved the name.
            entries = socket.getaddrinfo("api.weather.invalid", port)
            address = entries[0][4][0]
            check(ipaddress.ip_address(address) in PLACEHOLDER_NET,
                  "2. the sandbox is given a placeholder, never a routable address",
                  f"{address} ∈ {PLACEHOLDER_NET}")
            check(shim.name_for(address) == "api.weather.invalid",
                  "2b. and only the shim can map it back to the name")

            refused = None
            try:
                urllib.request.urlopen(f"http://tracker.invalid:{port}/beacon", timeout=10)
            except urllib.error.URLError as err:
                refused = err
            except EgressDenied as err:
                refused = err
            check(isinstance(refused, urllib.error.URLError),
                  "3. an undeclared host fails as a network error, not a framework exception",
                  type(refused).__name__ if refused else "it succeeded")
    finally:
        shim.uninstall()
        socket.getaddrinfo = real_getaddrinfo
        server.shutdown()


# -- 4: the asynchronous path, which four of six integrations' API names take (§7.31.11) --

def case_aiohttp(root: Path) -> None:
    try:
        import aiohttp
    except ImportError:
        skip("4. aiohttp reaches a declared host", "aiohttp is not installed here")
        return
    import asyncio

    server, port = api_server()
    shim, broker, _decisions = wire(root, "demo_async", [f"api.async.invalid:{port}"])
    real_getaddrinfo = socket.getaddrinfo

    async def fetch() -> bytes:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://api.async.invalid:{port}/x") as response:
                return await response.read()

    try:
        with _MediatorResolver({"api.async.invalid": "127.0.0.1"}):
            broker.resolver = socket.getaddrinfo
            shim.install()
            body = asyncio.run(asyncio.wait_for(fetch(), timeout=15))
            check(body == b'{"temperature": 12.5}',
                  "4. aiohttp reaches a declared host — the seam §5.10.3 would have missed",
                  body.decode(errors="replace"))
            check(shim.connected and shim.connected[-1][0] == "api.async.invalid",
                  "4b. and it went through the mediator rather than round it",
                  str(shim.connected[-1:]))
    except Exception as err:  # noqa: BLE001 — a failure here is a result, not a crash
        check(False, "4. aiohttp reaches a declared host", f"{type(err).__name__}: {err}")
    finally:
        shim.uninstall()
        socket.getaddrinfo = real_getaddrinfo
        server.shutdown()


# -- 5: the dividing line ----------------------------------------------------------------

def case_real_address_not_intercepted(root: Path) -> None:
    """A destination the shim never issued is left alone. In the sandbox it then fails, because
    the network namespace has no route — which is the point: the shim is compatibility and the
    namespace is security."""
    server, port = api_server()
    shim, _broker, decisions = wire(root, "demo_direct", [f"api.direct.invalid:{port}"])

    try:
        shim.install()
        # Straight to a real address, no name involved. Outside a sandbox this succeeds, which
        # is what the assertion below records: the shim did not touch it and asked nobody.
        direct = socket.create_connection(("127.0.0.1", port), timeout=5)
        direct.close()
        check(not decisions,
              "5. a connection to a real address is not intercepted and consults no manifest",
              f"{len(decisions)} decisions made")
        check(not shim.connected,
              "5b. and the mediator opened nothing on its behalf",
              "security is the namespace; the shim is compatibility")
    finally:
        shim.uninstall()
        server.shutdown()


def main() -> int:
    print(__doc__.strip().splitlines()[0])
    print("=" * 78)
    with tempfile.TemporaryDirectory(prefix="confine-shim-") as tmp:
        root = Path(tmp)
        case_urllib(root)
        case_aiohttp(root)
        case_real_address_not_intercepted(root)
    passed = sum(1 for ok, _ in _results if ok)
    print("=" * 78)
    print(f"{passed}/{len(_results)} checks passed")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
