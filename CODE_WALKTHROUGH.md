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
    ├── run_spike.sh             orchestration: andrews_arnold + the probe
    ├── run_targets.sh           runs all three integrations end to end
    ├── fake_aa_api.py           stub vendor cloud (outside the sandbox)
    ├── fake_matomo_api.py       ditto, for matomo
    ├── fake_icqa_api.py         ditto, for icqa
    ├── manifest.yaml            the security contract (andrews_arnold)
    ├── manifests/<name>.yaml    one contract per additional integration
    ├── supervisor.py            TRUSTED: policy + audit + process spawn
    ├── ha_backend.py            what sits behind it: stub house, or real HA over REST
    ├── ha_docker.sh             run a stock, unmodified HA in Docker
    ├── ha_onboard.py            headless onboarding + long-lived token
    ├── ha_seed.py               give the real HA a house worth protecting
    ├── ha_compare_setup.sh      load one integration natively AND via the framework
    ├── ha_bridge_setup.sh       install + configure the bridge inside HA
    ├── registry_gap.py          diff what HA thinks of the two sets of entities
    ├── bridge_integration/      TRUSTED: the native integration that owns entities
    ├── runner.py                sandbox entrypoint
    ├── isolate.py               TRUSTED: builds the namespaces + allowlisted root
    ├── syscall_filter.py        TRUSTED: the seccomp policy
    ├── probe.py                 adversarial test
    ├── test_matrix.sh           full matrix with assertions (15, or 24 with HA=1)
    ├── test_egress.py           egress policy + destination cases (35)
    ├── test_audit.py            hash chain: what it proves and what it does not
    ├── generate_shim.py         generates const.py + selector.py from HA's source
    ├── shim_coverage.py         scores the shim against surface_out/ (± install weighting)
    ├── shim/homeassistant/      the fake HA API (~2.5k lines)
    ├── target/custom_components/andrews_arnold_quota/   untrusted, unmodified
    └── targets/<name>/custom_components/<name>/         ditto: matomo, icqa
```

Two trust zones. `supervisor.py` and everything it holds is trusted. `runner.py`, the whole
shim, and the target are untrusted — they run in a separate OS process and hold no
credentials.

`isolate.py` sits on the boundary and is worth understanding as a *transition*: it starts
trusted (it is the supervisor's code, doing the mounts) and ends untrusted (it `exec`s the
runner, which is the integration's world). Everything it does happens before that `exec`, and
the seccomp filter it installs last is what it hands forward across the line.

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

### `ha_backend.py` — stub house or real Home Assistant

Two implementations of one interface (`get`/`all`/`set`/`remove`/`call_service`). `StubHouse`
is the in-memory dict the spike started with; `RestHouse` is a real HA reached over its public
REST API with a bearer token.

The important property is what *doesn't* change when you swap them: `supervisor.py`'s
`decide()` is identical either way, and every manifest check runs **before** the backend is
touched. That is why the adversarial probe can be reported for both backends in the same table
— the policy under test is provably the same code.

It is also the project's central claim in executable form. `RestHouse` talks to a stock
Home Assistant through an API that already exists for any token holder, so the framework is a
retrofit rather than a request that HA be redesigned. The supervisor holds the token; the
sandboxed integration never sees it and has no route to HA except the bridge — which is what
turns the confused-deputy attack into a policy question instead of a network one.

### `bridge_integration/sandbox_bridge/` — the trusted native half

The only part of the framework that runs *inside* Home Assistant, and the answer to the
measurement in `registry_gap.py`: publishing over `/api/states` produces states with no
identity — no registry row, no config entry, no device, and nothing that survives a restart.

It owns a config entry, creates one device per sandboxed integration, and exposes a service
`sandbox_bridge.publish` that the supervisor calls in place of posting a state. Entities are
`RestoreEntity` subclasses carrying a `unique_id`, which is what earns them a registry row; the
roster is persisted with `helpers.storage.Store`, so `async_setup_entry` recreates every entity
on startup and each restores its last value.

The trust argument matters more than the code. This component is **trusted and belongs to the
framework**, not to any integration it publishes for. It loads, imports and executes nothing
from a sandboxed integration — it receives a domain, a key, an entity_id, a state string and a
dict of attributes, and evaluates none of them. At ~250 lines it is small enough to review by
hand, which is the property a trusted component has to have.

`platform` on the resulting entities reads `sandbox_bridge` rather than the integration's own
domain. That is accurate — the bridge is what created them — and it makes the sandboxing
visible to the user rather than hiding it.

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

`EntityDescription` is deliberately **not** a dataclass. It carries
`metaclass=FrozenOrThawed, frozen_or_thawed=True`, exactly as real HA does, because the three
targets need mutually exclusive things from it: `andrews_arnold_quota` subclasses it with a
plain `@dataclass` and rewrites `entity_description.entity_id` in its constructor, while
`matomo` subclasses it with `@dataclass(frozen=True, kw_only=True)`. Python refuses to let a
frozen dataclass inherit from a non-frozen one or the reverse, so an unfrozen base runs the
first and raises `TypeError` on the second. See `util/frozen_dataclass_compat.py` below.

**`util/frozen_dataclass_compat.py`** — the metaclass that squares that circle. A class marked
`frozen_or_thawed=True` is never made a dataclass itself; instead it builds a parallel frozen
dataclass in `cls._dataclass` and delegates construction to it via `__new__`. Because the class
is not a dataclass, `@dataclass` on a subclass sees no dataclass base, so neither the frozen nor
the unfrozen form conflicts; the subclass picks up inherited fields through annotations the
metaclass injects. Upstream's version reads annotations with `annotationlib` (Python 3.14+);
this one reads `__annotations__` directly so it runs on 3.12.

**`components/diagnostics/__init__.py`** — just `async_redact_data`, which masks named keys
recursively before an integration hands a payload to HA's diagnostics download. Pure data
manipulation with no HA state involved, so the shim's version and the real one are the same
function. Seven of the thirty sampled polling sensors import it.

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

### `isolate.py` — building the box

Runs *inside* the namespaces created by `unshare`, before the runner starts. Three jobs, in
order, and the order is load-bearing:

1. **Scratch filesystems first.** A `tmpfs` on `/tmp` and `/run`. This must precede the
   allowlist, because the bridge socket lives in a `mkdtemp` under `/tmp` — mounting a fresh
   `tmpfs` over `/tmp` afterwards would shadow it and cut the sandbox off from the supervisor.
   This was a real bug, found by the sandbox silently failing to start.
2. **The allowlist.** `allowlist()` returns the host paths the sandbox may see, each bind-mounted
   in and then remounted read-only. The list is deliberately short: `/usr` (interpreter, stdlib,
   TLS certificates), the virtualenv if there is one, `runner.py`, `probe.py`, `shim/`, the
   integration, `resolv.conf`, and `ld.so.cache`. **Not** `supervisor.py`, and **not** `audit/` —
   which is what stops the sandbox rewriting its own decision log.
3. **`pivot_root`, then a private `/proc`.** After the pivot, everything not on the list ceases
   to exist. The fresh `/proc` is what removes `/proc/<supervisor>/environ` and `/cmdline`, the
   two credential-leak routes that cannot be closed from inside `supervisor.py`.

The allowlist mirrors the manifest on purpose: *declare what you need, get that and nothing
else.* A blocklist ("hide `/home`, hide `secrets.yaml`") would be weaker and would need editing
every time the host layout changed; an allowlist fails closed.

**Difficulty note for the defence.** `allowlist()` is ordinary Python — a list of paths with a
comment justifying each, and you should be able to read every line. The mount plumbing is not:
it calls `mount(2)` and `pivot_root(2)` through `ctypes` with kernel flag constants, and carries
a per-architecture syscall number because `pivot_root` has no glibc wrapper. Each line is
explainable ("bind this in, then remount it read-only"), but this is the advanced part of the
file and most developers would need the man pages to write it.

### `syscall_filter.py` — shrinking the kernel surface

Namespaces decide what the sandbox can *see*; seccomp decides what it can *ask the kernel to
do*. The second exists largely because of the first — unprivileged user namespaces widen the
reachable kernel surface, and that surface has a long local-privilege-escalation history.

`DENIED` is a list of 25 `(syscall, why no integration needs it)` pairs: `ptrace`,
`process_vm_readv`, `bpf`, `perf_event_open`, module loading, `kexec`, `setns`/`unshare`, the
mount family, the kernel keyring, `userfaultfd`, `io_uring_setup`. A loop adds one rule per
entry. That is the whole file — genuinely ordinary code.

Two honest notes that belong in the report. First, this is a **denylist over default-allow**,
which is weaker than an allowlist; the docstring says why (CPython, `aiohttp` and OpenSSL issue
a wide, version-dependent syscall set, and a wrong allowlist crashes the integration in ways
that look like bugs). Second, it is applied *after* the mounts and immediately before `exec` —
which is why it can safely deny `mount` and `pivot_root`. A seccomp filter survives `execve`,
which is what makes that ordering work.

Argument-level filtering permits `socket(AF_UNIX)` — the bridge — and denies `AF_INET`/`AF_INET6`.
**This is on by default** under `--isolate`, and it is what makes the `network:` allowlist
enforcing rather than advisory: with no IP socket available, the only way out is the supervisor.
`HACS_ALLOW_INET=1` turns it off, restoring the pre-2026-08-14 sandbox so the before/after stays
reproducible.

### `egress.py` — the only way out

The counterpart to the above. The sandbox has no network, so `MediatedClientSession` serialises
each request (method, URL, headers, body) over the bridge, and `Egress.fetch` performs it.

`_authorise` is the whole policy and reads like `Manifest`: check the scheme, check the host
against `network:`, refuse anything on `blocked_hosts`. It is called **once per redirect hop**,
not once per request, which is what closed the redirect gap the old shim documented but did not
fix.

It then answers a *second* question, and the difference between the two is the point. "May this
integration talk to this name" is the manifest. "Where does that name actually go" is the
resolution — and the author of the manifest also owns the DNS records the names point at.
Answering only the first was T14 (`PROJECT_STATUS.md` §12.2): a declared host with an A record on
192.168.1.1 was fetched by the supervisor, which is trusted and exempt from the sandbox's seccomp
`AF_INET` denial.

- **Ordinary, and you should be able to read this.** `forbidden_reason` is a pure function over
  `ipaddress` — refuse loopback, link-local, multicast, unspecified, reserved and private, in that
  order so the reason names the most specific match. `resolve` is one `getaddrinfo` call, split
  into its own method purely so tests can substitute an attacker-controlled zone. `_authorise`
  refuses if **any** answer is bad, not just the one about to be used.
- **⚠️ Advanced — study this before defending it.** `_PinnedHTTPConnection` and its HTTPS twin
  override `connect()` to dial the address that was checked instead of re-resolving the name.
  Without that there are *two* DNS lookups, the checked one and the used one, and an attacker
  owning the zone makes them differ — DNS rebinding, structurally a time-of-check-to-time-of-use
  bug. `self.host` is deliberately left untouched, so the `Host:` header and TLS certificate
  validation still use the declared name: **pinning changes where the connection goes, never who
  it claims to be talking to.** A pin that broke certificate checking would trade one hole for a
  worse one. The `functools.partial` in the handlers is only there because `urllib`'s `do_open`
  calls `http_class(host, ...)` positionally and the pinned address has to arrive as a keyword.

The rest of the file is limits, and they exist for a specific reason worth understanding: this
module is **trusted code acting on attacker-controlled input**, so it is a confused deputy by
construction. Response size, timeout, header count, header length, CRLF in header values, redirect
depth, and an empty `ProxyHandler` so ambient `http_proxy` cannot redirect egress. Each one bounds
something the sandbox could otherwise make the *supervisor* do. `test_egress.py` covers all of
them in both directions.

### `test_egress.py` and `test_matrix.sh`

Added 2026-08-14 after the question *"did you test this against multiple integrations with
multiple scenarios?"* — the answer being no. Widening the matrix found three defects, **all three
in measurement code rather than in controls** (see `PROJECT_STATUS.md` §5.11). Two more defects
followed, one of them in a probe check written the same day (§12.2b), making it **four of five**.

`test_egress.py` runs 35 policy cases against a local stub, covering both directions of every
rule — notably a redirect that *should* be followed as well as one that should not, since a
control that blocks everything looks correct until you test the positive path.

The last 18 cases are the destination check (T14, `PROJECT_STATUS.md` §12.2) and split three
ways, which is worth noticing as a pattern for testing security code. **Ordinary:** 14
classification cases calling `forbidden_reason` as a pure function — no network, no timing, every
address range in one table. **Ordinary but easy to get wrong:** four cases driving a
`ScriptedEgress` subclass whose DNS answers the test writes, standing in for a zone the attacker
owns — necessary because *rebinding is a difference between two resolutions*, which cannot be
demonstrated against a resolver you do not control. **Advanced, and the one to study before
defending it:** the pinning cases, which prove the connection reaches the address that was
checked. That proof is self-evidencing rather than assertion-based — the test's hostname does not
resolve in real DNS at all, so a 200 response is only explicable by the pin having been used.

`test_audit.py` covers the hash chain, and three of its five cases assert *limits* rather than
requirements — that a rebuilt chain still verifies (the unkeyed-digest limit from §5.8), and that
two runs cannot share a log file. Asserting a known limit is deliberate: a limit that is only
written down tends to quietly stop being true, and one that is tested cannot later be mistaken for
a bug someone already fixed.

`test_matrix.sh` asserts across 3 integrations × {stub, real HA, bridge} × {isolated, not} ×
{probe, no probe}, plus the three unit suites. 15 assertions without Docker, 24 with `HA=1`.
**Run it more than once** — defect 4 in §5.11 was invisible to any single run.

### `probe.py`

Runs *after* successful setup, in the same process, over the same manifest and bridge. **Ten
attempts**, each a single line a real author could add. Returns `(name, blocked, detail)` tuples
so results are tabulated rather than narrated. **6 of 10 blocked as an ordinary child process,
10 of 10 under `--isolate`.**

The design point is check #2. It does not just assert the call was denied — it inspects what came
back and counts entities outside this integration's *declared scope*:

```python
declared = json.loads(os.environ.get("HACS_DECLARED_SCOPE", "[]"))
leaked = [s.entity_id for s in states
          if not any(fnmatch(s.entity_id, p) for p in declared)]
```

An *allowed but empty* result is the correct behaviour, so testing for a denial would have been
the wrong test. Two earlier versions of this check were wrong — a hardcoded
`startswith("sensor.andrews_arnold")` that false-alarmed on the other two integrations, and
"anything I did not publish this run" that false-alarmed on entities legitimately persisting in a
real HA. Declared scope is the property the supervisor actually enforces, so it is what the check
should measure.

Check #5 reads a host file. It was written expecting to *fail* to be blocked, and reported
`ALLOWED` for two days. **A test suite that only contains tests you pass is marketing, not
evaluation** — and the payoff came on 2026-08-14, when isolation landed and that row flipped to
`BLOCKED` with a genuine before/after already on record. Checks #6, #7 and #8 followed the same
rule, written before their fixes existed; all three now block.

Checks **#9 and #10** came from writing the threat model rather than from writing code, and they
attack the *broker* instead of the sandbox: can the integration make the **supervisor** connect to
the LAN on its behalf? Two things about them are worth studying.

- They are blocked in **both** modes, because the control lives in `egress.py` rather than in the
  isolation — which is why the baseline moved from 4/8 to 6/10 rather than to 4/10.
- They must be requests the manifest *permits*, or the allowlist refuses them first and the check
  measures a control that was never in question. `--probe` widens the manifest with
  `supervisor.PROBE_HOSTS` and announces that it has done so.

And check #9 is the cautionary tale. On its first run against the unfixed broker it reported
`BLOCKED` — with the reason `transport failure: timed out`. The request had been authorised and
attempted and simply never arrived, because 192.0.2.10 is not routed. **A check that cannot tell a
control from a timeout would have shown the fix working before the fix existed.** It now reads the
reason string and reports three outcomes: blocked by the destination check, `NOT MEASURED` if the
allowlist got there first, or allowed-and-failed-in-transit. Write the failing check first, then
fix it — and then check that the check was measuring the thing you meant.

### `generate_shim.py`

The cost thesis, executed. It reads HA's own source with `ast` — never importing or running it,
the same discipline `hacs_api_surface.py` applies to untrusted integrations — and emits the
shim's pure-data modules: 469 constants into `const.py`, 93 selector classes into
`helpers/selector.py`.

Three design points worth keeping:

- **Pinned to a release tag, never `dev`.** Otherwise the shim's contents depend on the day it
  was run. It also matters practically: HA 2026.8.1's `helpers/selector.py` contains
  `except vol.Invalid, vol.MultipleInvalid:` — Python 2 syntax, a `SyntaxError` on any Python 3
  — so the generator falls back to line-based class extraction rather than dying.
- **It never silently drops a name.** Anything the previous module exported that the pinned
  source lacks is copied over verbatim, because a name can leave `const.py` without leaving the
  API: 2026.8 moved `Platform` into `homeassistant/generated/entity_platforms.py` (HA generates
  it too — independent support for this script's premise) and the lock states into their own
  component.
- **Dunders count as API.** Integrations do `from homeassistant.const import __version__` to
  gate on an HA version, so `__version__` is emitted and tracked like any other name. Missing
  this broke `andrews_arnold_quota` on the first generated run.

### `shim_coverage.py`

Closes the loop between the spike and the measurement tool. It `pkgutil.walk_packages` over
the shim, imports each module, and collects `dir(module)` into a set of `module:name` strings
— the *same* format `hacs_api_surface.py` emits. Then it replays `integrations.json` and
computes, per integration, `[s for s in symbols if s not in provided]`.

Dynamic import rather than static parsing, deliberately: it catches inherited and re-exported
names (like `DeviceInfo` re-exported from `device_registry`) that an AST pass would miss.

Its output — 6/30 clean, median 8 missing, ranked blockers — is a **work queue sorted by
value**. `binary_sensor` blocks 13 integrations and is a near-copy of `sensor`.

Two cautions on that number, both learned the hard way:

- **Run it under `../.venv/bin/python`.** With `aiohttp` unimportable, two shim modules fail
  to load, and the scorer reports 180 names and 0/30 while sending its warnings to stderr. The
  headline numbers print with equal confidence either way.
- **It is a work queue, not a compatibility score.** The dataset it replays was built with
  `--exclude-trivial`, so missing constants are invisible to it (`ha-icqa` was recorded as one
  symbol short and also failed on a missing `CONCENTRATION_*` constant), while integrations
  whose only gaps sit in never-executed modules count as failures despite running fine
  (`ha-matomo`). Use it to decide what to build next; use the executed-end-to-end count to
  claim compatibility.

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
