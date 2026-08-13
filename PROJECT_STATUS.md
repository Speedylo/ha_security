# Capstone — Project Status & Rolling Notes

**Owner:** Younes · Al Akhawayn University, BSc Computer Science
**Advisor (intended):** Prof. Omar Iraqi Houssaini — Professor of CS; IT & Cybersecurity Lead Auditor & Architect. Already took a cybersecurity course with him.
**Work period:** September – November 2026 (~13 calendar weeks; **~10 realistic engineering weeks** after proposal, mid-report, final report and defence overhead).
**Last updated:** 2026-08-13
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
| Read a host file | ALLOWED | **ALLOWED** (unchanged; no fs isolation) |

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

---

## 6. Open decisions

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | ~~**Compatibility strategy**~~ **SETTLED 2026-08-12** | (a) shim so real integrations run unmodified; (b) own SDK + toy integrations; (c) hand-port 2–3 and measure cost | **(a).** The spike (§5.3) ran a real integration unmodified, so the fallback to (c) is no longer needed. Still scoped to a core + generated constants with measured coverage reported — not "everything runs unmodified". |
| 2 | **Isolation primitive** | namespaces+seccomp / gVisor+its trace sink / gVisor+eBPF-as-boundary-verifier | **namespaces + seccomp** — coherent with eBPF, lighter on the Pi, and defensible as "controls proportionate to the threat model" (his language). |
| 3 | **Target pattern** ⚠️ **most open question — take this to the advisor first** | polling_sensor only (24.8% of repos but **only 10.6% of installs**) vs. extending to actuators (46.7% of repos and **64.8% of installs**) | **Install weighting (§5.2b) cuts against the polling-sensor default.** By repo count it looked like a quarter of the ecosystem; by what people actually run it is a tenth, while actuators are nearly two-thirds. Actuators are simultaneously where the threat model has teeth *and* where the users are — a security auditor will notice both. Counter-argument that still holds: actuator platforms are behavioural work (`switch`, `button`, `select`, `number` each block 30–50 of the top 100, §5.4), so the cost is real and the ~10 engineering weeks are not elastic. **Recommended position to take into the meeting:** keep polling_sensor as the *implemented* scope, but present the install numbers honestly, frame actuator support as the explicit next increment, and let him choose. Do not present 24.8% without 10.6% beside it. |
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

---

## 8. Next steps

### August (before the semester) — de-risk, don't build

> **#4 (shim spike) is DONE and came back GO — see §5.3. The one remaining item that
> cannot slip is #6 (advisor meeting, carrying Decision 3 from §6).**
>
> The spike changes what to bring to that meeting: there is now a working demo, a
> four-of-five adversarial result with an honestly-stated gap, and a measured coverage
> number. Lead with the demo.

1. **Environment.** Install **Ubuntu Server 24.04 LTS arm64** on the Pi 5 — *not* Raspberry
   Pi OS, whose kernels have historically shipped without `CONFIG_DEBUG_INFO_BTF` that
   modern eBPF tooling needs. Verify:
   - `ls /sys/kernel/btf/vmlinux` exists
   - `sudo bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s\n", comm); }'` streams output

   If either fails, plan for a small cloud VM rather than fighting kernel configs in October.
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
   - **Filesystem isolation** (namespaces + seccomp). Deferred by decision on 2026-08-13.
     Still the precondition for reproducing the 2021 HACS file-theft result, so the security
     chapter must state *why* the fifth probe row is unblocked rather than quietly reporting
     "4 of 5".
5. **Draft manifest schema** (strawman is in §2).
6. ⭐ **Meet the advisor** with a ~2-page pre-proposal — problem, evidenced gap, architecture
   sketch, deliverables, risks, and the coverage-curve figure. Secure buy-in *before*
   writing the full document; advisors invest more in projects they helped shape.
   **Carry three questions into that meeting:**
   - **Decision 3 (§6)** — polling sensors only, or push into actuators where the real
     threat model lives? This is the one that changes scope most.
   - Which threat-modelling framework he wants used (STRIDE / attack trees / ISO 27001 / NIST)?
   - Does the programme require a literature-review chapter, and is there a page target?
     *(Decision 4 in §6 — currently unknown.)*

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

**The accurate one-sentence claim:** *a demonstrated mechanism for confining unmodified HACS
integrations against a stock Home Assistant, plus the first empirical measurement of what
applying it across the real ecosystem would cost.* Both halves are contributions and the
second is the more novel one — no published account of the HA API surface appears to exist.
That sentence stays honest at 1.2% coverage; "a sandboxing framework for HACS" does not.

---

## 10. Key sources
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
