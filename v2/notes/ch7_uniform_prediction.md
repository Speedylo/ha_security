# The uniform-sample arm — registered before it runs

**Written 2026-09-02, before the corpus was drawn and before anything was run.**
This file exists so that §7.23's predictions are checkable rather than asserted. §7.6 is
frozen and dated and is **not** edited to add these; a prediction registered late is not a
prediction, and the commit that carries this file is the timestamp.

## What is being measured, and why it is owed

§7.9 records the corpus as a threat to external validity in plain terms: the 37 integrations
are the *most-installed* ones, so every figure in §6.11–§6.14 and §7.12 answers **"what do
most installations run?"** and not **"what do most integrations do?"** §7.10's item 7
scheduled the arm that separates them, and it is the only scheduled measurement this chapter
never attempted.

The two questions have different answers because the population is extremely skewed. §1.3
measured a long tail whose **median community integration has about 20 installs**. The
install-weighted corpus is drawn from the head of that distribution: actively maintained,
widely exercised, and quick to break loudly when a Home Assistant release moves under them.
A uniform draw is mostly tail.

## Method, fixed now

- **Same everything except the selection.** Same release (2026.8.3), same host, same
  interpreter, same profile (`declared` + core package set — §6.14's recommendation), same
  `inspect()` function, same harness.
- **Sample size 40 requested**, matching the head corpus's 40 requested / 39 fetched / 37
  usable, so the two are compared at the same n.
- **Seed 20260902**, chosen as today's date before the draw and recorded in the manifest.
  One draw. If it is re-drawn for any reason, both draws are reported.
- **Both arms.** Confined and unconfined baseline, as §7.12 established is the only way a
  compatibility number decomposes.

## Predictions

Recorded before the run, scored afterwards as written, and **not revised**. §7.12 scored P1
and P2 wrong; §7.19 scored P4 wrong; §7.20 falsified P5. Four of five so far, which is the
reason this file exists at all.

**P6 — the uniform sample imports clean at a *lower* rate than the head sample's 84%, by
between 10 and 30 percentage points.** Reasoning: tail integrations are less maintained, so
more of them have rotted against a release that has moved; §6.14.3 already found one head
integration (`eufy_security`) failing on a constant Home Assistant removed, and that class
should be commoner in the tail. Counter-argument I am recording because it may be what
actually happens: tail integrations are also *smaller* and *simpler*, often a single sensor
file with no dependencies, and the head corpus's failures were mostly missing packages —
which a simple integration does not have.

**P7 — the design's compatibility cost stays zero, or within one integration of it.**
Confined and unconfined will fail on the same set. §7.12's finding was structural rather than
a property of that corpus: nothing in the sandbox breaks an import that a full instance would
have completed. If this is wrong it is the most important result in the chapter, because it
would mean §7.12's zero was an artefact of measuring only well-maintained code.

**P8 — the *corpus artefact* rate is higher than the head sample's.** §6.14.3 set aside two
of 37 as corpus defects rather than failures (`hacs` bundling its frontend at release-build
time, `spook`'s directory layout). Tail repositories are less likely to follow the standard
`custom_components/<domain>/` layout, so the fetch itself should fail more often and more of
what is fetched should be unloadable for reasons that are nobody's design decision.

## What would make this measurement worthless

Stated now so it cannot be rationalised later:

- If the draw fetches fewer than about 25 usable integrations, n is too small to compare
  against 37 and the result is reported as indicative only.
- If the uniform arm is run at a different profile from the head arm, the comparison measures
  the profile and not the sampling. It will not be.
- If P6 is wrong in the *other* direction — the tail doing better than the head — that is a
  real result and gets reported as one, not explained away.
