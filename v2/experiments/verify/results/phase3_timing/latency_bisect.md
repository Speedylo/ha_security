# Mediation latency — why pass 1 found 43 µs where the report states 31.5

Pass 1 measured 43.2 µs (one client, median) against §7.19's 31.5 µs, outside the T criterion.
Two checks on the same Pi, 2026-10-05, ~22:45, the same `scale.py` (from 00dccc8) throughout, so that
only the framework varies.

**Old code against the frozen code, interleaved, same minute** (three runs each):

| Framework | 1 client, median | 26 clients, median |
|---|---|---|
| 00dccc8 (2026-09-02, the run behind 31.5 µs) | 31.9, 30.3, 30.2 µs | 518.6, 517.4, 522.4 µs |
| verify-2026-10 (frozen) | 41.6, 42.4, 42.4 µs | 794.3, 807.3, 797.6 µs |

So the machine reproduces the old figure today: the increase is the code's.

**Bisection over every commit that touched the request path** (two runs each, µs):

| Commit | Date | Change | Median |
|---|---|---|---|
| 00dccc8 | 09-02 | the §7.19 run | 30.7, 29.7 |
| c2d51ea | 09-02 | S9 wired to the manifest | 30.5, 30.3 |
| **68448a6** | **09-03** | **descriptor passing on the channel (egress step 1)** | **34.7, 34.1** |
| b828847 | 09-03 | mediated egress | 34.8, 34.1 |
| 86d914f | 09-03 | the datagram relay | 34.7, 35.6 |
| 559e0c3 | 09-03 | egress, allow_private | 35.8, 35.7 |
| 04a31db | 10-03 | T4, the durable log engaged | 35.0, 35.1 |
| **4222ab0** | **10-04** | **the push loop (outbox, per-reply selector updates)** | **40.4, 40.1** |
| b0a70ef | 10-04 | the real Home Assistant | 41.7, 40.6 |
| afab3e9 | 10-04 | commands | 41.8, 41.7 |
| d7a9db9 | 10-04 | W1 review fixes | 41.9, 41.5 |
| 0187f5e | 10-04 | (A)'s events between requests | 53.4, 40.8 |
| 3a05e8f | 10-04 | local TCP | 43.3, 40.4 |
| cd26992 | 10-04 | asyncio datagrams | 43.5, 43.2 |
| c16a151 | 10-05 | the flood cut-off | 41.9, 44.2 |

Two steps of about 15% each: the channel's descriptor passing (09-03) and the push loop (10-04).
**The 31.5 µs figure has described an older mediator since 2026-09-03**, the day after it was
measured. Both are costs of features the report depends on. Against the 3.67 ms durable record per
decision the added ~11 µs is under 0.3%, so §7.20.1's conclusions are unaffected; the stated figure is.
Finding F17.
