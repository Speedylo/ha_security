"""What an integration's egress actually *looks like*, as opposed to how much of it there is.

§7.18 measured demand — 81% of the corpus declares a network reach, 0 of 37 attempt egress at
import — and closed with the position that no observational method can do better, because
demand appears at setup and setup needs a credential for 26 of 37 (§7.17.1).

That position is right about **volume** and does not bind **shape**, and the difference is what
this module exists for. A bogus credential still produces a name resolution, a TCP connect, a
TLS handshake and a request; the server's 401 arrives *after* every mechanism a proxy would have
to implement has already been exercised. So the question "how many integrations need egress"
stays unanswerable by observation, while "what must a mediator support to serve egress at all"
becomes answerable — and the second is the one §5.8.2's scope item 2 has to be designed against.

**Why this is not `record_egress_attempts` with more fields.** That recorder answers §7.18 and
its numbers are cited; changing what it observes would move a published result. This is a
separate instrument with a separate question, and the two are cross-checked rather than merged.

## What it records, and which design question each field settles

| Observation | The proxy question it decides |
|---|---|
| socket `family` and `type` at the moment of use | whether TCP is sufficient, or UDP and multicast must be served too |
| how the name was resolved — `getaddrinfo`, or `aiodns` | **where the name-to-address seam is.** HA 2026.8.3 builds its client sessions with `AsyncDualMDNSResolver` over `aiodns`, which does not call `getaddrinfo` |
| `bind` and `listen` | whether *inbound* is needed — a capability §5.10.3's clause does not express at all |
| TLS: where it is wrapped, with what `server_hostname` and verification | whether the mediator can only hand back a connected descriptor (T09 retained) or could see content |
| the destination **port** | whether `network.egress`'s hostname-only clause (§5.10.3) is under-specified |
| the frame that initiated it | keeps §7.18's phase lesson: the platform's own components egress too, and attributing that to the integration inflated the first version of that measurement twentyfold |

## The blind spot, stated because it is load-bearing

This is an in-process observer: it sees what goes through Python's `socket` and `ssl` modules.
A library issuing syscalls from C — `pycares` under `aiodns` is exactly that — does its work
below this layer, so `aiodns` is instrumented **at its own API** rather than at the socket, and
anything else in C is invisible here. That is why the experiment pairs this recorder with
`strace -f -e trace=network`: the kernel sees everything and attributes nothing, this sees
little and attributes it precisely, and the pair is worth more than either. Where they disagree,
the kernel is right.
"""

from __future__ import annotations

import os
import sys
import time

# Set by the driver so an event can be attributed to the phase it occurred in, exactly as
# §7.18's recorder does. Sharing the convention rather than the code keeps the two instruments
# independent while letting their output be compared row for row.
CURRENT_PHASE = ["platform"]

# Re-entrancy guard. `wrap_socket` calls `connect`, `getaddrinfo` allocates sockets on some
# platforms, and an attribution walk must never itself be attributed. One flag, per-thread by
# virtue of the GIL being held across these short sections.
_INSIDE = [False]

_MAX_EVENTS = 20000


class Recorder:
    """Collects one run's network events, in order, with attribution."""

    def __init__(self, component_dir: str = "", deps_dir: str = "") -> None:
        self.events: list[dict] = []
        self.component_dir = os.path.realpath(component_dir) if component_dir else ""
        self.deps_dir = os.path.realpath(deps_dir) if deps_dir else ""
        self._t0 = time.monotonic()
        self._installed: list[tuple] = []

    # -- attribution ----------------------------------------------------------------

    def _origin(self) -> dict:
        """Who asked for this, in the terms the report needs: integration, platform, or library.

        Walks outward from the call site to the first frame that is not this module and not the
        standard library's own networking plumbing. The *first* such frame is the proximate
        caller — usually a vendor library — and the first frame under the integration's own
        directory, if any appears anywhere in the stack, is what attributes the event to the
        integration rather than to whatever it called.
        """
        proximate = ""
        integration_frame = ""
        try:
            frame = sys._getframe(2)
        except ValueError:
            return {"by": "unknown", "caller": ""}
        depth = 0
        while frame is not None and depth < 60:
            path = frame.f_code.co_filename
            real = os.path.realpath(path) if path and path[0] == "/" else path
            if not _is_plumbing(path):
                if not proximate:
                    proximate = f"{_short(path)}:{frame.f_lineno}"
                if self.component_dir and real.startswith(self.component_dir):
                    integration_frame = f"{_short(path)}:{frame.f_lineno}"
                    break
            frame = frame.f_back
            depth += 1

        if integration_frame:
            return {"by": "integration", "caller": integration_frame}
        if proximate:
            by = "platform" if "/homeassistant/" in proximate else "library"
            return {"by": by, "caller": proximate}
        return {"by": "unknown", "caller": ""}

    # -- recording ------------------------------------------------------------------

    def note(self, kind: str, **fields) -> None:
        if len(self.events) >= _MAX_EVENTS:
            return
        event = {"seq": len(self.events),
                 "t_ms": round((time.monotonic() - self._t0) * 1000, 3),
                 "kind": kind,
                 "phase": CURRENT_PHASE[0]}
        event.update(self._origin())
        event.update(fields)
        self.events.append(event)

    # -- installation ---------------------------------------------------------------

    def install(self) -> None:
        """Patch the observation points. Idempotent per Recorder; call once, before any import
        of the integration, so that a module-level connection is seen too."""
        import socket as _socket

        self._patch_resolution(_socket)
        self._patch_socket_methods(_socket)
        self._patch_tls()
        self._patch_aiodns()

    def _patch_resolution(self, _socket) -> None:
        real = _socket.getaddrinfo

        def getaddrinfo(host, port, *args, **kwargs):
            if not _INSIDE[0]:
                _INSIDE[0] = True
                try:
                    self.note("resolve", via="getaddrinfo",
                              host=_text(host), port=_port(port))
                finally:
                    _INSIDE[0] = False
            return real(host, port, *args, **kwargs)

        _socket.getaddrinfo = getaddrinfo
        self._installed.append((_socket, "getaddrinfo", real))

    def _patch_socket_methods(self, _socket) -> None:
        cls = _socket.socket

        def wrap(name: str, kind: str, address_index: int | None):
            real = getattr(cls, name)

            def method(sock, *args, **kwargs):
                if not _INSIDE[0]:
                    _INSIDE[0] = True
                    try:
                        fields: dict = {"family": _family(sock), "socktype": _socktype(sock)}
                        if address_index is not None and len(args) > address_index:
                            host, port = _split(args[address_index])
                            fields["host"] = host
                            fields["port"] = port
                        self.note(kind, **fields)
                    except Exception:  # noqa: BLE001 — an observer must never break the run
                        pass
                    finally:
                        _INSIDE[0] = False
                return real(sock, *args, **kwargs)

            setattr(cls, name, method)
            self._installed.append((cls, name, real))

        # `connect_ex` is asyncio's path on some platforms and `connect`'s on others; both are
        # recorded so the instrument does not depend on which one the event loop chose.
        wrap("connect", "connect", 0)
        wrap("connect_ex", "connect", 0)
        wrap("bind", "bind", 0)
        wrap("listen", "listen", None)
        wrap("sendto", "sendto", 1)

        # Multicast membership is not a connect and would otherwise be invisible, yet it is
        # exactly what §7.18 found the platform's `zeroconf` doing and what `scheduler` failed
        # on in §7.17.4. Recorded so that "needs multicast" is a finding rather than an
        # inference from a traceback.
        real_setsockopt = cls.setsockopt

        def setsockopt(sock, level, optname, *args, **kwargs):
            if not _INSIDE[0] and optname in _MULTICAST_OPTS:
                _INSIDE[0] = True
                try:
                    self.note("multicast", option=_MULTICAST_OPTS[optname],
                              family=_family(sock), socktype=_socktype(sock))
                except Exception:  # noqa: BLE001
                    pass
                finally:
                    _INSIDE[0] = False
            return real_setsockopt(sock, level, optname, *args, **kwargs)

        cls.setsockopt = setsockopt
        self._installed.append((cls, "setsockopt", real_setsockopt))

    def _patch_tls(self) -> None:
        try:
            import ssl as _ssl
        except ImportError:
            return
        cls = _ssl.SSLContext

        def wrap(name: str) -> None:
            real = getattr(cls, name, None)
            if real is None:
                return

            def method(ctx, *args, **kwargs):
                if not _INSIDE[0]:
                    _INSIDE[0] = True
                    try:
                        self.note("tls", how=name,
                                  server_hostname=_text(kwargs.get("server_hostname")),
                                  verify_mode=str(getattr(ctx, "verify_mode", "")),
                                  check_hostname=bool(getattr(ctx, "check_hostname", False)))
                    except Exception:  # noqa: BLE001
                        pass
                    finally:
                        _INSIDE[0] = False
                return real(ctx, *args, **kwargs)

            setattr(cls, name, method)
            self._installed.append((cls, name, real))

        # `wrap_bio` is aiohttp's path — asyncio drives TLS over a memory BIO, not over the
        # socket — so a recorder watching only `wrap_socket` would report that nothing in the
        # corpus uses TLS, which would be the wrong answer to the question this run asks.
        wrap("wrap_socket")
        wrap("wrap_bio")

    def _patch_aiodns(self) -> None:
        """The seam the socket layer cannot see.

        `aiohttp_client.py:479` gives every Home Assistant client session an
        `AsyncDualMDNSResolver` built on `aiodns`, and `aiodns` resolves through `pycares`,
        which owns its sockets in C. Nothing above would record a name being resolved. Patching
        `aiodns` at its own API restores that, and — more usefully — the *presence* of these
        events rather than `getaddrinfo` events is the finding: it says where a mediator would
        have to intervene.
        """
        try:
            import aiodns  # type: ignore[import-not-found]
        except ImportError:
            self.note("aiodns_absent")
            return
        cls = getattr(aiodns, "DNSResolver", None)
        if cls is None:
            return
        for name in ("query", "gethostbyname", "getaddrinfo", "getnameinfo"):
            real = getattr(cls, name, None)
            if real is None:
                continue

            def make(name: str, real):
                def method(resolver, *args, **kwargs):
                    if not _INSIDE[0]:
                        _INSIDE[0] = True
                        try:
                            self.note("resolve", via=f"aiodns.{name}",
                                      host=_text(args[0]) if args else "",
                                      port=None)
                        except Exception:  # noqa: BLE001
                            pass
                        finally:
                            _INSIDE[0] = False
                    return real(resolver, *args, **kwargs)
                return method

            setattr(cls, name, make(name, real))
            self._installed.append((cls, name, real))

    def uninstall(self) -> None:
        for target, name, real in reversed(self._installed):
            try:
                setattr(target, name, real)
            except Exception:  # noqa: BLE001
                pass
        self._installed.clear()

    # -- reporting ------------------------------------------------------------------

    def summary(self) -> dict:
        """The per-integration answer, in the shape §7.24 tabulates."""
        destinations: dict[str, dict] = {}
        for e in self.events:
            if e["kind"] not in ("connect", "sendto"):
                continue
            host, port = e.get("host") or "", e.get("port")
            if not host:
                continue
            key = f"{host}:{port}"
            row = destinations.setdefault(key, {
                "host": host, "port": port, "count": 0,
                "socktype": e.get("socktype"), "by": e.get("by"),
                "phase": e.get("phase"), "caller": e.get("caller")})
            row["count"] += 1

        return {
            "events": len(self.events),
            "by_kind": _tally(e["kind"] for e in self.events),
            "by_actor": _tally(e.get("by", "unknown") for e in self.events),
            "resolution": _tally(e.get("via", "") for e in self.events
                                 if e["kind"] == "resolve"),
            "socktypes": _tally(e.get("socktype", "") for e in self.events
                                if e["kind"] in ("connect", "sendto", "bind")),
            "tls": [e for e in self.events if e["kind"] == "tls"][:20],
            "listens": [e for e in self.events if e["kind"] in ("bind", "listen")][:20],
            "multicast": [e for e in self.events if e["kind"] == "multicast"][:10],
            "destinations": sorted(destinations.values(),
                                   key=lambda r: -r["count"])[:40],
        }


# -- helpers --------------------------------------------------------------------------

_MULTICAST_OPTS = {35: "IP_ADD_MEMBERSHIP", 36: "IP_DROP_MEMBERSHIP",
                   20: "IPV6_JOIN_GROUP", 21: "IPV6_LEAVE_GROUP"}

# Frames belonging to the machinery being observed, or to the plumbing every caller goes
# through. Skipped when looking for the proximate caller, because "asyncio/base_events.py"
# attributes nothing.
_PLUMBING = ("/netshape.py", "/asyncio/", "/socket.py", "/ssl.py", "/selectors.py",
             "/concurrent/futures/", "/threading.py", "<frozen ")


def _is_plumbing(path: str) -> bool:
    return any(part in path for part in _PLUMBING)


def _short(path: str) -> str:
    """Enough of the path to identify the package, without the machine's directory layout."""
    parts = path.split("/")
    for anchor in ("site-packages", "custom_components", "platform-deps"):
        if anchor in parts:
            return "/".join(parts[parts.index(anchor) + 1:])
    return "/".join(parts[-2:])


def _text(value: object) -> str:
    return "" if value is None else str(value)[:120]


def _port(value: object) -> object:
    return value if isinstance(value, int) else _text(value)


def _split(address: object) -> tuple[str, object]:
    if isinstance(address, tuple) and len(address) >= 2:
        return _text(address[0]), address[1]
    return _text(address), None


def _family(sock: object) -> str:
    try:
        return getattr(sock.family, "name", str(sock.family))  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return ""


def _socktype(sock: object) -> str:
    try:
        return getattr(sock.type, "name", str(sock.type))  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return ""


def _tally(values) -> dict:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))
