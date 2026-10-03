# §7.31 — three more real integrations, end to end: predictions

**Written 2026-10-03, before the harness was generalised and before anything was run.** Never
revised after a run; a wrong prediction is corrected in §7.31, not here. Same rule as
`ch7_uniform_prediction.md`.

## Why this measurement

§7.27 ran one real community integration (`nordpool`) confined against its real API, and that
one run found the most important defect in the project — `async_get_clientsession` joins the mDNS
group, a fresh netns `lo` has no `IFF_MULTICAST`, and so no real integration could build an HTTP
client in the sandbox, behind eighteen passing suites. §8.4.2's lesson is that real unmodified
code finds what instruments written out of the design's own assumptions cannot. **That lesson has
been applied once.** This applies it three more times.

## Selection, and a correction it forces

§7.27.1 says `nordpool` is, "as far as this corpus goes, the only member" of the intersection of
*network-using* and *configurable without a credential*. Surveying both corpora by `iot_class` and
by what `config_flow.py` asks for (survey script run 2026-10-03 on the Pi) shows that is not true
of the corpus. It is true of what §7.24 *observed*: §7.24 drove `dwd_weather`, its flow created an
entry, and no egress was attributed to it — because `dwd_weather`'s flow is offline (a bundled
station list) and it fetches only at its first coordinator update, after the flow. §7.24.7 files it
under "the flow stopped before its call". §7.27.1 then read *no egress observed* as *no egress
needed*. **That sentence is a finding to correct in §7.31, not here.**

Chosen to differ from `nordpool` and from each other in **network stack**, because §8.7 #7 says
the other stacks have never been spawned confined and §7.27 is the reason "presumably fine" is
not an answer:

| Subject | Corpus | Stack on the network path | Declared egress (read from source) | Flow input |
|---|---|---|---|---|
| `smhi_brandrisk` | uniform | aiohttp via `async_get_clientsession` — `nordpool`'s shape | `opendata-download-metfcst.smhi.se:443`, `opendata-download-warnings.smhi.se:443` | Stockholm, 59.33 N 18.07 E |
| `regensburg_transport` | uniform | **`requests` (urllib3), in an executor, during the flow**; then a **bare `aiohttp.ClientSession()`** in the sensor | `efa.rvv.de:443` | search "Arnulfsplatz", first match |
| `dwd_weather` | **head** | **`httpx`, synchronous, in an executor**, after setup | `opendata.dwd.de:443` | station `10865` (München-Stadt) |

All three import clean in both arms on 2026.8.3 (`compat_baseline.json`/`compat_declared_core.json`,
`uniform_baseline.json`/`uniform_confined.json`). All endpoints answered `200` from the Pi on
2026-10-03, except `opendata-download-warnings.smhi.se`, which returned **503 three times running**
— an upstream outage. `smhi_brandrisk` treats that call as non-critical (`except Exception`, debug log),
so it does not gate the result; it does mean arm A cannot show warnings succeeding either.

`smhi_brandrisk` gets a fourth arm, **D: only the forecast host declared**. Two hosts make it the
first subject that can show the grant is *per destination* rather than per integration, with a
clause pointer into a multi-entry list.

## The harness change, stated before it is made

`endtoend_egress.py` is generalised from one hard-coded subject to a table, with `nordpool` kept as
the default so §7.27's reproduction command is unchanged. One change to shared code:
`regensburg_transport`'s stop field is a `SelectSelector` with `default=False`, and its options are
the live search results, so neither the field's default (`fill_schema` would send `False`) nor any
fixed override can answer it. The spec gains `select_first` — named fields for which the first
offered option is chosen, as a user picks the top match. It lives in `drive_flow`, which both arms
share, so the two arms still differ only in confinement.

## Predictions

| | Prediction | Confidence |
|---|---|---|
| **P1** | Arm A loads and produces a real value for all three | high for SMHI, DWD; medium for Regensburg (the `Hauptbahnhof` query 502'd today, `Arnulfsplatz` did not) |
| **P2** | `smhi_brandrisk` arm B matches arm A's fire-risk value exactly, and C publishes no fetched value | high — it is `nordpool`'s shape with a different host |
| **P3** | `regensburg_transport` arm B completes its flow: the `requests` call during the flow goes through the shim's `getaddrinfo`/`connect` seams and is granted | **medium** — on paper `socket.create_connection` is covered; it has never run |
| **P4** | `regensburg_transport` arm C **fails its config flow** rather than degrading, because `get_stop_id` catches `HTTPError` and `Timeout` but not `ConnectionError`, so a refused connection propagates out of the step | medium-high |
| **P5** | `dwd_weather` arm B loads and publishes a real temperature over `httpx` | **medium** — same seams, and an executor thread; `httpx` may honour proxy environment variables or open its own resolver path |
| **P6** | `dwd_weather` arm C still reaches **LOADED** and degrades to `unavailable`, as `nordpool` did | medium |
| **P7** | Arm D grants the forecast host, denies the warnings host with clause `/permissions/network/egress`, and the fire-risk value still equals A's | high |
| **P8** | **At least one of the three finds something the suites did not** — a seam the shim misses, a phase where egress appears that nothing has watched, or an audit-record defect | **this is the project's own argument; if it is wrong, that is a result too** |
