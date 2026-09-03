"""Turn the recorded runs into the tables §7.24 reports, and keep the platform out of them.

§7.18.2's correction is the standing hazard here and it is worth restating, because this
measurement is more exposed to it than that one was: the platform's own discovery stack —
`zeroconf`, `async_upnp_client`, `aiodiscover`, `dbus_fast`, and `homeassistant.components.
network` — generates far more network activity than any integration does, it keeps generating
it during the integration's phase, and it is pulled in by `default_config` rather than by
anything the integration asked for. Counting it as demand would say every integration needs
multicast, broadcast and an ARP sweep.

Two filters are applied and both are stated rather than assumed:

  1. **phase** — the event happened after the integration's flow began; and
  2. **caller** — the frame that made the call is not in the platform's discovery stack.

Neither is sufficient alone. Phase alone keeps zeroconf's ongoing mDNS traffic; caller alone
drops an integration that legitimately uses a shared library the platform also uses. Rows that
pass one filter but not the other are reported separately rather than silently dropped, because
that boundary is where a wrong answer would live.

Usage: python3 analyse.py results/pi5_egress_shape.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

# Libraries that are the platform's discovery machinery, not an integration's choice. Each is
# here because `default_config` pulls it in: an integration that declares nothing still gets
# all of them, so their traffic cannot be evidence about the integration.
PLATFORM_CALLERS = ("zeroconf/", "async_upnp_client/", "aiodiscover/", "dbus_fast/",
                    "homeassistant/components/network/", "homeassistant/components/zeroconf/",
                    "homeassistant/components/ssdp/", "homeassistant/components/dhcp/",
                    "homeassistant/components/bluetooth/", "hass_nabucasa/")

# Destinations that are discovery by their nature. Belt and braces with PLATFORM_CALLERS: a
# vendored copy of a discovery library would not match a caller prefix but still goes here.
DISCOVERY_HOSTS = ("224.0.0.251", "ff02::fb", "239.255.255.250", "FF02::C", "ff02::c",
                   "255.255.255.255", "224.0.0.252")

# Home Assistant's own back-end services, which it contacts on its own account during the
# integration's phase. **These can only be excluded by destination.** The first pass caught them
# by neither filter and credited `alerts.home-assistant.io` to three integrations, because the
# fetch is made from `aiohttp/connector.py` — the identical frame a genuine integration request
# comes from. That is the asyncio attribution limit stated in the README arriving in the data:
# under an event loop the calling frame identifies the *library*, never the requester.
#
# It is also the clearest argument for why the framework does not attribute this way. In the
# artifact, identity is the socket the request arrived on (§5.11.2) — a property established
# before the request exists, which no amount of shared library code can blur.
PLATFORM_HOSTS = ("alerts.home-assistant.io", "version.home-assistant.io",
                  "analytics.home-assistant.io", "checkonline.home-assistant.io")


def is_platform(event: dict) -> bool:
    caller = event.get("caller") or ""
    if any(part in caller for part in PLATFORM_CALLERS):
        return True
    host = str(event.get("host") or "")
    name = str(event.get("server_hostname") or "")
    if host in DISCOVERY_HOSTS or host.endswith(".255"):
        return True
    return name in PLATFORM_HOSTS or host in PLATFORM_HOSTS


def platform_connect_seqs(events: list[dict]) -> set[int]:
    """Connects that are the platform's own, identifiable only by what was wrapped over them.

    A connect carries an **address**; the name is long gone by then (see §7.24 — the resolution
    and the connection happen in different libraries). So the platform's alert fetch is a
    connect to a Cloudflare address, indistinguishable by IP from any integration's. What does
    identify it is the TLS wrap that follows, which still carries `server_hostname`.

    Each TLS event naming a platform host is therefore walked back to the nearest preceding
    connect, and that connect is charged to the platform. The heuristic is stated because it is
    a heuristic: it assumes a wrap follows its own connect with no other connect in between,
    which holds for a sequential handshake and would not hold under a burst of concurrent
    connections to the same host. In this sample it moves exactly one row — `frigate`'s.

    **A connect the integration's own code made is never reassigned.** The first version of this
    walk-back had no such guard and removed `alexa_media`'s connection to the gateway's own
    Home Assistant — a genuine finding, attributed directly to `alexa_media/config_flow.py:329`
    — because the platform's alert wrap happened to be the next TLS event in the stream. A
    heuristic that can overturn direct evidence is not a filter, it is a bug, so the walk-back
    applies only to connects whose caller is a generic library frame and which therefore had no
    attribution of their own to lose.
    """
    seqs: set[int] = set()
    last_connect: dict | None = None
    for event in events:
        if event.get("kind") == "connect":
            last_connect = event
        elif event.get("kind") == "tls" and last_connect is not None:
            if (str(event.get("server_hostname") or "") in PLATFORM_HOSTS
                    and last_connect.get("by") != "integration"):
                seqs.add(last_connect.get("seq"))
    return seqs


def classify(report: dict) -> dict:
    events = report.get("events") or []
    inherited = platform_connect_seqs(events)
    integration, platform, ambiguous = [], [], []
    for event in events:
        if event.get("seq") in inherited:
            platform.append(event)
            continue
        in_phase = event.get("phase") == "integration"
        platform_caller = is_platform(event)
        if in_phase and not platform_caller:
            integration.append(event)
        elif platform_caller:
            platform.append(event)
        else:
            ambiguous.append(event)          # earlier phase, non-platform caller
    return {"integration": integration, "platform": platform, "ambiguous": ambiguous}


def tally(events: list[dict], field: str) -> dict:
    return dict(Counter(e.get(field) for e in events if e.get(field)).most_common())


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "results/pi5_egress_shape.json")
    data = json.loads(path.read_text())
    reports = [r for r in data["reports"] if r.get("netshape")]

    print(f"# Egress shape — {len(reports)} of {len(data['reports'])} integrations ran\n")

    # -- 1. Where the name becomes an address ------------------------------------------
    print("## 1. Resolution path — where a mediator would have to interpose\n")
    print("| Integration | getaddrinfo | aiodns | aiodns share |")
    print("|---|---|---|---|")
    totals = Counter()
    for report in reports:
        resolution = report["netshape"].get("resolution") or {}
        gai = sum(v for k, v in resolution.items() if k == "getaddrinfo")
        dns = sum(v for k, v in resolution.items() if k.startswith("aiodns"))
        totals["gai"] += gai
        totals["aiodns"] += dns
        share = f"{dns / (gai + dns) * 100:.0f}%" if (gai + dns) else "—"
        print(f"| `{report['domain']}` | {gai} | {dns} | {share} |")
    both = totals["gai"] + totals["aiodns"]
    print(f"| **all** | **{totals['gai']}** | **{totals['aiodns']}** | "
          f"**{totals['aiodns'] / both * 100:.0f}%** |" if both else "")

    # -- 2. Transport, with the platform removed ---------------------------------------
    print("\n## 2. Transport the integration itself used\n")
    print("| Integration | STREAM | DGRAM | RAW | ports reached |")
    print("|---|---|---|---|---|")
    all_ports: Counter = Counter()
    for report in reports:
        groups = classify(report)
        outbound = [e for e in groups["integration"]
                    if e["kind"] in ("connect", "sendto")]
        types = Counter(e.get("socktype") for e in outbound)
        ports = sorted({e.get("port") for e in outbound
                        if isinstance(e.get("port"), int) and e.get("port") > 1})
        all_ports.update(ports)
        print(f"| `{report['domain']}` | {types.get('SOCK_STREAM', 0)} | "
              f"{types.get('SOCK_DGRAM', 0)} | {types.get('SOCK_RAW', 0)} | "
              f"{', '.join(str(p) for p in ports) or '—'} |")
    print(f"\n**Ports across the sample:** "
          f"{', '.join(f'{p} ({n})' for p, n in all_ports.most_common())}")
    non_web = [p for p in all_ports if p not in (80, 443)]
    print(f"**Non-web ports:** {non_web or 'none'} — decides whether §5.10.3's "
          f"hostname-only clause is sufficient")

    # -- 3. TLS -------------------------------------------------------------------------
    print("\n## 3. TLS — can a mediator see content?\n")
    print("| Integration | wrap_bio | wrap_socket | verified | server_hostname seen |")
    print("|---|---|---|---|---|")
    for report in reports:
        # Filtered like every other table. The raw summary counts the platform's own alert
        # fetch, which is not the integration reaching anywhere.
        tls = [e for e in classify(report)["integration"] if e["kind"] == "tls"]
        bio = sum(1 for e in tls if e.get("how") == "wrap_bio")
        sock = sum(1 for e in tls if e.get("how") == "wrap_socket")
        verified = sum(1 for e in tls if e.get("check_hostname"))
        names = sorted({e.get("server_hostname") for e in tls if e.get("server_hostname")})
        print(f"| `{report['domain']}` | {bio} | {sock} | {verified} | "
              f"{', '.join(names[:3]) or '—'} |")

    # -- 4. Inbound ---------------------------------------------------------------------
    print("\n## 4. Inbound — a capability §5.10.3 cannot express\n")
    print("A *listener* is a `listen`, or a bind to a fixed port on an IP socket. A bind to port")
    print("0, or to a high ephemeral port, is what every UDP client does before it sends and is")
    print("not inbound. `AF_NETLINK` binds are route queries and are not network at all — the")
    print("first version of this table counted 79 of `scapy`'s and read as though integrations")
    print("listen constantly.\n")
    print("| Integration | listeners | IP binds (ephemeral) | netlink binds |")
    print("|---|---|---|---|")
    any_listener = False
    for report in reports:
        groups = classify(report)
        binds = [e for e in groups["integration"] if e["kind"] in ("bind", "listen")]
        netlink = [e for e in binds if e.get("family") not in ("AF_INET", "AF_INET6")]
        ip_binds = [e for e in binds if e.get("family") in ("AF_INET", "AF_INET6")]
        listeners = [e for e in ip_binds
                     if e["kind"] == "listen"
                     or (isinstance(e.get("port"), int) and 0 < e["port"] < 32768)]
        any_listener = any_listener or bool(listeners)
        detail = ", ".join(f"{e.get('host')}:{e.get('port')}" for e in listeners[:3]) or "none"
        print(f"| `{report['domain']}` | {detail} | {len(ip_binds) - len(listeners)} | "
              f"{len(netlink)} |")
    print(f"\n**No integration in the sample established a listener.**" if not any_listener
          else "\n**At least one integration listened — see the table.**")

    # -- 5. The blind spot, bounded -----------------------------------------------------
    print("\n## 5. In-process recorder against the kernel\n")
    print("Egress only — `AF_INET`/`AF_INET6` connect and sendto. The kernel's `AF_NETLINK` and")
    print("`AF_UNIX` traffic is route, interface, dbus and log-socket work, which is not egress")
    print("and which the recorder never claimed to watch.\n")
    print("| Integration | recorder | kernel (inet) | ratio | kernel non-inet |")
    print("|---|---|---|---|---|")
    for report in reports:
        kinds = report["netshape"].get("by_kind") or {}
        mine = kinds.get("connect", 0) + kinds.get("sendto", 0)
        kernel = report.get("kernel") or {}
        inet = kernel.get("inet") or {}
        theirs = inet.get("connect", 0) + inet.get("sendto", 0)
        ratio = f"{mine / theirs * 100:.0f}%" if theirs else "—"
        other = sum((kernel.get("non_inet") or {}).values())
        print(f"| `{report['domain']}` | {mine} | {theirs or '—'} | {ratio} | {other or '—'} |")

    # -- 6. What the integrations actually reached --------------------------------------
    print("\n## 6. Destinations attributed to the integration\n")
    for report in reports:
        groups = classify(report)
        outbound = [e for e in groups["integration"] if e["kind"] in ("connect", "sendto")]
        seen: dict[str, dict] = {}
        for e in outbound:
            key = f"{e.get('host')}:{e.get('port')}"
            seen.setdefault(key, {"n": 0, "caller": e.get("caller"),
                                  "type": e.get("socktype")})["n"] += 1
        if not seen:
            print(f"- **{report['domain']}** — nothing outbound attributed to it "
                  f"(flow: {report.get('flow', {}).get('type')})")
            continue
        print(f"- **{report['domain']}** ({report.get('flow', {}).get('type')}):")
        for key, info in sorted(seen.items(), key=lambda kv: -kv[1]["n"])[:8]:
            print(f"  - `{key}` ×{info['n']} — {info['type']}, via `{info['caller']}`")

    # -- 7. Ambiguity, reported rather than hidden --------------------------------------
    print("\n## 7. Events the two filters disagreed on\n")
    for report in reports:
        groups = classify(report)
        if groups["ambiguous"]:
            callers = Counter(e.get("caller") for e in groups["ambiguous"])
            print(f"- **{report['domain']}** — {len(groups['ambiguous'])}: "
                  f"{', '.join(f'{c} ×{n}' for c, n in callers.most_common(3))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
