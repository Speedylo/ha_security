# Egress shape — 12 of 12 integrations ran

## 1. Resolution path — where a mediator would have to interpose

| Integration | getaddrinfo | aiodns | aiodns share |
|---|---|---|---|
| `pirateweather` | 9 | 2 | 18% |
| `nordpool` | 9 | 2 | 18% |
| `dwd_weather` | 12 | 1 | 8% |
| `solcast_solar` | 8 | 1 | 11% |
| `alexa_media` | 9 | 1 | 10% |
| `waste_collection_schedule` | 9 | 1 | 10% |
| `localtuya` | 19 | 1 | 5% |
| `solarman` | 8 | 1 | 11% |
| `midea_ac_lan` | 9 | 1 | 10% |
| `bambu_lab` | 9 | 1 | 10% |
| `frigate` | 9 | 1 | 10% |
| `sonoff` | 8 | 1 | 11% |
| **all** | **118** | **14** | **11%** |

## 2. Transport the integration itself used

| Integration | STREAM | DGRAM | RAW | ports reached |
|---|---|---|---|---|
| `pirateweather` | 2 | 0 | 0 | 443 |
| `nordpool` | 4 | 0 | 0 | 443 |
| `dwd_weather` | 4 | 0 | 0 | 443 |
| `solcast_solar` | 1 | 0 | 0 | 443 |
| `alexa_media` | 0 | 0 | 0 | — |
| `waste_collection_schedule` | 0 | 0 | 0 | — |
| `localtuya` | 11 | 0 | 0 | 443 |
| `solarman` | 0 | 0 | 0 | — |
| `midea_ac_lan` | 2 | 18 | 0 | 443, 6445, 20086 |
| `bambu_lab` | 1 | 0 | 0 | 443 |
| `frigate` | 0 | 0 | 0 | — |
| `sonoff` | 1 | 0 | 0 | 443 |

**Ports across the sample:** 443 (8), 6445 (1), 20086 (1)
**Non-web ports:** [6445, 20086] — decides whether §5.10.3's hostname-only clause is sufficient

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
| `sonoff` | 0 | 0 | 0 | — |

## 4. Inbound — a capability §5.10.3 cannot express

A *listener* is a `listen`, or a bind to a fixed port on an IP socket. A bind to port
0, or to a high ephemeral port, is what every UDP client does before it sends and is
not inbound. `AF_NETLINK` binds are route queries and are not network at all — the
first version of this table counted 79 of `scapy`'s and read as though integrations
listen constantly.

| Integration | listeners | IP binds (ephemeral) | netlink binds |
|---|---|---|---|
| `pirateweather` | none | 0 | 10 |
| `nordpool` | none | 0 | 9 |
| `dwd_weather` | none | 0 | 11 |
| `solcast_solar` | none | 0 | 1 |
| `alexa_media` | none | 0 | 11 |
| `waste_collection_schedule` | none | 0 | 9 |
| `localtuya` | none | 0 | 5 |
| `solarman` | none | 0 | 6 |
| `midea_ac_lan` | none | 0 | 11 |
| `bambu_lab` | none | 0 | 11 |
| `frigate` | none | 0 | 9 |
| `sonoff` | none | 0 | 0 |

**No integration in the sample established a listener.**

## 5. In-process recorder against the kernel

Egress only — `AF_INET`/`AF_INET6` connect and sendto. The kernel's `AF_NETLINK` and
`AF_UNIX` traffic is route, interface, dbus and log-socket work, which is not egress
and which the recorder never claimed to watch.

| Integration | recorder | kernel (inet) | ratio | kernel non-inet |
|---|---|---|---|---|
| `pirateweather` | 8 | 20 | 40% | 385 |
| `nordpool` | 10 | 22 | 45% | 431 |
| `dwd_weather` | 9 | 19 | 47% | 389 |
| `solcast_solar` | 7 | 14 | 50% | 357 |
| `alexa_media` | 5 | 13 | 38% | 362 |
| `waste_collection_schedule` | 6 | 13 | 46% | 360 |
| `localtuya` | 17 | 95 | 18% | 459 |
| `solarman` | 5 | 13 | 38% | 362 |
| `midea_ac_lan` | 25 | 33 | 76% | 394 |
| `bambu_lab` | 6 | 14 | 43% | 366 |
| `frigate` | 6 | 13 | 46% | 356 |
| `sonoff` | 7 | 14 | 50% | 365 |

## 6. Destinations attributed to the integration

- **pirateweather** (create_entry):
  - `108.157.98.36:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
  - `108.157.98.49:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
- **nordpool** (create_entry):
  - `104.18.0.18:443` ×2 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
  - `104.18.1.18:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
  - `2606:4700::6812:112:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
- **dwd_weather** (create_entry):
  - `141.38.2.164:443` ×3 — SOCK_STREAM, via `dwd_weather/connector.py:419`
  - `104.26.4.238:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
- **solcast_solar** (None):
  - `104.26.5.238:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
- **alexa_media** — nothing outbound attributed to it (flow: None)
- **waste_collection_schedule** — nothing outbound attributed to it (flow: None)
- **localtuya** (form):
  - `3.69.78.245:443` ×4 — SOCK_STREAM, via `urllib3/util/connection.py:73`
  - `52.29.137.228:443` ×3 — SOCK_STREAM, via `urllib3/util/connection.py:73`
  - `52.57.166.16:443` ×3 — SOCK_STREAM, via `urllib3/util/connection.py:73`
  - `104.26.4.238:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
- **solarman** — nothing outbound attributed to it (flow: None)
- **midea_ac_lan** (form):
  - `127.0.0.1:6445` ×9 — SOCK_DGRAM, via `midea_ac_lan/config_flow.py:406`
  - `127.0.0.1:20086` ×9 — SOCK_DGRAM, via `midea_ac_lan/config_flow.py:406`
  - `172.67.68.90:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
  - `2606:4700:20::681a:4ee:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
- **bambu_lab** (None):
  - `104.26.4.238:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`
- **frigate** — nothing outbound attributed to it (flow: None)
- **sonoff** (None):
  - `172.67.68.90:443` ×1 — SOCK_STREAM, via `aiohappyeyeballs/impl.py:210`

## 7. Events the two filters disagreed on

- **pirateweather** — 2: urllib3/util/connection.py:127 ×1, homeassistant/components/http/server.py:254 ×1
- **nordpool** — 2: urllib3/util/connection.py:127 ×1, homeassistant/components/http/server.py:254 ×1
- **dwd_weather** — 2: util/connection.py:127 ×1, homeassistant/components/http/server.py:254 ×1
- **solcast_solar** — 2: urllib3/util/connection.py:127 ×1, homeassistant/components/http/server.py:254 ×1
- **alexa_media** — 2: util/connection.py:127 ×1, homeassistant/components/http/server.py:254 ×1
- **waste_collection_schedule** — 3: homeassistant/components/http/server.py:254 ×2, urllib3/util/connection.py:127 ×1
- **localtuya** — 2: urllib3/util/connection.py:127 ×1, homeassistant/components/http/server.py:254 ×1
- **solarman** — 2: urllib3/util/connection.py:127 ×1, homeassistant/components/http/server.py:254 ×1
- **midea_ac_lan** — 2: urllib3/util/connection.py:127 ×1, homeassistant/components/http/server.py:254 ×1
- **bambu_lab** — 2: urllib3/util/connection.py:127 ×1, homeassistant/components/http/server.py:254 ×1
- **frigate** — 3: homeassistant/components/http/server.py:254 ×2, urllib3/util/connection.py:127 ×1
- **sonoff** — 8: _utils/net.py:291 ×3, homeassistant/components/http/server.py:254 ×2, urllib3/util/connection.py:127 ×1
