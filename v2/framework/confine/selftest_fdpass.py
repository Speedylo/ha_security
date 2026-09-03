"""Descriptor passing across the sandbox boundary, and what a hostile sender cannot do with it.

§7.24 settled the egress mechanism: the mediator resolves a name, checks it against the manifest,
connects, and passes the **already-connected socket** into the sandbox. The sandbox receives
something it could not have created and — for TCP — cannot re-point, which
`selftest_socket_pinning.py` establishes and which is why only TCP travels this way.

This file tests the carriage rather than the policy: that a descriptor crosses intact and keeps
working, and that the four ways a sender could abuse the mechanism are refused.

**The sandbox is the untrusted end of this socket** (`channel.py`'s own words), and descriptor
passing is the first thing to cross it that costs the receiver a kernel resource. A sender that
can make the receiver hold descriptors it did not ask for can exhaust its descriptor table for
free, which is a denial of service against the mediator — the one component §5.15.4 names as
having nothing above it to check it. So the cases here are mostly about what is *refused*:

  1-2  a descriptor crosses, and the socket still works on the far side
  3    a descriptor sent to a caller not expecting one is **closed**, not retained
  4    more descriptors than `MAX_FDS` are refused and all of them closed
  5    a malformed frame carrying a descriptor closes it before raising
  6    ordinary frames still work — the change is additive

Cases 3-5 are checked by counting the receiver's open descriptors, which is the only way to tell
"closed" from "kept and forgotten": both look identical from the message.

Run: `python3 -m confine.selftest_fdpass`
"""

from __future__ import annotations

import array
import os
import socket
import sys
import threading

try:
    from .channel import MAX_FDS, Channel, ProtocolError
except ImportError:  # run as a plain script
    from channel import MAX_FDS, Channel, ProtocolError


PASS, FAIL = "  ok  ", " FAIL "
_results: list[tuple[bool, str]] = []


def check(condition: bool, name: str, detail: str = "") -> None:
    _results.append((bool(condition), name))
    print(f"[{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def open_fds() -> int:
    """How many descriptors this process holds. The only honest way to test for a leak."""
    try:
        return len(os.listdir("/proc/self/fd"))
    except OSError:
        return -1


def channel_pair() -> tuple[Channel, Channel]:
    left, right = Channel.pair()
    return Channel(left), Channel(right)


def _echo_server() -> tuple[socket.socket, int]:
    """A listener whose connections say something recognisable, so a passed descriptor can be
    shown to be *the same connection* rather than merely a valid socket."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)

    def serve() -> None:
        try:
            conn, _ = listener.accept()
            conn.sendall(b"hello-from-the-far-end")
            conn.recv(64)
            conn.close()
        except OSError:
            pass

    threading.Thread(target=serve, daemon=True).start()
    return listener, listener.getsockname()[1]


# -- 1-2: the descriptor crosses and still works ---------------------------------------

def case_descriptor_crosses() -> None:
    listener, port = _echo_server()
    mediator, sandbox = channel_pair()

    # What the mediator does: connect on the integration's behalf, then hand it over.
    connected = socket.create_connection(("127.0.0.1", port), timeout=5)
    mediator.send({"ok": True, "clause": "/permissions/network/egress/0"}, fd=connected.fileno())
    connected.close()          # the mediator drops its copy; the sandbox's must survive

    message, fd = sandbox.recv_message()
    check(message is not None and message.get("clause") == "/permissions/network/egress/0",
          "1. the message arrives alongside the descriptor",
          str(message))
    check(fd is not None, "1b. a descriptor arrived", f"fd={fd}")

    if fd is not None:
        received = socket.socket(fileno=fd)
        greeting = received.recv(64)
        check(greeting == b"hello-from-the-far-end",
              "2. the received descriptor is the live connection the mediator made",
              greeting.decode(errors="replace"))
        received.close()

    for handle in (mediator, sandbox):
        handle.close()
    listener.close()


# -- 3: an unexpected descriptor is closed ---------------------------------------------

def case_unexpected_descriptor_is_closed() -> None:
    """`recv` is the path every existing call site uses. A sender attaching a socket to an
    ordinary request must not make those call sites accumulate descriptors."""
    listener, port = _echo_server()
    mediator, sandbox = channel_pair()

    connected = socket.create_connection(("127.0.0.1", port), timeout=5)
    before = open_fds()
    mediator.send({"op": "entity.read", "entity": "sensor.x"}, fd=connected.fileno())
    connected.close()

    message = sandbox.recv()          # the plain path — not expecting a descriptor
    after = open_fds()

    check(message is not None and message.get("op") == "entity.read",
          "3. the message still arrives on the plain recv path")
    check(after <= before,
          "3b. an unexpected descriptor is closed, not retained",
          f"{before} descriptors before, {after} after")

    for handle in (mediator, sandbox):
        handle.close()
    listener.close()


# -- 4: more descriptors than allowed ---------------------------------------------------

def case_too_many_descriptors() -> None:
    """A sender is free to attach several; a receiver that kept them would let the far end fill
    its descriptor table. Sent with a raw `sendmsg` because `Channel.send` will not do it."""
    mediator, sandbox = channel_pair()
    spares = [os.open("/dev/null", os.O_RDONLY) for _ in range(MAX_FDS + 3)]

    before = open_fds()
    frame = b"\x00\x00\x00\x02{}"
    mediator.sock.sendmsg(
        [frame],
        [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", spares))])

    refused = False
    try:
        sandbox.recv_message()
    except ProtocolError as err:
        refused = "exceeds" in str(err) or "truncated" in str(err)
    after = open_fds()

    for fd in spares:
        os.close(fd)
    for handle in (mediator, sandbox):
        handle.close()

    check(refused, f"4. more than MAX_FDS={MAX_FDS} descriptors in one frame is refused")
    check(after <= before,
          "4b. and every one of them is closed rather than kept",
          f"{before} before, {after} after")


# -- 5: a malformed frame carrying a descriptor -----------------------------------------

def case_malformed_frame_closes_its_descriptor() -> None:
    """A frame can be refused *after* its descriptor has already been received — the ancillary
    data rides with the length prefix, and the payload is parsed afterwards. Every rejection
    path must close what it has, or a sandbox leaks the mediator's descriptors one bad frame
    at a time."""
    listener, port = _echo_server()
    mediator, sandbox = channel_pair()

    connected = socket.create_connection(("127.0.0.1", port), timeout=5)
    before = open_fds()

    # A valid length prefix carrying a descriptor, followed by a payload that is not JSON.
    payload = b"not json at all"
    frame = len(payload).to_bytes(4, "big") + payload
    mediator.sock.sendmsg(
        [frame],
        [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", [connected.fileno()]))])
    connected.close()

    refused = False
    try:
        sandbox.recv_message()
    except ProtocolError:
        refused = True
    after = open_fds()

    for handle in (mediator, sandbox):
        handle.close()
    listener.close()

    check(refused, "5. a frame whose payload is not JSON is refused even carrying a descriptor")
    check(after <= before,
          "5b. and the descriptor it carried is closed before the error propagates",
          f"{before} before, {after} after")


# -- 6: the change is additive ----------------------------------------------------------

def case_ordinary_frames_unaffected() -> None:
    """Twelve self-tests already depend on this class. The header read moved from `recv` to
    `recvmsg`, which is exactly the kind of change that works for the new case and quietly
    breaks the old one."""
    mediator, sandbox = channel_pair()
    mediator.send({"op": "service.call", "service": "lock.lock", "id": 7})
    message = sandbox.recv()
    check(message == {"op": "service.call", "service": "lock.lock", "id": 7},
          "6. an ordinary frame with no descriptor is unchanged", str(message))

    # A frame larger than one read, to exercise the loop in `_read_header` and `_read_exactly`.
    big = {"op": "x", "blob": "y" * 200_000}
    mediator.send(big)
    check(sandbox.recv() == big, "6b. a frame spanning several reads still reassembles")

    mediator.close()
    check(sandbox.recv() is None, "6c. a closed far end still reads as None, not an error")
    sandbox.close()


def main() -> int:
    print(__doc__.strip().splitlines()[0])
    print("=" * 78)
    for case in (case_descriptor_crosses,
                 case_unexpected_descriptor_is_closed,
                 case_too_many_descriptors,
                 case_malformed_frame_closes_its_descriptor,
                 case_ordinary_frames_unaffected):
        case()
    passed = sum(1 for ok, _ in _results if ok)
    print("=" * 78)
    print(f"{passed}/{len(_results)} checks passed")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
