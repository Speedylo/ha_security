"""Shim of homeassistant.helpers.aiohttp_client.

On real HA this hands back a shared, fully unrestricted HTTP session — an
integration that gets one can reach any host on the internet and any host on the
LAN, including HA's own API.

Here it hands back a session that does not have a network at all. Every request
is serialised, sent to the supervisor over the bridge socket, checked against the
manifest's ``network:`` allowlist, and performed *by the supervisor*. The
response comes back the same way.

Why it works like this. The previous version wrapped a real ``aiohttp`` session
and asked the supervisor for permission before each request — but the sandbox
still opened the connection, so the allowlist bound only an integration that
chose to use this helper. ``import socket`` walked straight past it. The
enforcement point has moved to the side of the boundary that cannot be skipped:
seccomp denies ``socket(AF_INET)`` in the sandbox, so the bridge is the only
way out.

What that does *not* do is make an integration trustworthy. It bounds where the
integration can reach; it says nothing about what it sends to a host it
legitimately declared.
"""

from __future__ import annotations

import base64
import json as jsonlib
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

import aiohttp  # for the exception types integrations catch; not for transport

from ..core import HomeAssistant


class MediatedResponse:
    """The subset of ``aiohttp.ClientResponse`` integrations actually use.

    Deliberately small. Every attribute here is one a target integration was
    observed to touch; anything else should fail loudly rather than silently
    return something plausible.
    """

    def __init__(self, url: str, status: int, headers: dict, body: bytes) -> None:
        self.url = url
        self.status = status
        self.headers = headers
        self._body = body

    @property
    def content_type(self) -> str:
        return self.headers.get("Content-Type", "").split(";")[0].strip()

    async def read(self) -> bytes:
        return self._body

    async def text(self, encoding: str = "utf-8") -> str:
        return self._body.decode(encoding, errors="replace")

    async def json(self, content_type: str | None = "application/json", **_: Any) -> Any:
        if content_type is not None and self.content_type and self.content_type != content_type:
            raise aiohttp.ContentTypeError(None, (), message=f"unexpected {self.content_type}")
        return jsonlib.loads(self._body.decode("utf-8"))

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=self.status,
                message=f"HTTP {self.status}",
            )

    # Integrations use both `await session.get(...)` and
    # `async with session.get(...) as resp:`. _RequestFuture below returns this
    # object either way, so it must also work as its own context manager.
    async def __aenter__(self) -> "MediatedResponse":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def close(self) -> None:
        return None

    def release(self) -> None:
        return None


class _RequestFuture:
    """Awaitable *and* async-context-manager, like aiohttp's own return value.

    ``await session.get(url)`` and ``async with session.get(url) as r:`` are both
    common in real integrations, and aiohttp supports both by returning an object
    that implements both protocols. This is the same trick, minus the streaming.
    """

    def __init__(self, coroutine) -> None:
        self._coroutine = coroutine
        self._response: MediatedResponse | None = None

    def __await__(self):
        return self._coroutine.__await__()

    async def __aenter__(self) -> MediatedResponse:
        self._response = await self._coroutine
        return self._response

    async def __aexit__(self, *_: object) -> None:
        return None


class MediatedClientSession:
    """An HTTP session whose transport is the supervisor."""

    def __init__(self, hass: HomeAssistant, **_: Any) -> None:
        self._hass = hass
        self._bridge = hass._bridge
        self._closed = False

    # -- the actual crossing ---------------------------------------------
    async def _send(
        self,
        method: str,
        url: str,
        *,
        params: Any = None,
        data: Any = None,
        json: Any = None,
        headers: Any = None,
        timeout: Any = None,
        **_: Any,
    ) -> MediatedResponse:
        request_headers = dict(headers or {})

        if params:
            parsed = urlparse(str(url))
            query = urlencode(params, doseq=True)
            merged = f"{parsed.query}&{query}" if parsed.query else query
            url = urlunparse(parsed._replace(query=merged))

        body: bytes | None = None
        if json is not None:
            body = jsonlib.dumps(json).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        elif isinstance(data, dict):
            body = urlencode(data, doseq=True).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        elif isinstance(data, str):
            body = data.encode("utf-8")
        elif isinstance(data, (bytes, bytearray)):
            body = bytes(data)

        # aiohttp.ClientTimeout, a number, or nothing.
        seconds = getattr(timeout, "total", timeout)

        reply = self._bridge.request(
            "http_request",
            method=method,
            url=str(url),
            headers=request_headers,
            body=base64.b64encode(body).decode("ascii") if body else "",
            timeout=seconds if isinstance(seconds, (int, float)) else None,
        )
        return MediatedResponse(
            url=str(url),
            status=int(reply.get("status", 0)),
            headers=dict(reply.get("headers") or {}),
            body=base64.b64decode(reply.get("body") or ""),
        )

    # -- aiohttp surface -------------------------------------------------
    def request(self, method: str, url: str = "", **kwargs: Any) -> _RequestFuture:
        # Integrations call this both positionally and as request(method=, url=).
        return _RequestFuture(self._send(method, kwargs.pop("url", url), **kwargs))

    def get(self, url: str, **kwargs: Any) -> _RequestFuture:
        return _RequestFuture(self._send("GET", url, **kwargs))

    def post(self, url: str, **kwargs: Any) -> _RequestFuture:
        return _RequestFuture(self._send("POST", url, **kwargs))

    def put(self, url: str, **kwargs: Any) -> _RequestFuture:
        return _RequestFuture(self._send("PUT", url, **kwargs))

    def patch(self, url: str, **kwargs: Any) -> _RequestFuture:
        return _RequestFuture(self._send("PATCH", url, **kwargs))

    def delete(self, url: str, **kwargs: Any) -> _RequestFuture:
        return _RequestFuture(self._send("DELETE", url, **kwargs))

    def head(self, url: str, **kwargs: Any) -> _RequestFuture:
        return _RequestFuture(self._send("HEAD", url, **kwargs))

    def ws_connect(self, url: str, **kwargs: Any) -> Any:
        # Not brokered. Failing loudly is correct: silently falling through to a
        # real socket is exactly the advisory-check mistake this replaced.
        raise NotImplementedError(
            "websockets are not brokered by the supervisor; "
            "the sandbox has no network of its own"
        )

    async def close(self) -> None:
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed


_SESSIONS: dict[int, MediatedClientSession] = {}


def async_get_clientsession(
    hass: HomeAssistant, verify_ssl: bool = True, family: int = 0, ssl_cipher: Any = None
) -> MediatedClientSession:
    """Shared session for this integration."""
    key = id(hass)
    if key not in _SESSIONS:
        _SESSIONS[key] = MediatedClientSession(hass)
    return _SESSIONS[key]


def async_create_clientsession(
    hass: HomeAssistant,
    verify_ssl: bool = True,
    auto_cleanup: bool = True,
    family: int = 0,
    **kwargs: Any,
) -> MediatedClientSession:
    """Fresh session; still mediated."""
    return MediatedClientSession(hass, **kwargs)


async def async_close_sessions() -> None:
    for session in list(_SESSIONS.values()):
        await session.close()
    _SESSIONS.clear()
