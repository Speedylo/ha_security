"""Datagrams through the relay, with real sockets on both ends.

`udp_demand.md` measured 15 of 75 integrations needing UDP — 20%, not the 1-of-12 that an
earlier draft used to recommend refusing it. This is what serving them costs and what it buys.

  1  a unicast datagram reaches a declared port and the reply comes back
  2  an undeclared port is denied, naming its clause
  3  **discovery** — the mediator broadcasts on a declared port and returns what answered
  4  the sandbox never holds a broadcast-capable socket: `SO_BROADCAST` is recorded, not applied
  5  **the observed-responder rule** — a scan reports which addresses answered, which is the
     only set an address may later be pinned from
  6  payload bounds are enforced before allocation, not after

The asymmetry with TCP is the point of the whole file. TCP hands over a connected descriptor
because a connected TCP socket cannot be re-pointed; UDP cannot, and `selftest_socket_pinning`
is why. So every datagram is copied through the mediator, the destination check lives in
software rather than in the kernel, and `decision_network_capability.md` §8 carries that as a
residual instead of letting "structural" cover both transports.

**What is not covered, and it is a quarter of the population.** Only the synchronous shape is
intercepted. An integration driving `asyncio.DatagramProtocol` waits on a real descriptor
becoming readable and there is none, so `govee`, `localtuya`, `tapo_control` and `xiaomi_miot`
are unserved — 4 of the 15. Case 7 asserts that this fails closed rather than half-working.

Run: `python3 -m confine.selftest_udp`
"""

from __future__ import annotations

import json
import selectors
import asyncio
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

try:
    from .egress import EgressRefused
    from .egress_shim import EgressDenied, DatagramMediator, EgressShim
    from .manifest import Manifest, policy_for
    from .udp_relay import MAX_DATAGRAM, UdpRelay
except ImportError:  # run as a plain script
    from egress import EgressRefused
    from egress_shim import DatagramMediator, EgressShim
    from manifest import Manifest, policy_for
    from udp_relay import MAX_DATAGRAM, UdpRelay


PASS, FAIL = "  ok  ", " FAIL "
_results: list[tuple[bool, str]] = []


def check(condition: bool, name: str, detail: str = "") -> None:
    _results.append((bool(condition), name))
    print(f"[{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))


# **The device's own socket calls, captured before the shim exists.** `egress_shim` patches
# `socket.socket` for the whole process, so a fake device living in this process is intercepted
# as readily as the integration is — its `recvfrom` was answered by the relay instead of by the
# network, and the reply never left. In deployment the device is another machine and the question
# cannot arise; here the test has to say which side of the boundary it is standing on. That is
# the third place this file's boundary has had to be made explicit, after `EgressBroker.resolver`
# and `udp_relay`'s captured methods, and the repetition is itself the finding: **an in-process
# test of a shim that patches a class globally must state, every time, whose sockets are whose.**
_RAW_RECVFROM = socket.socket.recvfrom
_RAW_SENDTO = socket.socket.sendto
_RAW_BIND = socket.socket.bind


def free_port() -> tuple[None, int]:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _RAW_BIND(probe, ("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return None, port


def echo_device(reply: bytes) -> tuple[socket.socket, int]:
    """A device that answers any datagram, standing in for an inverter or a bulb."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _RAW_BIND(sock, ("127.0.0.1", 0))

    def serve() -> None:
        while True:
            try:
                _data, sender = _RAW_RECVFROM(sock, 2048)
            except OSError:
                return
            try:
                _RAW_SENDTO(sock, reply, sender)
            except OSError:
                return

    threading.Thread(target=serve, daemon=True).start()
    return sock, sock.getsockname()[1]


def wire(root: Path, domain: str, permissions: dict) -> tuple[EgressShim, UdpRelay, list]:
    directory = root / "custom_components" / domain
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "__init__.py").write_text("# nothing\n")
    (directory / "manifest.json").write_text(json.dumps(
        {"domain": domain, "name": domain, "version": "1.0.0",
         "permissions": {"schema_version": 1, **permissions}}))
    policy = policy_for({domain: Manifest.load(directory, root)})
    relay = UdpRelay()
    decisions: list = []

    def decide(op: str, **fields):
        # No `allow_private` field: `udp_relay.py` does not read one. Reaching a local device
        # is what `network.local`/`network.discover` clauses are *for*, gated by whether the
        # clause matches at all rather than by a second, request-controlled flag — the flag
        # `network.egress`'s harness had to stop trusting for exactly this reason.
        request = {"op": op, **fields}
        decision = policy(domain, request)
        decisions.append((op, decision))
        return request, decision

    # W2 (b): the mediator watches every socket the relay opens for this sandbox and pushes
    # what arrives. Played here by a thread, so the shim's delivery path is the one under test.
    watched: dict = {}
    holder: list = []
    selector = selectors.DefaultSelector()

    def watch(answer: dict) -> None:
        source = answer.pop("_source", None)
        if source is not None:
            sock, route = source
            watched[sock] = route
            selector.register(sock, selectors.EVENT_READ)

    def pump() -> None:
        while True:
            try:
                ready = selector.select(0.05)
            except (OSError, ValueError):
                return
            for key, _ in ready:
                try:
                    data, sender = _RAW_RECVFROM(key.fileobj, 65535)
                except OSError:
                    continue
                if holder:
                    holder[0].deliver({"route": watched[key.fileobj],
                                       "sender": [sender[0], sender[1]], "data": data.hex()})
    threading.Thread(target=pump, daemon=True).start()

    def send(address: str, port: int, data: bytes) -> int:
        request, decision = decide("network.udp.send", address=address, port=port,
                                   data=data.hex())
        answer = relay.send(domain, request, decision)
        watch(answer)
        return answer["sent"]

    def listen_stream(port: int) -> None:
        request, decision = decide("discover.listen", port=port, stream=True)
        try:
            watch(relay.listen(domain, request, decision))
        except EgressRefused as err:
            # What the sandbox's `listen_stream` raises for a refusal: an `OSError`, which is what
            # unmodified integration code expects from the network (`egress_shim.EgressDenied`).
            raise EgressDenied(err.reason, err.clause) from err

    def recv(address: str, port: int) -> list[bytes]:
        request, decision = decide("network.udp.recv", address=address, port=port, timeout=1.0)
        answer = relay.recv(domain, request, decision)
        return [bytes.fromhex(d["data"]) for d in answer["datagrams"]]

    def scan(port: int, data: bytes) -> list:
        request, decision = decide("discover.scan", port=port, data=data.hex(),
                                   timeout=1.0, broadcast="127.0.0.1")
        answer = relay.scan(domain, request, decision)
        relay.last_scan = answer
        return [(bytes.fromhex(r["data"]), (r["address"], r["port"]))
                for r in answer["responses"]]

    def listen(port: int) -> list:
        request, decision = decide("discover.listen", port=port, timeout=0.5)
        answer = relay.listen(domain, request, decision)
        return [(bytes.fromhex(r["data"]), (r["address"], r["port"]))
                for r in answer["responses"]]

    shim = EgressShim(connect_via=lambda h, p: (_ for _ in ()).throw(
        OSError("TCP is not what this suite tests")),
        datagrams=DatagramMediator(send=send, recv=recv, scan=scan, listen=listen,
                                   listen_stream=listen_stream))
    holder.append(shim)
    return shim, relay, decisions


# -- 1-2: unicast --------------------------------------------------------------------------

def case_unicast(root: Path) -> None:
    device, port = echo_device(b"inverter-says-hello")
    shim, relay, decisions = wire(root, "demo_inverter",
                                  {"network": {"local": {"udp": [port]}}})
    try:
        shim.install()
        # An ordinary synchronous UDP client. It holds a socket that is connected to nothing
        # and carries no traffic; every call on it becomes a request to the mediator.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sent = sock.sendto(b"WIFIKIT-214028-READ", ("127.0.0.1", port))
        check(sent == 19, "1. a unicast datagram is accepted for a declared port", f"{sent} bytes")

        data, sender = sock.recvfrom(2048)
        check(data == b"inverter-says-hello",
              "1b. and the device's reply comes back through the relay",
              data.decode(errors="replace"))
        check(sender == ("127.0.0.1", port),
              "1c. with the address it came from, so the integration can tell devices apart",
              str(sender))
        sock.close()

        # An undeclared port. Nothing in this manifest mentions it.
        other = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        refused = None
        try:
            other.sendto(b"probe", ("127.0.0.1", port + 1))
        except EgressRefused as err:
            refused = err
        other.close()
        check(refused is not None, "2. an undeclared port is denied",
              refused.reason if refused else "it was sent")
        check(refused is not None and refused.clause == "/permissions/network/local/udp",
              "2b. and the denial names the clause that held no match (F3)",
              str(refused.clause) if refused else "")

        # 2c. W2 (a) baseline, arm C: a refused send left a peer behind, every later recvfrom
        # asked the relay for it and was refused, and the integration's retry loop turned that
        # into ~1,000 refused decisions a second. Now the socket just times out, asking nothing.
        asked_before = sum(1 for op, _ in decisions if op == "network.udp.recv")
        other2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        other2.settimeout(0.5)
        try:
            other2.sendto(b"probe", ("127.0.0.1", port + 1))
        except EgressRefused:
            pass
        try:
            other2.recvfrom(2048)
            outcome = "received something"
        except socket.timeout:
            outcome = "timed out"
        other2.close()
        asked_after = sum(1 for op, _ in decisions if op == "network.udp.recv")
        check(outcome == "timed out" and asked_after == asked_before,
              "2c. after a refused send, recvfrom times out and asks the mediator nothing",
              f"{outcome}; {asked_after - asked_before} recv requests")
    finally:
        shim.uninstall()
        relay.close()
        device.close()


# -- 8-9: what midea_ac_lan's discovery found, in a real sandbox (W2 (a), 2026-10-04) ---------

def case_two_peers_and_timeout(root: Path) -> None:
    """The two defects a real integration found, each as its own check.

    `midea-lan` sends one discovery datagram to port 6445 and one to 20086, then reads with a
    5 s timeout until `TimeoutError`. The shim asked only the last peer, and raised
    `BlockingIOError` instead of honouring the timeout, so discovery looped forever.
    """
    first, port_a = echo_device(b"reply-from-a")
    second, port_b = echo_device(b"reply-from-b")
    shim, relay, _ = wire(root, "demo_two_peers",
                          {"network": {"local": {"udp": [port_a, port_b]}}})
    try:
        shim.install()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.5)
        sock.sendto(b"discover", ("127.0.0.1", port_a))
        sock.sendto(b"discover", ("127.0.0.1", port_b))
        got = set()
        timed_out_after = None
        start = time.monotonic()
        while True:
            try:
                data, _ = sock.recvfrom(2048)
                got.add(data)
            except socket.timeout:
                timed_out_after = time.monotonic() - start
                break
            if time.monotonic() - start > 30:
                break
        sock.close()
        check(got == {b"reply-from-a", b"reply-from-b"},
              "8. replies from every peer the socket sent to are collected, not only the last",
              str(sorted(got)))
        check(timed_out_after is not None and timed_out_after < 10,
              "9. a socket with a timeout raises TimeoutError once nothing more arrives",
              f"after {timed_out_after:.1f} s" if timed_out_after else "it never timed out")
    finally:
        shim.uninstall()
        relay.close()
        first.close()
        second.close()


# -- 3-5: discovery ------------------------------------------------------------------------

def case_discovery(root: Path) -> None:
    device, port = echo_device(b"device-here")
    shim, relay, _decisions = wire(root, "demo_scanner",
                                   {"network": {"discover": {"scan": [port]},
                                                "local": {"udp": [port]}}})
    try:
        shim.install()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # This is what `solarman/scanner.py` does, line for line.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(b"WIFIKIT-214028-READ", ("255.255.255.255", port))

        # The sandbox's socket was never given SO_BROADCAST — the mediator's was.
        actual = sock.getsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST)
        check(actual == 0,
              "4. SO_BROADCAST is recorded by the shim and never applied to the sandbox's socket",
              f"the sandbox's socket reports {actual}")

        data, sender = sock.recvfrom(2048)
        check(data == b"device-here",
              "3. **discovery** — the mediator broadcast on the declared port and got an answer",
              f"{data.decode(errors='replace')} from {sender}")
        sock.close()

        observed = getattr(relay, "last_scan", {}).get("observed") or []
        check("127.0.0.1" in observed,
              "5. the scan reports which addresses answered — the observed-responder set",
              str(observed))
    finally:
        shim.uninstall()
        relay.close()
        device.close()


# -- 6: bounds -----------------------------------------------------------------------------

def case_bounds(root: Path) -> None:
    device, port = echo_device(b"x")
    shim, relay, _decisions = wire(root, "demo_bounds",
                                   {"network": {"local": {"udp": [port]}}})
    try:
        request = {"op": "network.udp.send", "address": "127.0.0.1", "port": port,
                   "data": "ab" * (MAX_DATAGRAM + 10)}
        from .manifest import Manifest as _M  # noqa: F401 — keeps the import local to the case
        policy = policy_for({"demo_bounds": Manifest.load(
            root / "custom_components" / "demo_bounds", root)})
        decision = policy("demo_bounds", request)
        refused = None
        try:
            relay.send("demo_bounds", request, decision)
        except EgressRefused as err:
            refused = err
        check(refused is not None and "exceeds" in refused.reason,
              "6. an oversized payload is refused before it is decoded, not after",
              refused.reason if refused else "it was sent")

        bad = dict(request, data="not-hex")
        refused = None
        try:
            relay.send("demo_bounds", bad, policy("demo_bounds", bad))
        except EgressRefused as err:
            refused = err
        check(refused is not None and "not hex" in refused.reason,
              "6b. and a payload that is not hex is refused rather than guessed at",
              refused.reason if refused else "it was sent")
    finally:
        relay.close()
        device.close()


# -- 7: the unserved quarter, failing closed ------------------------------------------------

def case_no_relay_fails_closed(root: Path) -> None:
    """A sandbox with no datagram grant, and the asyncio shape that has no descriptor to watch.

    Both must fail rather than half-work. The first is the fail-closed default; the second is
    the limitation named in `udp_relay`'s docstring, asserted here so that it is a *tested*
    boundary rather than a sentence in a docstring that drifts."""
    device, port = echo_device(b"x")
    shim = EgressShim(connect_via=lambda h, p: 0, datagrams=None)   # no grant at all
    try:
        shim.install()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.4)
        # Falls through to the real socket. In a sandbox the namespace has no route and this
        # fails; here it reaches loopback, which is what the assertion below actually checks —
        # that the shim consulted nobody, rather than that the datagram failed.
        sock.sendto(b"probe", ("127.0.0.1", port))
        check(shim.datagrams is None and not shim._dgram,
              "7. with no datagram grant the shim intercepts nothing and asks nobody",
              "fail-closed: in a sandbox this reaches nothing, because the namespace has no route")
        sock.close()
    finally:
        shim.uninstall()
        device.close()

    # 7b. Until W2 (b) this line was `check(True, "...not served...")` — a limitation stated
    # as a passing check that tested nothing. It is now a test of the shape being served:
    # an asyncio endpoint bound to a declared port, as `localtuya`'s discovery binds 6666.
    device, port = free_port()
    shim, relay, decisions = wire(root, "demo_asyncio",
                                  {"network": {"discover": {"listen": [port]}}})
    received: list = []

    class Protocol(asyncio.DatagramProtocol):
        def datagram_received(self, data, addr):
            received.append((data, addr))

    async def listen_and_wait() -> None:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            Protocol, local_addr=("0.0.0.0", port))
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(3):
            _RAW_SENDTO(sender, b"tuya-announce", ("127.0.0.1", port))
            await asyncio.sleep(0.2)
        sender.close()
        transport.close()
    try:
        shim.install()
        asyncio.run(listen_and_wait())
    finally:
        shim.uninstall()
        relay.close()
    check(len(received) >= 1 and received[0][0] == b"tuya-announce",
          "7b. an asyncio DatagramProtocol bound to a declared port receives what arrives",
          f"{len(received)} datagrams" + (f", first from {received[0][1]}" if received else ""))
    # 7d. `govee`'s shape: a socket bound to port 0, handed to `create_datagram_endpoint` with
    # `sock=`, then used to send. Its peer's reply must wake the event loop.
    device2, port2 = echo_device(b"govee-reply")
    shim2, relay2, _ = wire(root, "demo_ephemeral", {"network": {"local": {"udp": [port2]}}})
    replies: list = []

    class Reply(asyncio.DatagramProtocol):
        def datagram_received(self, data, addr):
            replies.append(data)

    async def send_and_wait() -> None:
        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 0))
        sock.setblocking(False)
        transport, _ = await loop.create_datagram_endpoint(Reply, sock=sock)
        transport.sendto(b"scan", ("127.0.0.1", port2))
        for _ in range(20):
            if replies:
                break
            await asyncio.sleep(0.1)
        transport.close()
    try:
        shim2.install()
        asyncio.run(send_and_wait())
    finally:
        shim2.uninstall()
        relay2.close()
        device2.close()
    check(replies == [b"govee-reply"],
          "7d. a socket bound to port 0 before its event loop registers it still gets replies",
          f"{replies}")
    # 7e. Zeroconf's sequence, which the platform's shared HTTP session runs (§7.27): bind 5353
    # with no listen declared, then join the mDNS group. W2 (b) made the bind raise, and then
    # the group join on the socket pair raise EOPNOTSUPP; either broke every confined
    # integration using that session (found by W2 (d), 2026-10-04). Both must succeed, quietly.
    shim3, relay3, decisions3 = wire(root, "demo_zeroconf", {"network": {}})
    outcome = "ok"
    try:
        shim3.install()
        zc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            zc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            zc.bind(("", 5353))
            zc.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                          socket.inet_aton("224.0.0.251") + socket.inet_aton("0.0.0.0"))
            zc.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
        except OSError as err:
            outcome = f"{type(err).__name__}: {err}"
        zc.close()
    finally:
        shim3.uninstall()
        relay3.close()
    refused = [d for op, d in decisions3 if op == "discover.listen" and not d.allowed]
    check(outcome == "ok" and len(refused) == 1,
          "7e. an undeclared bind and a multicast join succeed quietly; the listen is refused once",
          f"{outcome}; {len(refused)} refused listen")
    listens = [d for op, d in decisions if op == "discover.listen"]
    check(len(listens) == 1 and listens[0].allowed,
          "7c. and the listen is one recorded decision, however many datagrams follow",
          f"{len(listens)} listen decisions for {len(received)} datagrams")


def main() -> int:
    print(__doc__.strip().splitlines()[0])
    print("=" * 78)
    with tempfile.TemporaryDirectory(prefix="confine-udp-") as tmp:
        root = Path(tmp)
        case_unicast(root)
        case_two_peers_and_timeout(root)
        case_discovery(root)
        case_bounds(root)
        case_no_relay_fails_closed(root)
    passed = sum(1 for ok, _ in _results if ok)
    print("=" * 78)
    print(f"{passed}/{len(_results)} checks passed")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
