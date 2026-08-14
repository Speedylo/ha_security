# Shim spike — go/no-go

**Question:** can an unmodified HACS integration run outside Home Assistant's
process, against a fake `homeassistant` package, with every effect crossing a
permission-checked socket?

**Answer: yes — for three of them now.** Each sets up, polls twice and publishes
its sensor states through the bridge with **zero lines changed**. Every target's
source is exactly what its tarball contained.

| Target | Publishes | Mediated ops | Why this one |
|---|---|---|---|
| `andrew-codechimp/HA-Andrews-Arnold-Quota` v2.0.0 | 2 sensors | 7 | the integration-blueprint layout, the commonest polling-sensor shape |
| `abnvle/ha-matomo` | 15 sensors | 44 | frozen entity descriptions; many entities off one coordinator |
| `aniolpages/ha-icqa` | 8 sensors | 18 | public credential-free endpoint; `runtime_data`; nested payload parsing |

```bash
./run_targets.sh              # all three, end to end, against the stub house
./run_targets.sh matomo       # just one
PROBE=1 ISOLATE=1 ./run_targets.sh   # ...isolated, with the adversarial probe
./run_spike.sh                # andrews_arnold only: setup + two polls
./run_spike.sh --probe        # the above, then the adversarial probe
./run_spike.sh --probe --isolate   # ...with full isolation (8 of 8 blocked)
ISOLATE=1 ./run_targets.sh    # all three, each in its own namespaces
python3 syscall_filter.py     # self-test: load the filter, prove ptrace is denied
./generate_shim.py            # regenerate const.py + selector.py from HA's source
./generate_shim.py --check    # report what would change, write nothing
./shim_coverage.py            # score the shim against the full catalogue
./shim_coverage.py --installs # ...and weight it by real installed base
./supervisor.py --verify audit/<run>.jsonl
./test_matrix.sh              # full matrix with assertions (15; 24 with HA=1)
HA=1 ./test_matrix.sh         # ...including real HA and the bridge
./test_egress.py              # 17 egress policy cases
./test_audit.py               # hash chain: what it proves, and what it does not
```

### Against a real, unmodified Home Assistant

```bash
./ha_docker.sh up             # stock 2026.8.1 image — no patches, no custom components
./ha_onboard.py               # headless onboarding, mints a long-lived token
./ha_seed.py                  # give it locks, a camera, a device tracker
HA=1 ./run_targets.sh         # publish into the real instance
./ha_docker.sh down           # stop it
```

The supervisor reaches HA only through the REST API it already exposes to any
token holder. Nothing about Home Assistant is modified, which is the point: the
framework is a **retrofit**, not a proposal to redesign HA.

### How framework entities differ from native ones

```bash
./ha_compare_setup.sh              # same integration, loaded both ways at once
./registry_gap.py --restart-test
```

Installs `matomo` into HA's own `custom_components` *and* runs it through the
framework, then diffs what HA thinks of the two sets of entities:

| | native | framework, raw REST | framework, via bridge |
|---|---|---|---|
| entity-registry row | 4/10 set, 6 available | **none** | **4/10 set, 6 available** |
| config entries | 1 | **0** | **1** |
| devices | 1 | **0** | **1** per integration |
| **survives an HA restart** | 15/15 | **0/15** | **15/15** |

State-level presentation (`unit_of_measurement`, `state_class`, `device_class`,
`icon`) arrives intact in both modes.

### `sandbox_bridge` — closing that gap

```bash
./ha_bridge_setup.sh              # install the bridge, restart HA, configure it
HA=1 BRIDGE=1 ./run_targets.sh    # publish through it instead of raw states
```

A ~250-line **trusted** native integration in `bridge_integration/sandbox_bridge/`.
It owns a config entry, creates one device per sandboxed integration, and exposes
`sandbox_bridge.publish` for the supervisor to call. Entities are `RestoreEntity`
subclasses with a `unique_id`, and the roster is persisted with `Store`, so they
come back after a restart with their last values — verified with the supervisor
deliberately *not* re-run.

It loads no untrusted code: the sandboxed integrations still run in their own
process behind the manifest checks, and the bridge only ever receives a domain, a
key, an entity_id, a state string and an attribute dict, none of which it
evaluates. Being small is the point — it is the trusted half, so it has to be
reviewable.

`platform` reads `sandbox_bridge` rather than the integration's own domain. That
is accurate rather than a shortfall, and it makes the sandboxing visible in the
UI instead of hiding it.

Requires `../.venv` (aiohttp, voluptuous, awesomeversion, pyyaml).

## What runs

```
supervisor.py                     trusted; holds the manifest and the (future) HA token
  │  Unix socket, JSON lines
runner.py                         sandbox entrypoint; puts shim/ first on sys.path
  ├── shim/homeassistant/         fake HA API, ~2.5k lines
  ├── target/custom_components/   andrews_arnold_quota, unmodified
  └── targets/<name>/custom_components/   matomo, icqa — also unmodified
manifest.yaml, manifests/<name>.yaml     one security contract per integration
fake_aa_api.py, fake_matomo_api.py, fake_icqa_api.py
                                  stub vendor clouds, outside the sandbox
```

The supervisor and runner are target-agnostic: adding an integration is a
directory, a manifest and a stub, with no change to the enforcement path.

## Result of the run

```
[ALLOW] net_request  chaos2.aa.net.uk            network allowlist matches
[ALLOW] set_state    sensor.andrews_arnold_12345_a_1_monthly_quota
[ALLOW] set_state    sensor.andrews_arnold_12345_a_1_quota_remaining
sensor.andrews_arnold_12345_a_1_monthly_quota   = 1000.0 GB
sensor.andrews_arnold_12345_a_1_quota_remaining = 526.0 GB
audit chain: OK — chain intact (7 records)
```

Two polls, a state change between them, friendly names resolved from the
integration's own `translations/en.json`.

`./run_targets.sh` runs all three in sequence: **69 mediated operations, 0
denied, every audit chain intact**. Each stub moves its numbers between the two
polls, so the second refresh is visibly a refresh and not a replay — quota
drains, Matomo's day counters climb, ICQA's NO₂ rises from 28,3 to 41,7 µg/m³
(parsed through the Catalan decimal comma the real endpoint publishes).

## Adversarial probe

Eight things a malicious version of this integration would try. Each is one line
an author could add, and on stock HA every one of them succeeds today.

| Attempt | Stub house | **Real HA** | `--isolate` | Enforced by |
|---|---|---|---|---|
| Read `lock.front_door` (undeclared) | blocked | **blocked** | blocked | `reads_entities` |
| Enumerate the whole house (`/api/states` firehose) | 2 of 8 returned | **2 visible, 41 withheld** | same | read filtering |
| Call `lock.unlock` (confused deputy) | blocked | **blocked** | blocked | `calls_services` |
| Exfiltrate to `collector.exfil-example.net` | blocked | **blocked** | blocked | `network` allowlist |
| Read a host file directly | ALLOWED | **ALLOWED** | **blocked** | mount namespace |
| Read the supervisor's `/proc` (steal the token) | ALLOWED | **ALLOWED** | **blocked** | PID namespace |
| Raw socket → undeclared **LAN device** (lateral movement) | ALLOWED | **ALLOWED** | **blocked** | seccomp + brokered egress |
| Raw socket → undeclared internet host (exfiltration) | ALLOWED | **ALLOWED** | **blocked** | seccomp + brokered egress |

**4 of 8 without isolation, 8 of 8 with it.** Each of the last four checks was
written while it still failed, so every before/after is a measurement rather
than an assertion. See `../FINDINGS_2026-08-14_token_leak.md` and
`../RESULTS_2026-08-14_egress_broker.md`.

**Paired baseline**, same token used the way an in-process integration uses `hass` today:

| | baseline HA | under the framework |
|---|---|---|
| `lock.front_door` | readable (`'locked'`) | **denied** |
| entities enumerable | **43** | **2** |
| privacy-relevant entities exposed | 5 | **0** |

**The last row is now the honest one**, and it is a different row than it used
to be. Filesystem isolation landed on 2026-08-14 (`isolate.py`,
`syscall_filter.py`), so `open("/etc/passwd")` fails under `--isolate` and the
2021 HACS file-theft pattern *is* stopped. What remains open is **raw-socket
egress**: the `network:` allowlist is checked in `aiohttp_client`, which asks the
supervisor and then lets the *sandbox* make the connection, so a raw socket never
consults it. A network namespace alone would also cut the legitimate vendor poll,
so closing this needs an egress proxy on the supervisor side.
`HACS_DENY_INET=1 ./run_spike.sh --isolate` shows the enforcement half already
works: `socket(AF_UNIX)` is permitted, `AF_INET` is denied, and the integration
correctly fails to reach its cloud.

The audit log is hash-chained. Flipping the `lock.unlock` denial to an allow in
a copy of the log is detected: `BROKEN: line 10: record altered (hash mismatch)`.

## Coverage against the 200-repo dataset

`./shim_coverage.py`, replaying `surface_out/integrations.json` — now the **full catalogue**
(3105 repos, 3075 parsed, 763 polling sensors), not the 200-repo sample:

| | import cleanly | median missing among the rest |
|---|---|---|
| polling sensors (n=763) | **94/763 (12.3%)** | **4** |
| all patterns (n=3075) | **141/3075 (4.6%)** | 9 |

- shim exposes **814 importable names** (was 323, then 350 before the generator)
- **3 integrations executed end-to-end** (was 1)
- **1.2% of the real installed base** — `./shim_coverage.py --pattern all --installs`

That last row is the one that answers "how much of the real world does this run". Counting
repositories treats a 43,601-install integration and a 3-install one identically; Home
Assistant publishes per-domain install counts, so there is no need to. Of the 100
most-installed integrations, **1** imports cleanly, with a median of 22 symbols missing.

Run it under `../.venv/bin/python`, not the system interpreter. Without
`aiohttp` importable, two shim modules fail to load and the scorer silently
reports 180 names and 0/30 — the warnings go to stderr while the headline
numbers still print confidently. Worth hardening before these numbers are
quoted anywhere.

### Two corrections to how this number should be read

**1. `--exclude-trivial` makes it optimistic.** The 200-repo dataset was
generated with that flag, which drops `homeassistant.const`,
`homeassistant.exceptions`, `homeassistant.helpers.typing` and
`homeassistant.util.dt` from every integration's recorded symbol set. Those
symbols still have to exist for the import to succeed. `ha-icqa` was recorded as
missing exactly one symbol, and on first run failed on
`CONCENTRATION_MICROGRAMS_PER_CUBIC_METER` — a constant the dataset never
counted. So the measured gap understates the real one, though only by symbols
that are cheap and machine-generatable.

**2. Import-cleanliness is not an upper bound on compatibility.** The earlier
claim here was that it was. `ha-matomo` disproves it: it runs end-to-end while
still counting as one symbol short, because the missing name
(`ConfigFlowResult`) lives in `config_flow.py`, a module HA loads only when a
user adds the integration through the UI and which never executes during normal
operation. The metric therefore errs in **both** directions — it over-counts
integrations that import fine and then die on lifecycle behaviour, and
under-counts ones whose missing symbols sit on code paths that never run. It is
a cheap proxy, not a bound. The evaluation chapter should report executed
integrations as the real compatibility measure and use import counts only to
rank what to build next.

Top blockers, and why the number should move fast:

Ranked by how many of the **100 most-installed** integrations each blocks — i.e.
weighted by real-world use rather than by repository count:

| Missing | Blocks (of top 100) | Generatable? |
|---|---|---|
| `binary_sensor:BinarySensorEntity` | 50 | no — platform |
| `helpers:entity_registry` | 50 | no — stateful |
| `switch:SwitchEntity` | 49 | no — **actuator** platform |
| `button:ButtonEntity` | 41 | no — **actuator** platform |
| `util:dt` | 41 | thin stdlib wrapper |
| `select:SelectEntity` | 36 | no — **actuator** platform |
| `number:NumberEntity` | 33 | no — **actuator** platform |
| `restore_state:RestoreEntity` | 30 | no — stateful |
| `helpers.selector` (whole family) | — | **generated** |
| `const` (units, enums, keys) | — | **generated** |
| `config_entries:ConfigFlowResult` | — | done |
| `components.diagnostics:async_redact_data` | — | done |

**This qualifies the "the tail is generatable" thesis rather than confirming it.**
The thesis is true — `generate_shim.py` produced 469 constants and 93 selector
classes in an afternoon, and regenerates them free every HA release. But that
tail turned out to be a *smaller share of the problem than assumed*: clearing
every constant and selector moved import-cleanliness from 9.4% to 12.3%. What
actually blocks integrations is **behavioural** — entity platforms and stateful
helpers — and among the most-installed integrations those platforms are mostly
**actuator** platforms.

## Fidelity gaps found while building

Recorded because they are report material, not incidentals.

1. **`EntityDescription` frozen-ness — FIXED, and the fix is the most
   interesting result of adding a second integration.** Real HA uses a
   `FrozenOrThawed` metaclass so one description base can be subclassed by
   *either* a frozen or a plain `@dataclass`; Python forbids doing that
   directly. The shim originally just left the base unfrozen, which was enough
   for one target and looked like a harmless simplification.

   It is not, and two integrations prove it. `andrews_arnold_quota` declares a
   plain `@dataclass` and **mutates** `entity_description.entity_id` after
   construction; `matomo` declares `@dataclass(frozen=True, kw_only=True)`. An
   unfrozen base runs the first and raises `TypeError: cannot inherit frozen
   dataclass from a non-frozen one` on the second; a frozen base does the
   reverse. **No single choice runs both** — only reproducing HA's mechanism
   does. Implemented in `shim/homeassistant/util/frozen_dataclass_compat.py`
   (upstream's version needs `annotationlib` from Python 3.14; this one reads
   `__annotations__` directly and runs on 3.12).

   Worth the report's attention because it is a gap a one-integration spike
   *cannot* surface: with n=1 the simplification is invisible, and it is only
   the second sample that turns it into a contradiction. The same argument
   applies to every remaining fidelity shortcut in the shim.
2. **`config_entries.current_entry`.** Integrations read
   `coordinator.config_entry` having never assigned it; HA populates it from a
   ContextVar set during setup. Missing this breaks the blueprint layout at
   `entity.py`, not at import. Exactly the class of failure import counts cannot
   predict.
3. **Redirects escape the egress check.** Only the initial URL is authorised.
   A declared host answering with a 302 to an undeclared one would be followed.
   Fix: `allow_redirects=False` and a check per hop.
4. **Blocking bridge calls.** The shim's socket I/O blocks the event loop. Fine
   at spike scale, wrong for the real thing.
5. **Sandbox-side code is not a security boundary.** The shim runs inside the
   sandbox and the integration can rewrite or bypass it. Every check that
   matters is duplicated in the supervisor; the shim's checks are ergonomics.

## Adding a fourth target

1. `tar xzf ../.hacs_cache/<owner>__<repo>.tar.gz` into `targets/<name>/` —
   never edit what comes out.
2. Write `manifests/<name>.yaml`: the entities it may publish, what it may read,
   which services it may call, which hosts it may reach.
3. Stub its vendor cloud in `fake_<name>_api.py`, moving at least one value
   between polls so a refresh is distinguishable from a replay.
4. Add a row to `TARGETS` in `run_targets.sh`.

Whatever the shim is missing surfaces as an `ImportError` on the first run and
an `AttributeError` or a lifecycle failure on the second. Both are the point.

## Not yet built

**cgroups**, so resource exhaustion is bounded — a malicious integration can
still fork-bomb or exhaust RAM. **WebSocket brokering**: `ws_connect` raises
rather than falling through to a real socket, so an integration needing
WebSockets does not run here today. Subscription filtering under load, actuator
platforms, and manifest generation rather than hand-authoring.

*Since removed from this list:* filesystem and process isolation (built
2026-08-14), network egress (built 2026-08-14 — the supervisor performs all HTTP
and the allowlist is now enforcing), and the real HA backend (built 2026-08-13;
`DEFAULT_HOUSE` is gone).
