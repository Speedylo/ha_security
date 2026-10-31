# Do the new kinds' tests bite? Review and mutants M51–M79 — prediction (2026-10-31)

**Committed before any mutant runs.** Younes, 2026-10-31, after B4a: "defer b4b to later. First,
make sure the existing tests are correct and can fail." B4b's draft stays uncommitted
(`bridge_kinds_b4b_prediction_20261031.md`).

The B1–B4a tests (`selftest_commands` K12–K31, `selftest_bridge_types` T11–T31) each failed first
against the code before their batch, but that was coarse: (A) refused the whole kind, so every check
on it failed at once. It does not show that each check would notice the specific behaviour it is
named for going wrong. Two parts: a reading of the checks for ones that cannot fail, and one mutant
per behaviour, as phase 4.3 did (`verify/mutants/mutants.py`, M01–M50).

## 1. Checks that cannot fail, or fail only with another

Read from the fails-first runs (each batch's `*_pre.log`) and the test code:

| Checks | Why they cannot fail on their own | Status |
|---|---|---|
| T12, T18, T25, T29 "the call succeeds" | A call naming an entity (A) does not have succeeds silently in Home Assistant: they passed before every batch | Meaningful only after the routing check before them; kept, stated |
| T13, T19, T31 "no command decision was recorded" | Passed before (nothing was ever sent); they test that **Home Assistant** rejected the call in (A), which the first check of each pair shows | Checks of Home Assistant, not of the bridge; stated |
| K14, K20, K25, K31 refused services; K15/K26 "not in the log"; T14, T26 | Pass before (no rule, nothing forwarded). They can fail only if code forwards or logs what it must not | Covered by M58, M60–M62 below |
| T5 (a to-do list refused) | Passes before and after every batch | A guard against widening `SUPPORTED`; not mutated (the bridge has no to-do platform to load) |

## 2. Mutants

`verify/mutants/mutants_kinds.py` writes M51–M79 (`Mxx.patch`, one exact replacement each);
`verify/mutants/run_kind_mutants.sh` runs, on the Pi from a fresh clone of the committed tag, the
pristine tree first (control) and then each mutant in its own copy: `selftest_commands`, then (A)
`down` and `up --fresh` **from the mutated tree** (so (A) runs the mutated bridge; the runner checks
(A)'s copy of the mutated file), then `selftest_bridge_types`.

**Criteria, fixed now.** Control: both suites pass (251/251, 165/165). A mutant is **killed** when
either suite exits non-zero, and the failing check is recorded; it **survives** otherwise. A kill by
a check other than the predicted one is reported as such. For a bridge mutant, a run where (A)'s copy
is not the mutated file is void.

| Mutant | Behaviour broken | Predicted |
|---|---|---|
| M51 | data may carry keys the shape does not list | killed: K13 (entity_id redirect), also K3, K7, K19, K24, K30 |
| M52 | every key optional | killed: K13 (set_percentage with none), K19, K24, K30 |
| M53 | a colour of any length | killed: K13 (rgb of 2 and of 4) |
| M54 | flash any string | killed: K13 (flash medium) |
| M55 | white may not be empty | killed: K12 (white `null`) |
| M56 | codes up to 1024 characters | killed: K7 and K13 (65-character codes) |
| M57 | params, extras, remote commands 16× larger | killed: K19 (5 KiB params, 4097 characters, 65 commands), K30 (extra over 4 KiB) |
| M58 | notification text logged | killed: K26 |
| M59 | a time not parsed | killed: K24 (25:00) |
| M60 | a light's toggle forwarded | killed: K14 |
| M61 | an update's skip forwarded | killed: K25 |
| M62 | a media player's join forwarded | killed: K31 |
| M63 | a republished event fires again | killed: T24 (republish) |
| M64 | an unlisted event type raises in (A) | **may survive**: the exception is raised inside the bridge's dispatcher callback, which Home Assistant logs; T24 checks (A)'s state and that a later publish works, not (A)'s log |
| M65 | the sandbox's picture link shown | killed: T28 (no `entity_picture`) |
| M66 | browse, search, grouping offered | killed: T28 (features), T31 (join no longer refused in (A)) |
| M67 | an id (A) cannot resolve fails the call | killed: T30 (ring id) |
| M68 | (A)'s own media never resolved | killed: T30 (signed link) |
| M69 | volume_up worked out in (A) | killed: T29 (it arrives as volume_set) |
| M70 | release notes offered | killed: T22 (features 13) |
| M71 | siren tone by key | killed: T18 (`"1"` for `"fire"`) |
| M72 | water heater forwards all service data | killed: T18 °F (the target arrives too; the mediator refuses it) |
| M73 | away mode on sent as off | killed: T18 |
| M74 | a valve never reports its position | killed: T18 (open_valve instead of position 100) |
| M75 | fan speed count ignored | killed: T12 (51 instead of 75) |
| M76 | fan on/off by Home Assistant's rule | **survives**: the test fan is published on with a percentage, so both rules say on. No check publishes a fan on without a speed |
| M77 | lock code format not checked to compile | **survives**: no check publishes a format that does not compile |
| M78 | GPS tracker shows the sandbox's state | killed: T23 (home at (A)'s coordinates) |
| M79 | scanners built as GPS trackers | **survives**: built as a GPS tracker with no coordinates, a scanner shows its published home/not_home as a place name, and keeps the bridge's id and its MAC attribute; no check reads anything that differs (its `source_type`) |

**Then:** every survivor gets a check that fails under its mutant and passes on the pristine tree,
shown both ways, before it is counted as covered. Outcome appended below.
