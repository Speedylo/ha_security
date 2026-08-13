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
./run_targets.sh          # all three, end to end
./run_targets.sh matomo   # just one
./run_spike.sh            # andrews_arnold only: setup + two polls
./run_spike.sh --probe    # the above, then the adversarial probe
./shim_coverage.py        # score the shim against the 200-repo dataset
./supervisor.py --verify audit/<run>.jsonl
```

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

Five things a malicious version of this integration would try. Each is one line
an author could add, and on stock HA every one of them succeeds today.

| Attempt | Spike | Enforced by |
|---|---|---|
| Read `lock.front_door` (undeclared) | **blocked** | `reads_entities` |
| Enumerate the whole house (`/api/states` firehose) | **blocked** — 2 of 8 entities returned, 6 withheld | read filtering |
| Call `lock.unlock` (confused deputy) | **blocked** | `calls_services` |
| Exfiltrate to `collector.exfil-example.net` | **blocked** | `network` allowlist |
| Read a host file directly | **ALLOWED** | nothing yet — see below |

The last row is the honest one. The spike has process separation and a mediated
API; it has **no filesystem isolation**, so `open("/etc/passwd")` succeeds. That
is the namespaces + seccomp work, and until it lands the framework does not stop
the 2021 HACS file-theft pattern. Nothing else in the table depends on it.

The audit log is hash-chained. Flipping the `lock.unlock` denial to an allow in
a copy of the log is detected: `BROKEN: line 10: record altered (hash mismatch)`.

## Coverage against the 200-repo dataset

`./shim_coverage.py`, replaying `surface_out/integrations.json` — now the **full catalogue**
(3105 repos, 3075 parsed, 763 polling sensors), not the 200-repo sample:

| | import cleanly | median missing among the rest |
|---|---|---|
| full catalogue, constants included (n=763) | **72/763 (9.4%)** | **6** |
| 200-repo sample, `--exclude-trivial` (n=30) | 6/30 (20.0%), was 4/30 | 8 |

- shim exposes **350 importable names** (was 323)
- **3 integrations executed end-to-end** (was 1)

The full-catalogue percentage is lower for two reasons at once: it counts the constants
`--exclude-trivial` hid, and it draws on a population that is not alphabetically clustered.
**72 integrations importing cleanly** is the honest absolute number, and the median
non-clean integration is **6** symbols away.

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

Ranked on the full 763-integration population, which reorders the queue against
what the 30-integration sample suggested:

| Missing | Blocks | Cost | Status |
|---|---|---|---|
| `util:dt` | **257** | thin wrapper over stdlib | open |
| `binary_sensor:BinarySensorEntity` | **229** | mirror of `sensor`, ~1h | open |
| `helpers:entity_registry` | **163** | needs a supervisor-side registry | open |
| `binary_sensor:BinarySensorDeviceClass` | **150** | pure data | open |
| `helpers:selector` + the `Select*`/`Text`/`Number` family | **129 / 109 / 107 / 86 / 75 / 68** | pure data, generatable | open |
| `helpers.storage:Store` | **105** | absent from the sample's top list | open |
| `config_entries:ConfigFlowResult` | — | alias, minutes | **done** |
| `components.diagnostics:async_redact_data` | — | ~20 lines | **done** |

This is the §5.2 thesis holding up: the tail is mechanical, not hard — `util.dt`,
`selector` and the `binary_sensor` enums now sit at the top of the queue and are
all generatable or near-copies. The two marked done cost well under an hour
between them and moved the sample figure from 13.3% to 20.0%.

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

Filesystem/network isolation (namespaces + seccomp), a real HA backend behind
the supervisor instead of `DEFAULT_HOUSE`, subscription filtering under load,
actuator platforms, and manifest generation rather than hand-authoring.
