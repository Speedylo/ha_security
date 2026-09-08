# 11. Data Presentation

This chapter states what was measured, on what, and with what instruments — before §12 states what
the measurements showed. The separation is deliberate: an evaluation that introduces its method
alongside its results invites the reading that the method was chosen to fit them.

## 11.1 The rule this evaluation is written under

**Every figure in §12 names the run that produced it, and every claim carries its strength.** Three
labels are used throughout and they are not decorative:

| Label | Meaning |
|---|---|
| **Measured** | A number produced by a named run whose raw output is in the repository |
| **Demonstrated** | A behaviour observed in a named test, without a number attached |
| **Argued** | A conclusion reasoned from measurements, and labelled as reasoning |

A fourth category is reported explicitly rather than omitted: **a measurement that did not
resolve**. One did, and §12.8 reports it as unresolved rather than presenting three points as a
trend.

## 11.2 The test environment

Every measurement in this report was taken on one machine, and holding it fixed is what makes the
paired arms comparable.

| | |
|---|---|
| Device | **Raspberry Pi 5, 4 GB** |
| OS | Raspberry Pi OS trixie, kernel 6.12.47, aarch64 |
| Platform | **Home Assistant 2026.8.3**, pinned to a commit, unmodified |
| Interpreter | Python 3.14.7 |
| Privilege | **Unprivileged throughout** — no root, inside a systemd user scope |

**One release, one host, one architecture.** This is a stated limit and not a small one: two
integrations in the corpora fail on constants removed *in this very release*, which is a live
demonstration that a compatibility figure has a shelf life.

## 11.3 The corpora

Compatibility is measured over real, unmodified community integrations fetched from HACS. **Two
corpora were used, and using two is the point.**

**Table 11.1 — The two corpora**

| | Head-weighted | **Uniform (seed 20260902)** |
|---|---|---|
| Selection | The most-installed integrations | Drawn from the whole HACS index with equal probability |
| Repositories requested | 40 | 40 |
| **Distinct integrations measured** | **37** | **40** |
| Install count, median | **16,294** | **48** |
| Installs represented, total | **998,478** | 46,979 |
| Python files, median | 19 (max 1,015) | **11 (max 143)** |
| Declares no components at all | 18 of 37 | **26 of 40** |
| Declared components, median | 1 | **0** |
| **Overlap between the two** | — | **2** (`bermuda`, `browser_mod`) |

**Two of forty is the number that justifies having run this at all.** The corpora share 5% of their
members, so the second is close to an independent sample of the same ecosystem rather than a
re-slicing of the first. The head corpus represents **twenty-one times** the deployed reach of the
uniform one from the same number of repositories requested. Neither is wrong; they answer different
questions — **what most installations run**, and **what most integrations do**.

> **A detail worth stating, because it is a reproducibility limit found by re-reading.** The head
> corpus requests forty *repositories* and measures thirty-seven *integrations*: one fetch failed,
> and **three domains are each claimed by two different repositories**, while a domain is one slot
> on disk. Which repository won each collision is not recoverable from the manifest, and in one
> case the two candidates differ by 5 versus 46 Python files. The manifest permits the corpus to be
> redrawn; it does not fully determine what a redraw would contain.

## 11.4 The paired design, and why every headline number has two arms

**The single most important methodological decision in this evaluation is that nothing is measured
in one arm.** Every compatibility and security figure was produced twice on the same host, in the
same session, against the same release: once **confined**, and once against a **full, unconfined**
Home Assistant with no namespaces, no seccomp, no cgroup, no mount view, no mediator and no bridge.

Two construction decisions carry the validity of that comparison:

**The measurement function is shared, not copied.** Both arms import the same `inspect()` function
and call it with the same arguments, so both compute the same outcome ladder with the same platform
list and the same error handling. A reimplementation that drifted by one platform name would have
satisfied "hold the measurement fixed" in appearance only.

**The baseline's bias runs toward the baseline, deliberately.** The unconfined arm is given the
platform's base component, `default_config`, the integration's declared components and their
requirements, and the core package set. **A generous baseline makes the design's measured cost
larger**, which is the direction an evaluation of one's own artifact should err in.

> **The first version of this arm was biased the other way, and the correction is the reason to
> trust the second.** It set up only two components, so an integration declaring `mqtt` failed
> against the "full" instance while passing under confinement. **A baseline stingier than the arm
> it is compared against does not decompose a figure; it inverts it** — it would have reported a
> *negative* cost for confinement.

## 11.5 The instruments

| Instrument | What it produces |
|---|---|
| `compat.py` | The compatibility ladder in both arms, plus the C1 integrity count on every run |
| `selftest_*.py` (**19 suites**) | Every mechanism's behaviour, including the cases that must *fail* |
| The adversary integration | 38 attack attempts against a sandbox, recording three outcomes rather than two |
| `strace` cross-check | A second instrument bounding the in-process egress recorder |
| `integrity.py` | Source-tree hashing before and after each run — C1, counted |

**The adversary records three outcomes and the third is the design's whole argument:**

| Outcome | Meaning |
|---|---|
| `BLOCKED` | The attempt raised. Something refused it |
| `EMPTY` | The attempt **succeeded and found nothing**, because there was nothing there |
| `LEAKED` | It returned something it should not have |

**A design producing only `BLOCKED` would be the procedural one.** Collapsing `EMPTY` into "pass"
would hide exactly the property the architecture was chosen for.

## 11.6 Predictions registered before measurement

Eight predictions were committed to the repository **before** the corresponding runs, five in the
evaluation plan and three in a file committed before the uniform corpus was drawn. They are scored
in §12.9. Registering them is what makes the evaluation falsifiable rather than descriptive: **a
prediction is worth having precisely because it can be wrong**, and six of these were.

## 11.7 What this evaluation cannot do

Stated in advance rather than conceded afterwards.

- **It cannot measure what a live Home Assistant does with a mediated write**, because the far side
  of the mediator is a stand-in.
- **It cannot report an end-to-end compatibility rate**, because 26 of 37 head-corpus integrations
  require a credential before their own configuration flow completes, and no measurement of any
  confinement scheme can produce those credentials.
- **It cannot assess R3**, the mediator's unscoped credential, because the limitation is upstream.
- **It cannot demonstrate the absence of failures**, only the absence of the failures it looked
  for. This is why the threat model is a separate activity from the testing.
