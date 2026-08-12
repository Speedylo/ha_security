"""Sandbox-side client for the supervisor bridge.

Wire format: one JSON object per line, request/response, over a Unix socket.
Blocking I/O guarded by a lock. The supervisor is on the same host over a Unix
socket, so a round trip is tens of microseconds; a real implementation should
still move this onto the event loop rather than blocking it.
"""

from __future__ import annotations

import json
import os
import socket
import threading

SOCKET_ENV_VAR = "HACS_BRIDGE_SOCKET"


class PermissionDenied(Exception):
    """The supervisor refused an operation the manifest does not declare."""


class BridgeError(Exception):
    """The bridge itself failed (transport, protocol)."""


class Bridge:
    """Request/response client for the supervisor."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(path)
        self._reader = self._sock.makefile("r", encoding="utf-8")

    @classmethod
    def from_env(cls) -> "Bridge":
        path = os.environ.get(SOCKET_ENV_VAR)
        if not path:
            raise BridgeError(f"{SOCKET_ENV_VAR} is not set; not running under a supervisor")
        return cls(path)

    def request(self, op: str, **payload: object) -> dict:
        """Send one operation, block for the verdict."""
        message = json.dumps({"op": op, **payload}, default=str) + "\n"
        with self._lock:
            try:
                self._sock.sendall(message.encode("utf-8"))
                line = self._reader.readline()
            except OSError as err:  # pragma: no cover - transport failure
                raise BridgeError(f"bridge transport failed: {err}") from err

        if not line:
            raise BridgeError("supervisor closed the connection")

        reply = json.loads(line)
        if not reply.get("ok"):
            raise PermissionDenied(reply.get("reason", "denied"))
        return reply

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:  # pragma: no cover
            pass
