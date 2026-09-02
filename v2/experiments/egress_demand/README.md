# Experiment — how much egress is needed, and of what kind

**Run:** 2026-09-02 · **Pi 5, HA 2026.8.3, Python 3.14.7** · **Feeds:** §7.18 · **Informs:** §9.5

§9.5 leaves one decision open — whether to build §5.8.2's scope item 2 — and nothing in the
evaluation measured the thing it turns on: how many integrations need outbound network, and where.

## Declared: the corpus splits almost exactly in half

| `iot_class` | Count | Needs | Served by scope item 2 as scoped? |
|---|---|---|---|
| `cloud_polling` 13 + `cloud_push` 2 | **15 — 41%** | the internet | **yes** |
| `local_push` 12 + `local_polling` 3 | **15 — 41%** | LAN devices | only via §5.10.3's separate non-public flag (T10) |
| `calculated` | 6 — 16% | nothing | n/a |
| none declared | 1 | — | — |

**81% declare a network reach.** The proxy as scoped serves 41% of the corpus directly; the other
41% need a private address, which the design provides for but behind a louder declaration.

## Observed: zero, and the first attempt at this number was an artifact

`record_egress_attempts` patches `socket` and records every resolve and connect.

**The first version reported 23 of 37 integrations attempting egress at import.** All 23 reached
the identical triple `224.0.0.251`, `8.8.8.8`, `127.0.0.1` — which is not integrations behaving
alike. It was Home Assistant: `network` probes 8.8.8.8 for the default route, `zeroconf` joins the
mDNS group, both during `async_setup_component`, before the integration is imported.

With phase attribution:

| Phase | Attempts | Integrations |
|---|---|---|
| instance construction | 0 | 0 |
| **declared components** | **71** | **23** |
| **the integration itself** | **0** | **0** |

**No integration attempts egress at import.** That is the finding, not a null result: integrations
connect at *setup*, not at import.

## Why no observational method can answer this

Demand appears at setup. Setup needs a credential for 26 of 37 (§7.17.1). So neither this project
nor an unconfined baseline can observe egress demand across this corpus — **the declaration is
not the better estimator, it is the only one.**

## Limits

- In-process recorder: raw syscalls would not be seen. Fine for measuring ordinary demand; the
  adversary is §7.13's job.
- `iot_class` is the author's claim, subject to R1 — though over-declaring one's own network
  reach buys an attacker nothing.

## Reproducing

```bash
systemd-run --user --scope -q python3 -m confine.compat --corpus ~/r2exp/corpus \
    --python ~/r2exp/ha314/bin/python --profile declared \
    --platform-deps ~/r2exp/platform-deps --json results/pi5_import_phase.json
```
