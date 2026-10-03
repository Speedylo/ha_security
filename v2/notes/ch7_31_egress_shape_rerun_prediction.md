# §7.24's egress-shape run, repeated on the corrected instance: prediction

**Written 2026-10-03, before the run.** Never revised after it.

§7.24 ran twelve head-corpus integrations unconfined, with real network, through
`netshape_runtime`, which builds its instance with `build_hass`. §7.31.3 found that instance
missing the frame helper and loading `network` only via `http`, and §7.31.10 named §7.24 as the
experiment most likely to move. Same command as `experiments/egress_shape/README.md`, same corpus,
settle 20 s, `--strace --full-events`. Only the code differs.

| | Prediction | Confidence |
|---|---|---|
| **P1** | `dwd_weather` moves from "nothing outbound attributed" to reaching `opendata.dwd.de:443` over TCP, resolved through `getaddrinfo` (it is `httpx`), with TLS seen as `wrap_socket` and verified. Its setup failed on the frame helper; its fetch is at first refresh, inside setup | medium — the default station is whichever is nearest `build_hass`'s London coordinates, and its fetch must land inside 20 s |
| **P2** | No other integration changes between *reached the network* and *did not*. The other five non-reachers stopped for reasons §7.24.7 recorded — `recorder`, a corpus layout artifact, an unresolvable default host, a schema the shared credential set cannot satisfy, `aiofiles` — and none is the frame helper or `network` | medium-high — §7.24.7 records those reasons from tracebacks, not from a corrected run |
| **P3** | So six of twelve becomes **seven of twelve** reached the network | follows from P1 and P2 |
| **P4** | §7.24's three conclusions hold in kind: resolution is overwhelmingly `aiodns` (the aggregate share may fall by about a point, since `httpx` adds `getaddrinfo` calls), non-web ports and UDP are real, and no integration establishes a listener | high |
| **P5** | The recorder-versus-kernel ratios stay in §7.24's 42–87% band | medium-high |
