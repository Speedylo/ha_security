"""W2 (a) — `network.tcp.local`, at the decision layer: who may reach which device, and the record.

Until W2 (a) the capability existed in the manifest schema only (`notes/w2a_local_tcp_prediction.md`
§1). This suite runs the real `Mediator`, `ActingPolicy` and `EgressBroker`, with the sandbox's own
`Channel` on the far end, against a listener on one of this host's private addresses. The spawned
version, with a real integration and a fake device, is `endtoend_local`.

    L2   a declared port on a home-network address is granted, and the descriptor that crosses
         the channel is connected to the device: bytes sent on it arrive there
    L4   an undeclared port is refused, with the clause, and nothing reaches the device
    L5   loopback, link-local and public addresses are refused even with the port declared —
         by the mediator, which does not trust the sandbox's own routing
    L6   the durable record names the address as well as the port
    shim the sandbox routes a home-network address to the mediator and leaves its own loopback
         alone

Run:  python3 -m confine.selftest_local_tcp
"""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import sys
import tempfile
from pathlib import Path

from .audit import AuditLog
from .egress import EgressBroker, is_lan
from .egress_shim import EgressShim
from .mediator import Mediator
from .platform import ActingPolicy, Platform
from .selftest_push import Sandbox, component

results: list[bool] = []
PORT_DECLARED = 46444


def check(claim: str, condition: bool, detail: str = "") -> None:
    results.append(condition)
    print(f"{'  ok  ' if condition else '  FAIL'}  {claim}{f'  — {detail}' if detail else ''}")


def a_private_address() -> str | None:
    """One of this host's own home-network addresses, found without sending anything."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 9))      # UDP connect only picks a route
        address = probe.getsockname()[0]
    except OSError:
        return None
    finally:
        probe.close()
    return address if is_lan(address) else None


def main() -> int:
    lan = a_private_address()
    if lan is None:
        print("this host has no private address to stand a device on")
        return 2
    device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    device.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    device.bind((lan, PORT_DECLARED))
    device.listen(4)
    device.settimeout(2)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        directory = component(root, "localdev", [])
        (directory / "manifest.json").write_text(json.dumps(
            {"domain": "localdev", "name": "localdev", "version": "1", "requirements": [],
             "permissions": {"schema_version": 1,
                             "network": {"local": {"tcp": [PORT_DECLARED]}}}}))
        log = AuditLog(path=root / "audit" / "decisions.jsonl")
        mediator = Mediator(policy=ActingPolicy({}, Platform(), broker=EgressBroker(
            connect_timeout=2)), log=log)
        sandbox = Sandbox(mediator, "localdev", directory)

        def ask(address: str, port: int) -> tuple[dict, int | None]:
            import threading
            got: list = []
            worker = threading.Thread(target=lambda: got.append(sandbox.channel.exchange(
                {"op": "network.tcp.local", "address": address, "port": port})))
            worker.start()
            while worker.is_alive():
                mediator.serve(timeout=0.05)
            worker.join()
            return got[0]

        print(f"\nL2 — a device at {lan}:{PORT_DECLARED}, port declared\n")
        answer, fd = ask(lan, PORT_DECLARED)
        check("granted with the clause naming the declared port",
              answer.get("ok") is True
              and answer.get("clause") == "/permissions/network/local/tcp/0",
              f"{answer.get('clause')}")
        check("and a descriptor crossed the channel", fd is not None)
        try:
            peer, _ = device.accept()
            used = socket.socket(fileno=fd) if fd is not None else None
            if used is not None:
                used.sendall(b"query")
                arrived = peer.recv(16)
                used.close()
            else:
                arrived = b""
            peer.close()
        except OSError as err:
            arrived = f"{err}".encode()
        check("which is connected to the device: what the sandbox sends, the device receives",
              arrived == b"query", repr(arrived))

        print("\nL4 — an undeclared port\n")
        answer, fd = ask(lan, PORT_DECLARED + 1)
        check("refused, naming the clause that held nothing matching",
              answer.get("ok") is False and fd is None
              and answer.get("clause") == "/permissions/network/local/tcp",
              answer.get("reason", ""))

        print("\nL5 — the declared port, on addresses that are not the home network\n")
        for address, why in (("127.0.0.1", "loopback: the mediator's own host"),
                             ("169.254.10.10", "link-local"),
                             ("8.8.8.8", "public")):
            answer, fd = ask(address, PORT_DECLARED)
            check(f"{why} ({address}) is refused by the mediator",
                  answer.get("ok") is False and fd is None
                  and "not an address on the home network" in answer.get("reason", ""),
                  answer.get("reason", ""))

        print("\nL6 — the record\n")
        decided = [r for r in log.records() if r["kind"] == "decision"
                   and r["op"] == "network.tcp.local"]
        first = decided[0] if decided else {}
        check("the grant's durable record names the address and the port",
              first.get("requested", {}).get("address") == lan
              and first.get("requested", {}).get("port") == PORT_DECLARED
              and first.get("target") == str(PORT_DECLARED), f"{first.get('requested')}")
        loopback = [r["allowed"] for r in decided
                    if r.get("requested", {}).get("address") == "127.0.0.1"]
        check("a refused address shows the grant and then the refusal, the refusal last",
              loopback == [True, False], f"{loopback}")
        check("every chain verifies", log.verify() == [])

        print("\nshim — what the sandbox routes to the mediator\n")
        routed: list = []
        shim = EgressShim(connect_via=lambda h, p: -1,
                          connect_local=lambda a, p: routed.append((a, p)) or os.dup(0))
        shim.install()
        try:
            probe = socket.socket()
            try:
                probe.connect((lan, PORT_DECLARED))
            except OSError:
                pass
            probe.close()
            own = socket.socket()
            own.settimeout(0.5)
            try:
                own.connect(("127.0.0.1", 1))
            except OSError:
                pass
            own.close()
        finally:
            shim.uninstall()
        check("a home-network address is routed to the mediator",
              (lan, PORT_DECLARED) in routed, f"{routed}")
        check("the sandbox's own loopback is not", all(a != "127.0.0.1" for a, _ in routed))
        sandbox.channel.sock.close()
    device.close()

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
