# UDP demand across 75 distinct integrations

Corpora: corpus, corpus_uniform; 2 appear in both.

| Where the datagram code is | Integrations | Share |
|---|---|---|
| the integration's own source | 8 | 11% |
| a **device-protocol dependency** | 10 | 13% |
| **own source or a protocol library** | **15** | **20%** |
| any dependency, incl. general-purpose (ceiling) | 20 | 27% |

Dependency scan: 42 installed, 33 declare no requirements, 0 failed to install.

## By declared iot_class

| `iot_class` | total | with UDP | share |
|---|---|---|---|
| `cloud_polling` | 27 | 2 | 7% |
| `local_push` | 18 | 3 | 17% |
| `local_polling` | 16 | 1 | 6% |
| `calculated` | 7 | 0 | 0% |
| `cloud_push` | 5 | 1 | 20% |
| `none` | 2 | 1 | 50% |

## The integrations, and what was found

| Integration | `iot_class` | markers |
|---|---|---|
| `govee` | cloud_push | DatagramProtocol@lan.py:341, DatagramProtocol@lan.py:373, DatagramProtocol@lan_client.py:298, DatagramTransport@lan.py:467 |
| `localtuya` | local_push | DatagramProtocol@discovery.py:33, class TuyaDiscovery(DatagramProtocol)@discovery.py:33, create_datagram_endpoint@discovery.py:45, create_datagram_endpoint@discovery.py:48 |
| `solarman` | local_polling | SOCK_DGRAM@scanner.py:15, SO_BROADCAST@scanner.py:17, sendto@scanner.py:20 |
| `sonoff` | local_push | SOCK_DGRAM@camera.py:133, SO_BROADCAST@camera.py:135, recvfrom@camera.py:174, sendto@camera.py:113 |
| `sonyavr` | local_push | SOCK_DGRAM@sonyavr.py:799 |
| `tapo_control` | none | DatagramProtocol@binary_sensor.py:175, DatagramTransport@binary_sensor.py:82, class _TapoUdpProtocol(DatagramProtocol)@binary_sensor.py:175, create_datagram_endpoint@binary_sensor.py:143 |
| `xiaomi_home` | cloud_polling | SOCK_DGRAM@miot_lan.py:1184, SO_BROADCAST@miot_lan.py:1185, recvfrom_into@miot_lan.py:1215, sendto@miot_lan.py:1344 |
| `xiaomi_miot` | cloud_polling | DatagramProtocol@mini_miio.py:207, DatagramTransport@mini_miio.py:209, DatagramTransport@mini_miio.py:215, SOCK_DGRAM@mini_miio.py:120 |

## Datagram code found in declared dependencies

| Integration | `iot_class` | packages |
|---|---|---|
| `alexa_media` | cloud_polling | anyio (general) |
| `ble_monitor` | local_polling | pyric (general) |
| `dreame_vacuum` | cloud_polling | **miio**, **zeroconf** |
| `dwd_weather` | cloud_polling | anyio (general) |
| `eufy_security` | cloud_push | **aiortsp** |
| `llmvision` | cloud_polling | botocore (general) |
| `localtuya_rc` | local_polling | **tinytuya** |
| `midea_ac_lan` | local_push | **midealan** |
| `qolsys_panel` | local_push | **qolsys_controller**, **zeroconf** |
| `skybellgen` | cloud_polling | **aioskybellgen**, botocore (general), pytest_asyncio (general) |
| `solcast_solar` | cloud_polling | anyio (general) |
| `solis_modbus` | local_polling | **pymodbus** |
| `sonyavr` | local_push | **asyncping3** |
| `tapo_control` | none | **kasa** |
| `xiaomi_home` | cloud_polling | psutil (general) |
| `xiaomi_miot` | cloud_polling | **miio**, **zeroconf** |

## Calibration

`midea_ac_lan` has **no datagram code of its own** and is found in a declared dependency: midealan. This is the calibration passing in the more informative way — §7.24 observed the datagrams and charged them to `config_flow.py:406`, which is where the *call* is made, not where the socket code lives. An own-source scan alone would have reported this integration as needing no UDP.
