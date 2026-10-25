# F65: `http` cannot find a source address under the egress shim — prediction (2026-10-25)

**Committed before the fix and before any run below.** Younes approved the fix on 2026-10-25, after
the end-to-end extension (`notes/e2e_extension_prediction_20261025.md`) found
`waste_collection_schedule`'s calendar missing confined.

## The mechanism, as read and reproduced outside a sandbox

Home Assistant's `network.async_get_source_ip` (2026.8.3, `components/network/__init__.py:54`) asks
`network.util.async_get_source_ip` for 8.8.8.8, then 224.0.0.251, then 127.0.0.1. Each opens a UDP
socket, `connect`s it, and returns `getsockname()[0]`; any exception gives `None`. With no IPv4
adapter (the sandbox has only `lo`), three `None`s raise *"Could not determine source ip …"*, and
`http`'s setup awaits that unconditionally (`components/http/__init__.py:229`), so `http` fails,
and with it everything that depends on it — the calendar among them.

Under the egress shim, a datagram socket's `connect` is intercepted (`egress_shim.on_connect`) and
the socket is put on one end of an `AF_UNIX` socket pair with `dup2`. That socket's `getsockname()`
returns `''`, so `[0]` raises `IndexError` — for all three targets, loopback included. Without the
shim, the loopback target succeeds (`namespaces.bring_loopback_up`), which is why `alarmo` set up
`http` in `endtoend_function`, which installs no shim.

**Why it matters beyond one calendar.** `supervise.py` sets `"egress": True` for every sandbox, so
in deployment every sandbox has the shim. The compatibility runs never installed it (they set
`record_egress` only). In the final rerun (`final_20261016/step05_compat/c1_declared_core.json`),
`http` was set up — successfully — for **15 of the 37** head integrations: `alarmo`, `alexa_media`,
`bambu_lab`, `browser_mod`, `frigate`, `hacs`, `homematicip_local`, `llmvision`, `nordpool`,
`scheduler`, `solcast_solar`, `sonoff`, `webrtc`, `xiaomi_home`, `xiaomi_miot`.

## The fix

A datagram `connect` to a loopback address falls through to the real `connect`. Loopback is the
sandbox's own interface in its own network namespace: nothing sent there leaves the sandbox, so
there is nothing for the mediator to decide — the same rule TCP already follows
(`_home_network` excludes loopback, and the connect falls through). Only a socket the shim has not
yet put on a pair falls through; one already on a pair keeps today's behaviour. Nothing else
changes: datagrams to any other address are still relayed and checked.

Not done: making `getsockname` of a pair-backed socket return an IPv4 address. Home Assistant gets
`127.0.0.1` from the loopback target, which is what it gets without the shim.

## Predictions

Q1's case was written and run on the laptop before this note was committed: 22/25, with 8a (`''`),
8b (`None`) and 8c failing — the symptom exactly. The note was then corrected from "the first two
checks" to 8a–8c, since a loopback socket is relayed today and 8c asserts it is not.

| | Prediction | Where, criterion |
|---|---|---|
| Q1 | A new case in `selftest_udp` — a datagram `connect` to 127.0.0.1 under the shim reports `getsockname()[0] == '127.0.0.1'`; Home Assistant's three-target lookup, run as written, returns `'127.0.0.1'`; the loopback connect asks the mediator nothing; a connect to 8.8.8.8 is still put on a pair — **fails before the fix** (8a–8c; 8d passes either way) and passes after | laptop and Pi |
| Q2 | Every suite `experiments/selftests` runs still passes after the fix | Pi, fresh clone |
| Q3 | **Before the fix**, `compat --profile declared --egress` (the final rerun's measurement, with the shim installed as `supervise.py` installs it): `http` fails in **all 15**, each with *"Could not determine source ip"* in its setup log | Pi, fresh clone at the pre-fix tag |
| Q4 | **After the fix**, the same: `http` sets up in all 15, and every one of the 37 reaches the same level as in the final rerun | Pi, fresh clone at the post-fix tag |
| Q5 | **After the fix**, `endtoend_egress --subject waste_collection_schedule`: the harness's checks all pass, the confined arm publishes the calendar entity, and its log has no *"Could not determine source ip"* | Pi, same clone |

`--egress` is a new switch on `compat` that only adds what `supervise.py` adds: the shim in the
sandbox and `"egress": True` in its spec. Its mediator has no broker and no relay, so any network
request is refused — a corpus integration declares no network permission in this run anyway, and
the source-address lookup makes no request at all (a `connect` sends nothing).

## What a failure means

Q3 failing means F65's mechanism is not the one stated here, and the fix is not applied until it
is. Q4 or Q5 failing is reported with the unconfined arm consulted first. Levels in Q3 that differ
from the final rerun are recorded, not predicted. No run is repeated to obtain a pass. The outcome
is appended to this note.

---

## Outcome (appended 2026-10-25, after the runs)

Pi, fresh clones of `f65-pre` (`c2b7719`) and `f65-fix` (`a20661c`), each clean before and after,
18:05–18:15. Results: `experiments/compat/results/f65_20261025/` (`pre/`, `post/`, `verdicts_pre.txt`,
`verdicts_post.txt`, the drivers).

| | Outcome |
|---|---|
| Q1 | Held. Laptop: 22/25 before (8a `''`, 8b `None`, 8c), 25/25 after. Pi, after: 25/25 |
| Q2 | Held: 29 of 29 suites exit 0 |
| Q3 | **Half held.** `http` failed in all 15 (15/15). The setup-log criterion missed as written: the message is in 2 of the 15 logs. In the other 13 the runtime keeps only a component's first three warnings, one of them is "a custom integration … has not been tested", and the third is the network component's *"Because the system does not have any enabled IPv4 addresses…"*, logged on the same path immediately before the raise. The harness cut the line off; the log as kept does not show it. Levels: none differ from the final rerun |
| Q4 | Held: `http` set up in all 15; all 37 at the final rerun's level |
| Q5 | Held: the confined arm published `calendar.waste_collection_schedule_ead_darmstadt`; no source-IP message; the harness's checks 16/16 |

Q4 is what settles the mechanism Q3 could not show in 13 logs: the only change between the two runs
is the fix, and `http` went from 0/15 to 15/15.

**Not predicted — the same failure by a second route (still open).** Comparing every component's
setup with the final rerun, after the fix: `zeroconf` sets up for neither `sonoff` nor `xiaomi_home`
under the shim (in the final rerun, without it, it did for both). Its log: *"Error during setup of
component zeroconf: Could not determine source ip …"*. `zeroconf` asks for its announce addresses
(`network.async_get_announce_addresses`, `network/__init__.py:161`) with **one** target, the mDNS
group 224.0.0.251, not the three. Without the shim that connect succeeds, because
`namespaces.route_multicast_to_loopback` routes 224/4 to `lo`; under the shim it is still relayed, and
the fix covers loopback only. Before the fix the same two failed earlier, at `api` → `http`. The
levels do not change (both are `platforms_clean`), but a confined integration that relies on
`zeroconf` for discovery would not get it under the supervisor. Extending the fall-through to
multicast connects is the obvious fix, and it is not made here: it lets a socket send to the
multicast group without the mediator, which `route_multicast_to_loopback` argues reaches only the
sandbox itself — a decision for Younes, with its own prediction.

---

## The second route (`zeroconf`): prediction, committed before its fix (2026-10-25)

Younes: "fix zeroconf too, prediction first".

**Why not let multicast connects fall through, as loopback now does.** The shim treats a multicast
destination as discovery (`_is_broadcast`: `govee`'s scan goes to 239.255.255.250), which the
mediator serves as a declared, recorded capability. A multicast `connect` that fell through would
send what follows to `lo` with no record — and change how a connected discovery socket behaves. So
relayed sockets stay relayed.

**The fix.** `getsockname()` on a socket the shim has put on a pair answers what the sandbox's only
interface would: `('127.0.0.1', port)` (`('::1', port, 0, 0)` for IPv6), where `port` is the port it
was bound to, else 0. Without the shim that is exactly what the kernel reports in the sandbox for
224.0.0.251, since `route_multicast_to_loopback` sends 224/4 to `lo`. Before, it answered `''`, which
nothing could use. No request changes and nothing new reaches the network.

| | Prediction | Where, criterion |
|---|---|---|
| R1 | New `selftest_udp` case 9 — under the shim, a socket connected to 224.0.0.251 reports `('127.0.0.1', 0)`; Home Assistant's single-target lookup for 224.0.0.251 returns `'127.0.0.1'`; a socket bound to 5353 reports port 5353; the multicast socket is still relayed — **fails before** (9a–9c; 9d passes either way), passes after; case 8 still passes | laptop and Pi |
| R2 | Every suite still passes | Pi, fresh clone |
| R3 | `compat --profile declared --egress`: `zeroconf` sets up for `sonoff` and `xiaomi_home` (it did not in `f65_20261025/post`), and **every component's setup result, for all 37, equals the final rerun's** (which had no shim); every level equals it too | Pi, same clone |
| R4 | `endtoend_egress --subject waste_collection_schedule`: as Q5 — calendar published confined, no source-IP message, the harness's checks all pass | Pi, same clone |

R3's second clause is the strongest statement available: with the shim on, the platform components
each integration needs set up exactly as they did without it. A difference is reported, not
explained away. Outcome appended below.

### Outcome of the second route (appended 2026-10-25, after the runs)

Pi, fresh clone of `f65b-fix` (`3790cb1`), clean before and after, 18:21–18:28. Results:
`experiments/compat/results/f65_20261025/second/`, `verdicts_second.txt`. **Every prediction held.**

- R1: laptop 26/29 before (9a `''`, 9b `None`, 9c `''`), 29/29 after; Pi 29/29.
- R2: 29 of 29 suites exit 0.
- R3: `zeroconf` set up for `sonoff` and `xiaomi_home`; **for all 37, every component's setup result
  and every level equal the final rerun's**, which had no shim.
- R4: calendar published confined; no source-IP message; the harness's checks 16/16.

F65 is closed for the head corpus: with the shim installed as the supervisor installs it, the
platform components set up exactly as without it. Not measured with the shim: the uniform sample of
40, and the other end-to-end subjects (they ran with the shim before either fix, and none of them set
up `http` or `zeroconf`).

---

## The uniform sample of 40, with the shim: prediction, committed before the run (2026-10-25)

Younes: "re-measure the uniform 40 first, prediction first". The second sample
(`~/r2exp/corpus_uniform`) was last measured confined in the final rerun
(`final_20261016/step05_compat/uniform_confined.json`), without the shim. There `http` set up for 8
of the 40 (`alarm_clocks`, `als_sundance_marin`, `browser_mod`, `circuitsetup_energy_analyzer`,
`ha_insights`, `irrigationprogram`, `kroki`, `nuki_otp`) and `zeroconf` for 1; `recorder` (4) and
`logbook` (2) failed, for reasons unrelated to the network; levels 37 `platforms_clean`,
2 `platform_import_failed`, 1 `import_failed`.

Run: `compat --corpus ~/r2exp/corpus_uniform --profile declared --platform-deps … --egress`, from the
existing clean clone of `f65b-fix` on the Pi (the framework has not changed since that tag), (A) down.

| | Prediction | Criterion (`verify/f65_verdicts.py uniform`) |
|---|---|---|
| U1 | `http` sets up for the same 8, and `zeroconf` for the same 1 | `components_setup` |
| U2 | For all 40, every component's setup result equals the final rerun's — the `recorder` and `logbook` failures included | `components_setup`, row by row |
| U3 | Every level equals the final rerun's | `level` |

Not measured: this sample before the fixes (its failure under the unfixed shim is inferred from the
head sample, not shown). A difference is reported, not explained away; the run is not repeated to
obtain a pass. Outcome appended below.
