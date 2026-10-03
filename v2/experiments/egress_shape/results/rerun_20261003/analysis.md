# Egress shape — 12 of 12 integrations ran

## 1. Resolution path — where a mediator would have to interpose

| Integration | getaddrinfo | aiodns | aiodns share |
|---|---|---|---|
| `pirateweather` | 10 | 2 | 17% |
| `nordpool` | 9 | 2 | 18% |
| `dwd_weather` | 12 | 1 | 8% |
| `solcast_solar` | 9 | 1 | 10% |
| `alexa_media` | 9 | 1 | 10% |
| `waste_collection_schedule` | 8 | 1 | 11% |
| `localtuya` | 19 | 1 | 5% |
| `solarman` | 8 | 1 | 11% |
| `midea_ac_lan` | 10 | 1 | 9% |
| `bambu_lab` | 10 | 1 | 9% |
| `frigate` | 8 | 11 | 58% |
| `sonoff` | 9 | 2 | 18% |
| **all** | **121** | **25** | **17%** |

## 2. Transport the integration itself used

| Integration | STREAM | DGRAM | RAW | ports reached |
|---|---|---|---|---|
| `pirateweather` | 1 | 0 | 0 | 443 |
| `nordpool` | 4 | 0 | 0 | 443 |
| `dwd_weather` | 3 | 0 | 0 | 443 |
| `solcast_solar` | 0 | 0 | 0 | — |
| `alexa_media` | 1 | 0 | 0 | 8123 |
| `waste_collection_schedule` | 0 | 0 | 0 | — |
| `localtuya` | 9 | 0 | 0 | 443 |
| `solarman` | 0 | 0 | 0 | — |
| `midea_ac_lan` | 0 | 18 | 0 | 6445, 20086 |
| `bambu_lab` | 0 | 0 | 0 | — |
| `frigate` | 0 | 0 | 0 | — |
| `sonoff` | 2 | 0 | 0 | 443 |

**Ports across the sample:** 443 (5), 8123 (1), 6445 (1), 20086 (1)
**Non-web ports:** [8123, 6445, 20086] — decides whether §5.10.3's hostname-only clause is sufficient

## 3. TLS — can a mediator see content?

| Integration | wrap_bio | wrap_socket | verified | server_hostname seen |
|---|---|---|---|---|
| `pirateweather` | 1 | 0 | 1 | api.pirateweather.net |
| `nordpool` | 3 | 0 | 3 | dataportal-api.nordpoolgroup.com |
| `dwd_weather` | 0 | 3 | 3 | opendata.dwd.de |
| `solcast_solar` | 0 | 0 | 0 | — |
| `alexa_media` | 0 | 0 | 0 | — |
| `waste_collection_schedule` | 0 | 0 | 0 | — |
| `localtuya` | 0 | 10 | 10 | openapi.tuyaeu.com |
| `solarman` | 0 | 0 | 0 | — |
| `midea_ac_lan` | 0 | 0 | 0 | — |
| `bambu_lab` | 0 | 0 | 0 | — |
| `frigate` | 0 | 0 | 0 | — |
| `sonoff` | 1 | 0 | 1 | as-apia.coolkit.cc |

## 4. Inbound — a capability §5.10.3 cannot express

A *listener* is a `listen`, or a bind to a fixed port on an IP socket. A bind to port
0, or to a high ephemeral port, is what every UDP client does before it sends and is
not inbound. `AF_NETLINK` binds are route queries and are not network at all — the
first version of this table counted 79 of `scapy`'s and read as though integrations
listen constantly.

| Integration | listeners | IP binds (ephemeral) | netlink binds |
|---|---|---|---|
| `pirateweather` | none | 1 | 5 |
| `nordpool` | none | 0 | 11 |
| `dwd_weather` | none | 0 | 11 |
| `solcast_solar` | none | 1 | 1 |
| `alexa_media` | none | 0 | 6 |
| `waste_collection_schedule` | none | 0 | 2 |
| `localtuya` | none | 1 | 0 |
| `solarman` | none | 0 | 3 |
| `midea_ac_lan` | none | 1 | 8 |
| `bambu_lab` | none | 1 | 5 |
| `frigate` | none | 0 | 8 |
| `sonoff` | none | 0 | 11 |

**No integration in the sample established a listener.**

## 5. In-process recorder against the kernel

Egress only — `AF_INET`/`AF_INET6` connect and sendto. The kernel's `AF_NETLINK` and
`AF_UNIX` traffic is route, interface, dbus and log-socket work, which is not egress
and which the recorder never claimed to watch.

| Integration | recorder | kernel (inet) | ratio | kernel non-inet |
|---|---|---|---|---|
| `pirateweather` | 50 | 61 | 82% | 1030 |
| `nordpool` | 53 | 64 | 83% | 1112 |
| `dwd_weather` | 48 | 61 | 79% | 1071 |
| `solcast_solar` | 49 | 55 | 89% | 986 |
| `alexa_media` | 50 | 56 | 89% | 998 |
| `waste_collection_schedule` | 47 | 55 | 85% | 1001 |
| `localtuya` | 59 | 135 | 44% | 1137 |
| `solarman` | 49 | 55 | 89% | 1007 |
| `midea_ac_lan` | 67 | 73 | 92% | 1036 |
| `bambu_lab` | 47 | 55 | 85% | 986 |
| `frigate` | 47 | 56 | 84% | 1098 |
| `sonoff` | 51 | 61 | 84% | 1081 |

## 6. Destinations attributed to the integration

- **pirateweather** (create_entry):
  - `99.86.159.63:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
- **nordpool** (create_entry):
  - `104.18.0.18:443` ×2 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
  - `104.18.1.18:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
  - `2606:4700::6812:12:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
- **dwd_weather** (create_entry):
  - `141.38.2.164:443` ×3 — SOCK_STREAM, via `dwd_weather/connector.py:419`
- **solcast_solar** — nothing outbound attributed to it (flow: None)
- **alexa_media** (external):
  - `10.126.83.113:8123` ×1 — SOCK_STREAM, via `alexa_media/config_flow.py:329`
- **waste_collection_schedule** — nothing outbound attributed to it (flow: None)
- **localtuya** (form):
  - `52.29.137.228:443` ×4 — SOCK_STREAM, via `urllib3/util/connection.py:73`
  - `52.57.166.16:443` ×3 — SOCK_STREAM, via `urllib3/util/connection.py:73`
  - `3.69.78.245:443` ×2 — SOCK_STREAM, via `urllib3/util/connection.py:73`
- **solarman** — nothing outbound attributed to it (flow: None)
- **midea_ac_lan** (form):
  - `127.0.0.1:6445` ×9 — SOCK_DGRAM, via `midea_ac_lan/config_flow.py:406`
  - `127.0.0.1:20086` ×9 — SOCK_DGRAM, via `midea_ac_lan/config_flow.py:406`
- **bambu_lab** — nothing outbound attributed to it (flow: None)
- **frigate** — nothing outbound attributed to it (flow: form)
- **sonoff** (form):
  - `54.255.85.149:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
  - `52.76.7.82:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`

## 7. Events the two filters disagreed on

- **pirateweather** — 5: homeassistant/components/http/server.py:254 ×2, homeassistant/components/http/server.py:548 ×2, urllib3/util/connection.py:127 ×1
- **nordpool** — 5: homeassistant/components/http/server.py:254 ×2, homeassistant/components/http/server.py:548 ×2, urllib3/util/connection.py:127 ×1
- **dwd_weather** — 5: homeassistant/components/http/server.py:254 ×2, homeassistant/components/http/server.py:548 ×2, util/connection.py:127 ×1
- **solcast_solar** — 5: homeassistant/components/http/server.py:254 ×2, homeassistant/components/http/server.py:548 ×2, urllib3/util/connection.py:127 ×1
- **alexa_media** — 5: homeassistant/components/http/server.py:254 ×2, homeassistant/components/http/server.py:548 ×2, util/connection.py:127 ×1
- **waste_collection_schedule** — 5: homeassistant/components/http/server.py:254 ×2, homeassistant/components/http/server.py:548 ×2, urllib3/util/connection.py:127 ×1
- **localtuya** — 5: homeassistant/components/http/server.py:254 ×2, homeassistant/components/http/server.py:548 ×2, urllib3/util/connection.py:127 ×1
- **solarman** — 5: homeassistant/components/http/server.py:254 ×2, homeassistant/components/http/server.py:548 ×2, urllib3/util/connection.py:127 ×1
- **midea_ac_lan** — 5: homeassistant/components/http/server.py:254 ×2, homeassistant/components/http/server.py:548 ×2, urllib3/util/connection.py:127 ×1
- **bambu_lab** — 5: homeassistant/components/http/server.py:254 ×2, homeassistant/components/http/server.py:548 ×2, urllib3/util/connection.py:127 ×1
- **frigate** — 5: homeassistant/components/http/server.py:254 ×2, homeassistant/components/http/server.py:548 ×2, urllib3/util/connection.py:127 ×1
- **sonoff** — 10: _utils/net.py:291 ×3, homeassistant/components/http/server.py:254 ×2, homeassistant/components/http/server.py:548 ×2
