"""Mediated egress: the manifest gates a destination, and the check cannot be raced.

§5.8.2's scope item 2. Covers the four things that make this F2 and S4 rather than a proxy:

  1  a declared host:port is permitted and the connection works
  2  an undeclared host is denied, naming its clause (F3)
  3  **S4** — two integrations at once, and one is denied a host the *other* declared
  4  **T10/T11** — a name resolving to a non-public address is refused after resolution

Case 3 is the one §2.4.2's closest prior work structurally cannot satisfy: it consolidates every
plug-in's declarations into one gateway-level profile, so the effective policy for any plug-in is
the union of all of them. Two integrations with different declared hosts is the smallest
demonstration that this design does not share that limitation, and §5.8.2 says so in advance.

Case 4 is T11 with the roles reversed from the usual telling. The manifest granted a *name*; by
the time anything connects, the name is an address, and a name whose address changed between the
grant and the use is exactly the attack. So the non-public check runs against the resolved
address on every connection, never against the name and never once at parse time.

**No network is required.** Destinations are local listeners and the resolver is substituted, so
the test measures the decision path rather than the internet's availability — and it therefore
still means something on a machine with no route out.

Run: `python3 -m confine.selftest_egress`
"""

from __future__ import annotations

import json
import socket
import sys
import tempfile
import threading
from pathlib import Path

try:
    from .egress import EgressBroker, EgressRefused, is_public
    from .manifest import Manifest, ManifestRejected, policy_for
except ImportError:  # run as a plain script
    from egress import EgressBroker, EgressRefused, is_public
    from manifest import Manifest, ManifestRejected, policy_for


PASS, FAIL = "  ok  ", " FAIL "
_results: list[tuple[bool, str]] = []


def check(condition: bool, name: str, detail: str = "") -> None:
    _results.append((bool(condition), name))
    print(f"[{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def listener(greeting: bytes) -> tuple[socket.socket, int]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(4)

    def serve() -> None:
        while True:
            try:
                conn, _ = sock.accept()
            except OSError:
                return
            conn.sendall(greeting)
            conn.close()

    threading.Thread(target=serve, daemon=True).start()
    return sock, sock.getsockname()[1]


def component(root: Path, domain: str, permissions: dict) -> Manifest:
    directory = root / "custom_components" / domain
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "__init__.py").write_text("# nothing\n")
    (directory / "manifest.json").write_text(json.dumps(
        {"domain": domain, "name": domain, "version": "1.0.0",
         "permissions": {"schema_version": 1, **permissions}}))
    return Manifest.load(directory, root)


class _Resolver:
    """Stands in for DNS so a name can be made to resolve wherever a case needs it.

    Substituted rather than mocked at the socket layer: the broker calls `getaddrinfo` once, and
    replacing that one call is enough to drive every case without the test needing a network or
    a hosts file it would have to clean up.
    """

    def __init__(self, table: dict[str, str]) -> None:
        self.table = table
        self.real = socket.getaddrinfo

    def __enter__(self) -> _Resolver:
        def getaddrinfo(host, port, *args, **kwargs):
            if host in self.table:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "",
                         (self.table[host], port))]
            return self.real(host, port, *args, **kwargs)
        socket.getaddrinfo = getaddrinfo
        return self

    def __exit__(self, *_exc) -> None:
        socket.getaddrinfo = self.real


# -- 1-2: a declared destination works, an undeclared one is refused --------------------

def case_declared_and_undeclared(root: Path) -> None:
    server, port = listener(b"weather-api")
    manifest = component(root, "demo_weather",
                         {"network": {"egress": [f"api.weather.invalid:{port}"]}})
    policy = policy_for({"demo_weather": manifest})
    broker = EgressBroker()

    with _Resolver({"api.weather.invalid": "127.0.0.1",
                    "tracker.invalid": "127.0.0.1"}):
        # allow_private is a **test-harness** decision here, passed as a parameter to
        # `broker.open` — never through the request, which is exactly the field a hostile
        # sandbox could otherwise have set on itself (the bug `egress.py` records fixing).
        request = {"op": "network.egress", "host": "api.weather.invalid", "port": port}
        decision = policy("demo_weather", request)
        check(decision.allowed, "1. the declared host:port is permitted",
              f"clause {decision.clause}")

        fd, record = broker.open("demo_weather", request, decision, allow_private=True)
        received = socket.socket(fileno=fd)
        greeting = received.recv(32)
        received.close()
        check(greeting == b"weather-api",
              "1b. and the descriptor handed back is a live connection to it",
              greeting.decode(errors="replace"))

        undeclared = {"op": "network.egress", "host": "tracker.invalid", "port": port}
        refusal = policy("demo_weather", undeclared)
        check(not refusal.allowed, "2. an undeclared host is denied")
        check(refusal.clause == "/permissions/network/egress",
              "2b. and the denial names the capability that held no matching clause (F3)",
              str(refusal.clause))

        raised = None
        try:
            broker.open("demo_weather", undeclared, refusal, allow_private=True)
        except EgressRefused as err:
            raised = err
        check(raised is not None,
              "2c. the broker refuses to act on a denial rather than connecting anyway",
              raised.reason if raised else "it connected")

    server.close()


# -- 3: S4, the row the closest prior work cannot fill ----------------------------------

def case_s4_two_integrations(root: Path) -> None:
    server_a, port_a = listener(b"host-a")
    server_b, port_b = listener(b"host-b")

    a = component(root, "demo_a", {"network": {"egress": [f"a.invalid:{port_a}"]}})
    b = component(root, "demo_b", {"network": {"egress": [f"b.invalid:{port_b}"]}})
    policy = policy_for({"demo_a": a, "demo_b": b})
    broker = EgressBroker()

    with _Resolver({"a.invalid": "127.0.0.1", "b.invalid": "127.0.0.1"}):
        own = policy("demo_a", {"op": "network.egress", "host": "a.invalid", "port": port_a})
        check(own.allowed, "3. demo_a reaches the host demo_a declared")

        # The point of S4. `demo_b` declared this host; `demo_a` did not. A design that
        # consolidates declarations into one profile permits it, because the union contains it.
        borrowed = policy("demo_a", {"op": "network.egress", "host": "b.invalid",
                                     "port": port_b})
        check(not borrowed.allowed,
              "3b. **S4** — demo_a is denied a host declared only by demo_b",
              borrowed.reason)

        # The same host, the same port, the same request — and a different answer, because the
        # identity is different. That is what makes 3b attribution rather than a block list.
        mine_request = {"op": "network.egress", "host": "b.invalid", "port": port_b}
        mine = policy("demo_b", mine_request)
        check(mine.allowed and not borrowed.allowed,
              "3c. and demo_b reaches that same host, so 3b is attribution not a block",
              f"demo_b {mine.clause}; demo_a denied at {borrowed.clause}")

        # Identity comes from the socket the request arrived on, so a request that *claims* to
        # be the other integration changes nothing (§5.11.2). Worth asserting here rather than
        # only in selftest_channel, because egress is the capability worth lying for.
        lying = policy("demo_a", {"op": "network.egress", "host": "b.invalid",
                                  "port": port_b, "integration": "demo_b"})
        check(not lying.allowed,
              "3d. and claiming to be demo_b in the request body does not help",
              lying.reason)

        fd, _ = broker.open("demo_b", mine_request, mine, allow_private=True)
        received = socket.socket(fileno=fd)
        check(received.recv(16) == b"host-b",
              "3e. both integrations run against their own destinations concurrently")
        received.close()

    server_a.close()
    server_b.close()


# -- 4: T10 and T11 ---------------------------------------------------------------------

def case_t10_t11(root: Path) -> None:
    server, port = listener(b"internal")
    manifest = component(root, "demo_rebind",
                         {"network": {"egress": [f"innocent.invalid:{port}"]}})
    policy = policy_for({"demo_rebind": manifest})
    broker = EgressBroker()

    check(is_public("93.184.216.34"), "4. a routable address is public")
    # F58: 100.64.0.0/10, RFC 6598's shared address space (carrier-grade NAT, and Tailscale),
    # is neither private nor global, and passed as public until 2026-10-10. Listed first so
    # that the loop, which stops at the first public address, names it.
    for address in ("100.64.0.1", "100.127.255.254", "::ffff:100.64.0.1",
                    "127.0.0.1", "192.168.1.50", "10.0.0.1", "169.254.1.1",
                    "::1", "fe80::1", "::ffff:192.168.1.1", "0.0.0.0"):
        if is_public(address):
            check(False, f"4b. {address} must not count as public")
            break
    else:
        check(True, "4b. loopback, private, link-local, shared address space and IPv4-mapped "
                    "are all non-public",
              "including ::ffff:192.168.1.1, which the §7.24 run actually produced")

    # The manifest grants the *name*. The name resolves inward. Nothing about the grant changes.
    with _Resolver({"innocent.invalid": "127.0.0.1"}):
        request = {"op": "network.egress", "host": "innocent.invalid", "port": port}
        decision = policy("demo_rebind", request)
        check(decision.allowed,
              "4c. the manifest permits the name, because a manifest can only speak of names")

        raised = None
        try:
            broker.open("demo_rebind", request, decision)
        except EgressRefused as err:
            raised = err
        check(raised is not None and "not a public address" in raised.reason,
              "4d. **T11** — and the connection is refused on the resolved address",
              raised.reason if raised else "it connected to loopback")

    server.close()


# -- 4e: the bug this design caught in itself ---------------------------------------------

def case_allow_private_is_not_request_controlled(root: Path) -> None:
    """A hostile integration cannot grant itself T10's reach by writing one key into its own
    request. `egress.py`'s docstring records that the first version of `EgressBroker.open`
    trusted `request.get("allow_private")` — a field the sandbox controls — which would have
    let any integration bypass the non-public check simply by asking to. This is the check
    that the fix holds under exactly that attempt."""
    server, port = listener(b"should-not-be-reachable")
    manifest = component(root, "demo_hostile",
                         {"network": {"egress": [f"innocent.invalid:{port}"]}})
    policy = policy_for({"demo_hostile": manifest})
    broker = EgressBroker()

    with _Resolver({"innocent.invalid": "127.0.0.1"}):
        # The attempt: set allow_private in the request body itself, as a hostile integration
        # would if this were exposed to it. `broker.open` is called with no `allow_private`
        # keyword, exactly as `acting_policy` calls it in production.
        lying_request = {"op": "network.egress", "host": "innocent.invalid", "port": port,
                         "allow_private": True}
        decision = policy("demo_hostile", lying_request)
        check(decision.allowed, "4e. the manifest still permits the declared name")

        raised = None
        try:
            broker.open("demo_hostile", lying_request, decision)   # no allow_private kwarg
        except EgressRefused as err:
            raised = err
        check(raised is not None and "not a public address" in raised.reason,
              "4e. **fixed** — a request-supplied allow_private is ignored; T10 still refuses",
              raised.reason if raised else "it connected to loopback — the bug is back")

    server.close()


# -- 5: the schema change itself ---------------------------------------------------------

def case_schema(root: Path) -> None:
    def rejected(entry: str) -> str | None:
        try:
            component(root, "demo_schema", {"network": {"egress": [entry]}})
        except ManifestRejected as err:
            return str(err)
        return None

    check(rejected("api.example.com") is not None,
          "5. a host with no port is rejected at parse time",
          "a host alone grants all 65,535 of its ports")
    check(rejected("*.example.com:443") is not None,
          "5b. a wildcard host is rejected")
    check(rejected("api.example.com:0") is not None, "5c. port 0 is rejected")
    check(rejected("api.example.com:99999") is not None, "5d. a port above 65535 is rejected")
    check(rejected("api.example.com:443") is None, "5e. host:port is accepted")
    check(rejected("[::1]:8123") is None,
          "5f. a bracketed IPv6 literal is accepted, its colons not mistaken for the port")

    # A request that names no port cannot be matched against a clause that names one, and must
    # not be quietly widened to 443 — a default would grant whichever port the framework guessed.
    manifest = component(root, "demo_noport", {"network": {"egress": ["api.example.com:443"]}})
    policy = policy_for({"demo_noport": manifest})
    portless = policy("demo_noport", {"op": "network.egress", "host": "api.example.com"})
    check(not portless.allowed,
          "5g. a request naming no port is denied rather than defaulted",
          portless.reason)


def main() -> int:
    print(__doc__.strip().splitlines()[0])
    print("=" * 78)
    with tempfile.TemporaryDirectory(prefix="confine-egress-") as tmp:
        root = Path(tmp)
        case_declared_and_undeclared(root)
        case_s4_two_integrations(root)
        case_t10_t11(root)
        case_allow_private_is_not_request_controlled(root)
        case_schema(root)
    passed = sum(1 for ok, _ in _results if ok)
    print("=" * 78)
    print(f"{passed}/{len(_results)} checks passed")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
