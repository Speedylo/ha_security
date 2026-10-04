"""The mediator's side of outbound network: resolve, check, connect, hand over.

§5.8.2's scope item 2, built against §7.24's measurements rather than §5.10.3's assumptions.
`notes/decision_network_capability.md` is the design; this is the TCP half of it.

## The order, and why it is this order

    1. Decide   — the manifest, against host **and** port (§7.24.3)
    2. Resolve  — the mediator does it, itself, now
    3. Re-check — the resolved address against T10's non-public rule
    4. Connect  — to the address just checked, with no gap in between
    5. Hand over — the connected descriptor crosses the channel

**Steps 2 and 4 are adjacent on purpose, and that adjacency is the whole of T11.** The classic
attack against a name-based policy is to have a name resolve to something innocuous when it is
checked and to something internal when it is used. Here there is no interval between the two:
the same call site resolves the name and connects to the address it got back, and the sandbox
never possesses a routable address at all — its resolver returns a placeholder only the mediator
can map back (§7.24.2). So resolve-then-pin is not a rule this code follows carefully; it is a
shape the code cannot easily be written any other way.

§5.10.5 argues the same thing for the filesystem, and the two exist for one reason: **a name is
not the thing it names, and checking the name is not checking the thing.**

## Why only TCP travels as a descriptor

A connected TCP socket cannot be re-pointed: `sendto` naming another address has its address
ignored, and a second `connect` is refused with `EISCONN`. A connected **UDP** socket has no such
property — `sendto` naming another address delivers there. That was asserted, tested, and found
false, on both architectures; `selftest_socket_pinning.py` is the standing evidence. Handing a
UDP socket over would have let an integration granted one lamp reach every host on the network,
so UDP is relayed instead and this module does not serve it.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass, field
from typing import Callable

from .mediator import Decision

# A connect that never completes must not become a sandbox's way of occupying the mediator.
# §7.19 measured mediation at 0.009% utilisation with three to four orders of magnitude of
# headroom, so this bound is about liveness under a hostile or broken destination, not about
# throughput.
CONNECT_TIMEOUT = 10.0


class EgressRefused(Exception):
    """The destination was refused. Carries the clause or rule that refused it (F3)."""

    def __init__(self, reason: str, clause: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.clause = clause


def is_public(address: str) -> bool:
    """Is this an address the internet routes to?

    T10 is *"integration reaches other devices on the home LAN, or loopback services on the
    gateway"*, and this is the predicate that decides it. Everything the `ipaddress` module
    knows to be special is refused: private ranges, loopback, link-local, multicast, reserved,
    and the unspecified address.

    IPv4-mapped IPv6 is unwrapped first. `::ffff:192.168.1.1` is a private address wearing an
    IPv6 costume, and a check that looked only at the outer form would pass it — the §7.24 run
    recorded exactly that shape (`::ffff:192.168.11.109`) coming out of the platform's own
    discovery, so it is not hypothetical.
    """
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped is not None:
        parsed = parsed.ipv4_mapped
    return not (parsed.is_private or parsed.is_loopback or parsed.is_link_local
                or parsed.is_multicast or parsed.is_reserved or parsed.is_unspecified)


def is_lan(address: str) -> bool:
    """Is this a device on the home network — the only kind of address `network.tcp.local` reaches?

    Private (RFC 1918, and IPv6 unique-local), and **none** of the special ranges a private check
    also matches: not loopback; not link-local; not multicast, reserved or unspecified.

    **What refusing loopback protects, stated precisely** (review of W2, 2026-10-04): services the
    mediator's host binds to loopback **only**, such as the house's Home Assistant on 127.0.0.1:8123.
    The host also has an address on the home network, and anything it serves on *all* interfaces is
    reachable there on a declared port, exactly as any other device on the network is. That is the
    ceiling `decision_network_capability.md` §4.1 states, and W2 (a)'s own fake devices sat on the
    Pi's LAN address. An earlier version of this docstring said loopback was "the mediator's own host
    and its services", which overclaimed. IPv4-mapped IPv6 is unwrapped first, for
    the reason `is_public` gives. W2 (a), 2026-10-04.
    """
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped is not None:
        parsed = parsed.ipv4_mapped
    return parsed.is_private and not (parsed.is_loopback or parsed.is_link_local
                                      or parsed.is_multicast or parsed.is_reserved
                                      or parsed.is_unspecified)


@dataclass
class EgressBroker:
    """Opens outbound connections on behalf of sandboxes that are permitted them.

    Holds no policy of its own: the decision comes from the manifest through the mediator, and
    this class refuses to act without one. That separation is why the T10 re-check below is the
    *only* judgement it makes, and why that judgement is about an address rather than a name.
    """

    connect_timeout: float = CONNECT_TIMEOUT
    #: Every destination actually connected, for the audit record and for §7.24's evaluation.
    opened: list[dict] = field(default_factory=list)
    #: **The mediator resolves with its own resolver, not with whatever is globally installed.**
    #: In deployment the distinction is invisible — the sandbox's shim lives in another process
    #: entirely — but stating it here removes a whole class of confusion, and it had to be
    #: stated: co-locating the two in one test process made the broker call the sandbox's
    #: patched `getaddrinfo`, which returned a placeholder, which resolved to a placeholder,
    #: until the stack ran out. Defaults to the real one when not supplied.
    resolver: Callable[..., list] | None = None

    def open(self, identity: str, request: dict, decision: Decision,
             allow_private: bool = False) -> tuple[int, dict]:
        """Steps 2-5. Returns the connected descriptor and what to record about it.

        `decision` is step 1's answer and is not re-derived here — a component that both
        decides and acts can disagree with itself, and §5.11.3 puts the decision first for
        exactly that reason.

        **`allow_private` is a parameter the caller decides, never a field the request can
        set.** `network.egress` is the internet-host clause; §5.10.3's non-public destinations
        go through `network.local` instead, which is a different clause with a different
        target shape. The first version of this method read `request.get("allow_private")` —
        a field the **sandbox** controls — which meant a hostile integration could grant
        itself T10's reach by writing one key into its own request. Caught before it shipped:
        `acting_policy` (`platform.py`) calls this with the default for `network.egress` and
        never forwards anything the request said about privacy.
        """
        if not decision.allowed:
            raise EgressRefused(decision.reason, decision.clause)

        host = request.get("host")
        port = request.get("port")
        if not isinstance(host, str) or not isinstance(port, int):
            raise EgressRefused("a request must name a host and a port", decision.clause)

        # Step 2. The mediator resolves. The sandbox has no resolver that reaches anything and
        # never sees a real address, so this is the only resolution that happens.
        resolve = self.resolver or socket.getaddrinfo
        try:
            candidates = resolve(host, port, type=socket.SOCK_STREAM)
        except OSError as err:
            raise EgressRefused(f"{host} does not resolve: {err.strerror or err}",
                                decision.clause) from err

        errors: list[str] = []

        for family, socktype, proto, _canonical, sockaddr in candidates:
            address = sockaddr[0]

            # Step 3. **Checked after resolution, against the address, every time.** A name that
            # resolved to a public address a moment ago may resolve to 127.0.0.1 now, and it is
            # this check rather than the manifest's that notices — the manifest granted a name.
            if not allow_private and not is_public(address):
                errors.append(f"{address} is not a public address")
                continue

            # Step 4. Connect to the address just checked. Nothing between the two lines.
            sock = socket.socket(family, socktype, proto)
            try:
                sock.settimeout(self.connect_timeout)
                sock.connect(sockaddr)
                sock.settimeout(None)
            except OSError as err:
                sock.close()
                errors.append(f"{address}: {err.strerror or err}")
                continue

            record = {"identity": identity, "host": host, "port": port,
                      "address": address, "clause": decision.clause}
            self.opened.append(record)
            return sock.detach(), record

        # Every candidate refused or unreachable. The reason names which, because "connection
        # failed" is not a diagnosis and T10 refusals must be distinguishable from a device
        # being switched off.
        raise EgressRefused(
            f"no permitted address for {host}:{port} — " + "; ".join(errors[:4]),
            decision.clause)


    def open_local(self, identity: str, request: dict, decision: Decision) -> tuple[int, dict]:
        """`network.tcp.local`: connect to a device on the home network, on a declared port.

        Built in W2 (a), 2026-10-04: until then the capability existed in the manifest schema
        only, and every confined integration reaching a LAN device over TCP failed closed
        (`notes/w2a_local_tcp_prediction.md` §1). The manifest has already decided on the
        **port**. What is checked here is the **address**, and only a home-network address is
        accepted (`is_lan`). The sandbox's own test merely decides what to route here, and it is
        not trusted for this. A successful connection pins the address
        (`decision_network_capability.md` §4, the manual-entry case), and the pin is what
        `opened` and the durable record carry.
        """
        if not decision.allowed:
            raise EgressRefused(decision.reason, decision.clause)
        address, port = request.get("address"), request.get("port")
        if not isinstance(address, str) or not isinstance(port, int):
            raise EgressRefused("a request must name an address and a port", decision.clause)
        if not is_lan(address):
            raise EgressRefused(f"{address} is not an address on the home network",
                                decision.clause)
        parsed = ipaddress.ip_address(address)
        family = socket.AF_INET6 if parsed.version == 6 else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.connect_timeout)
            sock.connect((address, port))
            sock.settimeout(None)
        except OSError as err:
            sock.close()
            raise EgressRefused(f"{address}:{port}: {err.strerror or err}",
                                decision.clause) from err
        record = {"identity": identity, "host": address, "port": port, "address": address,
                  "clause": decision.clause, "pinned": "manual entry: first connection"}
        self.opened.append(record)
        return sock.detach(), record


def egress_response(record: dict) -> dict:
    """What the sandbox is told about a connection it was granted.

    It learns the **name it asked for** and not the address the mediator connected to. Returning
    the address would hand back the one thing the placeholder scheme exists to withhold, and an
    integration has no legitimate use for it: it asked for a name, and it got a working socket
    to that name.
    """
    return {"ok": True, "host": record["host"], "port": record["port"],
            "clause": record["clause"]}
