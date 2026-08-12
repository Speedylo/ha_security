"""Shim of homeassistant.helpers.aiohttp_client.

On real HA this hands back a shared, fully unrestricted HTTP session — an
integration that gets one can reach any host on the internet and any host on the
LAN, including HA's own API. Here it returns a session that asks the supervisor
before every request, so ``network:`` in the manifest is enforced rather than
documented.

Known gap: only the initial request URL is checked. A server that answers with a
redirect to a non-declared host would currently be followed by aiohttp without a
second check. The fix is ``allow_redirects=False`` plus a check per hop.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse, urlunparse

import aiohttp

from ..core import HomeAssistant

# Test-harness only: redirect a declared host to a local stub, so an unmodified
# integration can be exercised without credentials for the real vendor cloud.
# Format: HACS_EGRESS_REWRITE="chaos2.aa.net.uk=http://127.0.0.1:8765"
REWRITE_ENV_VAR = "HACS_EGRESS_REWRITE"


def _load_rewrites() -> dict[str, str]:
    raw = os.environ.get(REWRITE_ENV_VAR, "")
    rewrites = {}
    for pair in filter(None, (part.strip() for part in raw.split(","))):
        host, _, target = pair.partition("=")
        if host and target:
            rewrites[host.strip()] = target.strip()
    return rewrites


class MediatedClientSession:
    """aiohttp session with a permission check in front of it."""

    def __init__(self, hass: HomeAssistant, **kwargs: Any) -> None:
        self._hass = hass
        self._bridge = hass._bridge
        self._session = aiohttp.ClientSession(**kwargs)
        self._rewrites = _load_rewrites()

    # -- permission check ------------------------------------------------
    def _authorise(self, url: str) -> str:
        parsed = urlparse(str(url))
        host = parsed.hostname or ""
        # Checked against the manifest as written by the integration author,
        # before any test rewriting is applied.
        self._bridge.request("net_request", host=host, scheme=parsed.scheme, path=parsed.path)

        if host in self._rewrites:
            target = urlparse(self._rewrites[host])
            parsed = parsed._replace(scheme=target.scheme or parsed.scheme, netloc=target.netloc)
            return urlunparse(parsed)
        return str(url)

    # -- aiohttp surface -------------------------------------------------
    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        return self._session.request(method, self._authorise(url), **kwargs)

    def get(self, url: str, **kwargs: Any) -> Any:
        return self._session.get(self._authorise(url), **kwargs)

    def post(self, url: str, **kwargs: Any) -> Any:
        return self._session.post(self._authorise(url), **kwargs)

    def put(self, url: str, **kwargs: Any) -> Any:
        return self._session.put(self._authorise(url), **kwargs)

    def patch(self, url: str, **kwargs: Any) -> Any:
        return self._session.patch(self._authorise(url), **kwargs)

    def delete(self, url: str, **kwargs: Any) -> Any:
        return self._session.delete(self._authorise(url), **kwargs)

    def head(self, url: str, **kwargs: Any) -> Any:
        return self._session.head(self._authorise(url), **kwargs)

    def ws_connect(self, url: str, **kwargs: Any) -> Any:
        return self._session.ws_connect(self._authorise(url), **kwargs)

    async def close(self) -> None:
        await self._session.close()

    @property
    def closed(self) -> bool:
        return self._session.closed

    def __getattr__(self, item: str) -> Any:
        # Anything not mediated above falls through to aiohttp. Attributes that
        # can initiate traffic must be added to the list above, not left here.
        return getattr(self._session, item)


_SESSIONS: dict[int, MediatedClientSession] = {}


def async_get_clientsession(
    hass: HomeAssistant, verify_ssl: bool = True, family: int = 0, ssl_cipher: Any = None
) -> MediatedClientSession:
    """Shared session for this integration."""
    key = id(hass)
    if key not in _SESSIONS:
        connector = aiohttp.TCPConnector(ssl=None if verify_ssl else False)
        _SESSIONS[key] = MediatedClientSession(hass, connector=connector)
    return _SESSIONS[key]


def async_create_clientsession(
    hass: HomeAssistant,
    verify_ssl: bool = True,
    auto_cleanup: bool = True,
    family: int = 0,
    **kwargs: Any,
) -> MediatedClientSession:
    """Fresh session; still mediated."""
    connector = aiohttp.TCPConnector(ssl=None if verify_ssl else False)
    return MediatedClientSession(hass, connector=connector, **kwargs)


async def async_close_sessions() -> None:
    for session in list(_SESSIONS.values()):
        await session.close()
    _SESSIONS.clear()
