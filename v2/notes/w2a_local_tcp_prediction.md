# W2 (a) — local TCP to home-network devices, and a real raw-socket integration: prediction

**Written 2026-10-04, before any framework code.** §4 is never revised; outcomes are appended below it.
Decided by Younes 2026-10-04: build local TCP, then confine a real integration against a fake device.

## 1. What reading found

W2 (a) was meant to confine one integration that uses a plain socket, the one network stack never
spawned confined (§7.24.5, §8.7 #7). Reading the code to plan it found a larger gap.
**`network.tcp.local` exists only in the manifest schema.** `decision_network_capability.md` §3.2 and
§4 design it: ports declared, never addresses, and an address pinned on its first successful
connection to a declared port (the binding rule's manual-entry case). The code stops short in three
places:

- the egress shim substitutes a mediator-connected socket only for **placeholder** addresses it
  handed out for hostnames. A device's IP address, which a user types in, falls through to the real
  `connect`, and the sandbox's network namespace has no route to it;
- `ActingPolicy` has no step 5 for `network.tcp.local`;
- nothing sends the request at all.

So every integration that reaches a home-network device over TCP fails closed when confined,
whatever it declares. §7.18.1 and §8.2.2 describe the LAN-facing 41% of the corpus as served
"only with §5.10.3's separate flag", which reads as available behind a declaration. For TCP it is
not. Safe, but unusable, and not what the report says.

## 2. Design

- **Sandbox:** the shim sends `network.tcp.local` {address, port} when the integration connects to
  an IP literal on the home network, and adopts the connected descriptor the mediator hands back, as
  the egress path already does. Loopback stays inside the sandbox's own namespace and is never
  relayed.
- **Mediator:** the manifest decides on the **port** (`network/local/tcp`). Step 5 is the broker
  connecting to the address, but only for a LAN address: private, and not loopback, link-local,
  multicast, unspecified or reserved. That check lives in the mediator, which is the authority; the
  shim's own test only decides routing. A successful connection pins the address, and the durable
  record names the address as well as the port.
- **What this does not limit**, as `decision_network_capability.md` §4.1 already concedes: an
  integration declaring port 80 can reach any LAN host that answers on 80. The bound is "declared
  ports, one recorded address at a time", not "the device the user meant".

**The test integration** is `midea_ac_lan` 0.6.x with `midea-lan` 2026.8.0, unmodified: the
corpus's raw-socket member (§7.24.5). Its manual setup step discovers the device by **synchronous
UDP** on 6445 and 20086, then connects by **blocking TCP** on 6444. So it exercises local TCP, the
raw-socket stack, and the UDP relay in real namespaces (half of W2 (b)). **The device is fake.** A
program on the Pi's LAN address (10.126.83.113) answers discovery as a protocol-V2 air conditioner
and accepts the TCP connection. It uses `midea-lan`'s own encryption to build its discovery reply,
so it shares that code with the integration. That is acceptable, because the protocol is not what
is under test. A V2 device needs no token, so no cloud account is involved.

**Stage B (stretch):** the fake device answers the integration's status query with a valid
message, so a real entity state reaches the house.

## 3. Arms

| Arm | |
|---|---|
| **A** unconfined | the control: the fake device is good enough for the real integration |
| **B** confined, `network.local` declared (`tcp: [6444]`, `udp: [6445, 20086]`) | the measurement |
| **C** confined, nothing declared | denied with a clause, nothing reaches the device |

## 4. Predictions

| | Prediction | Confidence |
|---|---|---|
| **L1** | **Before the build**, arm B fails: discovery may get through the relay, but the TCP connect to 10.126.83.113:6444 cannot, and the flow ends in its own "Device auth failed" error. The fake device sees no TCP connection | high |
| **L2** | After the build, arm B's flow completes and the entry loads. The fake device sees a TCP connection, from the host's side and not from a sandbox address, and the integration's own query frames on it | medium |
| **L3** | Synchronous UDP discovery through the relay works in real namespaces: the first time the relay is exercised outside its decision-layer test | medium — never spawned |
| **L4** | Arm C is refused with clauses under `/permissions/network/local/…`, and the fake device sees nothing at all | high |
| **L5** | The mediator refuses `network.tcp.local` to loopback, link-local and public addresses even when the port is declared (decision-layer test) | high |
| **L6** | Each connection is a durable decision naming both address and port | high |
| **L7** | Arm A completes against the fake device | medium-high |
| **L8** | Something not listed is found | high |
