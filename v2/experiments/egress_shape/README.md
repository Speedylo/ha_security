# Experiment — what a mediator must actually do to serve egress

**Run:** 2026-09-03 · **Pi 5, HA 2026.8.3, Python 3.14.7** · **Feeds:** §7.24 ·
**Informs:** §5.10.3, and the artifact about to be built for §5.8.2 scope item 2

## Why this runs before the proxy and not after it

§9.5's decision is taken: build mediated egress. §7.18 informed *whether* — 81% of the corpus
declares a network reach, 41% cloud and 41% local. It did not inform *what*, and the design in
§5.10.3 carries three assumptions that no measurement has touched:

| # | Assumption in §5.10.3 | If wrong, what changes |
|---|---|---|
| 1 | Egress is **hostnames**; the clause has no port field | the manifest schema — a Chapter 5 correction |
| 2 | A name becomes an address through `socket.getaddrinfo`, which is where a mediator interposes for T11's resolve-then-pin | where the enforcement point *is* |
| 3 | Egress means **outbound TCP**; the clause cannot express UDP, multicast or an inbound listener | what the artifact has to serve, and what it must instead refuse and say so |

Each is cheaper to test than to unbuild. §6 corrected §5 four times by running a measurement
rather than re-reading the argument; this is the same move, made before the code exists instead
of after.

## The wall §7.18 hit, and why it is in the wrong place for this question

§7.18 closed with a strong claim: *no observational method can answer this*, because egress
demand appears at setup, and setup needs a credential for 26 of 37 (§7.17.1).

That holds for **how much** and does not bind **what shape**, because a config flow validates a
credential *by making the call*. A wrong API key still produces the name resolution, the TCP
connection, the TLS handshake and the request; only the last step is refused. Every mechanism a
mediator would have to implement has already run by the time the 401 comes back.

So the credential wall bounds one question and not the other, and this experiment answers only
the one it can reach: **the repertoire** — which protocols, which ports, which resolution paths,
whether anything listens.

## Method

Each integration is set up in a **full unconfined Home Assistant with real network access** —
the same arm as §7.17.5's baseline, same corpus, same release, same interpreter — and driven
through its own config flow by the **same `drive_flow`** the confined arm uses, imported rather
than reimplemented.

Two instruments run together, and the pairing is the point:

- **`framework/confine/netshape.py`** — in-process. Records resolutions (`getaddrinfo` *and*
  `aiodns`), connects, datagrams, TLS wraps, binds, listens and multicast joins, each tagged
  with the phase it occurred in and the calling frame. Sees little, attributes it precisely.
- **`strace -f -e trace=network`** — the kernel. Attributes nothing, misses nothing.

Where they disagree, the kernel is right, and the gap is the in-process recorder's blind spot
reported as a number rather than as a caveat.

**The instrument is tested before it is trusted.** `selftest_netshape.py` — 13 checks, passing
on both architectures. §7.18's own history is the argument for that: the first version of its
recorder reported 23 of 37 integrations attempting egress, and the figure was an artifact of
*attribution*, not of observation. Case 6 of the self-test is that mistake turned into a test.

### Credentials

Invalid by construction and non-secret by construction — no account exists behind any of them.
`host` fields are answered with `127.0.0.1`, which refuses instantly rather than hanging, so a
local-protocol integration reveals the port and transport it wanted without the run waiting out
a timeout. It also exercises exactly the non-public destination T10 is about.

### Selection

Twelve of the 37-integration head corpus, chosen to span the **mechanisms** a proxy would have
to serve rather than to be representative by count — §7.4.1's rule that a named set with its
selection stated beats a rate that will not scale. Six cloud-facing (the half §5.8.2's scope
item 2 serves directly) and six local-facing (the half served only behind §5.10.3's non-public
flag). The reason each is in the sample is recorded in `egress_shape.SAMPLE` and travels with
the results file.

## Separating the integration from the platform

`default_config` pulls in a discovery stack — `zeroconf`, `async_upnp_client`, `aiodiscover`,
`dbus_fast`, `homeassistant.components.network` — that generates far more network activity than
any integration does, and keeps generating it during the integration's phase. Counting it as
demand would conclude that every integration needs multicast, broadcast and an ARP sweep.

`analyse.py` applies two filters and states both: the event is in the integration's **phase**,
and its **calling frame** is not in that discovery stack. Neither is sufficient alone — phase
alone keeps zeroconf's ongoing traffic; caller alone drops an integration legitimately using a
library the platform also uses. Events that pass one filter and not the other are reported in
their own section rather than dropped, because that boundary is where a wrong answer would live.

## Limits, stated where the figures are used

- **It measures repertoire, not volume.** Polling frequency, sustained connection counts and how
  many integrations would use egress in service are all out of reach for the reason §7.18 gives,
  and nothing here claims them.
- **Stack-walk attribution is weak under asyncio.** A connection made from a coroutine scheduled
  on the event loop has no frame from the integration on its stack — the work happens inside
  `aiohttp`, `aiohappyeyeballs` or a vendor library. The `caller` field therefore identifies
  *which library performs the network operation*, which is what a proxy has to support, and is
  the reliable signal; the integration/library/platform trichotomy is not, and the phase filter
  is what carries attribution instead. **In the framework proper this problem does not arise** —
  identity comes from the socket the request arrived on (§5.11.2), never from a stack.
- **The C blind spot is why `strace` runs.** `pycares` under `aiodns` owns its sockets in C, so
  `aiodns` is instrumented at its own Python API instead. Anything else in C is invisible to the
  in-process recorder, which is what the kernel arm is for.
- **One host, one moment.** DNS results, CDN addresses and API availability all vary; the
  destinations are evidence of shape, not a fixed list.

## Reproducing

```bash
python3 -m confine.egress_shape --corpus ~/r2exp/corpus \
    --python ~/r2exp/ha314/bin/python --uv ~/.local/bin/uv \
    --platform-deps ~/r2exp/platform-deps \
    --settle 20 --strace --full-events \
    --json results/pi5_egress_shape.json

python3 analyse.py results/pi5_egress_shape.json
```

## Re-run 2026-10-03 — §7.31.11, `results/rerun_20261003/`

Same command on the corrected instance. `dwd_weather` now reaches `opendata.dwd.de:443`, so seven of
twelve reach the network. **The 96% `aiodns` share in §1 of `results/analysis.md` is not a property
of the integrations**: 3,048 of its 3,073 `aiodns` resolutions were reverse lookups of
`192.168.11.0/24` by `aiodiscover` (the platform's `dhcp` discovery), attributed to the integration
phase. The Pi is now on a `/16`, which `aiodiscover` does not sweep (`MAX_ADDRESSES = 2048`), and
the re-run's share is 17%; the original run with the sweep excluded is also 17%. Predictions:
`notes/ch7_31_egress_shape_rerun_prediction.md`.
