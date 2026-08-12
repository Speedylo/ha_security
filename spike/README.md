# Shim spike — go/no-go

**Question:** can an unmodified HACS integration run outside Home Assistant's
process, against a fake `homeassistant` package, with every effect crossing a
permission-checked socket?

**Answer: yes.** `andrew-codechimp/HA-Andrews-Arnold-Quota` v2.0.0 sets up,
polls, and publishes two sensor states through the bridge with **zero lines
changed** in the integration. Its source under `target/` is exactly what the
tarball contained.

```bash
./run_spike.sh            # setup + two polls
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
  ├── shim/homeassistant/         fake HA API, ~2.3k lines
  └── target/custom_components/   the untrusted integration, unmodified
fake_aa_api.py                    stub vendor cloud, outside the sandbox
```

Why this target: it is the HA integration-blueprint layout (`__init__` +
`coordinator` + `entity` + `sensor` + config flow), which is the shape most of
the polling-sensor population takes, so what works here generalises.

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

`./shim_coverage.py`, replaying `surface_out/integrations.json`:

- shim exposes **323 importable names**
- **4/30 (13.3%)** polling-sensor integrations import cleanly against it
- median **8** missing symbols among the rest; two are missing exactly one

Import success is an **upper bound** on compatibility — an integration can
import everything and still trip on lifecycle behaviour. The lower bound is the
number actually executed end-to-end, currently one.

Top blockers, and why the number should move fast:

| Missing | Blocks | Cost |
|---|---|---|
| `binary_sensor` platform | 13 | mirror of `sensor`, ~1h |
| `helpers.selector` (Select/Number/…) | 8 | pure data, generatable |
| `helpers:entity_registry` | 12 | needs a supervisor-side registry |
| `config_entries:ConfigFlowResult` | 12 | alias, minutes |
| `util:dt` | 10 | thin wrapper over stdlib |
| `components.diagnostics:async_redact_data` | 7 | ~20 lines |

This is the §5.2 thesis holding up: the tail is mechanical, not hard.

## Fidelity gaps found while building

Recorded because they are report material, not incidentals.

1. **`EntityDescription` frozen-ness.** Real HA uses a `FrozenOrThawed`
   metaclass so a frozen base can be subclassed by a plain `@dataclass`. The
   shim leaves it unfrozen, which accepts both forms but permits mutation HA
   would reject. This target *depends* on the mutable behaviour — it rewrites
   `entity_description.entity_id` in `__init__`.
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

## Not yet built

Filesystem/network isolation (namespaces + seccomp), a real HA backend behind
the supervisor instead of `DEFAULT_HOUSE`, subscription filtering under load,
actuator platforms, and manifest generation rather than hand-authoring.
