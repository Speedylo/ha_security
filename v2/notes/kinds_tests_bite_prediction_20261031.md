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

## Outcome, run 1 (2026-10-31, 16:18–17:09, tag `kinds-bite-pre`)

Results: `experiments/verify/results/kinds_bite_20261031/` (`run.txt`, one directory per mutant).
**Control** passed both suites. Every bridge mutant ran with (A)'s copy of the file mutated.

- **Killed as predicted (24):** M52–M63, M65–M73, M75 (also T11), M78. M58 was also caught in
  (A)'s durable log (T26).
- **Killed by another check (1):** M74 by T17 ((A)'s description of the valve: no `current_position`),
  before T18 runs.
- **Survived, as predicted (4):** M64, M76, M77, M79.
- **M51: killed, but not as intended.** Deleting the "only listed keys" test leaves the next line
  looking every key up in the shape, so an extra key raised a `KeyError` and both suites crashed with
  no FAIL line. That shows the test is what turns an extra key into a refusal rather than a crash. It
  does not show that K13 notices extra keys being accepted. The mutant was wrong as written (AI-use
  log 34). Added: **M51b**, the extra keys accepted and skipped.

## Run 2: the survivors' checks — prediction (before the run)

New checks in `selftest_bridge_types`, read from Home Assistant 2026.8.3; no framework code changed:

| Check | What it reads | Pristine | Mutant |
|---|---|---|---|
| T11 a fan published on with no speed and no preset shows on | `fan/__init__.py` `is_on`: a percentage above 0 or a preset | on | M76: off |
| T16' a lock published with the format `[0-9`: (A) offers none, and unlock with a code reaches the sandbox; the call succeeds | `lock/__init__.py` `code_format_cmp` compiles the format for every lock and unlock | passes | M77: `re.error` in (A), the call fails, nothing arrives (both checks) |
| T23 a scanner at home is in (A)'s home zone | `device_tracker/entity.py`: a scanner's `in_zones` is its associated zone (`zone.home` by default); a GPS tracker with no coordinates has none | `["zone.home"]` | M79: `[]` |
| T24 (A) accepts the unlisted event type's publish | `event/__init__.py` `_trigger_event` raises `ValueError`; raised inside `ws_publish`, Home Assistant answers the publish with an error, which the mediator returns as a refusal | ok | M64: refused |

(M64's earlier reason, that the exception would only be logged, was wrong: it reaches the publish
answer, which T24 had not read.)

**Run:** the control and M51b, M63, M64, M76, M77, M79 (`MUT_ONLY`), from a fresh clone of the new
tag. M63 is included because T24's helper changed. The other 23 mutants are not rerun: the Pi has
2.3 GB free and run 1's work copies take 1.9 GB.

**Predicted:**

- control: `selftest_commands` 251/251, `selftest_bridge_types` 170/170 (165 + 5).
- M51b: killed by the redirect checks (K3 text, K7 disarm, K13 light, K19/K24/K30), as FAIL lines.
  `selftest_bridge_types` passes, since no check there sends unlisted keys.
- M63: killed by T24 (republish).
- M64: killed by the new T24 check.
- M76: killed by the new T11 check.
- M77: killed by both new T16' checks.
- M79: killed by the new T23 check.

## Outcome, run 2 (2026-10-31, 17:37–17:49, tag `kinds-bite-2-pre`)

Results: `experiments/verify/results/kinds_bite_20261031_run2/`. **Every prediction held.**

- **Control:** `selftest_commands` 251/251, `selftest_bridge_types` 170/170. The four new checks pass
  on the pristine tree: the fan shows `on`; the lock offers no format and `unlock` arrives as
  `{'code': '5822'}`, then succeeds; the scanner's `in_zones` is `['zone.home']`; the publish is
  answered ok.
- **M51b:** killed by `selftest_commands` (227/251); `selftest_bridge_types` passes (170/170), as
  predicted. The 24 failures are every redirect check (K3, K7, K13, K19, K24, K30) and every
  extra-key check. They also include four bad-code checks (K7 and K13: a numeric code, a 65-character
  code), which were not predicted. A coded service lists an empty shape `{}` beside
  `{"code": …}` (`_CODED`), so with the code key skipped a bad code fits the empty shape.
- **M63:** killed by T24 (republish), 169/170, as in run 1.
- **M64, M76, M77, M79:** each killed by its new check alone: 169/170, and 168/170 for M77 (both
  T16' checks; in (A), "unterminated character set", Python's `re.error` for `[0-9`).

**Result.** Of 30 mutants (M51–M79, M51b), the tests now catch 29. M51 counts only as a crash, and
M51b replaces it as the measure. Every behaviour in B1–B4a has a check shown to fail without it.
Not rerun after the new checks: M52–M62 and M65–M75, M78. Their killing checks are unchanged, but the
Pi has no room for a full run beside run 1's work copies (`~/r2exp/km/work`, 1.9 GB, 2.3 GB free).
