"""A WebSocket client in the standard library, for the one connection the mediator makes to (A).

W1 step 2 (`notes/w1_step2_real_platform_prediction.md`). The mediator reaches the house's real
Home Assistant through its public WebSocket API with a long-lived token, because that is the
credential Chapter 5 gives it (§5.15.3, R3) and because REST cannot push. The Pi's system Python
has no WebSocket library, and the mediator is a single-threaded `selectors` loop that an
asynchronous library would not fit, so this is RFC 6455 written out. Only the parts a client of
Home Assistant needs:

  - **The opening handshake (§4.1).** An HTTP/1.1 `GET` asking to upgrade, with a random 16-byte
    `Sec-WebSocket-Key`. The server proves it understood by answering `101` with
    `Sec-WebSocket-Accept` = base64(SHA-1(key + a fixed GUID)), which is checked, so that an
    HTTP server that merely echoes headers is not mistaken for a WebSocket one.
  - **Frames (§5.2).** A two-byte header — FIN, opcode, MASK, a 7-bit length — then a 16- or
    64-bit extended length when the 7 bits say 126 or 127. **A client must mask** every frame it
    sends with a fresh 4-byte key (§5.3), and a server must not mask; a masked frame from the
    server is a protocol error here.
  - **Control frames (§5.5).** A ping is answered with a pong carrying the same payload; a close
    ends the connection.

Fragmented messages (§5.4) are reassembled, although Home Assistant does not send them, because
a parser that silently mis-joins a fragment is the kind of defect that surfaces three layers away.
No extensions are negotiated, so no compression.

The socket stays **blocking with a timeout**. The mediator reads it only when its selector says
it is readable, so a read never waits; and a send to (A) blocking briefly is acceptable where a
send to a sandbox was not (§7.36.2), because (A) is the trusted platform, not an untrusted peer.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"   # RFC 6455 §1.3, the same for every server

TEXT, BINARY, CONTINUATION = 0x1, 0x2, 0x0
CLOSE, PING, PONG = 0x8, 0x9, 0xA

#: Home Assistant's `get_states` on a populated house is the largest message here. 16 MB is far
#: above it and far below what would let a confused server exhaust the mediator's memory.
MAX_MESSAGE = 16 << 20


class WebSocketError(Exception):
    """The server broke the protocol, refused the upgrade, or closed the connection."""


def accept_for(key: str) -> str:
    """What a server must answer to `key` (RFC 6455 §4.2.2 step 5.4)."""
    return base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()


def encode_frame(opcode: int, payload: bytes, mask_key: bytes | None = None) -> bytes:
    """One frame, FIN set. Masked with `mask_key`, or a fresh random one, as a client must."""
    mask_key = mask_key if mask_key is not None else os.urandom(4)
    header = bytes([0x80 | opcode])
    length = len(payload)
    if length < 126:
        header += bytes([0x80 | length])
    elif length < 1 << 16:
        header += bytes([0x80 | 126]) + struct.pack(">H", length)
    else:
        header += bytes([0x80 | 127]) + struct.pack(">Q", length)
    masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    return header + mask_key + masked


class FrameParser:
    """Bytes in, whole frames out. Kept apart from the socket so that it can be tested on its own."""

    def __init__(self) -> None:
        self.buffer = bytearray()

    def feed(self, data: bytes) -> list[tuple[bool, int, bytes]]:
        """Every complete frame now in the buffer, as (fin, opcode, payload)."""
        self.buffer += data
        frames = []
        while True:
            frame = self._one()
            if frame is None:
                return frames
            frames.append(frame)

    def _one(self) -> tuple[bool, int, bytes] | None:
        buf = self.buffer
        if len(buf) < 2:
            return None
        fin, opcode = bool(buf[0] & 0x80), buf[0] & 0x0F
        if buf[0] & 0x70:
            raise WebSocketError("reserved bits set, but no extension was negotiated")
        if buf[1] & 0x80:
            raise WebSocketError("the server masked a frame, which RFC 6455 §5.1 forbids")
        length, offset = buf[1] & 0x7F, 2
        if length == 126:
            if len(buf) < 4:
                return None
            (length,), offset = struct.unpack(">H", buf[2:4]), 4
        elif length == 127:
            if len(buf) < 10:
                return None
            (length,), offset = struct.unpack(">Q", buf[2:10]), 10
        if length > MAX_MESSAGE:
            raise WebSocketError(f"a frame of {length} bytes exceeds {MAX_MESSAGE}")
        if len(buf) < offset + length:
            return None
        payload = bytes(buf[offset:offset + length])
        del buf[:offset + length]
        return fin, opcode, payload


class WebSocket:
    """One client connection. `messages()` returns whole text messages, decoded from JSON."""

    def __init__(self, host: str, port: int, path: str = "/api/websocket",
                 timeout: float = 10.0) -> None:
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.parser = FrameParser()
        self._fragments: list[bytes] = []
        self.closed = False
        self._handshake(host, port, path)

    def _handshake(self, host: str, port: int, path: str) -> None:
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
                           "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
                          .encode())
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise WebSocketError("the server closed the connection during the handshake")
            response += chunk
            if len(response) > 65536:
                raise WebSocketError("the handshake response has no end")
        head, _, rest = response.partition(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        if not lines[0].startswith("HTTP/1.1 101"):
            raise WebSocketError(f"upgrade refused: {lines[0]}")
        headers = {k.strip().lower(): v.strip()
                   for k, _, v in (line.partition(":") for line in lines[1:])}
        if headers.get("sec-websocket-accept") != accept_for(key):
            raise WebSocketError("the server's Sec-WebSocket-Accept does not match the key")
        # Frames that arrived in the same read as the handshake belong to the parser.
        self._pending = self._decode(self.parser.feed(rest)) if rest else []

    def fileno(self) -> int:
        return self.sock.fileno()

    def send(self, message: dict) -> None:
        self.sock.sendall(encode_frame(TEXT, json.dumps(message).encode()))

    def messages(self) -> list[dict]:
        """Read once — the caller knows the socket is readable — and return what completed."""
        ready, self._pending = self._pending, []
        if ready:
            # Already here, from the handshake's read. Reading again could wait for nothing.
            return ready
        data = self.sock.recv(65536)
        if not data:
            self.closed = True
            raise WebSocketError("the server closed the connection")
        return ready + self._decode(self.parser.feed(data))

    def receive(self) -> list[dict]:
        """Block until at least one message has arrived. For the handshake-time exchanges."""
        while True:
            got = self.messages()
            if got:
                return got

    def _decode(self, frames: list[tuple[bool, int, bytes]]) -> list[dict]:
        out = []
        for fin, opcode, payload in frames:
            if opcode == PING:
                self.sock.sendall(encode_frame(PONG, payload))
            elif opcode == PONG:
                continue
            elif opcode == CLOSE:
                self.closed = True
                raise WebSocketError(f"the server closed the connection: {payload[2:]!r}")
            elif opcode in (TEXT, BINARY, CONTINUATION):
                if opcode != CONTINUATION and self._fragments:
                    raise WebSocketError("a new message began before the last one finished")
                self._fragments.append(payload)
                if sum(map(len, self._fragments)) > MAX_MESSAGE:
                    raise WebSocketError(f"a message exceeds {MAX_MESSAGE} bytes")
                if fin:
                    whole = b"".join(self._fragments)
                    self._fragments = []
                    out.append(json.loads(whole))
            else:
                raise WebSocketError(f"unknown opcode {opcode:#x}")
        return out

    def close(self) -> None:
        if not self.closed:
            try:
                self.sock.sendall(encode_frame(CLOSE, struct.pack(">H", 1000)))
            except OSError:
                pass
        self.closed = True
        self.sock.close()
