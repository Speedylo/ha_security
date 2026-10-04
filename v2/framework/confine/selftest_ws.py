"""The WebSocket client against RFC 6455's own examples, before it is trusted with (A).

Every check here uses a value printed in the RFC, so the test does not share an author's
misunderstanding with the code it tests — the failure mode §7.31 found three times.

    §1.3 / §4.2.2   the accept value for the RFC's sample key
    §5.7            "Hello" as a single masked frame, byte for byte, with the RFC's mask
    §5.7            "Hello" unmasked from a server, and the same split into two fragments
    §5.7            the 126 and 127 extended-length forms (256 bytes, 64 KiB)
    §5.1            a masked frame *from the server* is refused
    §5.5.2          a ping is answered with a pong carrying its payload — over a real socket pair

Run:  python3 -m confine.selftest_ws
"""

from __future__ import annotations

import socket
import sys

from .ws import (PONG, TEXT, FrameParser, WebSocket, WebSocketError, accept_for,
                 encode_frame)

results: list[bool] = []


def check(claim: str, condition: bool, detail: str = "") -> None:
    results.append(condition)
    print(f"{'  ok  ' if condition else '  FAIL'}  {claim}{f'  — {detail}' if detail else ''}")


def main() -> int:
    check("§4.2.2: the accept value for the RFC's sample key",
          accept_for("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")

    rfc_masked = bytes([0x81, 0x85, 0x37, 0xfa, 0x21, 0x3d, 0x7f, 0x9f, 0x4d, 0x51, 0x58])
    check("§5.7: 'Hello' masked with the RFC's key is the RFC's eleven bytes",
          encode_frame(TEXT, b"Hello", mask_key=bytes([0x37, 0xfa, 0x21, 0x3d])) == rfc_masked)

    parser = FrameParser()
    check("§5.7: an unmasked server frame parses to 'Hello'",
          parser.feed(bytes([0x81, 0x05]) + b"Hello") == [(True, TEXT, b"Hello")])

    parts = parser.feed(bytes([0x01, 0x03]) + b"Hel")
    parts += parser.feed(bytes([0x80, 0x02]) + b"lo")
    check("§5.7: the fragmented form arrives as two frames, FIN only on the second",
          parts == [(False, TEXT, b"Hel"), (True, 0x0, b"lo")])

    check("bytes arriving one at a time still make one frame, and only at the end",
          [f for b in bytes([0x81, 0x05]) + b"Hello" for f in parser.feed(bytes([b]))]
          == [(True, TEXT, b"Hello")])

    medium, large = b"x" * 256, b"y" * 65536
    got = parser.feed(bytes([0x82, 126]) + (256).to_bytes(2, "big") + medium)
    got += parser.feed(bytes([0x82, 127]) + (65536).to_bytes(8, "big") + large)
    check("§5.7: the 16-bit and 64-bit extended lengths", got == [(True, 0x2, medium),
                                                               (True, 0x2, large)])

    try:
        FrameParser().feed(rfc_masked)
        refused = False
    except WebSocketError:
        refused = True
    check("§5.1: a masked frame from the server is refused", refused)

    # §5.5.2 over a real socket: a fake server sends a ping and then a message, and must get the
    # pong back before anything else, carrying the ping's payload.
    ours, server = socket.socketpair()
    client = WebSocket.__new__(WebSocket)
    client.sock, client.parser, client._fragments = ours, FrameParser(), []
    client.closed, client._pending = False, []
    server.sendall(bytes([0x89, 0x04]) + b"beat" + bytes([0x81, 0x07]) + b'{"a":1}')
    got = client.receive()
    raw = server.recv(64)
    # Unmask what the client sent, as a server would.
    frame = raw[0], raw[1] & 0x7F, raw[2:6], raw[6:]
    payload = bytes(b ^ frame[2][i % 4] for i, b in enumerate(frame[3]))
    check("§5.5.2: a ping is answered with a masked pong carrying its payload",
          frame[0] == 0x80 | PONG and raw[1] & 0x80 and payload == b"beat", repr(payload))
    check("and the message after the ping arrives as JSON", got == [{"a": 1}], repr(got))
    ours.close()
    server.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
