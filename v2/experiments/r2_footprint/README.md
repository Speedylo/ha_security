# Experiment — is R2 feasible, and what does it cost?

**Run:** 2026-08-24 · **Target:** Raspberry Pi 5, 4 GB, aarch64 (the C4 hardware)
**Question:** §5.6 must choose between R1 (proxy the `hass` object) and R2 (run a real,
stripped Home Assistant inside the sandbox). R2's premise was untested and its footprint
unknown. This settles both **before** the design chapter commits to either.

## Result

| | |
|---|---|
| **Q1 — can a minimal Home Assistant be built without bootstrap?** | **Yes** |
| **Q2 — does an ordinary integration run against it?** | **Yes** — config entry `LOADED`, `sensor.ticks` published |
| **Q3 — what does one sandbox cost on the Pi?** | **176 MB** resident, ready in **6.1 s** |
| **Q4 — what does each *additional* sandbox cost?** | **136 MB** — about **17** fit in 60% of the Pi's memory |

R2 is feasible on the target hardware. It is not free.

## Re-run on the corrected builder, 2026-10-03 (§7.35.2)

`measure.py` and `measure_scale.py` take `--builder corrected`: start with `async_start()` after
the integration is up (§6.3.3), plus the `frame`/`template` helpers and the `network` singleton
(§7.31). The base component is kept, so the two builders differ only in what §7.20.4 asked about.
`original` stays the default so the figures above remain reproducible. A listener now records
whether `EVENT_HOMEASSISTANT_START` fired: it does under `corrected` and not under `original`.

| | 2026-08-24 | original, today | corrected, today |
|---|---|---|---|
| One sandbox, RSS with the integration up — warm bytecode cache | — | 161.1 MB, 1.8 s | 161.3 MB, 1.5 s |
| One sandbox, RSS — **cold** cache (`-X pycache_prefix=<empty>`) | **176.1 MB, 6.1 s** | 177.6 MB, 6.4 s | 177.7 MB, 6.2 s |
| Six sandboxes, sum of PSS | 818.1 MB | 817.5 MB | 817.6 MB |
| PSS per sandbox, first → sixth | 154.7 → 136.4 | 154.1 → 136.2 | 154.1 → 136.3 |

**The builder moves nothing.** The start event's deferred work has no measurable memory cost.

**The 176 MB first-sandbox figure is a cold-start figure.** It was taken on the run that compiled
Home Assistant's bytecode for the first time; the compiler's allocations stay resident. A warm
start is 161 MB, and the 15 MB difference splits evenly between importing the helper layer and
setting up the base component, so the base component's share is 52.5 MB warm, not 60. The
six-sandbox run in August was already warm (per-sandbox RSS 161.8 MB), so the 136 MB marginal
figure was always the warm one and stands.

The `MemAvailable`-derived marginal is not reproducible run to run: 132.8 MB and 124.4 MB today,
and the corrected run's "first sandbox" read 40.4 MB because memory freed by the previous run was
still being returned. Quote PSS.

Results: `results/item12_20261003/`.

## What was measured, and why the marginal figure is the one to quote

A single sandbox's RSS counts the Python interpreter and the Home Assistant library, which
are read-only pages the kernel maps into every sandbox from the same physical memory. Six
sandboxes therefore do not cost six times one, and quoting 176 MB × N would overstate the
cost badly. Three figures were taken at six sandboxes:

| Measure | Six sandboxes | What it is |
|---|---|---|
| Sum of RSS | 970.8 MB | Counts every shared page once per process — an over-estimate |
| Sum of PSS | 818.1 MB | Each shared page divided among its sharers — the honest per-process figure |
| `MemAvailable` delta | 844.6 MB | The whole machine, before and after — ground truth |

Per-sandbox PSS falls as sandboxes are added (154.7 MB at one → 136.4 MB at six), which is
the sharing becoming visible. **Marginal cost: 136.5 MB.**

## Files

| File | What it does |
|---|---|
| `measure.py` | Builds one minimal instance, loads the probe, reports RSS per stage. `--serve` builds one and idles |
| `measure_scale.py` | Starts N sandboxes and reports RSS, PSS and machine-wide consumption |
| `custom_components/probe_sensor/` | A deliberately ordinary integration: config entry → `DataUpdateCoordinator` → `SensorEntity` → `async_add_entities` |
| `results/` | Raw output: `pi5_single.json`, `pi5_scale.json`, `x86_64_single.json` |

## Reproducing

Home Assistant 2026.8.3 requires Python ≥ 3.14.2, which is newer than the system Python on
both machines used here.

```bash
uv python install 3.14
uv venv --python 3.14 ha314
VIRTUAL_ENV=$PWD/ha314 uv pip install "homeassistant==2026.8.3"
./ha314/bin/python measure.py --json results/single.json
./ha314/bin/python measure_scale.py --count 6 --json results/scale.json
```

## Findings that go beyond the numbers

**1. The sandbox must not use `bootstrap`.** `homeassistant/bootstrap.py` imports
`.components` at module level — the frontend and the recorder's sensor support among them.
That is exactly the weight a sandbox exists to avoid. A minimal instance is built by
constructing `HomeAssistant` directly and wiring the registries by hand, which is what
`build_minimal_hass()` does; the recipe is adapted from Home Assistant's own
`tests/common.py`.

**2. The helper layer works untouched.** The probe uses `DataUpdateCoordinator`,
`CoordinatorEntity`, `SensorEntity` and `async_add_entities` — the pattern 38%/63% of
integrations use — and it worked against a locally-constructed `hass` with no HTTP server,
no recorder, no frontend and no auth. This is R2's premise, and it holds.

**3. The identified headroom is the base component.** Setting up the platform's own
`homeassistant` component costs **60 MB** of the 176 MB (115.9 → 176.0 MB). Whether a
sandbox needs it is the first optimisation Chapter 6 should test; if it can be dropped or
trimmed, the marginal figure falls substantially and the sandbox count roughly doubles.

**4. Home Assistant's custom-integration warning fired during the run**, verbatim: *"We
found a custom integration probe_sensor which has not been tested by Home Assistant."* That
is `notes/ch5_evidence_ha_coupling.md` §5 observed live — the platform detects third-party
code and spends the knowledge on a log line.

## Limits of this measurement

- **One integration, and a synthetic one.** It establishes that the *shape* works, not that
  any particular real integration does. Chapter 7's compatibility evaluation is a different
  measurement and is not anticipated by this one.
- **Idle, not working.** The sandboxes were measured at rest. An integration doing real work
  — holding an HTTP session, buffering responses — costs more, and Chapter 7's performance
  axis is where that belongs.
- **No mediator yet.** The sandbox here talks to nothing. The bridge, the IPC and the
  mediator process are all still to be built and will add their own cost.
- **Memory only.** Startup time is recorded (6.1 s on the Pi) but not analysed; CPU under
  load is not measured at all.
