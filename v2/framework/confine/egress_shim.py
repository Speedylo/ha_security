"""The sandbox's side of egress: a name goes out, a connected socket comes back.

The integration is unmodified (C1), so this has to meet it where it already is — at the two
points every Python network stack passes through. §7.24 measured which two, and the answer was
not the one §5.10.3 assumed.

## Why there are two seams and not one

    resolution:  socket.getaddrinfo   ·  aiohttp's resolver (over aiodns)
    connection:  socket.socket.connect

Home Assistant gives every client session an `AsyncDualMDNSResolver` built on `aiodns`
(`aiohttp_client.py:479`), and `aiodns` resolves through `pycares` in C without ever calling
`getaddrinfo`. Across twelve integrations, **96% of resolutions went that way** — 3,073 of 3,193,
uniformly 93-97%, which is what makes it a property of the platform rather than of anyone's taste
in libraries. A shim watching only `getaddrinfo` would see about one name in twenty-five.

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
import os
import socket
from typing import Callable

# Reserved for future use by RFC 1112 and routed by nothing. A placeholder that escaped this
# sandbox would be dropped by the first hop rather than delivered somewhere unintended, which
# is the property wanted from a value that stands in for a real destination.
PLACEHOLDER_NET = ipaddress.ip_network("240.0.0.0/4")


class EgressDenied(OSError):
    """The mediator refused. Raised as an `OSError` so that unmodified integration code, which
    expects network failures and not framework exceptions, handles it the way it already
    handles a refused connection."""

    def __init__(self, reason: str, clause: str | None = None) -> None:
        super().__init__(errno.ECONNREFUSED, reason)
        self.reason = reason
        self.clause = clause


class EgressShim:
    """Installed in the sandbox before the integration is imported.

    `connect_via(host, port)` is injected rather than built here: it returns a connected file
    descriptor or raises. Keeping the channel out of this class is what lets the whole loop be
    tested against a real `EgressBroker` with no sandbox, no mediator process and no network.
    """

    def __init__(self, connect_via: Callable[[str, int], int]) -> None:
        self.connect_via = connect_via
        self._names: dict[str, str] = {}      # placeholder address -> the name it stands for
        self._placeholders: dict[str, str] = {}   # and back, so a repeat lookup is stable
        self._next = int(PLACEHOLDER_NET.network_address) + 1
        self._installed: list[tuple] = []
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
        self._patch_aiohttp_resolvers()

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
            if name is None:
                return False
            port = address[1]
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
        """The asynchronous seam — 96% of the corpus's resolutions.

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
