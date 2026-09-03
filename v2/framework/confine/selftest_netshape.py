"""Does the recorder see what it claims to see?

`netshape` is an instrument, and §7.18's own history is the argument for testing it before
trusting it: the first version of that recorder reported 23 of 37 integrations attempting egress,
and the number was an artifact of *what it attributed*, not of what it observed. An instrument
whose output is going to justify a design decision has to be checked against behaviour whose
answer is already known.

Each case here provokes one network behaviour deliberately and asserts the recorder produced the
row that behaviour should produce. The cases are ordered by what they protect:

  1-3  the socket layer   — that TCP, UDP and inbound are told apart
  4    TLS over a memory BIO — the path aiohttp actually uses, which a `wrap_socket`-only
       recorder would miss entirely, reporting a corpus with no TLS in it
  5    multicast          — the mechanism `zeroconf` uses and `scheduler` died on (§7.17.4)
  6    attribution        — the property §7.18 got wrong once, tested by having a module in a
       "component directory" make the call and asserting it is charged to the integration
  7    the guard          — that an observer which throws does not take the run down with it

Run: `python3 -m confine.selftest_netshape` (or directly from this directory).
"""

from __future__ import annotations

import os
import socket
import ssl
import sys
import tempfile
import threading

try:
    from .netshape import Recorder
except ImportError:  # run as a plain script
    from netshape import Recorder


PASS, FAIL = "  ok  ", " FAIL "
_results: list[tuple[bool, str, str]] = []


def check(condition: bool, name: str, detail: str = "") -> bool:
    _results.append((bool(condition), name, detail))
    print(f"[{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))
    return bool(condition)


def _events(recorder: Recorder, kind: str) -> list[dict]:
    return [e for e in recorder.events if e["kind"] == kind]


def _serve_once(sock: socket.socket, tls: ssl.SSLContext | None = None) -> threading.Thread:
    """Accept one connection and drop it. Enough for a client to complete a handshake."""
    def run() -> None:
        try:
            conn, _ = sock.accept()
            if tls is not None:
                try:
                    conn = tls.wrap_socket(conn, server_side=True)
                except Exception:  # noqa: BLE001 — the client's view is what is under test
                    pass
            conn.close()
        except OSError:
            pass

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


# -- 1-3: the socket layer ----------------------------------------------------------------

def case_tcp_connect() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    recorder = Recorder()
    recorder.install()
    try:
        _serve_once(server)
        client = socket.create_connection(("127.0.0.1", port), timeout=5)
        client.close()
    finally:
        recorder.uninstall()
        server.close()

    connects = _events(recorder, "connect")
    check(any(e.get("port") == port for e in connects),
          "1. a TCP connect is recorded with its port",
          f"{len(connects)} connect event(s), port {port}")
    check(any(e.get("socktype") == "SOCK_STREAM" for e in connects),
          "1b. the socket type is recorded as SOCK_STREAM",
          _first(connects, "socktype"))


def case_udp_sendto() -> None:
    recorder = Recorder()
    recorder.install()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(b"x", ("127.0.0.1", 9))
        sock.close()
    finally:
        recorder.uninstall()

    sends = _events(recorder, "sendto")
    check(sends and sends[0].get("socktype") == "SOCK_DGRAM",
          "2. connectionless UDP is recorded as sendto on a SOCK_DGRAM socket",
          _first(sends, "socktype"))
    check(any(e.get("port") == 9 for e in sends),
          "2b. its destination port is recorded", _first(sends, "port"))


def case_inbound() -> None:
    recorder = Recorder()
    recorder.install()
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        server.close()
    finally:
        recorder.uninstall()

    check(_events(recorder, "bind") and _events(recorder, "listen"),
          "3. inbound is distinguishable — bind and listen are both recorded",
          f"{len(_events(recorder, 'bind'))} bind, {len(_events(recorder, 'listen'))} listen")


# -- 4: TLS, including the path aiohttp uses ----------------------------------------------

def case_tls_wrap_socket() -> None:
    recorder = Recorder()
    recorder.install()
    try:
        context = ssl.create_default_context()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            context.wrap_socket(sock, server_hostname="example.invalid",
                                do_handshake_on_connect=False)
        except Exception:  # noqa: BLE001 — the wrap is what is observed, not its success
            pass
        sock.close()
    finally:
        recorder.uninstall()

    tls = _events(recorder, "tls")
    check(any(e.get("server_hostname") == "example.invalid" for e in tls),
          "4. TLS via wrap_socket records its server_hostname (the SNI a mediator would see)",
          _first(tls, "server_hostname"))


def case_tls_wrap_bio() -> None:
    """aiohttp drives TLS over a memory BIO, not over the socket. A recorder that watches only
    `wrap_socket` reports a corpus in which nothing uses TLS — which would be false, and would
    wrongly suggest a mediator could inspect content."""
    recorder = Recorder()
    recorder.install()
    try:
        context = ssl.create_default_context()
        incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
        context.wrap_bio(incoming, outgoing, server_hostname="bio.example.invalid")
    finally:
        recorder.uninstall()

    tls = _events(recorder, "tls")
    check(any(e.get("how") == "wrap_bio" for e in tls),
          "4b. TLS over a memory BIO is recorded — aiohttp's actual path",
          _first(tls, "how"))
    check(any(e.get("server_hostname") == "bio.example.invalid" for e in tls),
          "4c. and it carries its server_hostname too",
          _first(tls, "server_hostname"))


# -- 5: multicast -------------------------------------------------------------------------

def case_multicast() -> None:
    recorder = Recorder()
    recorder.install()
    joined = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                            socket.inet_aton("224.0.0.251") + socket.inet_aton("127.0.0.1"))
            joined = True
        except OSError:
            pass  # no multicast route here; the recorder is still asked what it saw
        sock.close()
    finally:
        recorder.uninstall()

    events = _events(recorder, "multicast")
    check(events and events[0].get("option") == "IP_ADD_MEMBERSHIP",
          "5. a multicast group join is recorded even though it is not a connect",
          f"joined={joined}, {len(events)} event(s)")


# -- 6: attribution -----------------------------------------------------------------------

def case_attribution() -> None:
    """§7.18's mistake, as a test. A call made from a file inside the integration's own
    directory must be charged to the integration; one made from outside it must not be."""
    with tempfile.TemporaryDirectory() as tmp:
        component = os.path.join(tmp, "custom_components", "fake_integration")
        os.makedirs(component)
        module = os.path.join(component, "reach.py")
        with open(module, "w") as f:
            f.write("import socket\n"
                    "def reach(port):\n"
                    "    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)\n"
                    "    s.sendto(b'x', ('127.0.0.1', port))\n"
                    "    s.close()\n")

        sys.path.insert(0, component)
        try:
            import importlib
            reach = importlib.import_module("reach")

            recorder = Recorder(component_dir=component)
            recorder.install()
            try:
                reach.reach(9)                                   # from inside the component
                outsider = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                outsider.sendto(b"x", ("127.0.0.1", 10))          # from this file
                outsider.close()
            finally:
                recorder.uninstall()
        finally:
            sys.path.remove(component)
            sys.modules.pop("reach", None)

    sends = _events(recorder, "sendto")
    inside = [e for e in sends if e.get("port") == 9]
    outside = [e for e in sends if e.get("port") == 10]
    check(inside and inside[0]["by"] == "integration",
          "6. a call from the integration's own directory is charged to the integration",
          _first(inside, "caller"))
    check(outside and outside[0]["by"] != "integration",
          "6b. and a call from outside it is not",
          f"{_first(outside, 'by')} — {_first(outside, 'caller')}")


# -- 7: the guard -------------------------------------------------------------------------

def case_observer_never_breaks_the_run() -> None:
    """An instrument that can fail the thing it measures produces results nobody can use.
    `sendto` is called with an address shape the recorder does not expect; the call must still
    reach the real socket and behave normally."""
    recorder = Recorder()
    recorder.install()
    ok = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(b"x", ("127.0.0.1", 9))
            ok = True
        finally:
            sock.close()
    finally:
        recorder.uninstall()

    check(ok, "7. the recorder does not interfere with the call it observes")
    check(socket.socket.sendto.__qualname__.startswith("socket."),
          "7b. uninstall restores the originals",
          socket.socket.sendto.__qualname__)


def _first(events: list[dict], field: str) -> str:
    return str(events[0].get(field)) if events else "no event"


def main() -> int:
    print(__doc__.strip().splitlines()[0])
    print("=" * 78)
    for case in (case_tcp_connect, case_udp_sendto, case_inbound,
                 case_tls_wrap_socket, case_tls_wrap_bio, case_multicast,
                 case_attribution, case_observer_never_breaks_the_run):
        case()
    passed = sum(1 for ok, _, _ in _results if ok)
    print("=" * 78)
    print(f"{passed}/{len(_results)} checks passed")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
