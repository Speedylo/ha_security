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

import array
import json
import os
import socket
import struct

# Generous for the payloads of §5.11.3 — an entity read, a service call — and small enough
# that a sandbox declaring a four-gigabyte frame is refused rather than believed.
MAX_FRAME = 1 << 20

# **At most one descriptor per message, and the cap is enforced on receipt rather than trusted.**
# A sender is free to attach as many as it likes; a receiver that accepted them would let the far
# end fill its descriptor table, which is a denial of service against the mediator that costs the
# sandbox nothing. Anything above this is closed and the frame refused.
MAX_FDS = 1

# Space for the ancillary data of MAX_FDS descriptors, computed rather than guessed.
_FD_SPACE = socket.CMSG_SPACE(MAX_FDS * array.array("i").itemsize)

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

    @staticmethod
    def frame(message: dict) -> bytes:
        """The bytes of one frame, for a sender that queues them instead of blocking on them.

        The mediator needs this once it speaks first (W1's push loop): it must never block on
        a sandbox that has stopped reading, so it queues frames and writes them when the socket
        is writable, and the length check has to happen at queueing time.
        """
        payload = json.dumps(message, separators=(",", ":")).encode()
        if len(payload) > MAX_FRAME:
            raise ProtocolError(f"message of {len(payload)} bytes exceeds {MAX_FRAME}")
        return _LENGTH.pack(len(payload)) + payload

    def send(self, message: dict, fd: int | None = None) -> None:
        """One frame, optionally carrying one open file descriptor.

        The descriptor is how §7.24's egress path works: the mediator resolves the name, checks
        it against the manifest, connects, and passes the **already-connected socket** across.
        The sandbox receives something it could not have created and cannot re-point —
        `selftest_socket_pinning.py` is the evidence for that last clause, and for why only TCP
        travels this way.

        On a stream socket ancillary data rides with the first byte of the send, so the
        descriptor is attached to the length prefix and the receiver picks it up on the same
        read. A partial `sendmsg` is finished with an ordinary `sendall`: the descriptor has
        already crossed with the first byte and must not be sent twice.
        """
        frame = self.frame(message)

        if fd is None:
            self.sock.sendall(frame)
            return

        rights = array.array("i", [fd])
        sent = self.sock.sendmsg([frame],
                                 [(socket.SOL_SOCKET, socket.SCM_RIGHTS, rights)])
        if sent < len(frame):
            self.sock.sendall(frame[sent:])

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

    def _read_header(self) -> tuple[bytes | None, list[int]]:
        """The length prefix, and any descriptor that arrived with it.

        `recvmsg` rather than `recv` because on a stream socket the ancillary data rides with
        the first byte of the frame, which is in this header. Reading the header with a plain
        `recv` would make the kernel discard the descriptor — silently, and with the frame
        itself arriving intact, which is the kind of failure that gets diagnosed as "the
        connection didn't work" three layers away.

        **The untrusted end is on the other side of this call**, so what arrives is bounded
        before it is believed: descriptors above `MAX_FDS` are closed rather than kept, and a
        truncated control message is a protocol error rather than a partial success.
        """
        chunks: list[bytes] = []
        fds: list[int] = []
        remaining = _LENGTH.size
        while remaining:
            try:
                data, ancillary, flags, _ = self.sock.recvmsg(remaining, _FD_SPACE,
                                                              socket.MSG_CMSG_CLOEXEC)
            except OSError as err:
                _close_all(fds)
                raise ProtocolError(f"recvmsg failed: {err}") from err

            for level, kind, payload in ancillary:
                if level != socket.SOL_SOCKET or kind != socket.SCM_RIGHTS:
                    continue
                received = array.array("i")
                # Trailing bytes that do not complete an int are not a descriptor; truncate to
                # whole items rather than letting `frombytes` raise on a hostile length.
                received.frombytes(payload[:len(payload) - (len(payload) % received.itemsize)])
                fds.extend(received)

            # MSG_CTRUNC means the kernel had more control data than the space offered and
            # dropped some. Descriptors lost that way are closed by the kernel, not leaked, but
            # the frame can no longer be trusted to mean what it says.
            if flags & socket.MSG_CTRUNC:
                _close_all(fds)
                raise ProtocolError("control message truncated; descriptors were dropped")

            if not data:
                _close_all(fds)
                return (None if not chunks else b"".join(chunks)), []
            chunks.append(data)
            remaining -= len(data)

        if len(fds) > MAX_FDS:
            # Counted before closing: `_close_all` empties the list, and until 2026-10-07 this
            # message said "0 descriptors" in the durable record (verification 4.12, F52).
            count = len(fds)
            _close_all(fds)
            raise ProtocolError(f"{count} descriptors in one frame exceeds {MAX_FDS}")
        return b"".join(chunks), fds

    def recv(self) -> dict | None:
        """One message, or None when the far end has closed.

        A descriptor arriving on a call that was not expecting one is **closed**, not kept: a
        sandbox must not be able to grow the mediator's descriptor table by attaching sockets
        to ordinary requests. Callers that do expect one use `recv_message`.
        """
        message, fd = self.recv_message()
        if fd is not None:
            os.close(fd)
        return message

    def recv_message(self) -> tuple[dict | None, int | None]:
        """One message and the descriptor it carried, if any."""
        header, fds = self._read_header()
        fd = fds[0] if fds else None
        if header is None:
            _close_all(fds)
            return None, None
        if len(header) < _LENGTH.size:
            _close_all(fds)
            raise ProtocolError("truncated length prefix")
        # Every failure from here on closes the descriptor before raising. A frame that is
        # refused must not leave an open socket behind in the refusing process — that would let
        # a sandbox leak the mediator's descriptors one malformed frame at a time, which is the
        # same denial of service `MAX_FDS` exists to prevent, arrived at by another route.
        try:
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
        except BaseException:
            _close_all(fds)
            raise
        return message, fd

    def fileno(self) -> int:
        return self.sock.fileno()

    def close(self) -> None:
        self.sock.close()


def _close_all(fds: list[int]) -> None:
    """Close descriptors the receiver has decided not to keep.

    Once `recvmsg` has returned them they belong to this process, so dropping the reference
    leaks them. Every rejection path calls this, which is why the rejection paths are worth
    having a helper for rather than an `os.close` each.
    """
    for fd in fds:
        try:
            os.close(fd)
        except OSError:
            pass
    fds.clear()
