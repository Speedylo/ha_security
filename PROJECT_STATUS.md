# Capstone — Project Status & Rolling Notes

**Owner:** Younes · Al Akhawayn University, BSc Computer Science
**Advisor (intended):** Prof. Omar Iraqi Houssaini — Professor of CS; IT & Cybersecurity Lead Auditor & Architect. Already took a cybersecurity course with him.
**Work period:** September – November 2026 (~13 calendar weeks; **~10 realistic engineering weeks** after proposal, mid-report, final report and defence overhead).
**Last updated:** 2026-08-21
**Repo:** `~/capstone` (WSL filesystem, under git). The Windows `Desktop/Capstone`
copy is a stale backup — do not edit it. `/mnt/c` is avoided because file modes
there are fake, which would silently break filesystem permission tests.

> This file is the source of truth across sessions. Update it as decisions land.
>
> Companion docs: `CODE_WALKTHROUGH.md` (what every script does and how) ·
> `spike/README.md` (spike results, adversarial probe, known gaps).

---

## 1. Where we're heading

**Chosen project: a sandboxed execution framework for Home Assistant custom integrations.**
(Formerly "Option C". Options A and B are dropped — see §3.)

Home Assistant (HA) is a widely self-hosted open-source home-automation platform.
Its functionality is extended by *integrations*. Community-written ones — typically
installed via HACS — are **not security reviewed and run with full trust inside HA's own
process**. They can read every device state, call any service (unlock doors, disarm
alarms), and read `/config/secrets.yaml` containing every stored credential.

The goal is a **supervisor** that runs each integration in an isolated process which
reaches Home Assistant *only* through a permission-checked bridge governed by a
declared manifest — so a malicious or compromised integration is confined to what it
declared it needs.

### Grading criteria this is being designed against
Relevance · Feasibility · Innovation · Impact · Clarity.

---

## 2. Target architecture

```
   Real Home Assistant   ← unmodified, untouched source
            ▲
            │  ONLY the supervisor holds the HA API token
   ┌────────┴──────────┐
   │    SUPERVISOR      │  ← core deliverable #2
   │  • loads manifest, enforces it on every request
   │  • filters reads AND subscriptions (see §5, leak issue)
   │  • per-integration outbound network allowlist
   │  • tamper-evident audit log of every decision
   └────────┬──────────┘
            │  socket (JSON messages)
   ┌────────┴──────────┐
   │  Sandboxed process │  restricted: own dir, no stray network
   │   ├── COMPAT SHIM  │  ← core deliverable #1
   │   │     fake `homeassistant` package; translates
   │   │     hass.* calls into socket messages
   │   └── untrusted integration, running unmodified
   └────────────────────┘
```

**Example manifest** (the security contract):

```yaml
name: my_weather
publishes:       [sensor.outdoor_temperature]
calls_services:  []                        # none
reads_entities:  []                        # none
network:         [api.weatherapi.com]
```

**The two original contributions are the shim and the supervisor's permission
enforcement.** The sandbox and the monitoring layer are off-the-shelf components that
get *configured*. Time and report pages should be allocated accordingly.

---

## 3. Why Options A and B were dropped

| | Verdict |
|---|---|
| **A — Pi 5 handheld console** (gVisor + eBPF) | Cut. 3 weeks of hardware bring-up contributing nothing to the contribution; weakest impact ("a homebrew community that doesn't exist yet"); gap statement was *nobody-bothered*, not *unmet-need*. |
| **B — ESP32-S3 + WASM/WAMR** | Cut. Lowest risk and most finishable, but weakest on Impact, and its own research notes that AkiraOS already ships a near-identical capability-manifest design — novelty collapses on contact. |

Deciding factors for C: CS degree (pure software is acceptable), no hardware needed,
Pi 5 already owned, and a **real documented problem with real users**.

---

## 4. Corrections to the original `option_C_home_assistant_sandbox.md`

The folder document was an exploratory sketch. Three of its architectural claims do not hold.

### 4.1 BLOCKING — integrations cannot run outside HA's process
An integration is not a program; it is a Python module loaded by HA's bootstrap and
handed a live in-memory `hass` object. Isolate it and it dies at `import homeassistant`.
The original doc conceded this in one line under Limitations, but that concession
destroys its own impact argument (it cites dangers in *existing* integrations while
supporting none of them).

**Resolution:** build a **compatibility shim** — see §7 glossary. This is the project.

### 4.2 BLOCKING — eBPF cannot observe a gVisor-sandboxed process
The doc's "gVisor prevents, eBPF detects, two independent layers" is not a real
architecture. gVisor never passes syscalls to the host kernel; the Sentry handles them in
userspace. Host eBPF therefore watches the Sentry, not the application.
This is documented, not speculative: Falco could not monitor gVisor sandboxes at all
before 0.32.1 for exactly this reason, and their fix was to consume gVisor's own
runtime-monitoring feed over a Unix socket instead of using eBPF.

**Resolution options:** (a) drop gVisor, use namespaces + seccomp so eBPF works properly
[**recommended**]; (b) keep gVisor and use its native trace sink; (c) keep both but
re-scope eBPF as a boundary/containment verifier only.

### 4.3 BLOCKING — the confused-deputy hole the sandbox cannot see
A sandboxed integration must be allowed to talk to HA — that's its job. If it holds an API
token it can simply issue `POST /api/services/lock/unlock`. The sandbox sees allowed
network traffic; eBPF sees an ordinary socket write; HA sees a valid token. Door opens,
nothing anomalous logged.

**Resolution:** the supervisor holds the token; the integration declares a manifest; the
supervisor refuses and logs anything undeclared. *This is the actual security contribution.*

### 4.4 Other required fixes
- **Firehose leak.** `/api/states` returns every entity in the house and the WebSocket
  `subscribe_events` streams every state change. A naive forwarding proxy leaks occupancy,
  locks, cameras and holiday absence to a weather widget. **The bridge must filter reads
  and subscriptions, not just writes.** Finding and closing this is a strong report result.
- **Egress is required, not deniable.** Integrations exist to call cloud APIs. Needs
  per-integration domain allowlists, not a blanket network deny.
- **Cite browser extensions.** Manifest permissions are proven in Chrome/Firefox/Android.
  Frame as *proven elsewhere, absent here* — stronger and honest.
- **Drop the decentralised web-of-trust layer to Future Work.** It is a second capstone and
  invites Sybil-resistance questions that cannot be won. Keep a modest **local
  hash-chained audit log** in scope instead — cheap, and squarely in an auditor's wheelhouse.
- **Responsible disclosure paragraph** required: real HACS integrations will be probed;
  no working exploits published.

---

## 5. Work completed

### 5.1 `hacs_api_surface.py` — empirical API-surface measurement ✅
Stdlib-only Python tool. Downloads repos from the HACS default catalogue, parses every
`custom_components/**/*.py` with `ast` **straight out of the tarball in memory** (untrusted
code is never executed and never written to disk as an importable module), records every
`homeassistant.*` import, classifies each integration by architectural pattern, and
computes a **coverage curve**: integrations fully runnable vs. number of symbols implemented.

```bash
python3 hacs_api_surface.py --limit 200 --pattern polling_sensor --exclude-trivial
python3 hacs_api_surface.py --limit 0            # full catalogue (3105 repos)
```
Outputs to `surface_out/`: `symbols.csv`, `coverage.csv`, `nearmiss.csv`, `integrations.json`.
Tarballs cache in `.hacs_cache/`, so re-runs are instant.

### 5.2 Results — full catalogue ✅ (2026-08-13)

**The whole catalogue has now been analysed: 3105 repositories, 3075 parsed.** The
200-repo sample is superseded and kept only as `surface_out_200repo/` for provenance.

**Pattern distribution — by repo count, and by how many people actually run them:**

| pattern | repos (n=3075) | 200-repo sample | **by installed base** |
|---|---|---|---|
| actuator (receives commands) | 46.7% (1437) | 58.0% | **64.8%** |
| polling_sensor | 24.8% (763) | 15.0% | **10.6%** |
| sensor_other | 9.4% (288) | 13.5% | 5.0% |
| other | 8.0% (246) | 6.5% | 6.0% |
| local_discovery | 7.8% (240) | 6.0% | 7.4% |
| push_stream | 2.4% (75) | 0.5% | 4.9% |
| oauth_cloud | 0.8% (26) | 0.5% | 1.2% |

Two separate corrections here, and the second is the bigger one.

**(a) The sample was biased, as suspected.** Catalogue order is roughly alphabetical — which
is why every near-miss repo in the old results began with `a`. By repo count, polling sensors
are 24.8%, not 15%.

**(b) Repo counts are the wrong denominator.** ⭐ **Found 2026-08-13.** Home Assistant
publishes real install counts for custom integrations at
`https://analytics.home-assistant.io/custom_integrations.json`, keyed by **domain**, which
joins directly to `integrations.json`. 1,770 of 3,075 integrations match; 1,064,724 installs
total. Weighted by what people actually run:

- **actuators are 64.8% of the installed base**, not 46.7%;
- **polling sensors are 10.6%**, not 24.8%.

Counting repositories treats a 43,601-install integration (`AlexxIT/SonoffLAN`) and a
3-install one identically. **Every coverage figure in this project should be reported both
ways**, and the install-weighted one is the honest answer to "how much of the real world does
this run". `spike/shim_coverage.py --installs` computes it.

Installs are also extremely concentrated:

| top N integrations | share of all installs |
|---|---|
| 10 | 25.9% |
| 100 | **69.6%** |
| 200 | 82.3% |
| 500 | 94.3% |

⚠️ Caveat for the report: HA analytics is **opt-in telemetry**, so these are a lower bound and
a relative measure, not a census. They remain the only public signal of real-world usage, and
far better than assuming every repo is equally used.

**API surface, polling-sensor subset (n=763, constants included):** median **6** missing
symbols against the current shim, and 72 integrations already import cleanly.

*Historical, 200-repo sample (n=30, `--exclude-trivial`): 237 distinct symbols · median 29
per integration · max 74.*

**⚠️ The coverage curve, corrected twice.** The original working assumption of "~15 symbols"
was wrong; the 200-repo sample replaced it with "50% of integrations needs ~83 behavioural
symbols". **The full catalogue says even that was optimistic:**

| behavioural symbols implemented | integrations fully covered (n=763) |
|---|---|
| 30 | 15.2% |
| 51 | **25%** |
| 80 | 33.9% |
| 120 | **46.1%** (352) |

**50% is not reached within 120 behavioural symbols** — the sample's "~83 for 50%" does not
survive contact with the full population. Strict zero-modification coverage of the whole
polling-sensor class is therefore expensive, and the report should say so plainly.

**This does not undermine the project — it is the argument for how it is scoped.** Two
things stay true at full scale: the head of the distribution is extremely concentrated (the
table below), so a small core reaches a large minority of integrations quickly; and the
expensive tail is dominated by generatable material (`util.dt`, the `selector` family,
`const` enums), not by behavioural work. The honest claim is **"a small hand-written core
plus a generated constants layer runs a well-characterised fraction, measured and
reported"** — not "most integrations run unmodified". Report the curve, not a single number.

**The distribution is steeply concentrated, and the concentration survived the jump from 30
integrations to 763** — the single most important thing the full run confirms:

| symbol | appears in (n=763) | sample said |
|---|---|---|
| `update_coordinator:DataUpdateCoordinator` | **98.7%** | 100% |
| `core:HomeAssistant` | **98.2%** | 100% |
| `config_entries:ConfigEntry` | **96.7%** | 97% |
| `sensor:SensorEntity` | **93.8%** | 93% |
| `update_coordinator:CoordinatorEntity` | **93.8%** | 93% |
| `update_coordinator:UpdateFailed` | **77.3%** | 90% |
| `entity_platform:AddEntitiesCallback` | **73.0%** | 80% |
| `core:callback` | **69.7%** | 77% |
| `sensor:SensorDeviceClass` | **61.3%** | 70% |
| `sensor:SensorStateClass` | **59.1%** | 73% |
| `aiohttp_client:async_get_clientsession` | **51.1%** | 67% |

The head is slightly less dominant at full scale (each symbol's share drops a few points, and
the sample's two "100%" figures were artefacts of n=30), but the shape is unchanged: **the
same handful of symbols carries nearly the whole population.** Every scoping decision that
rested on this still holds, now on 763 integrations instead of 30.

- Much of the tail is `homeassistant.const` values, enums (`SensorDeviceClass`,
  `EntityCategory`) and selector configs — **machine-generatable from HA's source**, not
  hand-written. That collapses most of the tail to near-zero cost.

**Realistic budget: ~30–40 hand-written behavioural symbols + a generated constants layer.**

**Caveats to carry into the report:** the actuator classifier is heuristic and probably
over-broad; **imports are a lower bound on difficulty** — an integration can import
`SensorEntity` and still depend on lifecycle behaviour the shim doesn't reproduce (see the
`current_entry` gap in §5.3, and the two metric corrections below). The selection-bias caveat
is **retired**: the full catalogue has been analysed and the drift it predicted is quantified
in the table above.

**Datasets on disk** — each figure must state which one it came from:

| directory | population | `--exclude-trivial` |
|---|---|---|
| `surface_out/` | 3105 repos, 3075 parsed | no — constants included |
| `surface_out_excl_trivial/` | same | yes — behavioural symbols only |
| `surface_out_200repo/` | historical 200-repo sample | yes |

**This measurement is itself a contribution.** No published empirical account of the HA API
surface that HACS integrations depend on appears to exist. It is a report figure and it
justifies every downstream scoping decision — exactly the evidence an auditor grades well.

### 5.3 Shim spike — **GO** ✅ (2026-08-12)

Item 4 of the August plan, the go/no-go. Full write-up in `spike/README.md`.

**Result: unmodified real HACS integrations run outside HA's process.**
**Three of them as of 2026-08-13** — each sets up, polls twice and publishes sensor states
through a permission-checked Unix socket with **zero lines changed**:

| Target | Publishes | Mediated ops | Why this one |
|---|---|---|---|
| `andrew-codechimp/HA-Andrews-Arnold-Quota` v2.0.0 | 2 sensors | 7 | the integration-blueprint layout (`__init__` + `coordinator` + `entity` + `sensor` + config flow) — the shape most of the polling-sensor population takes |
| `abnvle/ha-matomo` | 15 sensors | 44 | frozen entity descriptions; many entities off one coordinator |
| `aniolpages/ha-icqa` | 8 sensors | 18 | public credential-free endpoint; `runtime_data`; nested payload parsing |

`spike/run_targets.sh` runs all three: **69 mediated operations, 0 denied, every audit
chain intact**. The supervisor and runner are target-agnostic — a new integration is a
directory, a manifest and a vendor-cloud stub, with no change to the enforcement path.

Built: `spike/shim/homeassistant/` (~2.3k lines: `core`, `const`, `config_entries`,
`exceptions`, `data_entry_flow`, `util`, `helpers/{entity,entity_platform,update_coordinator,
aiohttp_client,config_validation,device_registry,typing}`, `components/sensor`),
plus supervisor, sandbox runner, adversarial probe, stub vendor cloud and a coverage scorer
(~760 lines).

**Adversarial probe (`./run_spike.sh --probe`)** — four of five attacks blocked:

| Attempt | Result |
|---|---|
| Read undeclared `lock.front_door` | blocked by `reads_entities` |
| Enumerate whole house (the firehose) | blocked — 2 of 8 entities returned, 6 withheld |
| Call `lock.unlock` (confused deputy) | blocked by `calls_services` |
| Exfiltrate to undeclared host | blocked by `network` allowlist |
| **Read a host file directly** | **ALLOWED — no filesystem isolation yet** |

That last row is the honest gap: until namespaces + seccomp land, the framework does *not*
stop the 2021 HACS file-theft pattern, which is the strongest planned result (§8, Evaluation).
Nothing else in the table depends on it.

The hash-chained audit log works and detects tampering: flipping the `lock.unlock` denial to
an allow in a copy of the log yields `BROKEN: line 10: record altered (hash mismatch)`.

### 5.4 Constants generator, and the honest coverage position ✅ (2026-08-13)

`spike/generate_shim.py` reads HA's own source with `ast` — never importing or executing it —
and emits the shim's pure-data modules. It is pinned to release **2026.8.1**, never `dev`, and
carries over any name that disappears upstream rather than silently dropping it.

It generated **469 constants and 93 selector classes**, taking the shim from 350 to **814
importable names**. Three things surfaced while building it:

- **HA generates `Platform` themselves** — since 2026.8 it is `EntityPlatforms`, re-exported
  from `homeassistant/generated/entity_platforms.py`. Independent upstream support for the
  "constants are generated, not written" premise.
- **HA 2026.8.1's `helpers/selector.py` does not parse under Python 3** — line 621 is
  `except vol.Invalid, vol.MultipleInvalid:`, Python 2 syntax. The generator degrades to
  line-based extraction rather than failing. *Verify this independently before citing it.*
- **A latent supervisor bug**: `AuditLog.verify` raised `UnboundLocalError` on an empty log.
  Fixed.

**What generating actually bought — less than the thesis predicted:**

| | before | after |
|---|---|---|
| importable names | 350 | **814** |
| polling sensors import-clean | 9.4% | **12.3%** (94/763) |
| median missing among the rest | 6 | **4** |
| share of polling-sensor installs | — | **7.8%** |
| share of *all* installs | 0.8% | **1.2%** |

⚠️ **This qualifies §5.2's "the tail is generatable" thesis.** The thesis is *true* — the
constant tail was generated in an afternoon and regenerates free every HA release. But that
tail was **a smaller part of the problem than assumed**: clearing every constant and selector
moved import-cleanliness by three points. What actually blocks integrations is **behavioural**
— entity platforms and stateful helpers, none of which are generatable.

**Blockers among the 100 most-installed integrations** (69.6% of the installed base):

| missing | blocks | generatable? |
|---|---|---|
| `binary_sensor:BinarySensorEntity` | 50 | no — platform |
| `helpers:entity_registry` | 50 | no — stateful |
| `switch:SwitchEntity` | 49 | no — **actuator** platform |
| `button:ButtonEntity` | 41 | no — **actuator** platform |
| `util:dt` | 41 | thin wrapper |
| `select:SelectEntity` | 36 | no — **actuator** platform |
| `number:NumberEntity` | 33 | no — **actuator** platform |
| `restore_state:RestoreEntity` | 30 | no — stateful |

**How much ground the framework covers right now — state it plainly:**

| measure | value |
|---|---|
| **executed end-to-end** | **3** integrations |
| import-clean, polling sensors | 94/763 (12.3%) |
| import-clean, all patterns | 141/3075 (4.6%) |
| **share of real installed base** | **1.2%** |
| top 100 most-installed | **1/100** |

A greedy search — implement whole modules one at a time, always choosing the one unblocking
the most installs — reaches only **5.8% of the installed base after twelve more complete
modules**. The curve is flat because *every* import an integration makes must be satisfied,
and popular integrations import more (median **22** missing among the top 100).

**The conclusion to carry into the report:** this project has a **working mechanism** and
**very little coverage**, and those are compatible facts. The contribution is the mechanism
plus the first empirical measurement of what applying it ecosystem-wide would cost — not a
deployable product. See §10.

⚠️ **Two corrections to how the import number must be read** (both found 2026-08-13, both
report material):

1. **The dataset was built with `--exclude-trivial`**, which drops `homeassistant.const`,
   `.exceptions`, `.helpers.typing` and `.util.dt` from every recorded symbol set. Those
   symbols still have to exist for an import to succeed, so the measured gap **understates**
   the real one. `ha-icqa` was recorded as missing one symbol and in fact also failed on
   `CONCENTRATION_MICROGRAMS_PER_CUBIC_METER`, a constant the dataset never counted. The
   understatement is confined to cheap, generatable symbols — but it must be stated, and any
   headline coverage figure has to name the flag it was measured under.
2. **Import-cleanliness is *not* an upper bound on compatibility** — the earlier claim in
   this file. `ha-matomo` runs end-to-end while still counting as one symbol short, because
   the missing name sits in `config_flow.py`, which HA loads only when a user adds the
   integration through the UI and which never runs afterwards. So the metric errs in **both**
   directions: it over-counts integrations that import cleanly then die on lifecycle
   behaviour, and under-counts ones whose gaps sit on cold code paths. **It is a proxy for
   ranking work, not a bound.** Executed-end-to-end (now 3) is the compatibility measure;
   report it as the headline and import counts as the backlog.

**Fidelity gaps found (report material, all in `spike/README.md`):**
1. ✅ **FIXED — `EntityDescription` frozen-ness, and the single most interesting result of
   adding a second integration.** HA's `FrozenOrThawed` metaclass lets one description base
   be subclassed by *either* a frozen or a plain `@dataclass`; Python forbids that directly.
   The shim originally left the base unfrozen — enough for one target, and it looked like a
   harmless simplification. It is not: `andrews_arnold_quota` uses a plain `@dataclass` and
   **mutates** `entity_description.entity_id`, while `matomo` uses
   `@dataclass(frozen=True)`. An unfrozen base runs the first and raises `TypeError` on the
   second; a frozen base does the reverse. **No single choice runs both.** Now implemented
   as `shim/homeassistant/util/frozen_dataclass_compat.py` (upstream's needs `annotationlib`
   from Python 3.14; this reads `__annotations__` and runs on 3.12).
   **The methodological point for the report:** this is a gap a one-integration spike
   *cannot* surface — at n=1 the shortcut is invisible, and only the second sample turns it
   into a contradiction. The same argument applies to every remaining shortcut in the shim,
   and it is the argument for growing the executed-integration count rather than the import
   count.
2. `config_entries.current_entry` — integrations read `coordinator.config_entry` having never
   set it; HA fills it from a ContextVar during setup. Missing it breaks the blueprint layout
   at runtime, not at import. **Exactly the class of failure import counts cannot predict.**
3. Egress check misses redirects (only the first URL is authorised).
4. Bridge calls block the event loop.
5. Shim-side checks are ergonomics, not security — the integration can bypass them. All
   enforcement is duplicated supervisor-side. Worth stating explicitly in the threat model.

### 5.5 Real Home Assistant behind the supervisor ✅ (2026-08-13) ⭐

The item §9 called the highest-value one in the project. **Done, and it converts the central
claim from design intent into a demonstrated result.**

```bash
./ha_docker.sh up      # stock ghcr.io/home-assistant/home-assistant:2026.8.1
./ha_onboard.py        # headless onboarding, mints a long-lived token
./ha_seed.py           # give it a house worth protecting
HA=1 ./run_targets.sh  # all three integrations, publishing into real HA
```

**Nothing about Home Assistant is modified.** The official published image, no patches, no
custom components mounted, no config edits. The supervisor reaches it only through the REST
API that HA already exposes to any client holding a token.

**Result:** all three unmodified integrations run and publish into the live instance —
**25 entities** (15 matomo, 8 icqa, 2 andrews_arnold), with correct units and friendly names,
visible in HA's own `/api/states` alongside its native `sun.*` entities.

**The adversarial probe re-run against real HA — and the firehose result gets much stronger:**

| attempt | stub house | **real HA** |
|---|---|---|
| Read undeclared `lock.front_door` | blocked | **blocked** |
| Enumerate the whole house | 2 of 8 returned | **2 visible, 41 withheld** |
| Call `lock.unlock` (confused deputy) | blocked | **blocked** |
| Exfiltrate to undeclared host | blocked | **blocked** |
| Read a host file | ALLOWED | **ALLOWED** (unchanged; no fs isolation *at the time*) |

> **Superseded 2026-08-14 by §5.9.** The last row now reads **BLOCKED** under `--isolate`, and the
> probe has grown from five checks to seven. This table is retained as the measurement that
> motivated building isolation; §5.9 carries the current numbers.

**Paired baseline measurement — the comparison the evaluation chapter needs.** The same token,
used the way an ordinary in-process integration uses `hass` today:

| | baseline HA | under the framework |
|---|---|---|
| `lock.front_door` | readable (`'locked'`) | **denied** |
| entities enumerable | **43** | **2** |
| privacy-relevant entities exposed | 5 (locks, alarm, camera, device_tracker) | **0** |

That is the security result stated as a controlled comparison rather than a demo, against a
real instance, and it is reproducible with four commands.

**Design note worth keeping:** the switch is a backend swap, not a policy change.
`ha_backend.py` holds `StubHouse` and `RestHouse` behind one interface; `supervisor.py`'s
`decide()` is untouched by which is in use, and every manifest check still runs *before* the
backend is called. The stub path still works identically, which is what makes the two rows of
the probe table comparable.

**New scripts:** `ha_backend.py` (both backends), `ha_docker.sh` (up/down/logs/status),
`ha_onboard.py` (headless onboarding + long-lived token via the WebSocket API — HA has no REST
route for minting one), `ha_seed.py` (populate a realistic house).

### 5.6 The registry gap, quantified ✅ (2026-08-13)

§5.5 left one objection open: entities arrive over REST as plain states, not linked to a config
entry or the device registry. It is now **measured rather than asserted**, by running *the same
integration two ways at once* against the same live HA:

```bash
./ha_compare_setup.sh   # matomo natively in /config/custom_components AND via the framework
./registry_gap.py --restart-test
```

`matomo` was chosen because its config flow needs only a URL and a token, so it can be driven
headlessly against the same vendor stub the framework uses. Both halves publish 15 entities.

**Result 1 — the framework entity has no entity-registry row at all.** Not a sparse row: no
row. Every identity field is therefore structurally unavailable, rather than merely unset:

| field | native | framework | what it buys |
|---|---|---|---|
| `unique_id` | `matomo_1_actions_month` | **unavailable** | stable identity across restarts/renames |
| `config_entry_id` | set | **unavailable** | user can reload/delete the configuration |
| `device_id` | set | **unavailable** | grouped under a device in the UI |
| `platform` | `matomo` | **unavailable** | attributed to the integration that made it |
| `area_id`, `entity_category`, `disabled_by`, `hidden_by`, `name`, `icon` | available, unset | **unavailable** | assign to a room, hide, disable, rename |

Native: registry row exists — **4/10 populated** by the integration, the other **6 available**
for the user to set. Framework: **10/10 unavailable**.

**Result 2 — ownership.** Native produces **1 config entry and 1 device**; the framework
produces **0 and 0**. There is nothing for the user to reload, reconfigure, or delete from the
UI, and nothing to group entities under.

**Result 3 — ⚠️ the decisive one: framework entities do not survive an HA restart.**

| | survived a restart |
|---|---|
| native | **15/15** |
| framework | **0/15** |

This is not cosmetic. HA restarts a natively-loaded integration itself; REST-published states
are in-memory only and nothing re-creates them. **The supervisor must therefore be a
long-running, restart-aware service, not a one-shot process** — an architectural requirement
that was not visible before this measurement and that belongs in the design chapter.

**What is *not* lost:** state-level presentation is intact. `unit_of_measurement`,
`state_class`, `device_class` and `icon` all arrive identically. Only `friendly_name` differs
in form — native renders "Matomo - example.org" (device name + entity name) against the
framework's "Actions this month", because HA composes the device name in that pattern and the
framework has no device.

**Honest reading (as of the measurement):** the retrofit worked and the entities were real and
usable, but they were **second-class citizens** in HA's data model. Three mitigations were
identified, in rising order of effort: (a) accept and document; (b) register entities through
HA's WebSocket registry APIs; (c) ship a thin native HA integration that owns the config entry
and device on the framework's behalf.

### 5.7 `sandbox_bridge` — the registry gap closed ✅ (2026-08-13)

**Option (c) is built.** `spike/bridge_integration/sandbox_bridge/` is a ~250-line native HA
integration whose only job is to give sandboxed integrations first-class entities.

```bash
./ha_bridge_setup.sh            # install it, restart HA, create its config entry
HA=1 BRIDGE=1 ./run_targets.sh  # publish through it
./registry_gap.py --restart-test
```

**How it works.** It owns a config entry, creates one device per sandboxed integration, and
exposes a service `sandbox_bridge.publish` that the supervisor calls instead of `POST
/api/states`. Entities are `RestoreEntity` subclasses with a `unique_id`, so they get registry
rows; the roster is persisted with `helpers.storage.Store`, so the bridge recreates every
entity on startup and each restores its last value.

**Crucially, it does not weaken the threat model.** No untrusted code is loaded into HA. The
sandboxed integrations still run in their own process behind the supervisor's manifest checks;
the bridge only ever receives a domain, a key, an entity_id, a state string and a dict of
attributes, and never evaluates any of it. It is a *trusted* component of the framework, and
being ~250 lines it is small enough to actually review — which is the argument to make about it.

**Result — the gap is closed on every axis measured in §5.6:**

| | native | framework, REST (§5.6) | framework, via bridge |
|---|---|---|---|
| entity-registry row | 4/10 set, 6 available | **none — 10/10 unavailable** | **4/10 set, 6 available** |
| config entries | 1 | **0** | **1** |
| devices | 1 | **0** | **1** (one per integration) |
| **survives an HA restart** | 15/15 | **0/15** | **15/15** |

Across all three targets: **25 registry-backed entities and 3 devices** (`matomo` 15,
`icqa` 8, `andrews_arnold_quota` 2). The restart test was run with the supervisor deliberately
*not* re-run afterwards, so survival is the bridge's doing, not a re-publish.

**One accurate difference remains, and it is a feature.** `platform` reads `sandbox_bridge`
rather than `matomo`. That is true — the bridge really is what created the entity — and it
makes the sandboxing *visible* to the user in the UI rather than hiding it. The device is named
after the integration and modelled "Runs outside Home Assistant, under manifest enforcement".

**Publishing mode is now a supervisor flag** (`--ha-bridge`), so §5.6's table is reproducible in
both directions: the framework can still publish raw states to demonstrate the gap, then
publish through the bridge to demonstrate the fix. All three modes — stub, real REST, bridge —
are regression-tested and pass.

### 5.8 Self-audit of the security core — two findings ⚠️ (2026-08-14)

Full write-up: **`FINDINGS_2026-08-14_token_leak.md`** (commit `2ab970a`). Both findings were
confirmed by test on the dev machine. **No repository code was changed** — the weaknesses are
left intact deliberately so they can be *demonstrated* rather than described, and so the fix and
the finding can land together.

**Finding 1 — the HA token reaches the sandbox by three routes.** The supervisor is supposed to
be the sole holder of the credential; that is the premise the whole confinement argument rests
on. It is not currently true:

| # | Route | Why |
|---|---|---|
| 1 | The child's own environment | `env = dict(os.environ)` (`supervisor.py:320`) copies `HA_TOKEN`; the `env.update()` on the next line only *adds* keys |
| 2 | `/proc/<ppid>/environ` | Same uid, so the sandbox reads the supervisor's own environment directly |
| 3 | `/proc/<ppid>/cmdline` | Same uid, so `--ha-token` leaks identically |

Closing any one leaves the others open. Note that route 1 is reached by a **documented** way of
running the supervisor — line 283 reads the token from `HA_TOKEN` and the `--ha-token` help text
advertises it. The comment at `supervisor.py:329` (*"No HA token in the child's environment"*)
asserts a guarantee the code does not implement.

**Why it matters more than an ordinary bug:** an integration that reads the token does not attack
the policy layer at all. It calls HA's REST API directly, so `decide()` is never invoked. The
manifest is not defeated — it is bypassed. `probe.py` check #3 correctly blocks
`lock.unlock` *through the shim*; the same action via a stolen token is not seen.

**Finding 2 — the hash chain is sound for what it does, and its docstring overstates it.**
Demonstrated against a genuine 11-record audit log from 2026-08-12 (copies only; the original is
untouched):

| Test | Result |
|---|---|
| Untouched log | `OK: chain intact (11 records)` |
| Flip the `lock.unlock` DENY to allow, leave hashes alone | `BROKEN: line 10: record altered (hash mismatch)` ✅ working as designed |
| Same edit, recompute all 11 hashes from the zero anchor | **`OK: chain intact (11 records)`** ❌ |

`_digest` is unkeyed `sha256` (`supervisor.py:96`), so rebuilding the chain requires no secret —
about fifteen lines using only what is already in the file. The `AuditLog` docstring
(`supervisor.py:79–85`) claims an integration "cannot remove or reorder a decision without
breaking every hash after it"; true against a naive edit, false against a rebuild.

**Independently, the chain records only *mediated* operations.** `append()` is called in exactly
one place — inside the socket-reading loop, right after `decide()` (`supervisor.py:250`). A
bypassed action creates no record, and leaves no gap either: `seq` increments inside `append()`,
so it counts *records created*, not *events that occurred*. **Integrity is not completeness.**
After a successful token bypass the lock is open and `verify()` reports `OK`; both are true.

**One root cause, and it strengthens the case for workstream 4.** Both findings follow from a
single physical fact: the sandbox is a plain `subprocess.Popen` running as the same user, with
unrestricted filesystem and `/proc` visibility. The audit directory is an ordinary file the
sandbox can rewrite. Neither is fixable inside `supervisor.py` — scrubbing the environment leaves
routes 2 and 3; keying the chain still leaves the file writable. What closes them is a distinct
uid or a PID namespace, i.e. **workstream 4**, which was at zero lines when this was written. This
upgrades the argument for isolation from *"precondition for reproducing the 2021 HACS file-theft
result"* (someone else's finding) to:

> **Isolation is a precondition for the confidentiality of the HA credential and for the
> completeness of the audit log — without it the mediation layer can be bypassed entirely rather
> than defeated.**

> ✅ **Resolved the same day — see §5.9.** Isolation was built within hours of this being written,
> and probe check #6 (added to make this finding measurable) goes from ALLOWED to BLOCKED under
> `--isolate`. Routes 2 and 3 are closed; route 1 was fixed separately in `supervisor.py`, which
> is worth keeping distinct because it shows isolation is necessary but not sufficient. The audit
> directory is no longer visible inside the sandbox. **The finding stands as written** — it is
> what motivated the build, and the before/after is now a measured result rather than a warning.

**Cheap exception worth noting:** keying the chain with an HMAC closes the rebuild attack
*independently of workstream 4* and is a small change (`hashlib.sha256` → `hmac.new(key, …)`,
plus deciding where the key lives). It is one of the few security improvements available that is
not blocked on isolation.

**What to claim about the audit log**, replacing any "tamper-proof" phrasing: *tamper-evident
against after-the-fact modification by an actor that cannot recompute the chain*, with both
limits stated. `FINDINGS_2026-08-14_token_leak.md` §6.12 has the exact wording, and Part 10 there
carries two drafted threat→control→residual-risk rows ready to lift into `THREAT_MODEL.md`.

**Methodologically this is the fourth self-caught gap**, after `FrozenOrThawed`, the registry gap
(§5.6→§5.7), and the install-weighting reversal (§5.4). Worth making that pattern explicit in the
report rather than leaving a reader to notice it.

### 5.9 Isolation spike — namespaces + seccomp work end to end ✅ (2026-08-14) ⭐

Full write-up: **`RESULTS_2026-08-14_isolation_spike.md`**. Built to answer a direct question —
*can this project actually be completed end to end?* — by attacking the one workstream that was
at zero and made the plan look risky.

**It works, and it is ~260 lines.** `spike/isolate.py` builds a root filesystem containing only
an explicit allowlist of paths, pivots into it, and mounts a private `/proc`;
`spike/syscall_filter.py` adds a 25-rule seccomp policy. No root required — unprivileged user
namespaces throughout. Enabled with `--isolate` (or `ISOLATE=1 ./run_targets.sh`); the
unisolated path is unchanged, so every measurement is reproducible in both directions.

**The adversarial probe gains three checks and goes from 4/8 to 6/8 blocked** *(and to 8/8 once
egress was brokered later the same day — §5.10)***:**

| # | Check | Baseline | Isolated |
|---|---|---|---|
| 5 | read host filesystem (`/etc/passwd`) | ALLOWED | **BLOCKED** |
| 6 | read supervisor's `/proc` (credential theft, §5.8) | ALLOWED | **BLOCKED** |
| 7 | raw socket → undeclared **LAN device** (lateral movement) | ALLOWED | **ALLOWED** |
| 8 | raw socket → undeclared internet host (exfiltration) | ALLOWED | **ALLOWED** |

Row 5 is the 2021 HACS file-theft pattern — §8's "single strongest result available" is now
reachable. Row 6 closes §5.8's routes 2 and 3 (route 1, the copied environment, was fixed
separately in `supervisor.py`; keep the distinction, it shows isolation is necessary but not
sufficient). **Row 7 is the predicted Category B gap** and stays open honestly.

**Isolation is transparent to compatibility.** All three integrations produce identical operation
counts isolated and not: `andrews_arnold_quota` 7, `matomo` 44, `icqa` 18, chains intact. The
compatibility result is not traded away to get the security result.

**Seccomp argument filtering demonstrates the fix for rows 7–8.** `HACS_DENY_INET=1` permits
`socket(AF_UNIX)` (the bridge) and denies `AF_INET`/`AF_INET6`. The integration then fails to
reach its vendor cloud — *which is the point*: it proves the `network:` allowlist can be made
enforcing rather than advisory, with the traffic forced through the supervisor. Building that
proxy is the remaining Category B work.

> *Flag naming, so this stays reproducible: `HACS_DENY_INET=1` was opt-**in** while denial was
> experimental. Since §5.10 denial is the default and the flag inverted to `HACS_ALLOW_INET=1`,
> which restores the pre-fix behaviour for before/after runs. `HACS_DENY_INET` no longer exists.*

**Honest limits, all in the results doc:** tested on x86_64/WSL2 only — **the Pi 5 is aarch64 and
unverified**, and that is the cheapest next check; seccomp is a denylist over default-allow, not
an allowlist (justified, but should not be oversold); no network namespace and no cgroups, so
resource exhaustion is untouched; and the user namespace is itself attack surface, which the
denylist partly answers by removing `bpf`, `perf_event_open`, `setns` and module loading.

**Why this matters for the plan.** Every workstream now has either a result or a demonstrated
mechanism. Nothing remaining is blocked on something unproven — which was the actual question
being asked.

### 5.10 Lateral movement closed — the supervisor brokers egress ✅ (2026-08-14) ⭐

Full write-up: **`RESULTS_2026-08-14_egress_broker.md`**. Closes the gap §5.9 left open, and it
was the largest one: the `network:` allowlist was *advisory*, so a raw socket reached any LAN
device or internet host, unlogged.

**Why the old check could not be repaired.** `aiohttp_client` asked the supervisor for permission
and then let the sandbox open the connection. The check bound only an integration that chose to
use HA's HTTP helper; `import socket` walked past it. **The sandbox was the party making the
decision** — that is the defect, not a missing rule.

**The fix moves the decision to the side that cannot be skipped.** Seccomp denies
`socket(AF_INET)`/`AF_INET6` (default under `--isolate`), so the sandbox has no IP networking at
all — no TCP, no UDP, no DNS. `AF_UNIX` remains, so the bridge still works and is now the **only**
way out. All HTTP is serialised over it and performed by the supervisor (`spike/egress.py`, ~170
lines), which checks the manifest per request *and per redirect hop*.

**Result: the probe reaches 8 of 8**, from 4 of 8 unisolated *(on the 8-check probe of that
moment; checks 9 and 10 were added hours later when the threat model found T14 in this very
broker — §12.2. Current figures are 6/10 and 10/10.)* All three integrations produce
identical operation counts (7, 44, 18) and none was modified. Two side effects worth recording:
the **redirect gap closed for free** (each hop is re-authorised — a declared host answering `302`
to an undeclared one is now denied), and the **audit log improved** from a permission question to
what actually happened: `http_request -> allow | fetched chaos2.aa.net.uk [200]`.

**A measurement error was found and fixed in the process.** Checks 7 and 8 originally used
hostnames, but `socket.create_connection()` resolves before opening a socket, so they failed with
`gaierror` and never reached the layer under test — and `gaierror` looks identical whether a name
does not exist or the sandbox has no network. Both now use RFC 5737 documentation *addresses*, and
the probe distinguishes a refused syscall (`EPERM`/`EACCES`/`EAFNOSUPPORT`) from a request that
merely failed in transit. **A control has to be measured where it actually sits.**

**This created new attack surface, and saying so is part of the result.** The supervisor now
parses attacker-controlled URLs, headers and bodies and issues requests on the sandbox's behalf —
a confused deputy by construction. Eight limits bound it, each verified: scheme allowlist (no
`file://`), per-hop re-authorisation, 8 MiB response cap, 30 s timeout cap, header count and
length caps, CRLF rejection, no ambient `http_proxy`, and **Home Assistant's own host blocked
unconditionally regardless of manifest**. The residual is honest: ~170 lines of new trusted code,
small enough to review, but a bug there is a bug in the trusted half.

**The argument to make in the report is about attacker cost, not elimination.** Before: one line
of Python reaches any device on the LAN, unlogged. After, the attacker must either declare the
host in the manifest — where it is *visible in a public repository*, a weather integration
inexplicably naming the lock's address — or find a bug in 170 reviewable lines, or break seccomp
and the namespaces with a kernel exploit. **The open-source nature of HACS is what makes option
one expensive:** the manifest gives reviewers a declared baseline, turning "is this integration
overreaching?" into a mechanical question. The control's value is as much in what it makes
checkable as in what it blocks.

**Still open and structural:** exfiltration through a host the manifest *legitimately* declares.
An allowlist governs destination, not content. No allowlist fixes this; it belongs in the threat
model as accepted.

### 5.11 Test matrix — and four defects only wider testing could find ✅ (2026-08-14)

> **Updated later the same day: a fifth defect followed, in probe check 9 — see §12.2b.** The
> running tally is **four of five in measurement code**, and the lesson below is the reason it is
> worth counting at all.

Prompted by a direct question: *"did you test the current system against multiple integrations
with multiple scenarios?"* The honest answer was **no** — three integrations had been run for
operation counts, but the eight-check adversarial probe had only ever run against *one*
(`andrews_arnold_quota`), and the real-HA path had not been re-run since egress was rewritten.

Widening the matrix immediately found four defects. Three were not in the security mechanisms at
all but **in the things that measure them**, which is the more dangerous category, because a
broken measurement reports success.

| # | Defect | Why single-target testing could not find it |
|---|---|---|
| 1 | Probe check 2 hardcoded `startswith("sensor.andrews_arnold")`, so **matomo's own 15 entities counted as "belonging to others"** — a false ALLOWED | Only wrong for integrations other than the one it was written against |
| 2 | `run_targets.sh` used `HA_ARGS=(...)` rather than `+=` when `HA=1`, **silently discarding `--isolate`** | Only wrong when two options were combined; each worked alone |
| 3 | Relative redirects resolved against the *rewritten* URL, so an **in-allowlist redirect was wrongly denied** | Only wrong for the positive case; the negative case (off-allowlist) passed, which looked like the feature working |
| 4 | Audit run ids were second-resolution and the log opened in **append** mode, so two runs starting in the same second shared a file and `verify()` reported a **false "chain broken"** | Needs two runs close together — invisible in any single run, and it surfaced only when the matrix was run in a loop |
| 5 | *(later the same day, §12.2b)* Probe check 9 reported **BLOCKED because the request timed out**, not because policy refused it — it would have shown the fix working before the fix existed | Needs the before/after to be *run* rather than assumed; a check written against a fixed system never sees it |

**Defect 1 was fixed twice.** The first fix compared against "entities this sandbox published this
run" — which then false-alarmed against *real* HA, where matomo's entities legitimately persist
from an earlier run. The correct measure is the integration's **declared scope** (its own manifest
patterns, now passed in as `HACS_DECLARED_SCOPE`), because that is the property the supervisor
actually enforces. Two wrong proxies before the right one, each exposed by widening the matrix
again.

**Defect 3 is the one worth citing in the report.** The redirect test that *passed* was the denial;
the one that failed was the legitimate case. A control that blocks everything looks identical to a
correct control until you test the positive path. `spike/test_egress.py` now covers both
directions for every rule.

**Defect 4 is the most serious of the four**, and it is the one an examiner would enjoy finding.
The framework's headline includes a *tamper-evident* audit log; this bug made it report tampering
that had not happened. **A control that cries wolf is worse than one that is merely absent** — it
trains the operator to ignore it, and it would have discredited a live demo. Root cause: a chain
is only meaningful within one file, but nothing enforced one-file-per-run. Fixed on both sides —
run ids now include the pid (two processes cannot share one), and the log opens with `"x"`
(exclusive create) so a collision raises instead of silently appending. `spike/test_audit.py`
asserts both, and also asserts the **known limit** that an unkeyed chain can still be rebuilt
wholesale (§5.8), so that limit cannot quietly be mistaken for a fixed bug later.

**How it was found is the point:** not by reading the code, but by running the matrix four times
in a row and noticing the result was not the same each time. **An intermittent pass is a finding.**

**Now mechanical rather than claimed.** `spike/test_matrix.sh` runs the full matrix with
assertions — 3 integrations × {stub, real HA, bridge} × {baseline, isolated} × {with, without
probe}, plus the egress policy suite, the audit-log suite and the seccomp self-test.
**15 assertions without Docker, 24 with `HA=1`, all passing and stable across repeated runs** —
including `HACS_ALLOW_INET=1` restoring the pre-fix 6/8 so the before/after stays reproducible.
*(Both figures are on the 8-check probe of that moment; checks 9 and 10 arrived with §12.2, making
the same three assertions 6/10, 10/10 and 8/10.)*

```bash
./test_matrix.sh          # stub-house scenarios, no Docker needed
HA=1 ./test_matrix.sh     # ...plus real Home Assistant and the bridge
./test_egress.py          # 17 egress policy cases on their own
./test_audit.py           # hash chain: what it proves, and what it does not
```

**Two methodological points for the write-up**, both generalising beyond this project:

1. **Evaluation apparatus needs testing as much as the system does.** Four of these five defects
   were in measurement code rather than in controls, and a broken measurement reports success. An
   evaluation chapter that says "10 of 10 blocked" should also say how the probe was validated.
2. **Run the suite more than once.** Defect 4 was invisible to any single run and only appeared as
   a result that changed between identical invocations. Intermittency is information; a suite that
   is only ever run once cannot report it.

---

## 6. Open decisions

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | ~~**Compatibility strategy**~~ **SETTLED 2026-08-12** | (a) shim so real integrations run unmodified; (b) own SDK + toy integrations; (c) hand-port 2–3 and measure cost | **(a).** The spike (§5.3) ran a real integration unmodified, so the fallback to (c) is no longer needed. Still scoped to a core + generated constants with measured coverage reported — not "everything runs unmodified". |
| 2 | ~~**Isolation primitive**~~ **SETTLED 2026-08-14 — by building it** | namespaces+seccomp / gVisor+its trace sink / gVisor+eBPF-as-boundary-verifier | **namespaces + seccomp, now implemented and measured (§5.9).** The recommendation was acted on rather than merely accepted: user + PID + mount namespaces with an allowlisted root and a 25-rule seccomp denylist, ~260 lines, unprivileged, probe 4/8 → 6/8, and 8/8 once egress was brokered (§5.10) — **10/10 on today's 10-check probe, §12.2**. The trade-off stated below is unchanged and should still be argued explicitly — a syscall boundary is weaker than a fake kernel, and the seccomp policy is partly a response to that, removing `bpf`, `perf_event_open`, `setns` and module loading from the sandbox's reach. Original reasoning: **namespaces + seccomp** — coherent with eBPF, lighter on the Pi, and defensible as "controls proportionate to the threat model" (his language). |
| 3 | ~~**Target pattern**~~ **SETTLED 2026-08-14** | polling_sensor only (24.8% of repos but **only 10.6% of installs**) vs. extending to actuators (46.7% of repos and **64.8% of installs**) | **DECIDED: polling sensors as implemented scope; actuators as a stretch goal / basic PoC.** Younes' call, 2026-08-14, and it matches the recommendation that was already worked out below. The decision was taken directly rather than at a meeting because the advisor contact is now expected to be **an email carrying the proposal**, not a live discussion — so there was no meeting to defer it to, and leaving it open was blocking work for no benefit. Rationale for the choice: guarantee a deliverable result and keep scope tight, rather than gamble the isolation + threat-model budget on a 2–3 week inbound command path. **What this unblocks:** the shim freeze's *scope* rationale (§10.3 reason 1) is now void — the symbols needed are settled. Reason 2 (ownership) still stands, so the freeze holds by choice, not by uncertainty. **Original analysis, retained because the report needs it —** install weighting (§5.2b) cut against the polling-sensor default: by repo count it looked like a quarter of the ecosystem; by what people actually run it is a tenth, while actuators are nearly two-thirds. Actuators are simultaneously where the threat model has teeth *and* where the users are — a security auditor will notice both. **But full-platform support is not the right response — see §10.1, measured 2026-08-13.** Implementing all 21 HA entity platforms moves coverage from 1.2% to only 2.1% of installs, because platforms were never the real blocker (`homeassistant.helpers`, `.util`, `.helpers.event`, `.helpers.storage` block far more integrations than any platform). Actuators also require an **inbound** command path the framework does not have yet (HA → sandbox), versus the outbound-only path built so far. And manifest confinement is structurally weaker for actuators: it stops an integration reaching *other* devices, not misuse of the *one* device it legitimately declared and controls (the 3am-unlock scenario). **Recommended position for the meeting:** keep polling_sensor as the implemented scope; analyse actuators fully in the threat model, including the declared-capability-abuse limit; build **one** actuator platform (`switch`) end-to-end as an architecture proof, not a coverage push. Present 24.8%/10.6% together, and bring the 21-platform coverage table as evidence the scope call is deliberate, not avoidance. |
| 3b | **Which integrations to target inside the pattern** — new, 2026-08-13 | arbitrary / alphabetical (what happened so far) vs. **most-installed first** | **Most-installed first.** The top 20 polling sensors are 52% of all polling-sensor installs, and several are already within reach of today's shim — `MarcoGos/kleenex_pollenradar` (1,569 installs) and `delphiki/hass-tarif-edf` (1,473) need **zero** additional symbols; `jonandel/ha-hildebrandglow-dcc` (1,718) needs one. "Runs integrations installed on thousands of real systems" is a far stronger claim than "runs three integrations", for identical effort. |
| 4 | **Report requirements** | literature-review chapter? page target? | **Unknown — ask the advisor / check programme handbook.** |

---

## 7. Glossary (for future sessions)

- **Shim** — a fake replacement library with the same outside shape as the real one, so
  calling code can't tell. Here: a fake `homeassistant` package placed first on the
  sandbox's `sys.path`. The integration still calls `hass.states.async_set(...)`
  unchanged, but the call becomes a socket message to the supervisor instead of direct
  memory access. Python imports are just files on a path — control the path, control what
  `import homeassistant` resolves to.
- **Integration pattern** — the recurring architectural *shapes* HA integrations take
  (polling sensor, actuator, push/stream, local discovery, OAuth cloud). Scoping the shim to
  one pattern is what makes the API surface tractable.
- **Namespaces + seccomp** — Docker-style isolation. Real kernel, but it lies to the process
  about what filesystem/processes/network exist; seccomp blocks specific syscalls.
- **gVisor** — inserts a *fake kernel* (the "Sentry", written in Go) in userspace between the
  app and Linux. Stronger isolation, heavier, and it hides the app from host eBPF.
- **eBPF** — small programs loaded into the running Linux kernel that fire on events
  (file open, network connect, process spawn). Sensors inside the kernel. Used by Falco.
- **Confused deputy** — the privileged component (HA) is tricked into misusing its own
  authority on an attacker's behalf. The attacker never escapes the sandbox because they
  never need to.
- **Long-lived access token** — the credential HA issues for its REST/WebSocket API. It is
  **unscoped**: there is no read-only or sensors-only variant, so holding it is full control of
  the house. It is just text, so anything that can *read* it holds it. The supervisor holding it
  and the sandbox not holding it is the premise the whole confinement argument rests on (§5.8).
- **Environment variables** — a bag of labelled name/value notes carried by every running process.
  A child process receives a **copy of its parent's entire bag by default**, which is why secrets
  passed this way leak into children unless deliberately removed.
- **`/proc`** — a Linux pseudo-filesystem presenting every running process as files.
  `/proc/<pid>/environ` exposes that process's environment variables and `/proc/<pid>/cmdline`
  its command line, **both readable by any process running as the same user**. This is why
  process separation alone does not protect a secret held by the parent (§5.8).
- **PID namespace** — a kernel feature that gives a process its own view of the process table, so
  it can see only itself. It cannot read another process's `/proc` entries because from inside,
  those processes do not exist. Together with a separate uid, this is what closes §5.8's findings.
- **Hash chain** — an append-only log where each record's SHA-256 fingerprint is computed over its
  own contents **plus the previous record's fingerprint**, so editing, deleting or reordering any
  record breaks every fingerprint after it. Provides **tamper-evidence**, not tamper-proofing.
  Two limits it does not cover, both live here (§5.8): it says nothing about events that were
  never recorded (**integrity ≠ completeness**), and an *unkeyed* chain can be rebuilt wholesale
  by anyone who can write the file. An **HMAC** — a hash keyed with a secret — closes the second.

---

## 8. Next steps

> ⏸️ **PAUSED 2026-08-13, gate revised 2026-08-14 — shim coding remains on hold, for one reason
> now instead of two.**
>
> The original pause had two justifications (§10.3). **The first is now void:** Decision 3 was
> settled on 2026-08-14 — polling sensors as implemented scope, actuators as a stretch/PoC — so
> the shim's next increment no longer depends on an unanswered question. **The second still
> stands:** the shim is the hardest part of the codebase to personally own and contributes least
> to the security argument, so effort stays concentrated on the ~1,200 lines that carry the
> actual claim. The freeze therefore continues **by choice, not by uncertainty**, and can be
> lifted deliberately whenever the threat model is drafted.
>
> **Current focus is unchanged: the threat model** (§10.4, §11), which is required for the
> proposal regardless and is the highest-weight artifact for this advisor. Note that the advisor
> contact is now expected to be **an email carrying the proposal** rather than a live meeting
> (see #6 below), so there is no meeting to wait on — the proposal is the deliverable.
>
> **New since the pause:** §5.8 records two findings from a self-audit of the security core, and
> **§5.9 records that isolation (workstream 4) is now built** — user + PID + mount namespaces
> with an allowlisted root and a seccomp filter, ~260 lines, unprivileged. The adversarial probe
> goes from 6/10 to **10/10** blocked (§5.10 closed checks 7–8, §12.2 added and closed 9–10) and all three integrations run
> unchanged. This does not reopen the
> shim: it was the security core that grew, which is exactly where effort was meant to
> concentrate. **The plan no longer contains anything unproven** — every workstream now has
> either a result or a demonstrated mechanism.

### August (before the semester) — de-risk, don't build

> **#4 (shim spike) is DONE and came back GO — see §5.3. The one remaining item that
> cannot slip is #6 — now the *proposal email*, not a meeting (revised 2026-08-14, §11.1).
> Decision 3 no longer travels with it as a question; it is settled in §6 and is stated in the
> proposal as a costed scope decision.**
>
> The spike changes what the proposal leads with: there is now a working demo, a
> four-of-five adversarial result with an honestly-stated gap, and a measured coverage
> number. Lead with the demo and the measurement. Since #6 is written rather than spoken, it
> must also carry §5.8's self-audit — the weaknesses will not come up in conversation, so
> reporting them is the only way they get credited.

1. ✅ **DONE (2026-08-21) — environment, and the distro call reversed.** See §13.
   ~~Install **Ubuntu Server 24.04 LTS arm64** on the Pi 5 — *not* Raspberry Pi OS, whose
   kernels have historically shipped without `CONFIG_DEBUG_INFO_BTF` that modern eBPF tooling
   needs.~~ **Void:** eBPF left the architecture with Decision 2, so BTF buys nothing, and
   Ubuntu 24.04 would actively cost a sysctl (`kernel.apparmor_restrict_unprivileged_userns`)
   to permit the namespaces `isolate.py` depends on. **Staying on Raspberry Pi OS** (trixie,
   kernel 6.12.47, aarch64), where unprivileged namespaces, seccomp and cgroups v2 all work
   untouched — and which is also what Pi-based HA users actually run. Full probe passes 10/10
   there; no cloud VM needed.
2. ✅ **DONE (2026-08-13) — real HA behind the supervisor.** See §5.5. Stock 2026.8.1 image,
   unmodified; 25 entities published into it by three sandboxed integrations; probe re-run
   against it with a paired baseline comparison (43 entities readable without the framework,
   2 with). The retrofit claim in §9 is now demonstrated rather than intended.
   ✅ *Follow-ups also done:* the registry gap is quantified in §5.6 (no registry row, no
   config entry, no device, **0/15 entities surviving a restart vs 15/15 native**) and then
   **closed in §5.7** by `sandbox_bridge`, a ~250-line trusted native integration — all four
   measures now at parity, 25 registry-backed entities across the three targets. Restart
   survival is now the bridge's doing rather than the supervisor's, which also relaxes the
   "supervisor must be long-running" requirement into "should be, for freshness".
3. ✅ **DONE (2026-08-13) — full catalogue analysed** (3105 repos, 3075 parsed). See §5.2:
   polling sensors are 24.8% of the catalogue, not 15%, and the head of the symbol
   distribution held up at n=763. Selection-bias caveat retired.
4. ✅ **DONE (2026-08-12) — shim spine prototyped, result GO.** See §5.3 and `spike/README.md`.
   Follow-on work, in value order, none of it blocking the advisor meeting:
   - **Real HA behind the supervisor** — promoted to item 2 above; it now outranks
     everything else here.
   - ✅ **DONE (2026-08-13) — second and third integrations** (`abnvle/ha-matomo`,
     `aniolpages/ha-icqa`) run end-to-end. Forced the `FrozenOrThawed` fix above.
   - ✅ **DONE (2026-08-13) — constants generator** (§5.4). Shim 350 → 814 names.
   - **Targets #4 and #5, chosen by installed base** (Decision 3b, §6):
     `MarcoGos/kleenex_pollenradar` and `delphiki/hass-tarif-edf` need **zero** extra symbols
     and carry ~1,500 real installs each. `spike/README.md` documents the four-step recipe.
   - **`binary_sensor` + `util.dt` + `entity_registry` + `restore_state`** — the behavioural
     work that now dominates the blocker list (§5.4). Not generatable; budget accordingly.
   - ✅ **DONE (2026-08-14) — filesystem and process isolation** (namespaces + seccomp). See
     §5.9. Deferred on 2026-08-13, then built on 2026-08-14 to answer whether the project was
     completable end to end. The fifth probe row is now blocked, so the security chapter reports
     **10 of 10** (§5.10 closed checks 7–8; §12.2 added and closed 9–10) rather than explaining an unblocked filesystem row. The 2021 HACS file-theft reproduction is now reachable.
     *Remaining:* egress proxy, cgroups, and verification on aarch64.
5. **Draft manifest schema** (strawman is in §2).
6. ⭐ **Send the advisor a ~2-page pre-proposal** — problem, evidenced gap, architecture
   sketch, deliverables, risks, and the coverage-curve figure. Secure buy-in *before*
   writing the full document; advisors invest more in projects they helped shape.

   **Revised 2026-08-14: this is expected to be an email, not a live meeting.** That changes
   what it has to do. A meeting can be exploratory and leave decisions open; an email must
   **state positions and invite correction**, because there is no back-and-forth to rely on.
   Consequences:
   - **Decision 3 is stated, not asked.** ~~polling sensors only, or push into actuators?~~
     Settled 2026-08-14 (§6): polling sensors as scope, actuators as a stretch/PoC. Present it
     as a costed scope decision — bring the 21-platform table (1.2% → 2.1%) as evidence it is
     deliberate rather than avoidance — and invite disagreement rather than requesting a ruling.
   - ~~**Two questions genuinely remain open**~~ **One remains, 2026-08-14:**
     - ~~Which threat-modelling framework?~~ **SETTLED — `ISO 31000` for the process, `STRIDE`
       for identification.** Not a guess: both were taught in Younes' cybersecurity module, so
       he can defend the choice from coursework rather than from a citation. `THREAT_MODEL.md`
       Part 0 states how they join — STRIDE occupies ISO 31000 clause 6.4.2, which the standard
       deliberately leaves open for a technique. State this in the email as a decision made,
       and invite redirection.
     - Does the programme require a literature-review chapter, and is there a page target?
       *(Decision 4 in §6 — still unknown.)*
   - **Lead with the demo and the measurement**, and include §5.8's self-audit. For an advisor
     who is a lead auditor by profession, a team that reports two weaknesses in its own security
     core — with tests, and with the fix scoped — is showing the exact discipline being graded.

### Semester skeleton (~10 engineering weeks)
| Weeks | Work |
|---|---|
| 1 | HA API surface study; finalise manifest schema |
| 2–3 | Sandbox runner + process lifecycle + socket transport |
| 3–6 | **Compat shim + permission-enforcing bridge** ← the heart; protect this time |
| 6–7 | Manifest policy engine; read/subscription filtering; egress allowlists |
| 7–8 | Monitoring + hash-chained audit log *(sequenced last so it is cuttable)* |
| 8–9 | Adversarial test suite + measurements |
| 9–10 | Write-up, defence prep |

### Evaluation chapter — four axes (a demo is not a result)
1. **Compatibility** — how many real HACS integrations run unmodified vs. with *N* lines changed.
2. **Security** — attack scenarios derived from the threat model, pass/fail. **Including:
   reproduce the 2021 HACS file-theft vulnerability pattern against baseline HA (it works)
   and against the framework (it's blocked).** This is the single strongest result available.
3. **Performance** — added latency per state update, memory per sandboxed integration,
   max concurrent integrations on a Pi 5.
4. **Coverage** — honest table of supported vs. unsupported HA API surface.

### Framing for this specific advisor (auditor/architect)
Write for an auditor, not a hacker: explicit threat model with named trust boundaries,
a threat → control → layer → residual-risk table, and an evaluation *methodology* with
pass/fail criteria rather than a demo. Reuse the frameworks from his course (STRIDE, attack
trees, ISO 27001 / NIST — **confirm which**). Stated scope limits are an asset with him.

---

## 9. What this project actually claims (positioning) ⭐ 2026-08-13

Prompted by the right question: *"is what we are doing just 'if Home Assistant were rewritten
to be more secure, this is how it could be'?"* At 1.2% install coverage (§5.4) that question
will be asked in the defence, so the answer belongs in the report.

**No — and the distinction is the project's main asset.** The design requires **zero changes
to Home Assistant**. The supervisor sits *beside* stock HA and speaks to it through the REST
and WebSocket APIs that already exist and are already public; the integration runs unmodified.
Nothing upstream has to accept a patch, change an interface, or agree. That is a **retrofit**,
not a redesign — and redesign proposals are cheap to write and nobody has to adopt them.

**✅ PROVEN 2026-08-13 — see §5.5.** This was the open caveat: the supervisor talked to
`DEFAULT_HOUSE`, a hardcoded dict, so "works against unmodified HA" was an intention rather
than a demonstrated fact. It is now demonstrated. A stock
`ghcr.io/home-assistant/home-assistant:2026.8.1` container, no patches and no custom
components mounted, receives 25 sensor states from three unmodified HACS integrations running
outside its process under manifest enforcement. The retrofit claim is now evidence, not
design intent.

**Where the framing is genuinely vulnerable** — put these in the report rather than letting an
examiner find them:

- Users install HACS integrations *into HA's config directory*, and HA loads them. Using this
  framework means installing them somewhere else instead: a **workflow change for the user**,
  even though it is not a code change for HA.
- ~~Entities published over the REST API are not identical to natively-loaded ones.~~
  **Measured in §5.6 and then closed in §5.7.** The gap was real — no registry row, 0 config
  entries, 0 devices, 0/15 surviving a restart — and `sandbox_bridge`, a ~250-line trusted
  native integration, brings all four to parity with a native install. The framework no longer
  produces second-class entities. Keep both halves in the report: the measurement is what
  justified the design.
- HA's own "Remote Integration Execution" RFC moves toward process separation for
  non-security reasons. Engage directly: this supplies the **policy layer** their mechanism
  would need. Do not wait to be asked.
- ~~**The confinement demonstrated so far is API-level, not containment.**~~ **Largely closed
  2026-08-14 (§5.9), but the framing lesson survives and belongs in the report.** §5.8 found that
  a sandbox sharing a uid with the supervisor could read the HA token from `/proc` and bypass
  mediation entirely — so probe results were results about the **mediated path** only. Isolation
  now closes the filesystem and process routes, §5.10 closed the network ones and §12.2 closed the
  broker's own — **probe 6/10 → 10/10**. The precise claim today is *"an integration cannot read the host, steal the credential,
  reach the HA API unchecked, or open a socket the manifest never authorised — but nothing stops
  it sending whatever it likes to a host it legitimately declared."* Say exactly that. The
  general lesson — **distinguish results about the mediated path from claims about all paths** —
  is worth stating once explicitly, because it is what made two separate findings visible.

**The accurate one-sentence claim:** *a demonstrated mechanism for confining unmodified HACS
integrations against a stock Home Assistant, plus the first empirical measurement of what
applying it across the real ecosystem would cost.* Both halves are contributions and the
second is the more novel one — no published account of the HA API surface appears to exist.
That sentence stays honest at 1.2% coverage; "a sandboxing framework for HACS" does not.

---

## 10. Scope conversation and the plan going forward — 2026-08-13, end of day

After §9 was written, the conversation turned to whether the project as it stood was the
right size and whether it was something Younes could own and defend, not just something that
had been built. Recorded here because it changed the plan, not just the mood.

### 10.1 "Should we just cover the top integrations too?" — priced, not just answered

Two versions of that question, with different answers:

**"Target integrations by install count rather than arbitrarily"** — **yes, already Decision
3b.** Cheap and already actionable: `kleenex_pollenradar` and `hass-tarif-edf` need zero new
symbols and carry ~1,500 real installs each.

**"Support the actuator pattern generally, since that's most of the installed base"** —
**priced, and it does not pay off the way it looks like it should.**

| scope | integrations | share of installed base |
|---|---|---|
| today | 141 | 1.2% |
| + `binary_sensor` | 182 | 1.5% |
| + all 21 HA entity platforms (every actuator + `binary_sensor`) | 308 | **2.1%** |

Implementing **every entity platform HA has** — sensor, switch, button, select, number,
climate, cover, fan, light, lock, vacuum, siren, water_heater, humidifier, lawn_mower, valve,
text, update, media_player, remote, scene — moves coverage from 1.2% to 2.1%. Platforms were
never the binding constraint. What still blocks integrations once every platform exists:

```
1437  homeassistant.helpers          881  homeassistant.helpers.event
1017  homeassistant.util             511  homeassistant.helpers.storage
 498  homeassistant.core             437  homeassistant.helpers.restore_state
 362  homeassistant.components.http  304  homeassistant.helpers.dispatcher
```

Deep HA internals — event scheduling, persistent storage, state restoration, dispatch,
integrations serving their own HTTP endpoints — not platform classes.

**Two further reasons actuators are not "just more shim":**

1. **Architecture, not just coverage.** Everything built so far is outbound only: integration
   polls → publishes → HA. Actuators need an inbound path — HA receives a service call (user
   flips a switch) and must route it *into* the sandboxed process. The supervisor does not
   listen for HA service calls yet; the sandbox is a script, not a server. Estimated 2–3 weeks,
   which is most of the isolation + threat-model budget.
2. **Manifest confinement is structurally weaker for actuators, and this belongs in the threat
   model, not just the roadmap.** A manifest constrains *which* devices/services an integration
   reaches — it stops lateral movement. It cannot constrain *when or why* an integration uses a
   capability it legitimately declared. A malicious lock integration declaring
   `network: [api.lockvendor.com]` — which it genuinely needs to function — can still unlock
   the door at 3am through that same declared, legitimate channel. The framework prevents a
   compromised lock integration from becoming a whole-house compromise; it does not make lock
   integrations safe. State this precisely rather than letting it be discovered under
   questioning.

**Resulting plan:** freeze the general shim (§10.3). Build **one** actuator platform end-to-end
(`switch` is the natural pick — simplest command shape) as an *architecture* proof that the
inbound path works, not as a coverage push. Analyse actuators fully in the threat model,
including the declared-capability-abuse limit above. Bring the 21-platform table to the
proposal as evidence the scope call is deliberate. *(Settled 2026-08-14 — see §6 and §11.1;
this section is the analysis that produced the decision.)*

### 10.2 The five workstreams, and where each actually stands

The project is not one thing called "the shim." It is five, and the shim is the one furthest
along and the one that contributes least to the security argument:

| # | workstream | status |
|---|---|---|
| 1 | **Evidence / measurement** (§5.2, §5.4) | ✅ done — the novel contribution |
| 2 | **Compatibility (the shim)** (§5.3, §5.4) | ✅ substantially done — **now frozen, see §10.3** |
| 3 | **Mediation / policy** (supervisor, §5.3, §5.5–5.7) | ✅ core done; manifest schema still a strawman. ⚠️ **§5.8: mediation is currently *evadable*, not merely incomplete** — the sandbox can obtain the HA token and bypass the supervisor entirely. Policy logic is sound; its *unavoidability* depends on workstream 4. |
| 4 | **Isolation** (namespaces + seccomp + brokered egress) | ✅ **built 2026-08-14** — see §5.9, §5.10, `RESULTS_2026-08-14_isolation_spike.md` and `RESULTS_2026-08-14_egress_broker.md`. User + PID + mount namespaces with an allowlisted root, a 27-rule seccomp filter denying IP sockets, and supervisor-brokered HTTP. Probe goes **6/10 → 10/10** blocked; all three integrations run identically. **Outstanding:** cgroups (resource exhaustion); WebSockets not brokered. **Unverified:** aarch64 / the actual Pi. |
| 5 | **Evaluation + write-up** | ⚠️ 2 of 4 axes have data (compatibility, security-partial); performance is untouched; threat model is unwritten. §5.8 supplies two drafted threat→control→residual-risk rows to start it with. |

**What is genuinely banked regardless of how Decision 3 resolves** — i.e. the minimum
significant result already secured: the empirical measurement (§5.2/§5.4, likely the strongest
single artifact — no comparable published account of the HA API surface appears to exist);
three unmodified HACS integrations running against a stock HA (§5.5); API-level confinement
with a paired baseline, 43 entities readable without the framework vs 2 with (§5.5); tamper-
evident audit with detection demonstrated (§5.3); first-class entity registration via
`sandbox_bridge` (§5.7); **four** methodological findings that show self-correcting work
(`FrozenOrThawed`, the registry gap, the install-weighting reversal, and the §5.8 self-audit).

~~**What is not banked:** containment.~~ **Banked as of 2026-08-14 — see §5.9.** This paragraph
previously read "the framework stops API misuse; it does not yet stop `open('/etc/passwd')`". It
now does. Isolation was built the day after this was written, and the adversarial probe goes from
6/10 to **10/10** blocked with all three integrations running unchanged. **Add to the banked list:**
filesystem and process containment via unprivileged namespaces, with a measured before/after; the
2021 HACS file-theft pattern reproducible as *blocked*; and a fifth self-caught gap (§5.8's
credential leak) closed and demonstrated.

**What is still not banked, precisely:**

- ~~**Network containment.**~~ **Banked 2026-08-14 (§5.10).** The allowlist is now enforcing:
  seccomp denies IP sockets and the supervisor performs all HTTP, checking each redirect hop.
  Probe 10/10. *What remains is content, not destination* — exfiltration through a legitimately
  declared host, which is structural and belongs in the residual-risk table.
- **Resource containment.** No cgroups, so a malicious integration can still exhaust CPU or RAM.
  Availability is a security property and this belongs in the threat model.
- **Verification on the real target.** Everything is tested on x86_64 under WSL2; the Pi 5 is
  aarch64 and unverified. Cheapest outstanding check.

The qualifier on two earlier banked items still applies and should be stated once in the report:
the API-level confinement result (§5.5) and the tamper-evident audit (§5.3) are sound **for the
mediated path**. Isolation is what makes that path unavoidable for the filesystem and the process
table; it does not yet do so for the network.

### 10.3 Why the shim is paused, specifically

Two independent reasons were given. **As of 2026-08-14 only the second survives — see the note
after reason 1.**

1. ~~**Decision 3 is unresolved and the shim's next increment depends on the answer.**~~ Building
   more `sensor`-side symbols now is wasted if the advisor meeting settles on actuators; the
   symbols needed diverge (§10.1). Building before that conversation is the risk, not building
   less.

   > **VOID as of 2026-08-14.** Decision 3 is settled (§6): polling sensors as implemented scope,
   > actuators as a stretch/PoC. The advisor contact is an email carrying the proposal, not a
   > meeting, so there was nothing to defer to. The `sensor`-side symbols are the right ones and
   > building them is no longer a gamble.
2. **The shim is the hardest part of the codebase to personally own, and also the part that
   contributes least to the argument.** By line count: shim (hand-written + generated) is
   ~3,600 lines; the security core (supervisor + runner + probe + backend) and the measurement
   tools together are ~1,200 lines of comparatively ordinary Python (parse, count, check, log)
   — the metaclass work in `frozen_dataclass_compat.py` is the one genuinely advanced piece,
   and advanced by any standard, not a personal shortfall. Freezing the shim concentrates
   remaining effort on the ~1,200 lines that carry the actual claim and that are realistic to
   fully understand and defend.

**What "frozen" means in practice:** the three existing integrations, the generated constants
layer, and `shim_coverage.py` stay as they are. No new HA symbols are added and no new
integration targets are onboarded until Decision 3 is settled. Targets 3b's zero-cost
candidates (`kleenex_pollenradar`, `hass-tarif-edf`) are a candidate exception — they cost a
manifest and a stub, not shim growth — but even those wait until after the threat model is
drafted, so the current focus stays undivided.

### 10.4 Immediate next action

> ✅ **DONE 2026-08-14 — `THREAT_MODEL.md` v0.1 exists. See §12.** ISO 31000 + STRIDE, 21
> threats, 6 retained residual risks, and it found a new High risk (T14) in the egress broker
> the moment it was applied to the code. The section below is kept as the brief it was written
> against; all four required residual risks appear, as R1–R4.

Write the threat model (workstream 5) before writing any more code, in `THREAT_MODEL.md`. It is
the highest-weight artifact for an advisor who is a lead auditor by profession, it is required
for the proposal regardless of how Decision 3 resolves, and — unlike the shim — it is work
Younes can own end to end, since it is reasoning about the design rather than Python
implementation detail.

> **Updated 2026-08-14 — it now has a running start.**
> `FINDINGS_2026-08-14_token_leak.md` Part 10 supplies **two completed
> threat → control → residual-risk rows** in the required format (credential disclosure across
> the sandbox boundary; audit-log completeness and forgeability), each with asset, boundary,
> actor, STRIDE category, attack, current control, planned control, residual risk and detection
> already filled in. Lift them in and build outward. §5.8 also fixes the first trust boundary
> concretely — supervisor (holds credential) ↔ sandbox (runs untrusted code) — with a measured
> account of where it currently leaks.

Skeleton to fill in: trust boundaries (who holds the HA token, where does untrusted code run,
where does the manifest get authored and by whom), asset list (device control, `secrets.yaml`,
occupancy/presence data, camera feeds), actor list (integration author — possibly malicious;
HACS as an unvetted distribution channel; the user, who both authors trust decisions and is
the asset owner), a STRIDE or attack-tree pass per boundary, and a threat → control → residual-
risk table. **Four** residual risks that must appear because they are already known, not
hypothetical:

1. **The over-declaring manifest nobody reads** — a weather widget that declares lock access is a
   red flag *if reviewed*, and there is currently no mechanism forcing review.
2. **Declared-capability abuse on the integration's own device** — §10.1's 3am-unlock scenario,
   which manifest confinement structurally cannot prevent.
3. **The supervisor holds an unscoped credential** (§5.8) — even with isolation built, compromise
   of the supervisor is full house compromise, because HA offers no scoped tokens. This is an
   *upstream* limitation, not a design flaw here, and should be stated as such.
4. **A local audit log cannot be authoritative against whoever controls the writer** (§5.8) —
   only external anchoring changes that, and full decentralised attestation is explicitly out of
   scope (`supervisor.py:83–85`).

Answer "who writes the manifest?" explicitly **in the proposal itself** — it will be asked early,
and an email affords no chance to answer it live. The honest position: the manifest does not stop a determined malicious author from
declaring what they need, the same way an Android permission list does not. It converts an
*invisible* capability into a *declared, reviewable* one, closing the silent-full-trust default
that exists today. That is the browser-extension precedent already cited in §4.4, stated as an
explicit limit rather than an implicit hope.

---

## 11. Decision 3 settled, and a self-audit — 2026-08-14

A short session with two outcomes, one planning and one technical.

### 11.1 Decision 3 is settled, and the advisor contact changed shape

**The advisor contact is now expected to be an email carrying the proposal, not a live meeting.**
That matters more than it first appears, because §8 and §10 had both been written around a
meeting that would settle open questions. There is no such meeting. Consequences already applied
above:

- **Decision 3 is decided rather than deferred** (§6): polling sensors as implemented scope,
  actuators as a stretch goal / basic PoC. Rationale: guarantee a deliverable result and keep
  scope tight, rather than spend the isolation + threat-model budget on a 2–3 week inbound
  command path. This matches the recommendation §10.1 had already worked out, so nothing is
  re-litigated — it is the same conclusion, now taken as a decision instead of a proposal.
- **The shim freeze narrows to one reason** (§10.3): the scope-uncertainty justification is void;
  the ownership justification stands. The freeze continues **by choice**, and can be lifted
  deliberately once the threat model is drafted.
- **The proposal must state positions, not ask questions** (§8 #6). An email has no
  back-and-forth. Present the scope decision as costed and invite disagreement; ask only the two
  questions that genuinely remain open (threat-modelling framework, literature-review
  requirement) and proceed with a default rather than blocking on either.

### 11.2 Self-audit of the security core

Full detail in §5.8 and `FINDINGS_2026-08-14_token_leak.md` (commit `2ab970a`). Two findings, both
confirmed by test, no repository code changed:

1. **The HA token reaches the sandbox by three routes** — the copied environment, and
   `/proc/<ppid>/environ` and `/proc/<ppid>/cmdline` via shared uid. An integration that reads it
   bypasses the policy layer rather than defeating it.
2. **The audit log's hash chain is unkeyed and records only mediated operations.** A rebuilt chain
   verifies as `OK` while asserting a denied `lock.unlock` was allowed (demonstrated on a real
   log); and a bypassed action leaves no record and no gap, because `seq` counts records created,
   not events that occurred.

**Both trace to one root cause** — the sandbox is a plain `subprocess` sharing a uid with the
supervisor — and one control, isolation, substantially addresses both.

**Why this was worth a session.** It converts workstream 4 from deferred hardening into a
precondition for two claims the project already makes, which is a stronger argument for building
it than "it lets us reproduce a 2021 CVE". It also sharpens what §5.3/§5.5's results actually
say: they are results about the **mediated path**, and the report should say so explicitly rather
than let a reader over-read them. And methodologically it is the fourth self-caught gap, which is
worth stating as a pattern in the write-up.

**Deliberately not fixed** *(at the time — see §11.3)*. Both weaknesses were left intact so the
"before" state stayed demonstrable and the fix could land with the finding. Two exceptions worth
considering early: the misleading comments at `supervisor.py:329` and `:79–85`, and **keying the
chain with an HMAC**, which closes the rebuild attack independently of workstream 4.

### 11.3 Isolation built, same day

Full detail in §5.9 and `RESULTS_2026-08-14_isolation_spike.md` (commit `6e42481`).

The trigger was a direct question — *can this project actually be completed end to end?* — and the
right way to answer it was to attack the one workstream at zero, since that was what made the plan
look risky. **It worked, in ~260 lines, unprivileged**: user + PID + mount namespaces, a root
filesystem built from an explicit allowlist, and a 25-rule seccomp denylist.

Three things are worth carrying forward beyond the result itself:

1. **The fix landed with the finding, as intended.** §5.8 said the weaknesses were being left
   intact so the before/after would be demonstrable. Probe checks #6 and #7 were added for exactly
   that purpose, and #6 goes ALLOWED → BLOCKED in the same day's work. That is a much better story
   than either half alone.
2. **Isolation cost the compatibility result nothing.** All three integrations produce identical
   operation counts isolated and not. This is the finding that makes the approach adoptable and it
   should be stated prominently — a security mechanism that broke the integrations would have
   undermined the project's central claim.
3. **The predictions held.** `ANALYSIS_2026-08-14_isolation_coverage.md` was written a few hours
   earlier and sorted the weaknesses into four categories. Category A closed exactly as predicted;
   Category B (network egress) stayed open exactly as predicted; and the Category D practical
   obstacles — "a mount namespace needs a working minimal filesystem" — showed up as three
   concrete bugs. Analysis before building was worth the time, and saying so is worth a line in
   the methodology chapter.

**What this does to the schedule.** Workstream 4 was the largest unstarted piece; it is now the
smallest remaining one. Nothing in the plan is blocked on something unproven. Remaining, in value
order: verify on aarch64, write the threat model, build the egress proxy, add cgroups, HMAC the
audit chain.

> **Superseded 2026-08-14, later the same day.** The egress proxy was built (§5.10) and the threat
> model written (§12). Current order is in §12.4 — and it starts with a *new* item the threat
> model surfaced: the broker authorises host **names** without ever checking the address they
> resolve to.

---

## 12. Threat model written — and it found a new High risk — 2026-08-14

### 12.1 Framework choice settled from coursework

`THREAT_MODEL.md` v0.1 exists (workstream 5), built on **ISO 31000:2018 for the process** and
**STRIDE for identification**. The choice is not arbitrary: both were taught in Younes'
cybersecurity module, which means the method can be defended from what he actually knows rather
than from a citation — the same ownership criterion that keeps the shim frozen (§10.3).

**The join is the part to be able to state in one sentence.** ISO 31000 clause 6.4.2 is *risk
identification*, and the standard deliberately prescribes no technique for it — that is left to
IEC 31010, which catalogues techniques and expects you to choose. STRIDE fills that slot;
everything around it (context, criteria, analysis, evaluation, treatment, monitoring, recording)
is 31000. Also worth knowing: **ISO 31000 is guidance, not certifiable** — 27001 is the
certifiable one. An auditor will check whether that distinction is understood.

**Contents:** 7 assets, 5 actors, 5 trust boundaries, **21 identified threats** across the six
STRIDE categories, 10 probe checks, a 5×5 likelihood/consequence matrix with a stated tolerance, an inherent-vs-
residual register, an ISO 31000 §6.5.2 treatment-option mapping, a prioritised treatment plan,
and **six formally retained residual risks** (R1–R6) — the four required by §10.4 plus the
declared-capability limit and the surface added by the controls themselves.

**The headline number for the report: inherent 7 Critical / 7 High → residual 0 Critical /
6 High.** Every Critical eliminated, each backed by a measurement rather than an assertion. And
**not one of the six survivors is unfinished work** — four are structural limits of the design
(an allowlist governs destination not content; a self-declared contract is self-declared) or
upstream (HA has no scoped tokens), and two need a change to HACS itself. The two that *were*
fixable implementation gaps were found by the model and closed the same day (§12.2).

### 12.2 ✅ New finding, found and closed the same day: the broker checked host *names*, never destinations

Found while grounding the threat model in the code, and **measured, not theorised** (T14/T15).
Fixed hours later, with the measurement written first.

`egress.py:86–102` authorises a request by comparing `parsed.hostname` against the manifest
allowlist and `blocked_hosts`. It **never resolves the name and never inspects the address it is
about to connect to.** So the manifest constrains names, while the attacker controls the mapping
from names to addresses: declare `cdn.their-domain.example` — plausible enough to survive review —
and point its A record at `192.168.1.1`. The supervisor, trusted and *not* subject to the seccomp
`AF_INET` denial, then makes the request and hands back the body.

Demonstrated with the existing `Egress` class and `blocked_hosts=("127.0.0.1",)` exactly as
`supervisor.py` passes it: a manifest declaring `localhost` fetched a loopback URL, status 200,
body returned to the sandbox.

**Why it is more interesting than an ordinary bug.** §5.10 closed lateral movement by denying the
sandbox `AF_INET` — probe checks 7 and 8 ALLOWED → BLOCKED. But denying the sandbox sockets meant
giving the supervisor the job of fetching on its behalf, and the supervisor has no such
restriction. **The control that closed the hole re-opened a version of it one layer up, through
the deputy it created.** A textbook confused deputy, and the cleanest available illustration of
the governing principle: every control adds surface, so the question is never "is it closed" but
"what did closing it cost". Note too that such a request is logged as *allowed* to a *declared*
host — the audit log is complete, intact, and reports nothing wrong.

**Treatment, applied 2026-08-14.** Probe checks 9 and 10 were written **first**, against the
unfixed broker, so the before/after is a measurement:

```
BEFORE  [ALLOWED] broker: declared host → LAN address   allowed by policy, failed in transit
        [ALLOWED] broker: declared name → loopback      supervisor fetched localhost for us
AFTER   [BLOCKED] broker: declared host → LAN address   192.0.2.10 is private, not a public destination
        [BLOCKED] broker: declared name → loopback      127.0.0.1 is loopback, not a public destination
```

`egress.py` now resolves in the broker; refuses loopback, link-local, multicast, unspecified,
reserved and private addresses; refuses if **any** answer is bad rather than only the one about to
be used; connects to the **checked** address instead of re-resolving the name; applies all of it
per redirect hop; and records the address in the audit trail (`vendor.example[93.184.216.34]`)
rather than only the name.

**The pinning is the one non-routine part and the one to be able to explain.** Checking an address
and then handing the *name* to `urlopen` means two DNS lookups — the one checked and the one used.
An attacker owning the zone answers differently the second time, so the check passes on a public
address and the connection lands on 192.168.1.1. That is **DNS rebinding**, structurally a
time-of-check-to-time-of-use bug. `http.client` resolves `self.host` inside `connect()`, so
overriding `connect()` is the whole change; `self.host` is untouched, so the `Host:` header and
TLS certificate validation still use the declared name. **Pinning changes where the connection
goes, never who it claims to be talking to** — a pin that broke certificate checking would trade
one hole for a worse one.

**Verification.** `test_egress.py` grew 17 → **35 cases**: 14 address-classification cases as a
pure function (RFC 1918, loopback, link-local, multicast, unspecified, IPv6 ULA, and
`::ffff:192.168.1.1`, plus three public addresses that must still pass); four attacker-controlled-
DNS cases through a `ScriptedEgress` whose answers the test writes, **because rebinding is a
difference between two resolutions and cannot be shown against a resolver you do not control**;
and four pinning cases proving the connection reaches the checked address, that resolution happens
exactly once per hop, that `Host:` still carries the declared name, and that the hop is logged with
its address. Matrix: **15/15 without Docker, 24/24 against real HA**, stable across repeats.

Against real HA this is also what closes T15: `blocked_hosts` holds `127.0.0.1` as a *string* and
never matched `localhost`. The destination check does.

### 12.2b ⚠️ Defect 5 — and it was in the new check, on its first run

**Probe check 9 reported a false BLOCKED against the unfixed broker**, with the reason
`transport failure: timed out`. The request had been authorised and attempted and merely never
arrived, because 192.0.2.10 is not routed. Every supervisor refusal reaches the sandbox as the
same `PermissionDenied`, whatever caused it.

A check that cannot tell a control from a timeout **would have shown the fix working before the
fix existed**. It now reads the reason string and reports three outcomes: blocked by the
destination check, *NOT MEASURED* because the allowlist got there first, or allowed-and-failed-in-
transit. Same failure mode as the `gaierror` confound in checks 7/8 and the two wrong versions of
check 2 — **four of the five defects found in this project have been in measurement code**, which
is the more dangerous kind, because a broken measurement reports success.

Caught only because the before/after was run as a measurement rather than assumed. Writing the
failing check first is now twice-proven as a method, once for what it measures and once for what
it revealed about itself.

### 12.3 The methodological point this proves

`test_egress.py` had 17 cases covering both directions of every rule it knew about. **It did not
find this.** A test suite can only test the threats someone already thought of — tests demonstrate
the absence of *known* failures, never the absence of failures. That is exactly why threat
modelling is a separate activity from testing, and it is now demonstrable in this project rather
than merely asserted: the model found a real gap in code that had already passed a targeted suite,
and the suite grew 17 → 35 cases as a result.

Pair it with §5.11 and §12.2b (**four of five defects were in *measurement* code**) and the
methodology chapter has two independent, evidenced arguments about how the evaluation was done.

### 12.4 Revised order of remaining work

1. ~~Resolve-and-pin in the broker (T14/T15)~~ — **done 2026-08-14**, §12.2
2. ~~**Verify on aarch64**~~ — **done 2026-08-21**, §13. 10/10 on a real Pi 5 under Raspberry Pi OS.
3. **HMAC the audit chain** (T03) — ~1 hour, and makes two controls fail independently
4. **cgroups** (T07) — the only threat with no control at all
5. Distinct uid for the sandbox (defence in depth for T05/T08)

---

## 13. aarch64 verified on the real Pi — 2026-08-21 ⭐

**The most schedule-critical open item (§12.4 #2) is closed.** Every isolation result until now
was x86_64 under WSL2 while the claim was about a Pi 5. It now runs on the Pi.

### 13.1 The distro question, settled by measurement rather than by the old plan

§8 item 1 mandated **Ubuntu Server 24.04 arm64**, on the grounds that Raspberry Pi OS kernels
historically ship without `CONFIG_DEBUG_INFO_BTF`, which modern eBPF tooling needs. **That
rationale is void:** eBPF left the architecture when Decision 2 settled on namespaces + seccomp,
and it now survives in these documents only as the explanation for why gVisor was dropped. The
seccomp policy actively *denies* `bpf` to the sandbox.

Measured on the existing Pi (Raspberry Pi OS trixie / Debian 13, kernel 6.12.47+rpt-rpi-2712,
aarch64, 4 GB):

| check | result |
|---|---|
| unprivileged user namespaces | ✅ work out of the box |
| `user+pid+mount` (the `isolate.py` set) | ✅ |
| AppArmor userns restriction | ✅ **absent** |
| seccomp filter support · `libseccomp2 2.6.0` | ✅ |
| cgroups v2 (`cgroup2fs`) | ✅ — T07 is unblocked |
| BTF / eBPF | ❌ absent — confirms the old concern, now irrelevant |

**Decision: stay on Raspberry Pi OS.** Ubuntu 24.04 would have *cost* something here — it ships
`kernel.apparmor_restrict_unprivileged_userns=1`, which blocks precisely the mechanism
`isolate.py` is built on until a sysctl is changed. Pi OS needs no such change, and it is also
what Pi-based HA users actually run, so the deployment-representativeness caveat disappears
instead of needing to be written into the limitations.

### 13.2 Results on the Pi

Python 3.14.7, aarch64, `--isolate`:

- **Adversarial probe: 10/10 blocked**, identical to x86_64, including both filesystem rows,
  both raw-socket rows and both broker-destination rows.
- `andrews_arnold_quota` runs end to end and publishes both sensors; **8 allowed, 5 denied**;
  audit chain intact, 13 records.
- All three integrations run via `run_targets.sh` (icqa: 18 allowed, 0 denied, chain intact).
- `test_egress.py` and `test_audit.py` pass in full.
- `isolate.available()` → PASS; `PIVOT_ROOT_SYSCALL` resolved `aarch64 → 41` correctly, so the
  architecture port that was written speculatively in `isolate.py:46` was right.

**Nothing about the security result is architecture-dependent.** That is the finding.

### 13.3 The Python version question — and a correction worth reporting

Three interpreters were in play: laptop venv **3.12.3**, Pi system **3.13.5**, and — measured by
running `python3 -V` inside the pinned `ghcr.io/home-assistant/home-assistant:2026.8.1` image —
**real Home Assistant runs 3.14.6**. Neither development machine matched the target.

This matters more than ordinary version hygiene: the compatibility claim is *"unmodified HACS
integrations run"*, and that claim is only meaningful on the interpreter HA would actually have
run them on. Coverage measured on 3.12 could be optimistic or pessimistic in ways nobody had
checked, and the shim contains **no `version_info` guards anywhere**.

**Standardised on CPython 3.14** (3.14.7 via `uv`, closest available to HA's 3.14.6). Everything
passes on it. The laptop should be moved to 3.14 too so the two machines and the target agree;
until then, the Pi is the more faithful environment, not the less.

### 13.4 A portability defect the port exposed — sixth self-caught finding

The first Pi run failed with `FileNotFoundError` from `os.execvp` *after* the seccomp filter had
loaded. Not an architecture problem and not a Python-version problem:

`allowlist()` bound `sys.prefix` and `sys.base_prefix`, and `sys.base_prefix` is already
symlink-resolved — but a venv's `bin/python` may *reach* the interpreter through a
**version-alias symlink** (`uv` and `pyenv` both do this: `cpython-3.14-…` → `cpython-3.14.7-…`).
Binding only the resolved home left the alias dangling inside the new root, so the interpreter
was present and unreachable.

Fixed in `isolate.py:allowlist()` by walking the interpreter's symlink chain and binding every
interpreter home it passes through. Verified against uv's own layout (previously failing, now
10/10) and re-verified on x86_64 for regression.

**Why it belongs in the report:** the isolation code was implicitly coupled to a
*distro-packaged interpreter layout*, and nothing in the threat model or the 35-case egress
suite could have found it — only running on a second machine did. It is the same lesson as
§12.3, from an independent direction: **environment assumptions are invisible until the
environment changes.** Pair with §5.11 and §12.2b in the methodology chapter.

---

## 14. Key sources
- Home Assistant security disclosure, Jan 2021 — file theft via custom integrations
- **HA analytics — `https://analytics.home-assistant.io/custom_integrations.json`** — per-domain
  install counts for custom integrations; opt-in telemetry, so a lower bound. The basis for
  every install-weighted figure in §5.2 and §5.4.
- Home Assistant official security page (trust assumptions)
- GitHub Security Lab — "Securing our home labs: Home Assistant code review"
- HA community RFC, 2026 — "Remote Integration Execution" (process separation, *not* security-motivated; engage with it directly, position as complementary)
- gVisor architecture guide · gVisor runtime monitoring docs
- Falco gVisor support (why eBPF does not work inside gVisor)
- HA developer docs — integration development, REST/WebSocket APIs
- Chrome/Firefox/Android extension permission manifests (prior art for the manifest model)
