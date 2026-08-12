# Code walkthrough — how every script works and why it exists

**Written:** 2026-08-12 · **Covers:** `hacs_api_surface.py` and everything under `spike/`

A mechanical tour of the codebase, in execution order. For *what the results mean*, see
`PROJECT_STATUS.md` §5.2–5.3. For the spike's findings and known gaps, see `spike/README.md`.

---

## The file map

```
~/capstone/
├── hacs_api_surface.py          measurement: what API do real integrations need?
├── surface_out/                 its results (the evidence base)
└── spike/
    ├── run_spike.sh             orchestration
    ├── fake_aa_api.py           stub vendor cloud (outside the sandbox)
    ├── manifest.yaml            the security contract
    ├── supervisor.py            TRUSTED: policy + audit + process spawn
    ├── runner.py                sandbox entrypoint
    ├── probe.py                 adversarial test
    ├── shim_coverage.py         scores the shim against surface_out/
    ├── shim/homeassistant/      the fake HA API (~2.3k lines)
    └── target/custom_components/andrews_arnold_quota/   untrusted, unmodified
```

Two trust zones. `supervisor.py` and everything it holds is trusted. `runner.py`, the whole
shim, and the target are untrusted — they run in a separate OS process and hold no
credentials.

---

## Part 1 — `hacs_api_surface.py`, the evidence base

Predates the spike. Answers the question the whole project rests on: *if I reimplement only
the N most-used pieces of HA's API, how many real integrations run?*

### How it works

Fetches the HACS default catalogue (a JSON array of `owner/repo` strings), downloads each
repo's tarball from `codeload.github.com`, and — the important part — **parses the Python
straight out of the tarball in memory** using `tarfile.extractfile` piped into `ast.parse`.
Nothing is extracted to disk, nothing is imported, nothing is executed. These are ~1900
unreviewed community repos; running any of them would be absurd. See `analyze_tarball()`.

### What it extracts

`_Collector` is an `ast.NodeVisitor` — it walks the parsed syntax tree and fires on node
types:

- `visit_ImportFrom` records `from homeassistant.core import HomeAssistant` as the string
  `homeassistant.core:HomeAssistant`. It skips `node.level > 0`, which is relative imports
  (`from .const import DOMAIN`) — that's the integration's own code, not HA's API.
- `visit_Import` records `import homeassistant.util.dt` as `homeassistant.util.dt:<module>`.
- `visit_FunctionDef` / `visit_AsyncFunctionDef` record every method name defined.

That method-name set powers `classify()`. If an integration defines `async_turn_on` or
`async_unlock`, it *receives commands* — it's an actuator, not a sensor. That's where the 58%
actuator figure comes from, and it is why Decision 3 matters: actuators are the majority and
where the security stakes live.

### The coverage curve

`coverage_curve()` is the key computation:

```python
implemented = set()
for n, sym in enumerate(ranked[:max_budget], start=1):
    implemented.add(sym)
    covered = sum(1 for s in sets if s <= implemented)   # s ⊆ implemented
```

Rank all symbols by popularity, add them one at a time, and after each addition count how
many integrations have their *entire* symbol set contained in what's implemented
(`s <= implemented` is the subset operator on sets). That produces `coverage.csv`: budget
size → integrations fully covered. This single curve justifies every scoping decision
downstream and is the strongest report figure available.

### Limits to carry into the report

Imports are a **lower bound on difficulty** — an integration can import `SensorEntity` and
still depend on behaviour a shim doesn't reproduce. The actuator classifier is heuristic and
probably over-broad. The sample is 200 of ~1900 in catalogue order, so possibly biased; hence
`--limit 0` on the to-do list.

---

## Part 2 — The spike, in execution order

### `run_spike.sh`

Starts `fake_aa_api.py` in the background, polls port 8765 with `connect_ex` until it
accepts, then execs `supervisor.py` with the manifest, the integration path, and the
egress-rewrite rule. A `trap` kills the stub cloud on exit. Passes `"$@"` through so
`--probe` reaches the supervisor.

### `fake_aa_api.py` — the stand-in vendor cloud

A `http.server` handler answering `POST .../quota` with the JSON shape the real Andrews &
Arnold CHAOS API returns:

```json
{"quota": [{"ID": "12345@a.1", "quota_monthly": "1000000000000", "quota_remaining": "532000000000"}]}
```

It exists because the target integration calls a real cloud service we have no credentials
for. Three deliberate details:

- It reads and discards the POST body **without logging it**. Credentials arrive there;
  logging them would be sloppy in a security project.
- `quota_remaining` **decreases by 3 GB per request after the first**. Without that, a second
  poll produces an identical value and you cannot distinguish "the update path works" from
  "nothing happened." This is why the final reading is 526.0 and not 532.0 — three requests
  occur: the setup connection test, the first refresh, and the forced second refresh.
- It serves `Content-Type: application/json`, because aiohttp's `response.json()` rejects
  other content types by default.

### `supervisor.py` — the trusted side

Four responsibilities, kept in one file so the trusted computing base stays readable.

**1. `Manifest`** — loads the YAML and answers permission questions. Every check is `fnmatch`
against a declared pattern list:

```python
def may_publish(self, entity_id):
    return any(fnmatch(entity_id, p) for p in self.publishes)
```

Default-deny falls out for free: `reads_entities: []` means no pattern matches anything, so
every read is refused. One deliberate asymmetry — `may_read()` also returns true for anything
the integration published itself, since being unable to read back your own sensor would be
absurd.

**2. `AuditLog`** — append-only JSONL where each record commits to its predecessor:

```
hash_n = sha256(hash_{n-1} + canonical_json(record_n))
```

`json.dumps(..., sort_keys=True, separators=(",",":"))` gives a canonical serialization, so
the same record always hashes identically. `verify()` replays the chain from the all-zeros
genesis hash and reports the first line where either the stored `prev` doesn't match or the
recomputed hash doesn't match. Editing record 10 invalidates 10 and every record after it.
That property was tested, not assumed — see `spike/README.md`.

**3. `Supervisor.decide()`** — the policy engine. One branch per operation, each returning
`(allowed, reason, payload)`. The interesting cases:

| Op | Control |
|---|---|
| `set_state` | `may_publish`, then stores into `self.house` |
| `get_state` | `may_read`, returns the entity or `None` |
| `list_states` | **never denied, always filtered** — see below |
| `call_service` | `may_call("lock", "unlock")` — the confused-deputy chokepoint |
| `register_service` | refuses any domain that isn't the integration's own, so it can't squat on `lock.unlock` |
| `fire_event` | same idea — must be prefixed with its own domain |
| `net_request` | `may_connect(host)` |

`list_states` is the firehose fix. Real HA's `/api/states` returns everything; here it returns
`[s for s in house if may_read(s)]` and reports `2 visible, 6 withheld`. Denying the call
outright would break integrations that legitimately enumerate; filtering the *result* is the
correct control.

`DEFAULT_HOUSE` is a hardcoded stand-in for a real HA: a lock, an alarm, a camera, a device
tracker, a temperature sensor, a holiday-mode flag. Replacing it with a REST/WebSocket client
against a live HA does not touch `decide()` at all — the policy layer is independent of the
backend, which is the design property to preserve.

**4. Process and transport.** Makes a temp dir, binds a Unix socket at `0o600`,
`subprocess.Popen`s `runner.py` with a scrubbed environment, and accepts connections in a
loop with a 0.5s timeout so it notices when the child exits. Each connection gets a thread
running `handle_connection`, which reads newline-delimited JSON, calls `decide()`, **logs the
decision before replying**, and writes back `{"ok": true, ...}` or
`{"ok": false, "reason": ...}`.

Note what is *not* in the child's environment: any HA token. The whole architecture is that
the credential never crosses the boundary.

### `runner.py` — the sandbox entrypoint

Small, but it does the three things that make the illusion work.

**1. The path shadow.** This is the entire trick:

```python
sys.path.insert(0, str(SHIM_DIR))                       # shim wins over real HA
sys.path.insert(1, str(INTEGRATION_DIR.parent.parent))  # so custom_components.X resolves
```

Python's `import X` searches `sys.path` in order and takes the first hit. Put `spike/shim/`
first and `import homeassistant.core` finds ours — even if real HA is installed. Position 1
is the directory *containing* `custom_components/`, so
`importlib.import_module("custom_components.andrews_arnold_quota")` resolves. No `__init__.py`
is needed there; Python 3 implicit namespace packages handle it.

**2. The ContextVar.** The subtle one:

```python
current_entry.set(entry)
```

Real HA sets a context variable while a config entry is being set up, so helpers constructed
during setup can find their own entry without being handed it. The target's `entity.py` does
`coordinator.config_entry.entry_id` having **never assigned `config_entry`**. Without
reproducing this, the integration imports perfectly and then crashes at runtime. Concrete
proof that import counts cannot predict compatibility.

**3. Lifecycle emulation.** Calls `async_setup(hass, {})`, then `async_setup_entry(hass, entry)`,
then `async_block_till_done()`, then forces a second `coordinator.async_refresh()`, optionally
runs the probe, then `async_unload_entry` and `coordinator.async_shutdown()`. That sequence is
HA's own integration lifecycle. It also loads `translations/en.json` into the shim so friendly
names render as HA would.

### The shim, module by module

**`_bridge.py`** — the socket client. `request(op, **payload)` sends one JSON line under a
`threading.Lock`, blocks on `readline()`, and raises `PermissionDenied` if the reply says
`ok: false`. Turning a denial into a Python exception is what makes enforcement feel native:
the integration sees an exception where HA would have silently complied.

**`core.py`** — the `hass` object. `HomeAssistant` composes four facades:

| Facade | Real HA | Shim |
|---|---|---|
| `hass.states` | direct dict access to every entity | `set_state` / `get_state` / `list_states` messages |
| `hass.services` | direct call into any registered service | `call_service` message |
| `hass.bus` | subscribe to every event in the house | `subscribe_events` message |
| `hass.config` | `.path()` reaches `/config/secrets.yaml` | resolves inside the sandbox dir only |

Plus `async_create_task`, `async_add_executor_job` and `async_block_till_done` — the task
plumbing integrations use. `callback` is just a decorator that tags a function; on real HA it
is a scheduling hint rather than a wrapper, so tagging is faithful.

**`const.py`** — 235 lines of pure data: `Platform`, `EntityCategory`, unit enums, `CONF_*`
keys, state strings. This is the file that should eventually be *generated* from HA's source.
It is a large share of the long tail in `symbols.csv` and it is why that tail is cheap.

**`config_entries.py`** — `ConfigEntry` (stored configuration), `ConfigEntries` (the
`hass.config_entries` manager), `ConfigFlow` (setup-wizard base class), and `current_entry`.
The load-bearing method is `async_forward_entry_setups`:

```python
module = importlib.import_module(f"custom_components.{entry.domain}.{platform}")
entity_platform = EntityPlatform(self._hass, entry.domain, str(platform))
await module.async_setup_entry(self._hass, entry, entity_platform.async_add_entities)
```

That is how `sensor.py` gets loaded and handed its `async_add_entities` callback.
`ConfigFlow.__init_subclass__` accepts the `domain=DOMAIN` keyword integrations put in their
class definition — miss it and the module fails at import.

**`helpers/entity.py`** — the `Entity` base class and the `_attr_*` convention (HA lets you
either override a property or set `_attr_name`; both must work). The critical method is
`async_write_ha_state()`, where an entity leaves the sandbox:

```python
if not self.available:      state = "unavailable"
elif self.state is None:    state = "unknown"
attributes = self._build_attributes()   # friendly_name, unit, icon, device_class, attribution
self.hass.states.async_set(self.entity_id, state, attributes)
```

`EntityDescription` is a `@dataclass(kw_only=True)` here. Real HA uses a `FrozenOrThawed`
metaclass so a frozen base can be subclassed by a plain `@dataclass`; ours is simply unfrozen.
That accepts both forms but permits mutation HA would reject — and the target *depends* on the
mutable behaviour, rewriting `entity_description.entity_id` in its constructor. Fidelity
gap #1.

**`helpers/entity_platform.py`** — `async_add_entities` is sync (as on real HA) and schedules
the real work as a task. That task sets `entity.hass`, generates an `entity_id` if the
integration didn't set one, awaits `async_added_to_hass()`, then calls
`async_write_ha_state()` — which produces the *initial* state write.

**`helpers/update_coordinator.py`** — the highest-value file, since `DataUpdateCoordinator`
appeared in 100% of the polling-sensor sample. It reproduces:

- the **listener protocol**: `async_add_listener` returns an unsubscribe callable, and
  registering the first listener starts the refresh timer
- `_async_refresh` with HA's exception ladder: `ConfigEntryAuthFailed` → reauth,
  `UpdateFailed` → logged failure, anything else → caught broadly (HA is equally broad)
- the `async_config_entry_first_refresh` **contract**: a failure raises `ConfigEntryNotReady`
  so setup aborts and HA retries later, rather than leaving a half-configured integration
- `self.config_entry` populated from the ContextVar

`CoordinatorEntity` subscribes in `async_added_to_hass`, and its `_handle_coordinator_update`
calls `async_write_ha_state`. That is the fan-out: one poll updates every entity.

**`helpers/aiohttp_client.py`** — `async_get_clientsession` on real HA hands back an
unrestricted HTTP session; that is the exfiltration route. `MediatedClientSession` wraps
aiohttp and puts `_authorise(url)` in front of every verb:

```python
def request(self, method, url, **kw):
    return self._session.request(method, self._authorise(url), **kw)
```

`_authorise` parses the host, calls the bridge, and **only then** applies the test rewrite. So
the manifest is always checked against the host the author declared, never the redirected one
— the harness cannot accidentally launder a denial into an allow. Returning aiohttp's own
`_RequestContextManager` unchanged is what keeps both `await session.request(...)` and
`async with session.request(...)` working; the target uses the first form.

Two known gaps live here: redirects are not re-checked per hop, and `__getattr__` falls
through to the raw aiohttp session, so any traffic-initiating attribute not explicitly wrapped
would escape.

**`components/sensor/__init__.py`** — `SensorEntity` with the contract integrations actually
rely on: they implement `native_value`, never `state`, and `state` derives from it. Plus
`SensorDeviceClass` / `SensorStateClass`, which are pure data.

### `probe.py`

Runs *after* successful setup, in the same process, over the same manifest and bridge. Five
attempts, each a single line a real author could add. Returns `(name, blocked, detail)` tuples
so results are tabulated rather than narrated.

The design point is check #2. It does not just assert the call was denied — it inspects what
came back and counts entities not belonging to this integration:

```python
leaked = [s.entity_id for s in states if not s.entity_id.startswith("sensor.andrews_arnold")]
results.append(("enumerate whole house", not leaked, ...))
```

An *allowed but empty* result is the correct behaviour, so testing for a denial would have
been the wrong test.

Check #5 reads a host file, expects to succeed, and reports it as `ALLOWED`. A test suite that
only contains tests you pass is marketing, not evaluation.

### `shim_coverage.py`

Closes the loop between the spike and the measurement tool. It `pkgutil.walk_packages` over
the shim, imports each module, and collects `dir(module)` into a set of `module:name` strings
— the *same* format `hacs_api_surface.py` emits. Then it replays `integrations.json` and
computes, per integration, `[s for s in symbols if s not in provided]`.

Dynamic import rather than static parsing, deliberately: it catches inherited and re-exported
names (like `DeviceInfo` re-exported from `device_registry`) that an AST pass would miss.

Its output — 4/30 clean, median 8 missing, ranked blockers — is a **work queue sorted by
value**. `binary_sensor` blocks 13 integrations and is a near-copy of `sensor`.

---

## Part 3 — One value, end to end

`526.0 GB` making the entire trip. The whole architecture in one path:

1. `runner.py` calls `coordinator.async_refresh()`
2. shim `_async_refresh` calls the target's own `_async_update_data` (**unmodified code**)
3. target calls `self.client.query("quota")` →
   `session.request(method="post", url="https://chaos2.aa.net.uk/broadband/quota", data=params)`
4. `MediatedClientSession.request` → `_authorise()` →
   `bridge.request("net_request", host="chaos2.aa.net.uk")`
5. → socket → `Supervisor.decide()` → `manifest.may_connect()` → **ALLOW**, logged with a
   chain hash
6. *now* the rewrite applies → aiohttp hits `127.0.0.1:8765` → stub returns
   `quota_remaining: "526000000000"`
7. coordinator stores `self.data`, calls `async_update_listeners()`
8. each `CoordinatorEntity._handle_coordinator_update()` → `async_write_ha_state()`
9. `SensorEntity.state` → the target's own `native_value` →
   `round(int(...)/1000000000, 1)` = **526.0**
10. `Entity._build_attributes()` adds `friendly_name` (from the integration's translations),
    `unit_of_measurement: GB`, `icon`, `attribution`
11. `hass.states.async_set(...)` → `bridge.request("set_state", ...)`
12. → socket → `may_publish("sensor.andrews_arnold_12345_a_1_quota_remaining")` vs
    `sensor.andrews_arnold_*` → **ALLOW**, logged
13. supervisor stores it; the trace line prints

Steps 3, 9 and the rounding are the integration's own untouched code. Everything else is shim
or supervisor. At no point does the integration hold a credential or touch anything it did not
declare.

---

## Part 4 — How this maps to the capstone

| Piece | Report role |
|---|---|
| `hacs_api_surface.py` + `surface_out/` | Empirical contribution — the API-surface measurement nobody has published |
| `shim/homeassistant/` | Original contribution #1 — the compatibility layer |
| `supervisor.py` `decide()` + `manifest.yaml` | Original contribution #2 — manifest-based permission enforcement |
| `AuditLog` | The auditor-facing control: tamper-evident decision trail |
| `probe.py` | Evaluation axis 2 (Security) — pass/fail scenarios, not a demo |
| `shim_coverage.py` | Evaluation axes 1 and 4 (Compatibility, Coverage) |
| *not yet built* | Evaluation axis 3 (Performance) — needs the Pi |

The trust boundary in the threat model is one line: **the Unix socket**. Everything above it
is trusted and small enough to review; everything below is assumed hostile. The shim living on
the hostile side is exactly why every check is duplicated in the supervisor — the shim's own
checks are ergonomics. Saying so plainly in the threat model earns credit with an auditor
rather than losing it.
