# W2 (b) — asyncio datagram endpoints in the sandbox: design and prediction

**Written 2026-10-04, before any code.** §4 is never revised; outcomes are appended below it.

## 1. The problem

Four of the corpus's fifteen UDP integrations (`govee`, `localtuya`, `tapo_control`, `xiaomi_miot`)
use `loop.create_datagram_endpoint`. asyncio then waits for the socket's **descriptor to become
readable** (`add_reader`). Under this design there is nothing to read: the sandbox has no route,
and the mediator holds every real UDP socket. The synchronous emulation that §7.40 made work
answers `recvfrom` calls, but an asyncio transport never calls `recvfrom` until its descriptor is
readable, so it waits for ever. `selftest_udp` case 7b names this as unserved (§7.25.5).

## 2. Design

**A descriptor that becomes readable.** The shim backs every relayed datagram socket with one end of
an `AF_UNIX`/`SOCK_DGRAM` socket pair (`dup2` onto the integration's own descriptor, as the egress
path does for TCP). A delivered datagram is written into the other end, framed with its sender's
address. The integration's event loop sees its descriptor become readable, calls `recvfrom`, and the
shim reads the frame and returns `(data, sender)`. The synchronous path goes through the same pair,
so there is one mechanism, not two.

**Delivered by the mediator, not polled from the sandbox.** A listen is decided and recorded once
(`discover.listen` on a declared port). The mediator binds the real port, watches it in its own
selector loop, and pushes each datagram down the channel (`"push": "datagram"`) without a record
per datagram. That is decision A of W1 step 1, applied to datagrams. The alternative, a thread in the
sandbox polling over the channel, is rejected because every poll is a durable decision: one or two a
second per listening socket, for ever, which is the flood of §8.6.3 #14. Queued datagrams per
channel are bounded, and the oldest is dropped past the bound, as a real socket's receive buffer
would drop.

**Scope.** Listening (`localtuya`'s discovery, and the listen half of `govee`) is built and measured.
Replies to datagrams an asyncio endpoint sent (the unicast half of `govee` and `xiaomi_miot`) use the
same push, from the relay's per-peer sockets, but are tested only at the decision layer: no corpus
member that needs it can run without a real device or account.

**The test.** `localtuya`, unmodified, set up with `no_cloud`. Its component setup starts
`TuyaDiscovery` on 6666 (plaintext) and 6667 (encrypted with a key published in its own source). A
fake Tuya device broadcasts both kinds to the Pi's LAN address, once a second. The evidence is
`localtuya`'s own `hass.data["localtuya"]["discovery"].devices`, reported by the sandbox.

| Arm | |
|---|---|
| A unconfined | the control: the fake broadcasts are good enough |
| B confined, `discover.listen: [6666, 6667]` | the measurement |
| C confined, nothing declared | refused; nothing discovered |

## 3. Predictions

| | Prediction | Confidence |
|---|---|---|
| **D1** | **Before the build**, arm B discovers nothing. The endpoint is created without error, because the shim records the `bind`, and its descriptor never becomes readable | high |
| **D2** | After the build, arm B discovers the fake device's `gwId` from both ports, as arm A does | medium — the frame format and `reuse_port` are the risks |
| **D3** | Each listen is **one** durable decision. Datagrams delivered afterwards add no records, however many arrive | high |
| **D4** | The sender address the integration sees is the device's real address, not the mediator's | medium |
| **D5** | Arm C: the listen is refused with `/permissions/network/discover/listen`, nothing is discovered, and there is no refusal flood | high |
| **D6** | §7.40's synchronous path (`midea_ac_lan` arm B) still loads, through the same pair | medium |
| **D7** | A sandbox that never reads its datagrams costs the mediator a bounded queue | high |
| **D8** | Something not listed is found | high |

---

## 4. Outcomes, 2026-10-04 (appended; §3 is unchanged)

Evidence: `experiments/local_tcp/results/w2b_20261004/` (`prebuild.*` is the baseline, `build_*` the
built code, for both subjects).

| | Outcome |
|---|---|
| **D1** | **Held exactly.** Before the build, confined `localtuya` with the listen declared loaded and discovered **nothing**, with no error anywhere, so it could not be told apart from the arm with nothing declared. Unconfined, it discovered both fake devices |
| **D2** | **Held.** After the build, confined `localtuya` discovers `fakeplain000006666` and `fakecrypt000006667`, the same as unconfined, through its own unmodified `asyncio.DatagramProtocol` |
| **D3** | **Held.** **Two** durable decisions, one listen per port, for every broadcast the fake device sent in the run (one a second on each port) |
| **D4** | **Held at the decision layer only.** `selftest_udp` 7b: the asyncio endpoint sees the device's real address and port. `localtuya` reads the address from the payload, so the end-to-end run does not test this |
| **D5** | **Held.** With nothing declared, both listens are refused and recorded once each, the bind fails where a real bind would, `localtuya` logs that discovery failed to start, and there is no flood |
| **D6** | **Held, and improved.** `midea_ac_lan`, synchronous, still loads confined through the same pair, and its 8 per-poll `udp.recv` decisions are gone: replies are pushed, with no record per datagram |
| **D7** | **Held.** Flooded with 20,000 datagrams it never reads, a stalled sandbox costs the mediator 64 queued, oldest dropped first (8,609 dropped), and its relay socket is closed when its channel goes (`selftest_push`) |
| **D8** | **Held once, and the finding is in the test suite.** `selftest_udp`'s case 7b, "the asyncio DatagramProtocol shape is not served", was `check(True, …)`: a stated limitation counted as a passing check, testing nothing. It is now a real test of the shape being served |

**Two more found after the first build ran, both fixed, both by checking a claim rather than
running a measurement.**
- The first draft of this section said "no asyncio endpoint in the corpus" registers a socket before
  binding it. **That was false.** `govee` binds its send socket to port 0 and hands it to
  `create_datagram_endpoint(sock=...)`, and the build attached the pair only for a real port, so
  that socket would have got its pair at its first `sendto`, after `epoll` was already watching the
  old file description. Its replies would never have woken the loop. A bind to port 0 now attaches
  the pair too. `selftest_udp` 7d tests `govee`'s shape, and fails with the line removed.
- On the Pi, `selftest_udp` case 8 lost the first device's reply, which never happened on the laptop.
  The shim added a peer's route only after the send returned, and on the Pi's loopback the reply
  could be pushed and delivered in that gap with nowhere to go. The same gap exists in a real
  sandbox, where the event loop's thread delivers while the sending thread is still returning. The
  route is now added before sending and removed if the send is refused. Five runs on the Pi, 17/17.

**Not served:** an asyncio socket that its event loop registered before its first `bind` or
`connect`. All four asyncio integrations in the corpus bind or connect first, `govee`'s send socket by
binding port 0. The unicast half (`govee`'s and `xiaomi_miot`'s replies) uses the same push and is
tested at the decision layer only (`selftest_udp` 7d).
