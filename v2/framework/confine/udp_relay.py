"""Datagrams, relayed rather than handed over — and why that asymmetry exists.

TCP egress passes a connected descriptor into the sandbox (`egress.py`) because a connected TCP
socket cannot be re-pointed. **A connected UDP socket can.** `sendto` naming another address on
one delivers there, on x86_64 and aarch64 alike, and `selftest_socket_pinning.py` is the standing
evidence. Handing a UDP socket to a sandbox would have let an integration granted one lamp send
datagrams to every host on the home network — T10, delivered by the control written to prevent it.

So datagrams never cross the boundary as descriptors. The mediator owns every UDP socket and the
sandbox asks it to send and to hand back what arrived.

## The three operations, and the clause each answers to

| Operation | Clause | What the mediator does |
|---|---|---|
| `udp.send` / `udp.recv` | `network/local/udp` | a socket per pinned peer, connected, so its **inbound** filter is the kernel's (that half of the pinning does hold) |
| `discover.scan` | `network/discover/scan` | broadcasts the sandbox's payload on a declared port and returns what answered |
| `discover.listen` | `network/discover/listen` | binds a declared port and returns what arrives |

## What this costs, stated because it is the honest half

Relaying means the destination check lives in **this code** rather than in the kernel. TCP's
guarantee survives a bug in the relay loop; UDP's does not. `notes/decision_network_capability.md`
§8 records that asymmetry as a residual rather than letting the word "structural" cover both.

And the sandbox side can only be transparent to integrations that use datagrams **synchronously**
— `sendto` and `recvfrom` on a socket object, which `egress_shim` can intercept. An integration
driving `asyncio.DatagramProtocol` selects on a real descriptor, and under this design there
isn't one. Of the fifteen integrations in `results/udp_demand.md`, **four** take that route
(`govee`, `localtuya`, `tapo_control`, `xiaomi_miot`) and are not served. That is a limitation
with a number rather than an omission, and §6.11.1's rule applies: report which half is missing
instead of a figure that hides it.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass, field

from .egress import EgressRefused
from .mediator import Decision

# **The real socket methods, captured at import.** The mediator is the trusted side of this
# boundary and must not be subject to the sandbox's shim: `egress_shim` patches `send`,
# `sendto`, `recvfrom`, `bind` and `setsockopt` on `socket.socket`, and in a process where both
# live the relay would call the sandbox's patches and recurse until the stack ran out. It did,
# the first time this was tested.
#
# In deployment the two are separate processes and it cannot arise — the mediator imports this
# module before any sandbox exists. Capturing the originals here says which side of the boundary
# this code belongs to instead of relying on the process split to say it, which is the same
# lesson `EgressBroker.resolver` records for resolution.
_SEND = socket.socket.send
_SENDTO = socket.socket.sendto
_RECV = socket.socket.recv
_RECVFROM = socket.socket.recvfrom
_BIND = socket.socket.bind
_CONNECT = socket.socket.connect
_SETSOCKOPT = socket.socket.setsockopt

#: A relayed datagram is copied into the mediator's memory, so its size is the sandbox's to
#: choose and therefore has to be bounded. Larger than any device-discovery payload in the
#: corpus and far below anything that would matter to `memory_mb`.
MAX_DATAGRAM = 65507

#: How many datagrams the mediator will hold for a sandbox that has asked for none of them yet.
#: A discovery scan on a busy network answers faster than an integration reads, and a queue
#: without a bound is a sandbox's way of spending the mediator's memory instead of its own.
QUEUE_LIMIT = 64

#: A scan or a listen occupies a real socket for its duration. Bounded so that a sandbox cannot
#: hold one open indefinitely, and generous enough for the slowest device in the corpus to answer.
MAX_WAIT = 5.0


@dataclass
class UdpRelay:
    """Owns every UDP socket on behalf of every sandbox.

    Keyed by `(identity, host, port)` rather than by anything the request says about itself, for
    the reason §5.11.2 gives about the channel: the identity came from the socket the request
    arrived on, and a handle the sandbox names is a claim.
    """

    #: Per-peer connected sockets, so the kernel drops datagrams from anyone but the pinned peer.
    peers: dict[tuple[str, str, int], socket.socket] = field(default_factory=dict)
    #: Every datagram sent and every scan performed, for the audit record.
    activity: list[dict] = field(default_factory=list)

    # -- unicast ------------------------------------------------------------------------

    def send(self, identity: str, request: dict, decision: Decision) -> dict:
        """One datagram to a pinned peer."""
        if not decision.allowed:
            raise EgressRefused(decision.reason, decision.clause)
        address = request.get("address")
        port = request.get("port")
        data = request.get("data")
        if not isinstance(address, str) or not isinstance(port, int):
            raise EgressRefused("a datagram must name an address and a port", decision.clause)
        payload = _decode(data, decision.clause)

        # **No `is_public` check here, and that is deliberate rather than an omission.**
        # `network.egress` is the internet-host clause and T10 restricts it to public
        # addresses. `network.local.udp` is a different clause with a different meaning: it
        # exists *specifically* to reach a device on the home network, so a private address is
        # what this operation is for, not an exception to it. Gating is done once, upstream,
        # by whether the `local` clause matches at all (`manifest.py`'s `decide`) — there is no
        # second, request-controlled gate to bypass here the way the egress path had.
        sock = self._peer(identity, address, port)
        _SEND(sock, payload)
        self.activity.append({"identity": identity, "op": "udp.send", "address": address,
                              "port": port, "bytes": len(payload), "clause": decision.clause})
        return {"ok": True, "sent": len(payload), "clause": decision.clause}

    def recv(self, identity: str, request: dict, decision: Decision) -> dict:
        """Whatever the pinned peer has sent back, up to the queue limit."""
        if not decision.allowed:
            raise EgressRefused(decision.reason, decision.clause)
        address, port = request.get("address"), request.get("port")
        key = (identity, str(address), int(port) if isinstance(port, int) else -1)
        sock = self.peers.get(key)
        if sock is None:
            return {"ok": True, "datagrams": [], "clause": decision.clause}

        wait = min(float(request.get("timeout", 0.5)), MAX_WAIT)
        return {"ok": True, "clause": decision.clause,
                "datagrams": _drain(sock, wait, expect_address=False)}

    def _peer(self, identity: str, address: str, port: int) -> socket.socket:
        """A connected socket per peer.

        Connected even though `sendto` could reach the same place, because the **receive** half
        of the pinning is real: a connected UDP socket drops datagrams from anyone but its peer,
        in the kernel. So the relay never has to decide in software whether an inbound datagram
        came from the right device — which is one fewer check to write wrong, in the one place
        this design has to fall back on checks at all.
        """
        key = (identity, address, port)
        sock = self.peers.get(key)
        if sock is None:
            sock = socket.socket(socket.AF_INET6 if ":" in address else socket.AF_INET,
                                 socket.SOCK_DGRAM)
            _CONNECT(sock, (address, port))
            sock.setblocking(False)
            self.peers[key] = sock
        return sock

    # -- discovery ----------------------------------------------------------------------

    def scan(self, identity: str, request: dict, decision: Decision) -> dict:
        """Broadcast the sandbox's payload on a declared port and return what answered.

        **The sandbox never holds a broadcast-capable socket.** It supplies opaque bytes and a
        port it declared; the mediator sets `SO_BROADCAST` on its own socket, sends, waits a
        bounded time and returns the replies with their addresses. So the capability is a
        request the mediator performs and records, not a socket the sandbox owns — which is
        what makes it rate-limitable, time-bounded and attributable at all.

        `results/broadcast_fallbacks.md` is why this exists rather than being refused: three of
        the four integrations that broadcast do it only to avoid asking the user for an address,
        and making a non-expert find a device's IP is a networking task pushed onto exactly the
        person who cannot do it.
        """
        if not decision.allowed:
            raise EgressRefused(decision.reason, decision.clause)
        port = request.get("port")
        if not isinstance(port, int):
            raise EgressRefused("a scan must name a port", decision.clause)
        payload = _decode(request.get("data", ""), decision.clause)
        wait = min(float(request.get("timeout", 1.0)), MAX_WAIT)
        target = str(request.get("broadcast", "255.255.255.255"))

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            _SETSOCKOPT(sock, socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setblocking(False)
            if payload:
                _SENDTO(sock, payload, (target, port))
            answers = _drain(sock, wait, expect_address=True)
        finally:
            sock.close()

        self.activity.append({"identity": identity, "op": "discover.scan", "port": port,
                              "responses": len(answers), "clause": decision.clause})
        # The addresses that answered are the only ones this integration may later be pinned to
        # (`decision_network_capability.md` §4): a machine that does not speak the protocol
        # cannot be reached merely by naming it.
        return {"ok": True, "responses": answers, "clause": decision.clause,
                "observed": sorted({a["address"] for a in answers})}

    def listen(self, identity: str, request: dict, decision: Decision) -> dict:
        """Bind a declared port and return what arrives. Sends nothing, reaches nothing."""
        if not decision.allowed:
            raise EgressRefused(decision.reason, decision.clause)
        port = request.get("port")
        if not isinstance(port, int):
            raise EgressRefused("a listen must name a port", decision.clause)
        wait = min(float(request.get("timeout", 1.0)), MAX_WAIT)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            _SETSOCKOPT(sock, socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            _BIND(sock, ("", port))
            sock.setblocking(False)
            answers = _drain(sock, wait, expect_address=True)
        except OSError as err:
            raise EgressRefused(f"cannot listen on {port}: {err.strerror or err}",
                                decision.clause) from err
        finally:
            sock.close()

        self.activity.append({"identity": identity, "op": "discover.listen", "port": port,
                              "datagrams": len(answers), "clause": decision.clause})
        return {"ok": True, "responses": answers, "clause": decision.clause,
                "observed": sorted({a["address"] for a in answers})}

    def close(self) -> None:
        for sock in self.peers.values():
            sock.close()
        self.peers.clear()


def _drain(sock: socket.socket, wait: float, expect_address: bool) -> list[dict]:
    """Collect datagrams for a bounded time, up to a bounded count.

    Both bounds are the sandbox's exposure to the network rather than to the mediator: a busy
    discovery port answers faster than any integration reads, and an unbounded collection would
    let whatever is on the network decide how much of the mediator's memory this costs.
    """
    import selectors
    import time

    answers: list[dict] = []
    deadline = time.monotonic() + wait
    selector = selectors.DefaultSelector()
    selector.register(sock, selectors.EVENT_READ)
    try:
        while len(answers) < QUEUE_LIMIT:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                break
            try:
                if expect_address:
                    data, sender = _RECVFROM(sock, MAX_DATAGRAM)
                    answers.append({"address": sender[0], "port": sender[1],
                                    "data": data.hex()})
                else:
                    data = _RECV(sock, MAX_DATAGRAM)
                    answers.append({"data": data.hex()})
            except OSError:
                break
    finally:
        selector.close()
    return answers


def _decode(data: object, clause: str | None) -> bytes:
    """Payloads cross the channel as hex, because the channel is JSON (§5.11.3).

    Bounded before it is decoded rather than after: the length is the sandbox's claim about how
    much memory the mediator should allocate, which is the same reasoning `channel.py` applies
    to a frame's declared length.
    """
    if not isinstance(data, str):
        raise EgressRefused("a datagram payload must be a hex string", clause)
    if len(data) > MAX_DATAGRAM * 2:
        raise EgressRefused(f"payload of {len(data) // 2} bytes exceeds {MAX_DATAGRAM}", clause)
    try:
        return bytes.fromhex(data)
    except ValueError as err:
        raise EgressRefused(f"payload is not hex: {err}", clause) from err
