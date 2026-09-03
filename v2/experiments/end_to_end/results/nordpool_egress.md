# `nordpool` confined against the real Nord Pool API — §7.27

**Run 2026-09-03** on the C4 device (Raspberry Pi 5, HA 2026.8.3, Python 3.14.7), real internet.
`python3 -m confine.endtoend_egress --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python`.

`pi5_nordpool_egress.json` is the machine record. **11 of 11 checks passed.**

## The three arms

| | A — unconfined | B — confined, declared | C — confined, no clause |
|---|---|---|---|
| Config entry | LOADED | **LOADED** | LOADED |
| `sensor.nordpool_kwh_se1_eur_3_10_025` | **0.026** | **0.026** | `unavailable` |
| `network.egress` decisions | — | **3 granted** | **3 denied** |
| Logged destination | — | `dataportal-api.nordpoolgroup.com:443` | `dataportal-api.nordpoolgroup.com:443` |
| Clause | — | `/permissions/network/egress/0` | `/permissions/network/egress` |
| Connections completed | — | 3 | 0 |
| `oom_kill` | — | 0 | 0 |

Arm A publishes ten entities; **one of them is `nordpool`'s**. The other nine — `sun.*`,
`zone.home`, `conversation.home_assistant` — belong to `default_config`, which the generous
baseline of §7.12.1 sets up and the sandbox does not. It is a profile difference, not nine lost
entities.

Arm C's name still **resolves** inside the sandbox, to the placeholder only the mediator can map
(§7.24.2); what is refused is the connection. A denial record showing a successful resolution is
the design working, not a leak.

## What the first run found

Arms B and C failed with an empty egress audit — the integration never asked the mediator for
anything:

    homeassistant.setup: Error during setup of component nordpool: [Errno 19] No such device
      File "zeroconf/_utils/net.py", line 350, in add_multicast_member
        listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, _value)

`nordpool` neither declares nor imports `zeroconf`. It calls what the platform documents:

    async_get_clientsession(hass)
      -> aiohttp_client._async_make_resolver(hass)
      -> HassAsyncDNSResolver(async_zeroconf=zeroconf.async_get_async_zeroconf(hass))

**Every Home Assistant client session joins the mDNS group when it is built**, and a fresh network
namespace's `lo` carries no `IFF_MULTICAST`. So a real integration could not construct an HTTP
client inside the sandbox at all — before any name was resolved or any connection attempted.
§7.25's subject used a bare `aiohttp.ClientSession()` and skipped the helper that breaks the
design, which is why every earlier egress result was measured around the defect.

## The correction, in two steps

Measured, not reasoned:

    lo flags 0x1049 (UP | LOOPBACK | RUNNING | MULTICAST)
        join via 127.0.0.1 : OK
        join via 0.0.0.0   : [Errno 19] No such device     <- IFF_MULTICAST alone
        join via 0.0.0.0   : OK                            <- after routing 224.0.0.0/4 to lo

`zeroconf` joins through `INADDR_ANY`, and the kernel picks the interface for an unbound join from
the routing table — which is empty for the multicast range in a fresh namespace.
`namespaces.route_multicast_to_loopback()` adds it with `SIOCADDRT`.

**The grant is vacuous.** The route's device is `lo`, so every multicast datagram the sandbox sends
is delivered to the sandbox, and no second interface can be added without `CAP_NET_ADMIN` over a
namespace it does not own. The cost: an integration that genuinely needs mDNS finds nothing here.

## Also fixed

`audit.py`'s `decision()` extracted `request.get("host")` alone, so after §7.25 added ports to the
clause the durable record could not distinguish `:443` from `:6445` on the same host. Now
`host:port`. Invisible to every prior test, because none logged an egress decision to a real log.

## Harness faults, recorded per §6.3.3

- The audit log was created inside the directory the harness removes, so `records()` read an empty
  directory and reported no decisions — which presents as "the mediator logged nothing".
- The first version read `request` out of `mediator.audit`, which carries `op`/`allowed`/`clause`
  at the top level and not the request; every destination read as `None`. Destination evidence now
  comes from the durable log.

**All 18 self-test suites re-run after both changes: 18/18.**
