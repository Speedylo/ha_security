# Evidence — what integrations actually ask the platform for

**Derived:** 2026-08-24 · **Working note, not a report chapter.** · **Discharges:** the
API-surface item of `00_METHOD.md` §2. · **Feeds:** §5.10 (manifest schema and granularity),
S3, S5, S6, S8; Chapter 7's compatibility axis.

## 1. Why this measurement exists

§5.10 must fix the manifest's granularity, and §3.5 S5 makes granularity a *security*
property rather than a formatting decision. Choosing it without evidence produces one of two
failures:

- **Too coarse** — a permission nearly every integration needs is not a permission, it is a
  formality. If 94% of integrations must be granted X, granting X confines nobody.
- **Too fine** — a manifest enumerating what integrations never do is unusable, and
  unusable manifests are written badly or not at all.

The useful question is therefore empirical: **which of the nine handles reachable from `hass`
(`ch5_evidence_ha_coupling.md` §4) do integrations actually use, how many use each, and at
what granularity?**

## 2. Method

**Parsing, not grepping.** Every `.py` file is parsed with Python's `ast` module and walked
for attribute chains rooted at `hass` or `self.hass`, plus subscripts of `hass.data` and
calls to the service registry. This matters: `# hass.services.async_call` in a comment and
`"hass.states.async_set"` in a docstring are not uses, and a regex counts both. Files that
fail to parse are counted and reported, not skipped silently.

Script: `figures/api_surface.py`. Corpus fetcher: `figures/fetch_hacs_corpus.py`.

**Two corpora, because the population matters.**

| Corpus | What it is | n | Files |
|---|---|---|---|
| `core-2026.8.3` | Every integration shipped with Home Assistant 2026.8.3 | 1,458 | 9,633 |

> **Why 1,458 and not 1,482.** `homeassistant/components/` holds 1,482 directories, which is
> the figure §5.6.1 and §5.9.1 quote because those measurements count manifests and grep over
> files. This parser skips a directory containing no `.py` file at all, and 24 shipped
> integrations are exactly that — brand and translation metadata with no code. Both totals are
> correct for what they count; the denominators differ because the questions do. Any figure
> quoted from this file is out of 1,458.
| `hacs-top150` | Community integrations, by install count, fetched 2026-08-24 | 144 | 4,628  *Pinned 2026-10-06 (F16): `figures/hacs_top150_manifest.json`* |

The community corpus is sampled **by install count, not at random**. The argument §5.10 needs
is about what confinement would break in practice, and breaking an integration on 40,000
installations is not equivalent to breaking one on twelve. §1.3 records a long tail whose
median integration has 20 installs; a uniform sample would be dominated by it and would
describe a population almost nobody runs. Every repository fetched is recorded in
`figures/hacs_corpus_manifest.json` so the corpus rebuilds exactly.

**Both were parsed under Python 3.14**, matching the platform's own requirement. An earlier
run under 3.12 failed on 322 files using newer syntax; that run was discarded rather than
reported, and the final measurement has **zero parse failures in either corpus**.

### 2.1 A correction, recorded because the first numbers were wrong

The first run of this measurement **under-counted every handle**, and the error is worth
recording rather than quietly fixing.

`chain_of()` walked an attribute chain inwards to find its root. For a bare `hass.states.get`
the root is the name `hass` and the match succeeded. But for `self.hass.states.get` the walk
consumed `hass` as an ordinary attribute before the root test ran, leaving the root as `self`
— and the match failed. **`self.hass.X` is the dominant idiom in entity classes**, so the
effect was large and systematic, not marginal.

It surfaced because a cross-check disagreed: `grep` found `hass.states.get` in 38% of
community integrations where the parser reported 22.9%. A parser is supposed to beat a grep
by excluding comments and strings, so it may report *less* — but not by a third. The gap was
the signal.

| | first run | corrected |
|---|---|---|
| `hass.states` (community) | 25.7% | **41.0%** |
| `hass.loop` (community) | 55.6% | **78.5%** |
| `hass.config` (community) | 45.8% | **61.8%** |
| Integrations calling another's services | 11.8% | **22.2%** |

Every figure below is from the corrected run. Two process points follow, and both are worth
keeping: **a measurement whose method is more rigorous is not automatically more correct**,
and the cheap grep cross-check that caught it should be run against any future parser-based
measurement in this project before its numbers are used.

## 3. The first result: the population changes the answer

| Handle | core | HACS top-150 | ratio |
|---|---|---|---|
| `hass.config_entries` | 63.5% | **94.4%** | 1.5× |
| `hass.data` | 19.0% | **86.1%** | 4.5× |
| `hass.loop` / executor | 34.7% | **78.5%** | 2.3× |
| `hass.services` | 15.2% | **64.6%** | 4.2× |
| `hass.config` | 17.2% | **61.8%** | 3.6× |
| `hass.bus` | 19.9% | 48.6% | 2.4× |
| `hass.states` | 8.3% | 41.0% | 4.9× |
| `hass.http` | 4.5% | 19.4% | 4.3× |
| `hass.auth` | 1.1% | 5.6% | 5.1× |

**Community integrations use every handle between 1.5 and 5.1 times more than the platform's
own.** Measuring on core alone — which is what is conveniently on disk — would have
understated what confinement must accommodate across the board, and would have made
confinement look far cheaper than it is.

This vindicates the limitation stated in §5.6.1 and §5.9.1 rather than merely acknowledging
it, and it is a methodological result worth carrying: **on this platform, results from the
shipped integrations do not transfer to the community ones.** Chapter 7 should state it, and
any future measurement here should assume it.

The plausible explanation is selection: core integrations are reviewed against a quality
scale and pushed toward the helper layer, which handles platform interaction on their behalf.
Community integrations have no such pressure and reach for the platform directly. That is an
inference, not a measured cause, and should be labelled as one if used.

## 4. What this says about granularity

### 4.1 A handle is the wrong unit

`hass.config_entries` is used by 94.4% of community integrations, which by §1's test makes it
useless as a permission. But the breakdown shows why:

| Member | Share of community integrations |
|---|---|
| `config_entries.async_forward_entry_setups` | 88.9% |
| `config_entries.async_update_entry` | 79.9% |
| `config_entries.async_unload_platforms` | 72.2% |
| `config_entries.async_entries` | **41.0%** |

The first three are an integration managing **its own** entry — the ordinary setup and
teardown lifecycle. `async_entries` enumerates **everyone's**. Those are entirely different
authorities behind one attribute name, and A3 (stored credentials) hangs on the difference.

**Conclusion: the manifest cannot express permissions per handle.** It must reach at least
operation level, and for operations that take a target — an entity, a domain, a path — it
must reach the target too. This is S5's requirement generalised: `lock.unlock` must not
arrive with `lock.lock`, and *everyone's config entries* must not arrive with *mine*.

### 4.2 Where denial is cheap

| Capability | Community integrations using it | Cost of default-deny |
|---|---|---|
| `hass.auth` | 5.6% (8) | Near-zero |
| `hass.http` route registration | 19.4% | Low |
| **Calling another integration's services** | **22.2%** | Moderate — and this is T05's path |
| `hass.config.path` — the config directory | 33.3% | Moderate |
| Reading others' state (`states.get`) | 38.9% | High |

**The service-call result is the most useful thing in this measurement.** 56.2% of community
integrations *register* services — that is how they expose their own functionality — but only
**22.2% call** services belonging to anything else. T05, the register's joint-highest risk, is
an integration calling `lock.unlock`. Default-denying outbound service calls therefore costs
about one integration in five, and those declare what they need. S6's default-to-denial is
affordable at the point where the highest-rated threat lives — though at roughly twice the
cost the first, buggy run suggested, which is why §2.1 exists.

### 4.3 Where denial is not cheap, and S8 must be scoped rather than absolute

**33.3% of community integrations call `hass.config.path`** — a third of them read or write
inside the configuration directory. S8 requires filesystem confinement "to declared resources", and this
number is why the qualifier is load-bearing: a design that simply denied filesystem access
would break a quarter of the population, while a design that grants the whole configuration
directory grants `secrets.yaml` and reproduces T14 exactly.

The manifest therefore needs **path-scoped** filesystem permission, and the sandbox's natural
default — the integration's own directory, and nothing else — is what §5.6.2's empty-by-
construction principle already suggests.

### 4.4 Cross-integration reach is mostly platform services, not peers

71.5% of community integrations import another component, which sounds alarming until the
targets are examined: `diagnostics` (40), `http` (28), `repairs` (17), `recorder` (15),
`homeassistant` (13), `device_automation` (12), `persistent_notification` (11), `frontend`
(11), `lovelace` (9), `mqtt` (8).

Almost all are **platform services** — the diagnostics protocol, the HTTP layer, the repairs
system — rather than peer integrations whose data is being reached for. `mqtt` at 8 is the
notable genuine peer dependency, and it is a legitimate architectural one.

So TB6 (integration ↔ integration) is crossed far less often *by import* than the raw figure
suggests. The crossing that matters is the one §5.2 established and Corno & Mannella
demonstrated — the shared object graph — which no import-based measurement can see.

## 5. A result that confirms §5.9.3 from an unexpected direction

The script extracts the domain argument of every service call, to learn which domains are
called and at what granularity. Across 17 community integrations that call services, it
recovered only a handful of literal domains — `weather`, `todo`, `persistent_notification`,
`xiaomi_miot`, `homeassistant`, `automation`, `spotcast`.

**Almost every call passes the domain as a constant or a variable, not a literal string.** A
static reader therefore cannot say which services an integration calls without resolving
constants across modules — and in the general case, not at all.

This is §5.9.3's verdict on M3 arriving from a second direction: static analysis **can
propose and cannot certify**. It was argued there from Python's dynamism in the abstract;
here it is a measured property of this corpus. The two should be cited together, because an
argument that survives contact with the actual code is worth more than one that does not.

## 6. Limits of this measurement

- **Static parsing under-counts.** `getattr(hass, name)` and dispatch through a variable are
  invisible. Every figure is a **lower bound** on use — the conservative direction for a
  compatibility argument, since it can only understate what confinement would break.
- **The community sample is head-weighted by design.** 144 integrations chosen by install
  count, against 4,220 in the ecosystem whose median has 20 installs. It describes what most
  *installations* run, not what most *integrations* do. A uniform sample would answer the
  second question and is worth running before Chapter 7 reports coverage.
- **Use is not need.** An integration that calls `hass.states.get` might work without it. The
  measurement bounds what confinement would *disturb*, not what it would *break*; the
  difference is exactly what Chapter 7's end-to-end compatibility number measures, and this
  note must not be quoted as anticipating it.
- **One release.** Core at 2026.8.3, community as of 2026-08-24.

## 7. What §5.10 takes from this

1. Permissions are **per operation with a target**, not per handle (§4.1).
2. **Default-deny outbound service calls** — 22.2% cost, and it is T05's path (§4.2).
3. **Filesystem permission is path-scoped**, defaulting to the integration's own directory —
   an absolute denial breaks 33.3% (§4.3).
4. **State reads are mediated, not blanket-denied** — 41.0% touch the state machine and
   38.9% read others' state (§4.3). This is the most-used capability after lifecycle and
   storage, and blanket denial is not available.
5. `hass.auth` is **denied by default** at near-zero cost — 5.6% (§4.2).
6. The manifest must distinguish **one's own config entry from everyone's** (§4.1).

## 7. The uniform corpus, run 2026-10-03 (report §7.33)

`figures/api_surface_uniform.json` — the parser unchanged, Python 3.14, §7.23's uniform corpus of
40, zero parse failures.

```bash
# the corpus is §7.23's: experiments/compat/results/hacs_corpus_manifest_uniform.json, seed 20260902
<python3.14> figures/api_surface.py --root ~/r2exp/corpus_uniform --label hacs-uniform40 \
    --json figures/api_surface_uniform.json
``` Every conclusion in §4 holds: own-entry lifecycle 90% against everyone's
entries 22.5%; calling others' services 12.5%; `config.path` 20.0%; cross-component reach 50.0%,
mostly platform services; `states` 35.0%. The tail uses `bus` (17.5% against 48.6%), `services`
(37.5% against 64.6%) and `config` (37.5% against 61.8%) far less than the head.

*A small inconsistency in §4.3, noticed while re-reading it: it says denying filesystem access
"would break a quarter of the population" two sentences after measuring a third (33.3%). The
figure is right and the paraphrase is not; on the uniform corpus it would be a fifth.*
