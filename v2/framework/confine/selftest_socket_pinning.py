"""Is a connected socket's peer actually pinned by the kernel? Asked, not assumed.

The egress design hands a **connected descriptor** into the sandbox: the mediator resolves the
name, checks it against the manifest, connects, and passes the open socket across the channel.
The security of that rests entirely on one claim — that the sandbox cannot re-point the socket it
was given. If it can, the mediator's check happened and then stopped mattering, and every
destination guarantee in §5.10.3 is decoration.

**This test exists because the claim was made and was half wrong.** The design note of
2026-09-03 asserted that a connected UDP socket refuses other destinations the way a connected
TCP socket does. It does not. On Linux, `sendto()` with an explicit address on a *connected* UDP
socket **delivers to that address**, on x86_64 and aarch64 alike. Only the inbound direction is
filtered. Had that gone unchecked, an integration granted UDP to one lamp would have been able to
send datagrams to every host on the home network — T10, delivered by the control meant to prevent
it.

TCP behaves differently and correctly: the address argument to `sendto()` is ignored, and a second
`connect()` is refused with `EISCONN`.

So the rule the design follows, and which this file is the evidence for:

    Descriptor passing is safe only for TCP.
    Every UDP path — unicast, listening, discovery — is relayed through the mediator instead.

This is not a test of our code. It is a test of **the kernel property our code depends on**, which
is why it is worth keeping: a future kernel or a different platform that behaves otherwise would
silently invalidate the design, and this fails loudly instead.

Run: `python3 -m confine.selftest_socket_pinning`
"""

from __future__ import annotations

import errno
import socket
import sys
import threading

PASS, FAIL = "  ok  ", " FAIL "
_results: list[tuple[bool, str]] = []


def check(condition: bool, name: str, detail: str = "") -> None:
    _results.append((bool(condition), name))
    print(f"[{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def _errname(err: OSError) -> str:
    return f"{errno.errorcode.get(err.errno, err.errno)} ({err.strerror})"


# -- TCP: the path the design does hand over -------------------------------------------

def case_tcp_is_pinned() -> None:
    received: dict[str, str] = {}

    def serve(listener: socket.socket, name: str) -> None:
        try:
            conn, _ = listener.accept()
            received[name] = conn.recv(64).decode()
            conn.close()
        except OSError:
            pass

    allowed, other = socket.socket(), socket.socket()
    for listener in (allowed, other):
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
    threads = [threading.Thread(target=serve, args=(allowed, "allowed"), daemon=True),
               threading.Thread(target=serve, args=(other, "other"), daemon=True)]
    for thread in threads:
        thread.start()

    sock = socket.socket()
    sock.connect(allowed.getsockname())      # what the mediator does before the handoff
    sock.send(b"to-the-pinned-peer")

    # The sandbox's side: try to use the descriptor it was given to reach somewhere else.
    try:
        sock.sendto(b"elsewhere", other.getsockname())
        redirect_refused = False
        detail = "sendto() accepted the call"
    except OSError as err:
        redirect_refused = True
        detail = _errname(err)

    reconnect_refused = False
    try:
        sock.connect(other.getsockname())
    except OSError as err:
        reconnect_refused = err.errno == errno.EISCONN
        detail += f"; connect() → {_errname(err)}"

    for thread in threads:
        thread.join(timeout=1.0)
    sock.close()
    allowed.close()
    other.close()

    # The claim is about *delivery*, not about which call raised. `sendto` may be accepted and
    # its address ignored — that is still a pin, and it is what Linux does.
    check(received.get("allowed") == "to-the-pinned-peer",
          "TCP — data reaches the peer the mediator connected to",
          received.get("allowed", "nothing arrived"))
    check("other" not in received,
          "TCP — sendto() to another address does NOT deliver there",
          "delivered" if "other" in received else f"not delivered; {detail}")
    check(reconnect_refused or redirect_refused,
          "TCP — the descriptor cannot be re-pointed at a second destination",
          detail)


# -- UDP: the path the design does NOT hand over, and why ------------------------------

def case_udp_is_not_pinned() -> None:
    """Documents the negative result rather than asserting the behaviour we wish it had.

    This case *passes* when UDP turns out to be redirectable, because that is the finding the
    design is built on. If a platform ever pins UDP too, this fails and says so — the design
    would then be safe to simplify, which is worth being told about.
    """
    allowed = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    other = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    allowed.bind(("127.0.0.1", 0))
    other.bind(("127.0.0.1", 0))
    allowed.settimeout(0.3)
    other.settimeout(0.3)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(allowed.getsockname())
    sock.send(b"to-the-pinned-peer")
    reached_peer = _recv(allowed) == "to-the-pinned-peer"

    try:
        sock.sendto(b"elsewhere", other.getsockname())
        leaked = _recv(other) == "elsewhere"
        detail = "delivered" if leaked else "call accepted but not delivered"
    except OSError as err:
        leaked = False
        detail = _errname(err)

    # Inbound is filtered even though outbound is not — worth recording, because it is the half
    # of the property that does hold and it is why a relayed UDP socket still benefits from
    # being connected on the mediator's side.
    intruder = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    intruder.sendto(b"unsolicited", sock.getsockname())
    sock.settimeout(0.3)
    inbound_dropped = _recv(sock) is None

    for handle in (sock, allowed, other, intruder):
        handle.close()

    check(reached_peer, "UDP — data reaches the connected peer")
    check(leaked,
          "UDP — sendto() to another address DOES deliver: descriptor passing is unsafe",
          detail + " — this is why every UDP path is relayed, not handed over")
    check(inbound_dropped,
          "UDP — inbound from a non-peer is dropped, so the receive half is pinned")


def _recv(sock: socket.socket) -> str | None:
    try:
        return sock.recv(64).decode()
    except (TimeoutError, OSError):
        return None


def main() -> int:
    print(__doc__.strip().splitlines()[0])
    print("=" * 78)
    case_tcp_is_pinned()
    case_udp_is_not_pinned()
    passed = sum(1 for ok, _ in _results if ok)
    print("=" * 78)
    print(f"{passed}/{len(_results)} checks passed")
    if passed == len(_results):
        print("\nDescriptor passing is safe for TCP and unsafe for UDP on this host, which is "
              "what\n`notes/decision_network_capability.md` §5.1 is built on.")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
