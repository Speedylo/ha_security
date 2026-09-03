# Can the four broadcast integrations work without it?

**Read 2026-09-03**, from source in `~/r2exp/corpus`. Follows `udp_demand.md`, which found 15 of
75 integrations need UDP and that 4 of those reach for broadcast or multicast.

The question this answers is the one that decides whether refusing broadcast costs four
integrations or nearly none: **is the broadcast a convenience over a manual address, or is it the
only way in because devices are dynamic?**

## Per integration

| Integration | What the broadcast does | Non-broadcast path | Verdict |
|---|---|---|---|
| `solarman` | `("<broadcast>", 48899)` in `scanner.py`, sends `WIFIKIT-214028-READ` | `CONF_INVERTER_HOST` is **required** in the config flow; `sensor.py:33` only calls the scanner when the host is left as the sentinel `"0.0.0.0"` | **Works fully.** No broadcast is sent at all when an address is given |
| `xiaomi_home` | `ping(target_ip='255.255.255.255')` in `miot/miot_lan.py:1359` for LAN control | LAN control is opt-in — `update_lan_ctrl_config` in the options flow, default `False`. Devices otherwise come from the cloud account | **Works fully** in its default configuration |
| `sonoff` | `BROADCAST = ("255.255.255.255", 32108)` in `core/ewelink/camera.py` | Config flow is a cloud login (username/password/country); `CONF_MODE` defaults to `"auto"`. Broadcast is confined to the camera feature | **Core works.** The camera feature loses discovery |
| `govee` | multicast scan to `239.255.255.250:4001`, replies on `:4002` | `CONF_LAN_TARGETS` — accepts addresses, hostnames and CIDR subnets, unicast-swept | **Partly** — see the gap below |

Note `sonoff` also illustrates a scanner limitation worth carrying: it sets `SO_BROADCAST` on a
socket whose every `sendto` goes to `device.addr`, a specific device. **Setting the option is not
the same as using it**, so the static scan's broadcast count is an upper bound in the same way its
UDP count is.

## The argument this produces, which is stronger than "the user can type an address"

`govee`'s own comment above `CONF_LAN_TARGETS`:

> Extra LAN discovery targets for devices the local multicast scan can't reach — e.g. Govee
> devices on a different VLAN/subnet than Home Assistant (issue #57). […] addresses, and CIDR
> subnets (≤ /24, unicast-swept since inter-VLAN firewalls […])

**The fallback exists because real home networks already impose this constraint.** VLANs, subnet
boundaries and firewalls block broadcast routinely, and integration authors have had to handle it
already. A sandbox that refuses broadcast is not imposing a novel restriction on the ecosystem; it
is imposing a familiar one, for which fallbacks are already written and already documented.

## The gap, stated rather than rounded away

`api/lan.py` records that some Govee firmware sends its scan **response** as multicast to the
group, so the receiving socket must join `239.255.255.250` via `IP_ADD_MEMBERSHIP` or the reply is
never seen. That is a *receive*-side multicast requirement and unicast sending does not satisfy it.

Under a unicast-only design, `govee`'s LAN mode works with firmware that answers unicast and
silently does not with firmware that answers multicast. One integration of 75, in an optional
local mode, with a working cloud path — but a real loss, and Chapter 8 owes it a sentence rather
than a rounding.

## What this shares with the `allow_private` question

The two are the same problem seen from opposite ends. **A device's address is not knowable when
the manifest is written** — it comes from the user's DHCP lease, years later. Discovery is the
ecosystem's answer to that; a manifest written at authoring time cannot be.

§5.10.4 already reasons this way about entities: patterns are permitted there *because* "an
integration usually cannot know the entity IDs it will need at authoring time — they depend on the
user's devices — whereas it always knows which services it calls." A device IP falls on the
unknowable side of exactly that line.

So both questions resolve the same way: **the address is supplied by the user at configuration
time and pinned by the mediator**, rather than declared by an author who cannot know it.
Broadcast discovery is the alternative to asking the user — and it is the alternative a sandbox
cannot safely offer, because "send to every device on the home network" is T10 in its literal
wording.
