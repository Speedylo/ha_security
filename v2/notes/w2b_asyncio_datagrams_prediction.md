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
