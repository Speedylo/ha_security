# Experiment — do real community integrations run inside the sandbox?

**Run:** 2026-08-25 · **Target:** Raspberry Pi 5, 4 GB, aarch64 (the C4 hardware), Python
3.14.7, Home Assistant 2026.8.3 · **Feeds:** §6.12 · **Settles:** §5.6.5's second G3 trigger

§5.6.5 named three conditions that would send the design back from R2 to R1, and §6.11.3 called
the second the one most likely to fire:

> "Real community integrations fail against a minimal instance for reasons a *fuller* instance
> would fix — would mean the stripping, not the architecture, is what breaks compatibility, and
> R1 would then be no worse."

Until the bridge existed (§6.10) this could not be tested. It can now.

## Result

**37 community integrations, taken by install count, each in its own sandbox, source untouched.**

| | Arm A — the minimal instance | Arm B — with declared components |
|---|---|---|
| **Imports clean, all entity platforms** | **17/37 — 46%** | +4 → **21/37 — 57%** |
| Failed for want of a declared component | 16 | 12 |
| Failed on a dependency they never declared | 3 | 3 |
| Corpus artifact (`spook`, integration directory not found) | 1 | 1 |
| Peak memory, median / max | 100.6 / 151.0 MB | 110.8 / **209.4** MB |

**The trigger fires, and it fires in a qualified way that matters more than a yes.** A fuller
instance fixes **4 of the 16** — the rest fail because the components they declare *do not
themselves set up* in a stripped instance.

Raw output: `results/pi5_compat.json`. Corpus: `results/hacs_corpus_manifest.json`, rebuildable
with `figures/fetch_hacs_corpus.py`:

```bash
python3 figures/fetch_hacs_corpus.py --rebuild experiments/compat/results/hacs_corpus_manifest.json --out ~/r2exp/corpus
python3 figures/fetch_hacs_corpus.py --rebuild experiments/compat/results/hacs_corpus_manifest_uniform.json --out ~/r2exp/corpus_uniform
```

*Until 2026-10-06 "rebuildable" was not true: the manifests named `HEAD`, not a commit (finding F21).
The commits were recovered by an exact file-content match against the copies measured on the Pi,
and both corpora rebuilt from them are identical to those copies
(`../verify/results/phase4/pin_corpus/README.md`).*

## What a pass/fail number would have hidden

An integration that cannot import a package nobody installed has said nothing about R2, so every
failure is classified by *what* failed. One classification decision carries an argument and is
worth stating:

> **A missing Python module is not automatically a packaging gap.** Home Assistant installs a
> component's `requirements` when that component is *set up*. An integration declaring
> `dependencies: ["mqtt"]` gets `paho-mqtt` because mqtt was set up — so in a minimal instance
> the module is missing *because the component is missing*, and calling that a packaging problem
> would have hidden the finding entirely.

Arm B therefore installs each declared component's own requirements from Home Assistant's
manifests and sets the component up, which is what a real installation does. Every dependency
install succeeded — **0 install failures across 37 integrations** — so nothing here is
attributable to packaging.

## The single biggest blocker is `http`

Of the components declared and unavailable:

| Component | Integrations blocked |
|---|---|
| **`http`** | **10** |
| `mqtt` | 6 |
| `lovelace` | 4 |
| `frontend`, `websocket_api` | 3 each |
| `panel_custom`, `stream` | 2 each |
| `notify`, `bluetooth_adapters`, `private_ble_device`, `media_source`, `repairs`, `python_script`, `backup` | 1 each |

And the ones that *did* set up inside a minimal instance, which is the encouraging half:
`persistent_notification` (4), `ffmpeg` (4), `device_automation`, `device_tracker`, `dhcp`,
`light`, `group`, `template`, `select`, `utility_meter`, `integration`, `onvif`, `network`.

**`http` is the decisive one.** §5.6.3 built the minimal instance with "no HTTP server, no
recorder, no frontend and no authentication", and 27% of this corpus declares a dependency on
exactly the first of those. Whether a sandbox can run `http` — and what it costs — is now the
question R2 turns on, and it is a narrower question than "is R2 compatible".

## Three integrations depend on packages nobody declares

`battery_notes` imports `async_timeout`, `dreame_vacuum` imports `turbojpeg`, `dwd_weather`
imports `numpy` — and none of the three declares them, nor is any shipped by Home Assistant.

In a real installation they work only because *some other* integration installed the package
into the shared environment. R2 gives each sandbox its own declared dependencies and nothing
else, so this class breaks. **It is a compatibility cost of isolation, not of stripping**, and it
is counted separately for that reason.

## The two triggers are coupled, and Chapter 5 treated them as independent

§5.6.5 lists footprint and compatibility as separate conditions. They are not:

**Every component added to fix trigger 2 costs footprint, which is trigger 1.** Arm B's peak
memory rose from a 151 MB maximum to **209 MB**, for four recovered integrations. Un-stripping
far enough to run `http` for a quarter of the corpus would move it further.

> **A caution on that number.** `memory.peak` is the cgroup's own high-water mark and includes
> page cache; §6.3.2's 90 MB is proportional set size at rest. The two are not comparable and
> the figures above are an indication of direction, not a revised budget. Chapter 7 must
> re-measure PSS at scale with real integrations loaded.

## Limits

- **Imports-clean is an upper bound on compatibility, and the other number is not measured
  here.** N2 requires "executed end-to-end" be reported separately; this run stops at importing
  the integration and its entity platforms. A config entry needs configuration data that only
  each integration's own config flow can produce.
- **There is no baseline arm.** Without running the same 37 against a *full* Home Assistant, 46%
  does not decompose into "confinement broke it" and "it was broken anyway on this release".
  Chapter 7 owes that comparison, and it is what turns this into a measurement of the design
  rather than of the corpus.
- **Head-weighted corpus.** The top 40 by install count, which describes what most installations
  run and not what most integrations do — the same limitation
  `notes/ch5_evidence_api_surface.md` §6 records, and the same uniform-sample re-run is owed.
  *Both since run: compatibility in §7.23 (`results/uniform_*.json`), the API surface in §7.33
  (`figures/api_surface_uniform.json`).*
- **One release, one host.** Home Assistant 2026.8.3, Python 3.14.7, aarch64.

## Reproducing

```bash
python3 fetch_hacs_corpus.py --top 40 --out ~/corpus          # figures/
systemd-run --user --scope -q python3 -m confine.compat \
    --corpus ~/corpus --python <interpreter-with-homeassistant> --json results/pi5_compat.json
```

`--no-install` skips dependency installation, which reproduces the first version of this
measurement and shows why it was wrong: without it, 5 of the first 6 integrations fail on their
own declared packages and the trigger cannot be tested at all.

---

## Third run, 2026-08-25 evening — the `declared` profile, and where the blanket profile's lead comes from

`--profile declared` was added after §6.12.4 named it as the design to build: wire the auth
manager for every sandbox, then set up **only the components the integration's own
`manifest.json` asks for**, plus their requirements. All 37 re-run under it.

| Profile | Imports clean, all platforms | Peak memory, median | Peak, max |
|---|---|---|---|
| `minimal` — stripped instance | 17/37 — 46% | 100.6 MB | 151.0 MB |
| **`declared` — per integration** | **21/37 — 57%** | **109.6 MB** | 207.8 MB |
| `unstripped` — blanket ten components | 26/37 — 70% | 132.8 MB | 226.2 MB |

Raw output: `results/compat_declared.json`, `results/compat_declared.txt`.

**§6.12.4 predicted 70–76%. It got 57%, over exactly the same twenty-one integrations as the
earlier per-integration arm that ran with auth unwired.** Wiring auth changed eleven integrations'
reported failure reason and moved the corpus figure by zero. The budget half of the prediction
held — +9.0 MB over the minimal instance against the blanket profile's +32.2 MB, and twelve
integrations declare no components and are charged nothing. The declaration distribution, which
is what task 2's budget curve needs: 12 declare nothing, 3 declare one component, 9 declare two,
and the tail runs to `spook` at seventeen. The median is two, and `http` is declared by 15 of 37.

**Why the blanket profile is still ahead, and it is not components.** Nine integrations pass under
`unstripped` that fail under `declared`; `nodered` goes the other way (it declares `conversation`,
which the blanket list omits). Net six — and **all six fail on a missing Python package**, not a
missing component:

| Integration | Missing | Declares it? |
|---|---|---|
| `browser_mod`, `dwd_weather`, `llmvision`, `webrtc` | `numpy` | no |
| `dreame_vacuum`, `powercalc` | `turbojpeg` | no |

Both are requirements of `stream` (`PyTurboJPEG==1.8.3`, `av==17.0.1`, `numpy==2.3.2`). None of the
six declares `stream`; none lists either package in its own `requirements`; four declare no
packages at all. They work in a real installation because some core component has always pulled
those wheels into the shared environment, and the blanket profile reproduced that accident.

**So the blanket profile's whole compatibility advantage is dependency spillover.** 70% =
57% earned by what integrations declare + 16 points borrowed from packages they do not. Setting up
more components bought none of it.

**The measurement this indicates**, and it is the cheap one: `declared` unchanged, with the
platform's own component requirements present in the sandbox environment rather than only those of
the components it declares. Packages are bound read-only like the `homeassistant` library, so the
cost is disk, not per-sandbox memory. Written up in §6.13.

**A bound on Chapter 5's premise, worth recording as a number:** 16% of this corpus imports at
least one package its manifest never names. The declaration exists; for those six it is
incomplete.

```bash
systemd-run --user --scope -q python3 -m confine.compat \
    --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python \
    --profile declared --json results/compat_declared.json
```

---

## Fourth run, 2026-08-25 — `declared` + the core package set

The measurement §6.13.4 indicated. `--profile declared` unchanged, plus `--platform-deps`
pointing at a directory holding the packages a *stock* installation has. "Stock" is computed
rather than asserted: `core_requirements()` takes the dependency closure of `default_config`
(**57 components** on 2026.8.3) and the union of the `requirements` those components declare
(**39 packages**, `results/core_requirements.txt`, printable with `--print-core-requirements`).
Resolved with transitive dependencies: **641 MB on disk**, bound read-only and shared between
sandboxes as the `homeassistant` library already is.

| Profile | Imports clean, all platforms | Peak memory, median | Premium |
|---|---|---|---|
| `minimal` | 17/37 — 46% | 100.6 MB | — |
| `declared` | 21/37 — 57% | 109.6 MB | +9.0 MB |
| `unstripped` — blanket ten | 26/37 — 70% | 132.8 MB | +32.2 MB |
| **`declared` + core packages** | **31/37 — 84%** | **119.7 MB** | **+19.1 MB** |

Raw output: `results/compat_declared_core.json`, `results/compat_declared_core.txt`.

**It strictly dominates the blanket profile.** Every integration passing under `unstripped` passes
under this one — the set difference is empty in that direction — plus `alexa_media`,
`battery_notes`, `frigate`, `nodered` and `xiaomi_miot`, at **13.1 MB less** per sandbox. All
sixteen of §6.11.3's component-level failures are gone; the only declared component that still
fails to set up is `python_script` for `hacs`, which wants `RestrictedPython`.

**The six residual failures, and only three are the design's:**

| Integration | Failure | Whose |
|---|---|---|
| `bambu_lab`, `bermuda`, `tapo_control` | `ModuleNotFoundError: aiofiles` | the design's |
| `eufy_security` | `SOURCE_TYPE_GPS` no longer exists in `homeassistant.components.device_tracker` | HA 2026.8.3 — would fail unsandboxed |
| `hacs` | `custom_components.hacs.hacs_frontend` absent | the corpus — bundled at release-build time |
| `spook` | `IntegrationNotFound` | the corpus — directory layout |

Setting aside the release incompatibility and the two corpus artifacts: **31/34 — 91%**. Setting
them aside is what the baseline arm exists to justify; `eufy_security` is the one case the error
string settles on its own, and that is one case rather than a licence.

**`aiofiles`, and Home Assistant testifying about its own ecosystem.** All three remaining
failures import it; none declares it; no declared package pulls it in. No component in
`default_config` requires it — only `matrix` and `slack` do. And `package_constraints.txt` says:

```
# aiofiles keeps getting downgraded by custom components
aiofiles>=24.1.0
```

Upstream knows custom components install packages nobody declared, and pinned defensively rather
than requiring a declaration. **8% of this corpus still imports a package no amount of supplying
what the platform has would provide**, down from 16% before the core set.

**A classifier defect found by reading reasons, not verdicts (§6.6.5, third occurrence).** `hacs`
was classified `needs_component` because `python_script: False` appears in its setup record, while
the actual `ImportError` is HACS's own bundled module. Right verdict, wrong reason.

```bash
python3 -m confine.compat --python <interp> --corpus <corpus> --print-core-requirements \
    > core-reqs.txt
uv pip install --python <interp> --target ./platform-deps $(tr '\n' ' ' < core-reqs.txt)
systemd-run --user --scope -q python3 -m confine.compat \
    --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python \
    --profile declared --platform-deps ./platform-deps \
    --json results/compat_declared_core.json
```

---

## Fifth run, 2026-09-02 — the baseline arm

The measurement this file's own Limits section said was missing, and §7.4.1 made the first item
on Chapter 7's schedule:

> "**There is no baseline arm.** Without running the same 37 against a *full* Home Assistant, 46%
> does not decompose into 'confinement broke it' and 'it was broken anyway on this release'."

**Run:** 2026-09-02 · Pi 5, aarch64, Home Assistant 2026.8.3, Python 3.14.7 — the same host,
release and interpreter as every arm above · `--profile baseline`

### The instance, and the direction its bias runs

`confine/baseline_runtime.py` runs each integration against a **full, unconfined** Home
Assistant: no namespaces, no seccomp, no cgroup, no mount view, no mediator, no bridge. Absence
of confinement is the independent variable and the only one.

Every doubtful construction choice is resolved **in the baseline's favour**, because a generous
baseline makes the design's measured cost larger:

- the base `homeassistant` component, dropped from the sandbox in §6.3.2, is set up here;
- `default_config` is set up — the same definition of "stock" that §6.13.4's core package set is
  computed from, so one definition serves both;
- the integration's **declared components** are set up as well, and their requirements installed;
- the core package set is on the path, exactly as in the `declared` + core profile;
- the integration's own declared requirements are installed per integration, as above.

**The first version of this arm was wrong in the opposite direction and the correction is worth
recording.** It set up `homeassistant` + `default_config` only. `default_config` does not contain
`mqtt`, so `alarmo` — which declares it — failed against the "full" instance while *passing*
under confinement. A baseline stingier than the arm it is compared against does not decompose the
figure, it inverts it.

**The measurement itself is not reimplemented.** `inspect()` is imported from
`sandbox_runtime.py` and called with the same arguments; §7.9 requires the measurement be held
fixed while confinement varies, and a copy that drifted by one platform name or one truncation
length would make the comparison meaningless without making it look wrong.

### Result

| | Baseline — full, unconfined | Confined — `declared` + core packages |
|---|---|---|
| **Imports clean, all entity platforms** | **31/37 — 84%** | **31/37 — 84%** |
| Components loaded in the instance | median **52** | median **2** set up |
| Peak memory | median 291 MB, max 365 MB (RSS) | median 119.7 MB (cgroup peak) |

Raw output: `results/compat_baseline.json`, `results/compat_baseline.txt`.

**The two failure sets are identical, and so are the failure reasons.**

| Integration | Baseline | Confined | Same cause? |
|---|---|---|---|
| `bambu_lab` | `ModuleNotFoundError: aiofiles` | `ModuleNotFoundError: aiofiles` | identical |
| `bermuda` | `ModuleNotFoundError: aiofiles` | `ModuleNotFoundError: aiofiles` | identical |
| `tapo_control` | `ModuleNotFoundError: aiofiles` | `ModuleNotFoundError: aiofiles` | identical |
| `eufy_security` | `ImportError: cannot import name 'SOURCE_TYPE_GPS'` | same, byte for byte | identical |
| `hacs` | `ModuleNotFoundError: custom_components.hacs.hacs_frontend` | same | identical |
| `spook` | `IntegrationNotFound` | same | identical |

```
    failures(confined) = failures(baseline) + failures(design)
          6            =        6           +        0
```

**The import-level compatibility cost of confinement, on this corpus, is zero integrations of 37.**
No integration passes unconfined and fails confined. The set difference is empty in both
directions.

### `aiofiles` — the prediction that was wrong, and why the answer is better

§7.6's P2 predicted the baseline would *pass* the three `aiofiles` integrations, on the reasoning
that `package_constraints.txt` pins the package precisely because real installations have it. It
does not, and the check is direct:

```
$ ls ~/r2exp/ha314/lib/python3.14/site-packages/aiofiles*   -> ABSENT
$ ls ~/r2exp/platform-deps/aiofiles*                        -> ABSENT
```

A stock `pip install homeassistant` on 2026.8.3 does not provide `aiofiles`, and neither does the
`default_config` closure. **The three integrations are broken on a stock installation too.** The
constraint pin is upstream defending against a package custom components install *themselves*,
and it carries an issue reference — `home-assistant/core#118004` — which is citable evidence that
the platform maintainers treat this as an ecosystem problem rather than a packaging one.

This strengthens §6.14.4 rather than weakening it. The argument there was that "the author would
just declare it" is contradicted by the evidence; the baseline now adds that these integrations
do not work on an ordinary installation either, so confinement is not what breaks them.

### What this arm does and does not license

**Licensed.** Setting aside `eufy_security` (a release incompatibility), `hacs` and `spook`
(corpus artifacts) — §6.14.3 asserted this and the baseline now measures it. All three fail
unconfined, for the same reasons. The `aiofiles` three may be set aside on the same grounds,
which §6.14.3 did *not* claim and which the baseline establishes.

**Not licensed.** Three things, and the first is the one most likely to be over-read:

- **This is an import-level result on both arms.** N2's second number — executed end-to-end —
  has a population of one and is not addressed here. "Zero import-level compatibility cost" is
  not "zero compatibility cost", and the qualifier is not optional.
- **One corpus, head-weighted.** The uniform sample is still owed (§7.4.1).
- **One release, one host.** `eufy_security` failing on a constant removed in 2026.8.3 is a live
  demonstration that these figures have a shelf life.

### The secondary finding, which was not predicted

The baseline instance loads a **median of 52 components**; the confined sandbox sets up a
**median of 2**. They reach the same import-level compatibility. Whatever the other 50 are
doing for a stock installation, the corpus's integrations do not need them in order to load —
which is a statement about how much of Home Assistant an integration actually touches, and it
belongs in Chapter 8 alongside §6.14.5's honesty cost.

```bash
python3 -m confine.compat --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python \
    --profile baseline --platform-deps ~/r2exp/platform-deps \
    --json results/compat_baseline.json
```
