"""A fake Tuya device announcing itself on the home network, for W2 (b).

Tuya devices broadcast a discovery message about every five seconds: plaintext JSON on UDP 6666
(protocol 3.1) and AES-encrypted JSON on 6667 (3.3). `localtuya` listens on both with asyncio
datagram endpoints, the shape §7.25.5 found unserved. Each message is framed the way `localtuya`'s
`TuyaDiscovery.datagram_received` reads it: a 20-byte header, then the payload, then an 8-byte
trailer (`data[20:-8]`). The key for 6667 is `md5("yGAdlopoPVldABfn")`, published in
`localtuya`'s own source.

The two ports announce **different** device ids, so the result shows which port each discovery
came through. Sent once a second, unicast to the given address, for `--seconds`. Every send is
logged.

Run:  python3 fake_tuya.py --to 10.126.83.113 --log sends.jsonl
"""

from __future__ import annotations

import argparse
import binascii
import json
import socket
import struct
import sys
import time
from hashlib import md5

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()
PLAIN_ID, ENCRYPTED_ID = "fakeplain000006666", "fakecrypt000006667"


def frame(payload: bytes, cmd: int = 0x13) -> bytes:
    header = struct.pack(">IIIII", 0x000055AA, 0, cmd, len(payload) + 8, 0)
    crc = binascii.crc32(header + payload) & 0xFFFFFFFF
    return header + payload + struct.pack(">II", crc, 0x0000AA55)


def announcement(device_id: str, address: str, version: str) -> bytes:
    return json.dumps({"ip": address, "gwId": device_id, "active": 2, "ability": 0,
                       "mode": 0, "encrypt": True, "productKey": "fakeproductkey",
                       "version": version}).encode()


def encrypt(data: bytes) -> bytes:
    pad = 16 - len(data) % 16
    data += bytes([pad]) * pad
    encryptor = Cipher(algorithms.AES(UDP_KEY), modes.ECB()).encryptor()
    return encryptor.update(data) + encryptor.finalize()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--seconds", type=float, default=900)
    args = ap.parse_args()
    log = open(args.log, "a", buffering=1)
    plain = frame(announcement(PLAIN_ID, args.to, "3.1"))
    encrypted = frame(encrypt(announcement(ENCRYPTED_ID, args.to, "3.3")))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(json.dumps({"ready": True, "ids": [PLAIN_ID, ENCRYPTED_ID]}), flush=True)
    deadline = time.monotonic() + args.seconds
    while time.monotonic() < deadline:
        for port, payload in ((6666, plain), (6667, encrypted)):
            try:
                sock.sendto(payload, (args.to, port))
                log.write(json.dumps({"t": round(time.time(), 3), "kind": "sent",
                                      "port": port, "bytes": len(payload)}) + "\n")
            except OSError as err:
                log.write(json.dumps({"t": round(time.time(), 3), "kind": "error",
                                      "port": port, "error": str(err)}) + "\n")
        time.sleep(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
