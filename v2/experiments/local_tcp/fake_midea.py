"""A fake Midea air conditioner on the home network, for W2 (a).

It answers what `midea_ac_lan`'s manual setup asks of a device, and records everything it sees:

  - **UDP 6445 and 20086, discovery.** Any datagram gets a protocol-V2 discovery reply: a `5a5a`
    header carrying the device id, then a body encrypted with `midea-lan`'s own `LocalSecurity`.
    The body gives the TCP port, a serial number and an SSID whose second part names the type
    (`ac`). Using the library's encryption shares that code with the integration, which is
    acceptable because the protocol is not what is under test (`notes/w2a_local_tcp_prediction.md`).
  - **TCP 6444, the device connection.** Accepted, held open, and every byte received recorded.
    A V2 device needs no authentication, so a successful connect is all the setup step requires.

Every event is one JSON line in the log: kind, the peer's address, and the bytes' length and
first bytes. **The peer's address is the evidence that matters**: in the confined arm it must be
the host's own, because the sandbox has no route and the mediator makes the connection.

Run (on the Pi, with `midea-lan` importable):
    PYTHONPATH=~/r2exp/t2/midea-src python3 fake_midea.py --bind 10.126.83.113 --log events.jsonl
"""

from __future__ import annotations

import argparse
import json
import selectors
import socket
import sys
import time

from midealan.security import LocalSecurity

DEVICE_ID = 151732605161920          # fits the 6 bytes the reply carries
TCP_PORT = 6444
# 32 characters: the integration takes the model from [9:17] and, for this length, the MAC from
# [16:28], which must be hexadecimal.
SERIAL = "0000AC00000000000a1b2c3d4e5f0000"
SSID = "midea_ac_0042"


def discovery_reply() -> bytes:
    """The V2 reply `midealan.discover._parse_discover_response` accepts."""
    body = bytearray(41)
    body[4:8] = TCP_PORT.to_bytes(4, "little")
    body[8:40] = SERIAL.encode("ascii")
    body[40] = len(SSID)
    body += SSID.encode("ascii") + bytes(16)
    header = bytearray(40)
    header[0:2] = bytes.fromhex("5a5a")
    header[20:26] = DEVICE_ID.to_bytes(6, "little")
    return bytes(header) + LocalSecurity().aes_encrypt(bytes(body)) + bytes(16)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--seconds", type=float, default=900)
    args = ap.parse_args()
    log = open(args.log, "a", buffering=1)

    def note(kind: str, peer, data: bytes = b"") -> None:
        log.write(json.dumps({"t": round(time.time(), 3), "kind": kind, "peer": peer[0],
                              "port": peer[1], "bytes": len(data),
                              "head": data[:8].hex()}) + "\n")

    selector = selectors.DefaultSelector()
    for port in (6445, 20086):
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp.bind((args.bind, port))
        selector.register(udp, selectors.EVENT_READ, "udp")
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((args.bind, TCP_PORT))
    listener.listen(8)
    selector.register(listener, selectors.EVENT_READ, "listen")
    print(json.dumps({"ready": True, "device_id": DEVICE_ID}), flush=True)

    deadline = time.monotonic() + args.seconds
    while time.monotonic() < deadline:
        for key, _ in selector.select(1.0):
            sock = key.fileobj
            if key.data == "udp":
                data, peer = sock.recvfrom(2048)
                note("udp", peer, data)
                sock.sendto(discovery_reply(), peer)
            elif key.data == "listen":
                conn, peer = sock.accept()
                note("tcp_accept", peer)
                selector.register(conn, selectors.EVENT_READ, ("tcp", peer))
            else:
                peer = key.data[1]
                data = sock.recv(4096)
                if not data:
                    note("tcp_close", peer)
                    selector.unregister(sock)
                    sock.close()
                else:
                    note("tcp_data", peer, data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
