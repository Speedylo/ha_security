# Capstone — Project Status & Rolling Notes

**Owner:** Younes · Al Akhawayn University, BSc Computer Science
**Advisor (intended):** Prof. Omar Iraqi Houssaini — Professor of CS; IT & Cybersecurity Lead Auditor & Architect. Already took a cybersecurity course with him.
**Work period:** September – November 2026 (~13 calendar weeks; **~10 realistic engineering weeks** after proposal, mid-report, final report and defence overhead).
**Last updated:** 2026-08-10

> This file is the source of truth across sessions. Update it as decisions land.

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
python3 hacs_api_surface.py --limit 0            # full catalogue (~1900 repos)
```
Outputs to `surface_out/`: `symbols.csv`, `coverage.csv`, `nearmiss.csv`, `integrations.json`.
Tarballs cache in `.hacs_cache/`, so re-runs are instant.

### 5.2 Results from a 200-repo sample

**Pattern distribution:**

| pattern | share |
|---|---|
| actuator (receives commands) | 58.0% |
| polling_sensor | 15.0% |
| sensor_other | 13.5% |
| other | 6.5% |
| local_discovery | 6.0% |
| oauth_cloud | 0.5% |
| push_stream | 0.5% |

**API surface, polling-sensor subset (n=30):** 237 distinct symbols · median **29** per
integration · max 74.

**⚠️ Correction to an earlier estimate:** the working assumption of "~15 symbols" was
**wrong**. Strict zero-modification coverage of 50% of integrations needs ~83 behavioural
symbols; 75% is not reached within 120.

**But the distribution is steeply concentrated — the good case:**

| symbol | appears in |
|---|---|
| `core:HomeAssistant` | 100% |
| `update_coordinator:DataUpdateCoordinator` | 100% |
| `config_entries:ConfigEntry` | 97% |
| `update_coordinator:CoordinatorEntity` | 93% |
| `sensor:SensorEntity` | 93% |
| `update_coordinator:UpdateFailed` | 90% |
| `entity_platform:AddEntitiesCallback` | 80% |
| `core:callback` | 77% |
| `sensor:SensorStateClass` | 73% |
| `sensor:SensorDeviceClass` | 70% |
| `aiohttp_client:async_get_clientsession` | 67% |

- Top 30 symbols = **69% of all import usage**.
- With the top 30 implemented, the **median integration is missing only 5** more symbols;
  **18 of 30 are missing ≤6**.
- Much of the tail is `homeassistant.const` values, enums (`SensorDeviceClass`,
  `EntityCategory`) and selector configs — **machine-generatable from HA's source**, not
  hand-written. That collapses most of the tail to near-zero cost.

**Realistic budget: ~30–40 hand-written behavioural symbols + a generated constants layer.**

**Caveats to carry into the report:** sample is 200 of ~1900 repos in catalogue order
(possible selection bias — rerun with `--limit 0`); the actuator classifier is heuristic and
probably over-broad; **imports are a lower bound on difficulty** — an integration can import
`SensorEntity` and still depend on lifecycle behaviour the shim doesn't reproduce.

**This measurement is itself a contribution.** No published empirical account of the HA API
surface that HACS integrations depend on appears to exist. It is a report figure and it
justifies every downstream scoping decision — exactly the evidence an auditor grades well.

---

## 6. Open decisions

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | **Compatibility strategy** | (a) shim so real integrations run unmodified; (b) own SDK + toy integrations; (c) hand-port 2–3 and measure cost | **(a) scoped to the ~30-symbol core + generated constants, reporting measured coverage; (c) as the written fallback.** Not "everything runs unmodified" — that's out of budget. |
| 2 | **Isolation primitive** | namespaces+seccomp / gVisor+its trace sink / gVisor+eBPF-as-boundary-verifier | **namespaces + seccomp** — coherent with eBPF, lighter on the Pi, and defensible as "controls proportionate to the threat model" (his language). |
| 3 | **Target pattern** ⚠️ **most open question — take this to the advisor first** | polling_sensor only (15%, read-only, easiest, least security-interesting) vs. extending to actuators (58%, where the real stakes are — locks, alarms, switches) | Least settled of the four. Default: start polling_sensor, state actuator support as stretch. But a *security auditor may well push toward actuators*, since that is where the threat model has teeth, and that changes the scope materially. Have this conversation **before** writing the proposal, not after. |
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

> **The two highest-priority items this month are #4 (shim spike) and #6 (advisor meeting,
> carrying Decision 3 from §6). Everything else can slip; those two cannot.**

1. **Environment.** Install **Ubuntu Server 24.04 LTS arm64** on the Pi 5 — *not* Raspberry
   Pi OS, whose kernels have historically shipped without `CONFIG_DEBUG_INFO_BTF` that
   modern eBPF tooling needs. Verify:
   - `ls /sys/kernel/btf/vmlinux` exists
   - `sudo bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s\n", comm); }'` streams output

   If either fails, plan for a small cloud VM rather than fighting kernel configs in October.
2. **Run HA in Docker on the Pi**, and drive it from a Python script over the REST and
   WebSocket APIs. Makes everything downstream concrete.
3. **Re-run the surface analysis over the full catalogue** (`--limit 0`) to replace the
   200-repo sample with definitive numbers.
4. ⭐ **HIGHEST VALUE — prototype the shim's spine.** Fake `homeassistant.core` +
   `DataUpdateCoordinator` + `SensorEntity`, enough to make *one* real HACS sensor
   integration produce a state update through a socket. **This is a go/no-go spike: it
   proves or kills the entire approach in days rather than in week 8**, when there would be
   no time to recover. Nothing else in August matters as much. Timebox it to ~3 days; if it
   is clearly going nowhere, that is a *result* — switch Decision 1 to option (c),
   hand-port-and-measure, and the project still stands.
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

## 9. Key sources
- Home Assistant security disclosure, Jan 2021 — file theft via custom integrations
- Home Assistant official security page (trust assumptions)
- GitHub Security Lab — "Securing our home labs: Home Assistant code review"
- HA community RFC, 2026 — "Remote Integration Execution" (process separation, *not* security-motivated; engage with it directly, position as complementary)
- gVisor architecture guide · gVisor runtime monitoring docs
- Falco gVisor support (why eBPF does not work inside gVisor)
- HA developer docs — integration development, REST/WebSocket APIs
- Chrome/Firefox/Android extension permission manifests (prior art for the manifest model)
