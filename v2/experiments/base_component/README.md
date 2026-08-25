# Experiment — does a sandbox need Home Assistant's `homeassistant` base component?

**Run:** 2026-08-25 · **Target:** Raspberry Pi 5, 4 GB, aarch64 (the C4 hardware), Python
3.14.7, Home Assistant 2026.8.3 · **Feeds:** Chapter 6; revises §5.6.5 and §5.8.1

§5.6.5 hands Chapter 6 one measurement to run before any other: **60 MB of the 176 MB a
sandbox costs is the platform's own base component**, and §5.8.1's third qualification says
that if it can be dropped, the sandbox budget "roughly doubles". Neither section knew whether
it can be. This settles it, and revises the prediction.

## Result

| | |
|---|---|
| **Q1 — does an ordinary integration still load without it?** | **Yes** — both probes reach `LOADED` and publish the same entities |
| **Q2 — what does dropping it save per sandbox, at scale?** | **46.6 MB** (PSS). Capacity **17 → 26** sandboxes: **1.53×**, not the predicted 2× |
| **Q3 — what is lost?** | The whole `homeassistant` service domain — **13 services**. Nothing else |
| **Q4 — does state restoration survive?** | **Yes** — but only after fixing a defect this experiment found in §5.6.3's own recipe |

**Recommendation: drop it.** The cost is 13 services that the design routes through the
mediator anyway (§5.11.3), and the gain is half again as many sandboxes.

Raw output: `results/pi5_base_component.json`, and `results/pi5_base_component_reversed.json`
for the ordering control described below.

## What was measured, and why it is not a subtraction

The tempting version of this experiment is to build one sandbox each way and subtract the two
resident-memory figures. §5.6.3 established why that is wrong for the *cost* of a sandbox, and
the same arithmetic invalidates it for a *saving*: most of a sandbox is interpreter and library
pages the kernel maps into every sandbox from the same physical memory, so a megabyte removed
from one process's RSS is a megabyte removed from the budget only if it was private.

So the saving is measured the way the cost was — across six live sandboxes per arm.

| Arm | RSS, one sandbox | **PSS per sandbox, six live** | Sandboxes in 60% of 4 GB |
|---|---|---|---|
| With the base component | 161.3 MB | **136.6 MB** | **17** |
| Without it | 109.4 MB | **90.0 MB** | **26** |
| **Difference** | 51.9 MB | **46.6 MB** | **+9 (1.53×)** |

**§5.6.5's prediction was too optimistic, and predictably so.** "Roughly doubles" comes from
taking 60 MB off the single-process figure; measured marginally the saving is 46.6 MB, and the
budget improves by half rather than doubling. This is the error §5.6.3 warned about, made by
the chapter that contains the warning — which is the argument for running the measurement
before quoting the consequence.

### The control that decides which number to quote

Two marginal figures were available and they disagreed, so both arms were run in both orders:

| | with base | without base |
|---|---|---|
| PSS per sandbox, arm run **first** | 136.6 MB | 90.0 MB |
| PSS per sandbox, arm run **second** | **136.6 MB** | **90.0 MB** |
| `MemAvailable` marginal, arm run **first** | 127.5 MB | 79.3 MB |
| `MemAvailable` marginal, arm run **second** | **123.7 MB** | **74.1 MB** |

`MemAvailable` moved by 4–5 MB purely on running order, always downward for the arm that ran
second, because that arm reads files the first left in the page cache. PSS did not move at
all — the same figure to 0.1 MB, in both orders and across two full runs of the experiment.
§5.6.3 called `MemAvailable` ground truth, which it is for a single measurement on a quiet
machine and is not for a comparison of two arms. **PSS is what this experiment quotes**, and
`--order` exists so that the choice can be checked rather than asserted.

**One independent confirmation worth noting.** The with-base arm's PSS per sandbox is
**136.6 MB** against §5.6.3's **136.5 MB**, measured a day earlier by a different script. The
two agree to 0.1 MB, which is the strongest available evidence that these are the same system
and that the change being measured is the only change.

## What is actually lost (Q3)

Exactly one component and its thirteen services:

```
check_config  reload_all  reload_config_entry  reload_core_config  reload_custom_templates
restart  save_persistent_states  set_location  stop  toggle  turn_off  turn_on  update_entity
```

Without the base component the sandbox's service registry is **empty** — not sparse, empty.
That is §5.6.2's claim, which says the sandbox's registry "starts empty" and that denial is
therefore structural rather than checked, made literally true. With the base component set up
it is not empty: it holds the thirteen most target-generic services on the platform.

Three observations, and the first is the one that decides:

1. **These services are cross-integration by nature, and the design routes them through the
   mediator.** `homeassistant.turn_on` takes an arbitrary entity as its target. Inside a
   sandbox whose state machine holds only that integration's own declared entities, a local
   copy of it can reach nothing the integration does not already have — so it is a dead end
   rather than a capability. Removing it converts a silent no-op into an explicit
   `ServiceNotFound`, which is the more honest failure.
2. **The security gain is small and should not be inflated.** Nothing crosses a boundary either
   way, because the registry is local. What changes is that a claim in §5.6.2 becomes checkable.
3. **The compatibility cost is bounded but not zero.** From the corpus already measured in
   `notes/ch5_evidence_api_surface.md`: **8 of 144** community integrations (5.6%) call a
   `homeassistant.*` service with a literal domain, and **13 of 144** (9.0%) import the
   component. Both are static lower bounds. Those calls do not disappear — they become
   requests the mediator sees, which is where a cross-integration effect belongs.

## The defect this experiment found by accident (Q4)

The restore probe was written to fail loudly if dropping the base component broke state
restoration, since the base component is what registers
`homeassistant.save_persistent_states`. It failed — **in both arms**, including the one that
keeps the base component. A result identical on both sides of the variable is not a finding
about the variable; it is a broken test, and it was treated as one.

The cause is in §5.6.3's recipe, and not in the base component at all. `build_minimal_hass`
reaches the running state with:

```python
hass.set_state(CoreState.running)
```

That sets the flag without firing `EVENT_HOMEASSISTANT_START`, and
`homeassistant.helpers.start.async_at_start` — the platform's standard way of deferring work
until the instance is up — behaves differently on each side of that flag. So the omission has
**two** distinct failure modes, and only the first is loud enough to find by accident:

| Registered | `hass.is_running` | What happens | Real HA |
|---|---|---|---|
| **Before** the flag is set | `False` | Waits for an event that never arrives — **lost permanently** | Runs at start |
| **After** the flag is set | `True` | Runs **immediately**, part-way through assembling the instance | Runs at start, after every component is set up |

The helper layer wires itself during construction, so it lands in the first row.
`RestoreStateData.async_setup` registers there, which is why **no state is ever dumped and
every `RestoreEntity` in the sandbox silently restores nothing.** Integrations, set up after
the flag, land in the second row instead: they are not lost, they are merely run in the wrong
place. In Home Assistant 2026.8.3 the helper is used by **28 shipped components**, `mqtt`,
`template`, `group`, `filter`, `utility_meter`, `history_stats` and `zwave_js` among them, and
a callback written on the assumption that its peers already exist is a plausible way for that
to matter.

**The fix is to start the instance rather than to declare it started, and to start it where
Home Assistant does** — after everything is set up, not before:

```python
hass = await build_minimal_hass(config_dir)
...                              # base component, config entries, platforms
await hass.async_start()         # fires EVENT_HOMEASSISTANT_START, then runs startup jobs
```

With that, the round trip passes in both arms: generation 1 → 2, `restored_from: 1`. Adding
the start *before* the integrations are loaded also repairs restoration, and was the first fix
tried; it is the wrong one, because it leaves every integration in the second row of the table
above. The order is part of the fix.

Two things follow for Chapter 6:

- **The supervisor must call `hass.async_start()`, last.** The sandbox is not ready until it
  returns, and nothing may be set up after it.
- **The failure mode is the one to watch for.** This defect produced no exception, no warning
  and no log line; it produced a sensor that quietly reported the wrong number. Any future
  compatibility failure must be checked against the minimal instance before it is charged to
  the design — otherwise Chapter 7 measures the recipe and reports it as the cost of
  confinement.

`experiments/r2_footprint/measure.py` is deliberately **left unmodified**, so §5.6.3's
published figures remain reproducible exactly as reported; this experiment imports its
`build_minimal_hass` and applies the correction here, where it is answerable for it.

## Files

| File | What it does |
|---|---|
| `measure_base.py` | Both arms: per-stage RSS, six-sandbox PSS, the service/component diff, and the restore round trip under both recipes |
| `custom_components/probe_sensor/` | The §5.6.3 integration, copied unchanged, so Q1 is asked of the same subject |
| `custom_components/probe_restore/` | A `RestoreSensor` publishing a generation counter — the falsification attempt behind Q4 |
| `results/` | `pi5_base_component.json`, and `..._reversed.json` for the ordering control |

## Reproducing

Needs the environment from `../r2_footprint/README.md`, and that directory beside this one —
`build_minimal_hass` is imported from it rather than copied.

```bash
./ha314/bin/python measure_base.py --count 6 --json results/pi5_base_component.json
./ha314/bin/python measure_base.py --count 6 --order without_base,with_base \
    --json results/pi5_base_component_reversed.json
```

## Limits

- **Two probes, both synthetic.** They establish that the loading path and the restoration path
  survive; they are not the compatibility evaluation, which is Chapter 7's and needs real
  community integrations. In particular no probe here calls a `homeassistant.*` service.
- **The `async_at_start` bound is over shipped components only, and it bounds exposure, not
  breakage.** Twenty-eight components use the helper; how many of them would actually misbehave
  when run early is not measured, and how many *community* integrations defer work to start-up
  is not measured either.
  `figures/fetch_hacs_corpus.py` rebuilds the corpus that would answer it, and this belongs
  with the uniform-sample re-run already owed before Chapter 7 reports coverage.
- **Idle, and without a mediator.** Unchanged from §5.6.3: both arms were measured at rest,
  with nothing attached to the sandbox. The 26-sandbox figure will move when the bridge, the
  channel and the mediator exist.
- **One host.** Pi 5, 4 GB, one kernel, one Python. The saving is a property of what the base
  component allocates, so it should travel; the capacity figure is specific to this machine.
