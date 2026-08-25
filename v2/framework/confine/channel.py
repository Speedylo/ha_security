"""The one channel that crosses the sandbox boundary, and its framing.

§5.11.2: each sandbox is created with a single connected Unix domain socket, inherited as a
file descriptor. The supervisor creates the pair **before the sandbox exists**, keeps one end
for the mediator and passes the other into the child. Nothing else crosses: the sandbox's
network namespace has no route, its IPC namespace is its own, and its mount namespace contains
no path to any other socket.

The consequence is the design's answer to T02. **Identity is a property of the channel, not a
claim in the message.** The mediator knows which integration is speaking because it created
that socket for that sandbox and holds the other end. There is no field to forge and no
authentication step to bypass, and `selftest_channel.py` demonstrates the difference by having
two sandboxes both claim to be the same integration.

§5.11.3 fixes the wire format: a four-byte big-endian length followed by a JSON object. Small
and readable, because the message rate is modest (§5.11.4) and a format that can be read during
evaluation is worth more than the bytes it costs.

**The sandbox is the untrusted end of this socket**, which drives two decisions here that would
be unnecessary between cooperating processes: a frame's declared length is checked against a
cap *before* anything is allocated for it, and a malformed frame raises rather than propagating
— one sandbox must not be able to stop the mediator by sending rubbish.
"""

from __future__ import annotations

import json
import socket
import struct

# Generous for the payloads of §5.11.3 — an entity read, a service call — and small enough
# that a sandbox declaring a four-gigabyte frame is refused rather than believed.
MAX_FRAME = 1 << 20

_LENGTH = struct.Struct(">I")


class ProtocolError(Exception):
    """The far end sent something that is not a frame. Never fatal to the mediator."""


class Channel:
    """One end of the sandbox boundary's only socket."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock

    @staticmethod
    def pair() -> tuple[socket.socket, socket.socket]:
        """(mediator end, sandbox end). Created before the sandbox, by the supervisor."""
        return socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)

    @classmethod
    def from_fd(cls, fd: int) -> Channel:
        """The sandbox's own view: a file descriptor it was born holding."""
        return cls(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, fileno=fd))

    def send(self, message: dict) -> None:
        payload = json.dumps(message, separators=(",", ":")).encode()
        if len(payload) > MAX_FRAME:
            raise ProtocolError(f"message of {len(payload)} bytes exceeds {MAX_FRAME}")
        self.sock.sendall(_LENGTH.pack(len(payload)) + payload)

    def _read_exactly(self, count: int) -> bytes | None:
        chunks: list[bytes] = []
        remaining = count
        while remaining:
            chunk = self.sock.recv(remaining)
            if not chunk:
                # A clean close mid-frame is still a truncated frame, but only if some of it
                # arrived; nothing at all is an ordinary hang-up.
                return None if not chunks else b"".join(chunks)
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def recv(self) -> dict | None:
        """One message, or None when the far end has closed."""
        header = self._read_exactly(_LENGTH.size)
        if header is None:
            return None
        if len(header) < _LENGTH.size:
            raise ProtocolError("truncated length prefix")
        (length,) = _LENGTH.unpack(header)
        # Checked before the read, not after: this number came from the sandbox.
        if length > MAX_FRAME:
            raise ProtocolError(f"declared frame of {length} bytes exceeds {MAX_FRAME}")
        payload = self._read_exactly(length) if length else b""
        if payload is None or len(payload) < length:
            raise ProtocolError("truncated frame")
        try:
            message = json.loads(payload)
        except ValueError as err:
            raise ProtocolError(f"not JSON: {err}") from err
        if not isinstance(message, dict):
            raise ProtocolError(f"frame is {type(message).__name__}, expected an object")
        return message

    def fileno(self) -> int:
        return self.sock.fileno()

    def close(self) -> None:
        self.sock.close()
