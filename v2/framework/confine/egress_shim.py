"""The sandbox's side of egress: a name goes out, a connected socket comes back.

The integration is unmodified (C1), so this has to meet it where it already is — at the two
points every Python network stack passes through. §7.24 measured which two, and the answer was
not the one §5.10.3 assumed.

## Why there are two seams and not one

    resolution:  socket.getaddrinfo   ·  aiohttp's resolver (over aiodns)
    connection:  socket.socket.connect

Home Assistant gives every client session an `AsyncDualMDNSResolver` built on `aiodns`
(`aiohttp_client.py:479`), and `aiodns` resolves through `pycares` in C without ever calling
`getaddrinfo`. Of six integrations that resolved their own API's hostname, **four went that way**
(§7.31.11) — the platform's client session — and two, on `httpx` and `requests`, went through
`getaddrinfo`. A shim watching either seam alone misses names integrations actually use.

(§7.24 first reported 96% — 3,073 of 3,193. That figure was the platform's `dhcp` discovery doing
reverse lookups across a /24 LAN, attributed to the integrations; without it the share is 17%.)

The other half of the finding is worse for a naive design: **the name does not survive to the
connection.** By the time `connect` is called the destination is an address — the §7.24 recorder
caught `pirateweather` connecting to `108.157.98.116:443` with no hostname anywhere in the call —
and resolution and connection happen in *different libraries* that share nothing. So an
enforcement point at the resolver has a name it cannot connect, and one at the connection has an
address it cannot judge.

## The placeholder, which is what joins them

Resolution returns an address from `240.0.0.0/4` — reserved, unroutable, and meaningless outside
this sandbox. The shim remembers which name it stands for. When the integration connects to that
placeholder, the shim recovers the name and asks the mediator for it.

The security property falls out of the mechanism rather than being checked by it: **the sandbox
never holds a routable address at any point.** The classic attack on a name-based policy is to
have a name check as innocuous and resolve as internal in the gap between the two — here there is
no gap, and nothing in the sandbox to substitute. §5.10.5 makes the same argument for paths, for
the same reason: *a name is not the thing it names.*

## What is deliberately not intercepted

A connection to a **real** address — one the shim never issued — falls through to the ordinary
socket call, where it fails, because the sandbox's network namespace has no route to anywhere.
That is the design's dividing line and it is worth being explicit about:

    Security is structural — the namespace. Compatibility is best-effort — this shim.

An integration that bypasses the shim does not get unfiltered network; it gets nothing. So the
shim's coverage decides how many *honest* integrations work and never how far a *hostile* one
reaches. That is why an unrecognised destination is left to fail rather than being chased.
"""

from __future__ import annotations

import errno
import ipaddress
import json
import os
import socket
import time
import weakref
from dataclasses import dataclass
from typing import Callable

# Reserved for future use by RFC 1112 and routed by nothing. A placeholder that escaped this
# sandbox would be dropped by the first hop rather than delivered somewhere unintended, which
# is the property wanted from a value that stands in for a real destination.
PLACEHOLDER_NET = ipaddress.ip_network("240.0.0.0/4")


#: Returned by a datagram handler that has decided this call is not its business, so the
#: original socket method runs. A sentinel rather than `None`, because `None` is what several
#: of these calls legitimately return.
_FALL_THROUGH = object()


def _is_broadcast(host: str) -> bool:
    """A destination that reaches every host on the segment rather than one of them.

    `255.255.255.255` and any address ending `.255` — the corpus uses both: `solarman` sends to
    the literal `<broadcast>`, which resolves to the former, and `xiaomi_home` pings
    `255.255.255.255` directly. Multicast counts too, since `govee`'s scan goes to
    `239.255.255.250` and is the same capability wearing a different addressing mode.
    """
    if host in ("255.255.255.255", "<broadcast>"):
        return True
    try:
        parsed = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(parsed.is_multicast) or str(parsed).endswith(".255")


@dataclass
class DatagramMediator:
    """The relay, as four calls the shim can make.

    Injected for the same reason `connect_via` is: it keeps the channel out of this module, so
    the whole loop can be exercised against a real `UdpRelay` with no sandbox and no second
    process, and what is under test stays the emulation rather than the plumbing.
    """

    send: Callable[[str, int, bytes], int]
    recv: Callable[[str, int], list]
    scan: Callable[[int, bytes], list]
    listen: Callable[[int], list]
    #: W2 (b): ask the mediator to bind `port` and push what arrives. Raises if refused.
    listen_stream: Callable[[int], None] | None = None


class EgressDenied(OSError):
    """The mediator refused. Raised as an `OSError` so that unmodified integration code, which
    expects network failures and not framework exceptions, handles it the way it already
    handles a refused connection."""

    def __init__(self, reason: str, clause: str | None = None) -> None:
        super().__init__(errno.ECONNREFUSED, reason)
        self.reason = reason
        self.clause = clause


def _home_network(address: str) -> bool:
    """Routing only: private, and not this sandbox's own loopback, which never leaves it."""
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped is not None:
        parsed = parsed.ipv4_mapped
    return parsed.is_private and not (parsed.is_loopback or parsed.is_unspecified)


class EgressShim:
    """Installed in the sandbox before the integration is imported.

    `connect_via(host, port)` is injected rather than built here: it returns a connected file
    descriptor or raises. Keeping the channel out of this class is what lets the whole loop be
    tested against a real `EgressBroker` with no sandbox, no mediator process and no network.
    """

    def __init__(self, connect_via: Callable[[str, int], int],
                 datagrams: DatagramMediator | None = None,
                 connect_local: Callable[[str, int], int] | None = None) -> None:
        self.connect_via = connect_via
        #: W2 (a): a connection to a device on the home network, by address. Injected for the
        #: same reason as `connect_via`; `None` keeps the old fail-closed behaviour.
        self.connect_local = connect_local
        #: The relay, if this sandbox is permitted datagrams at all. `None` means UDP falls
        #: through to the ordinary socket calls, where it fails — the same fail-closed default
        #: an unrecognised TCP destination gets.
        self.datagrams = datagrams
        self._names: dict[str, str] = {}      # placeholder address -> the name it stands for
        self._placeholders: dict[str, str] = {}   # and back, so a repeat lookup is stable
        self._next = int(PLACEHOLDER_NET.network_address) + 1
        self._installed: list[tuple] = []
        #: Per-socket datagram state. A UDP socket in the sandbox is never connected to anything
        #: — it is a handle the shim keeps notes against. **Keyed by the socket object, weakly,
        #: not by its descriptor number**, and cleared on `close`. Keyed by number, a new socket
        #: that reused a closed one's descriptor inherited its peers and its queued datagrams
        #: (W2 (a), 2026-10-04, found by `selftest_udp` case 2c).
        self._dgram: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        #: Where pushed datagrams go (W2 (b)): ("listen", port) or ("peer", address, port) ->
        #: the writer ends of the sockets routed to it.
        self._routes: dict[tuple, list] = {}
        self.delivered = 0
        #: Every name resolved and every connection made, for the evaluation and for tests.
        self.resolved: list[str] = []
        self.connected: list[tuple[str, int]] = []

    # -- the placeholder map ----------------------------------------------------------

    def placeholder_for(self, host: str) -> str:
        """A stable placeholder per name. Stable because a resolver may be called repeatedly
        for the same host and an integration may cache what it got back; handing out a fresh
        address each time would leave the earlier ones unresolvable."""
        existing = self._placeholders.get(host)
        if existing is not None:
            return existing
        address = str(ipaddress.ip_address(self._next))
        self._next += 1
        self._placeholders[host] = address
        self._names[address] = host
        self.resolved.append(host)
        return address

    def name_for(self, address: str) -> str | None:
        return self._names.get(address)

    # -- installation ------------------------------------------------------------------

    def install(self) -> None:
        self._patch_getaddrinfo()
        self._patch_connect()
        self._patch_datagrams()
        self._patch_aiohttp_resolvers()

    # -- datagrams ---------------------------------------------------------------------

    def _patch_datagrams(self) -> None:
        """Datagrams are relayed, not handed over — and since W2 (b), delivered into a real descriptor.

        TCP could be given a real connected descriptor because a connected TCP socket cannot be
        re-pointed. UDP cannot (`selftest_socket_pinning.py`), so the mediator owns every real UDP
        socket and every send is a request to it.

        **Receiving.** Until W2 (b) a `recvfrom` asked the relay, and an asyncio transport, which
        waits for its descriptor to become readable before it calls `recvfrom` at all, waited for
        ever: §7.25.5's four integrations (`govee`, `localtuya`, `tapo_control`, `xiaomi_miot`)
        were not served. Now each relayed socket is backed by one end of an `AF_UNIX` datagram
        socket pair, put under the integration's own descriptor with `dup2`, and the mediator
        **pushes** what arrives: for a listen, from the port it bound once the listen was granted;
        for a peer, from the connected socket its first permitted send opened. `deliver` writes
        each datagram into the pair, framed with its sender, so the descriptor becomes readable
        exactly as a real one would, and `recvfrom` is a plain read of it — which honours the
        socket's own timeout or non-blocking mode with no emulation at all. The grant is recorded
        once; the datagrams are not, as decision A of W1 step 1 has it for states.

        **What is still not served:** a socket whose event loop registered it before its first
        `bind` or `connect` (a `sendto` comes too late). `dup2` replaces the file description, and
        an `epoll` registration follows the old one. All four asyncio integrations in the corpus
        bind or connect first — `govee`'s send socket by binding port 0, which is why a bind to
        port 0 attaches the pair too.
        """
        cls = socket.socket
        shim = self

        def state(sock: socket.socket) -> dict | None:
            """Notes for this socket, if it is a datagram socket the relay is serving."""
            if shim.datagrams is None:
                return None
            try:
                if sock.type != socket.SOCK_DGRAM:
                    return None
            except OSError:
                return None
            return shim._dgram.setdefault(sock, {"port": None, "peer": None,
                                                 "broadcast": False})

        def wrap(name: str, handler) -> None:
            real = getattr(cls, name)

            def method(sock, *args, **kwargs):
                notes = state(sock)
                if notes is not None:
                    outcome = handler(sock, notes, real, *args, **kwargs)
                    if outcome is not _FALL_THROUGH:
                        return outcome
                return real(sock, *args, **kwargs)

            setattr(cls, name, method)
            self._installed.append((cls, name, real))

        def attach(sock, notes, key: tuple | None) -> None:
            """Back this socket with a pair, once, and route `key`'s datagrams into it, if any."""
            if notes.get("writer") is None:
                inner, outer = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
                timeout = sock.gettimeout()
                os.dup2(inner.fileno(), sock.fileno())
                inner.close()
                # dup2 brought the pair's blocking mode; restore the integration's own.
                sock.settimeout(timeout)
                outer.setblocking(False)
                notes["writer"] = outer
            if key is None:
                return
            writers = shim._routes.setdefault(key, [])
            if notes["writer"] not in writers:
                writers.append(notes["writer"])

        # `bind` declares the port the integration wants to hear on. The mediator binds it and
        # pushes what arrives; a refusal is raised here, where a real bind would fail.
        def on_bind(sock, notes, real, address, *rest):
            if isinstance(address, tuple) and len(address) >= 2:
                port = int(address[1])
                notes["port"] = port
                if port:
                    shim.datagrams.listen_stream(port)
                    attach(sock, notes, ("listen", port))
                else:
                    # An ephemeral port: nothing to listen for, but the pair goes in **now**,
                    # before an event loop can register this descriptor. `govee`'s send socket
                    # binds port 0 and is then handed to `create_datagram_endpoint`; attached at
                    # its first `sendto` instead, the pair would replace a file description that
                    # `epoll` was already watching, and its replies would never wake the loop.
                    attach(sock, notes, None)
                return None
            return _FALL_THROUGH

        def on_setsockopt(sock, notes, real, level, option, *rest):
            if level == socket.SOL_SOCKET and option == socket.SO_BROADCAST:
                # Recorded, never applied. The sandbox holds no socket that could broadcast;
                # what this flag now means is "a later sendto to a broadcast address should be
                # served as discovery", and discovery is a declared capability of its own.
                notes["broadcast"] = bool(rest[0]) if rest else True
                return None
            return _FALL_THROUGH

        def on_connect(sock, notes, real, address, *rest):
            if isinstance(address, tuple) and len(address) >= 2:
                peer = (str(address[0]), int(address[1]))
                notes["peer"] = peer
                attach(sock, notes, ("peer", *peer))
                return None
            return _FALL_THROUGH

        def on_sendto(sock, notes, real, data, *rest):
            address = rest[-1] if rest else None
            if not (isinstance(address, tuple) and len(address) >= 2):
                return _FALL_THROUGH
            host, port = str(address[0]), int(address[1])
            if _is_broadcast(host):
                # The integration is scanning. The mediator performs it — bounded, rate-limited
                # and attributed — and the replies are collected for the next recvfrom.
                notes["scanned"] = shim.datagrams.scan(port, bytes(data))
                notes["port"] = port
                return len(data)
            # Routed **before** sending: the peer's reply can be pushed and delivered before the
            # send's own answer returns, and arriving with no route it was dropped — `selftest_udp`
            # case 8 lost the first device's reply that way on the Pi (W2 (b)). And unrouted again
            # if the send is refused, so a refusal still leaves nothing behind (W2 (a) baseline,
            # arm C: 463,631 refused decisions in 7.5 minutes).
            key = ("peer", host, port)
            fresh = notes.get("writer") is None or notes["writer"] not in shim._routes.get(key, [])
            attach(sock, notes, key)
            try:
                sent = shim.datagrams.send(host, port, bytes(data))
            except OSError:
                if fresh and notes["writer"] in shim._routes.get(key, []):
                    shim._routes[key].remove(notes["writer"])
                raise
            notes["peer"] = (host, port)
            return sent

        def on_send(sock, notes, real, data, *rest):
            peer = notes.get("peer")
            if peer is None:
                return _FALL_THROUGH
            return shim.datagrams.send(peer[0], peer[1], bytes(data))

        def on_recvfrom(sock, notes, real, bufsize=65535, *rest):
            if notes.get("scanned"):
                data, sender = notes["scanned"].pop(0)
                return data[:bufsize], sender
            if notes.get("writer") is None:
                return _FALL_THROUGH
            # A plain read of the pair: the socket's own timeout or non-blocking mode applies,
            # and raises what a real socket raises (`TimeoutError`, `BlockingIOError`).
            frame = real(sock, bufsize + 512)[0]
            header, _, data = frame.partition(b"\n")
            sender = json.loads(header)
            return data[:bufsize], (str(sender[0]), int(sender[1]))

        def on_recv(sock, notes, real, bufsize=65535, *rest):
            outcome = on_recvfrom(sock, notes, real, bufsize)
            if outcome is _FALL_THROUGH:
                return _FALL_THROUGH
            return outcome[0]

        def on_close(sock, notes, real, *rest):
            writer = notes.get("writer")
            if writer is not None:
                for writers in shim._routes.values():
                    if writer in writers:
                        writers.remove(writer)
                writer.close()
            shim._dgram.pop(sock, None)
            return _FALL_THROUGH

        wrap("close", on_close)
        wrap("bind", on_bind)
        wrap("setsockopt", on_setsockopt)
        wrap("connect", on_connect)
        wrap("sendto", on_sendto)
        wrap("send", on_send)
        wrap("recvfrom", on_recvfrom)
        wrap("recv", on_recv)

    def deliver(self, push: dict) -> int:
        """A datagram the mediator pushed, into every socket routed to it. Returns how many took it.

        Called from whichever thread read the push off the channel. Writing to a socket pair is
        safe from any thread, and a full pair drops the datagram, as a full receive buffer does.
        """
        route = push.get("route") or {}
        if route.get("kind") == "listen":
            key: tuple = ("listen", int(route.get("port", 0)))
        else:
            key = ("peer", str(route.get("address")), int(route.get("port", 0)))
        frame = json.dumps(push.get("sender")).encode() + b"\n" \
            + bytes.fromhex(str(push.get("data", "")))
        taken = 0
        for writer in list(self._routes.get(key, [])):
            try:
                writer.send(frame)
                taken += 1
            except OSError:
                pass
        self.delivered += taken
        return taken

    def _patch_getaddrinfo(self) -> None:
        """The synchronous seam — `requests`, `urllib3`, and anything using raw sockets.

        §7.24 found `localtuya` reaching Tuya's cloud through `urllib3` for ten connections, so
        this is not a legacy path kept for completeness: it is one of the three network stacks
        the corpus actually uses.
        """
        real = socket.getaddrinfo

        def getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):  # noqa: A002
            if isinstance(host, str) and host and not _is_address(host):
                placeholder = self.placeholder_for(host)
                return [(socket.AF_INET, type or socket.SOCK_STREAM, proto or 0, "",
                         (placeholder, port if isinstance(port, int) else 0))]
            return real(host, port, family, type, proto, flags)

        socket.getaddrinfo = getaddrinfo
        self._installed.append((socket, "getaddrinfo", real))

    def _patch_connect(self) -> None:
        """The connection seam, where a placeholder becomes a real socket."""
        cls = socket.socket
        real_connect = cls.connect
        real_connect_ex = cls.connect_ex

        def substitute(sock: socket.socket, address) -> bool:
            """Replace this socket's descriptor with one the mediator connected. True if done."""
            if not (isinstance(address, tuple) and len(address) >= 2):
                return False
            name = self._names.get(str(address[0]))
            port = address[1]
            if name is None:
                # Not a name this shim resolved. If it is an address on the home network, a
                # device the user typed in, ask the mediator for `network.tcp.local`; until W2 (a)
                # it fell through to the real `connect`, and the sandbox has no route, so every
                # LAN device over TCP failed. Anything else still falls through and fails. The
                # mediator re-checks the address and is the authority; this only routes.
                if self.connect_local is None or not _home_network(str(address[0])):
                    return False
                fd = self.connect_local(str(address[0]), int(port))
                name = str(address[0])
            else:
                fd = self.connect_via(name, int(port))
            # `dup2` makes the integration's descriptor refer to the mediator's connection. The
            # integration keeps the socket object it created and never learns that the thing
            # underneath it changed — which is what C1 requires, since it cannot be asked to
            # cooperate.
            blocking = sock.getblocking()
            try:
                os.dup2(fd, sock.fileno())
            finally:
                os.close(fd)
            # dup2 shares the open file description, so the mediator's blocking mode came with
            # it. Restore what this socket had, or an asyncio integration gets a blocking socket
            # under an event loop and stalls the whole sandbox on its first read.
            sock.setblocking(blocking)
            self.connected.append((name, int(port)))
            return True

        def connect(sock, address):
            if substitute(sock, address):
                return None
            return real_connect(sock, address)

        def connect_ex(sock, address):
            if substitute(sock, address):
                return 0
            return real_connect_ex(sock, address)

        cls.connect = connect
        cls.connect_ex = connect_ex
        self._installed.append((cls, "connect", real_connect))
        self._installed.append((cls, "connect_ex", real_connect_ex))

    def _patch_aiohttp_resolvers(self) -> None:
        """The asynchronous seam — the platform's client session, and four of six integrations' API names.

        Interposed at **aiohttp's resolver interface** rather than inside `aiodns`, for two
        reasons. `aiodns` resolves in `pycares`, which is C and owns its own sockets, so there
        is nothing in Python to replace; and `resolve()` returns a small documented list of
        dicts, where the layer below returns `pycares` result objects that would have to be
        reconstructed field by field. Patching the narrow, stable interface is both easier and
        less likely to break on a version bump.

        `AsyncDualMDNSResolver` is patched by name as well: Home Assistant builds it directly
        (`aiohttp_client.py:506`), and it overrides `resolve` rather than delegating, so
        patching the base class alone would miss every session the platform hands out.
        """
        try:
            from aiohttp import resolver as aiohttp_resolver
        except ImportError:
            return

        candidates = [getattr(aiohttp_resolver, name, None)
                      for name in ("AsyncResolver", "ThreadedResolver", "DefaultResolver")]
        try:
            from aiohttp_asyncmdnsresolver.api import (  # type: ignore[import-not-found]
                AsyncDualMDNSResolver, AsyncMDNSResolver)
            candidates += [AsyncDualMDNSResolver, AsyncMDNSResolver]
        except ImportError:
            pass

        shim = self
        for cls in candidates:
            if cls is None or not hasattr(cls, "resolve"):
                continue

            async def resolve(self, host, port=0, family=socket.AF_INET, *,
                              _cls=cls):  # noqa: ANN001
                placeholder = shim.placeholder_for(host)
                return [{"hostname": host, "host": placeholder, "port": port,
                         "family": socket.AF_INET, "proto": 0, "flags": 0}]

            real = cls.resolve
            cls.resolve = resolve
            self._installed.append((cls, "resolve", real))

    def uninstall(self) -> None:
        for target, name, real in reversed(self._installed):
            try:
                setattr(target, name, real)
            except Exception:  # noqa: BLE001
                pass
        self._installed.clear()


def _is_address(host: str) -> bool:
    """Already an address, so there is no name to carry and nothing to stand in for."""
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return True
