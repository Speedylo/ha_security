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

---

## 5. Outcomes, 2026-10-04 (appended; §4 is unchanged)

Evidence: `experiments/local_tcp/results/w2a_20261004/`. A correction to §2: `midea_ac_lan`'s
version is 2026.8.0, not 0.6.x.

**The baseline, on the code before the build.** Arm A worked against the fake device. Arm B
**hung in discovery** and never reached TCP: 1,471 `udp.recv` polls over 25 minutes before it was
stopped. Arm C hung too, and worse: **463,631 refused decisions, a 289 MB audit log, in 7.5
minutes**. Arm A's report was lost when the run was stopped during C.

**What the baseline found, besides the gap the build closes:** four defects in the sandbox side of
the UDP relay, and two in the harnesses.
1. `recvfrom` asked only the last peer sent to, so discovery replies from port 6445 sat unread.
2. A socket's timeout was not honoured. `BlockingIOError` was raised where a real socket raises
   `TimeoutError`, and `midea-lan` looped on it for ever.
3. A refused `sendto` still registered its peer, so every later `recvfrom` asked for it, was refused
   again, and the integration's retry loop made about 1,000 refused decisions a second. That was arm
   C's flood.
4. Per-socket state was keyed by descriptor number, so a new socket that reused a closed one's
   number inherited its peers. This was found by the regression test written for item 3.
5. `Mediator.serve` had no deadline, so a sandbox that never stops asking held a harness for ever.
6. Both runners printed their result only after Home Assistant had shut down, which an integration
   retrying a silent device can delay past any harness limit.

All six are fixed, each with a test that fails without the fix where that can be shown.

| | Outcome |
|---|---|
| **L1** | **Held in substance, not in its detail.** Arm B failed before the build, but in discovery (items 1–2), not at the TCP connect as predicted. It never got far enough to meet the TCP gap |
| **L2** | **Held.** After the build, arm B's flow completes and the entry loads, publishing `climate.151732605161920_climate`. The device saw 6 connections and 4,440 bytes of the integration's own query frames, all from the host's address |
| **L3** | **Held only after the fixes.** The relay itself worked in real namespaces from the first run (the device received both discovery datagrams), but the sandbox side did not behave like a socket (items 1–4). After the fixes, discovery took 2 sends and 8 bounded polls |
| **L4** | **Held.** Arm C: 9 refused sends, each with its clause `/permissions/network/local/udp`; the integration's own flow reported `invalid_device_ip`; the device saw nothing |
| **L5** | **Held.** `selftest_local_tcp`: loopback, link-local and public addresses refused by the mediator even with the port declared (12/12) |
| **L6** | **Held.** The durable record names the address and the port (`selftest_local_tcp`) |
| **L7** | **Held.** Arm A loads and publishes the same climate entity, recovered from a shutdown that ran past the limit |
| **L8** | **Held, six times** (above). Item 3's flood also exposed a design question that remains open: every refusal is a durable record, so a hostile sandbox can issue refused requests in a loop and exhaust the mediator's decision budget and the disk |

**Not done:** stage B. The fake device never answers the integration's queries, so device-to-
integration bytes over a passed descriptor are covered only by the descriptor being a real
connected socket, which `selftest_local_tcp` exercises in one direction. The asyncio datagram
shape (§7.25.5's four integrations) is still not served.
