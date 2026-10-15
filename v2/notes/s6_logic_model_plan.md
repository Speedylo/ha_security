# §6 Logic Model — plan and decisions (2026-10-15)

Budget 900 words, 3 pp; drafted at ~1,080 prose words (trim at week 6 or on review). Skill loaded
before drafting. Rebuilt from the approved sections; the 2026-09-08 draft used as a skeleton only.

## The scorecard behind Table 6.1 (every `notes/*prediction*.md`, 35 files)

Counted from each note's own Outcome section or the working report's scorecard for it.

**Row 1 — first evaluation (2 held / 8):** report §7.6 P1–P5 (§7.23.7: P3 held) + `ch7_uniform` P6–P8
(P7 held). F36: git cannot show §7.6 preceded its run.

**Row 2 — 3–5 Oct (107 / 119), 16 notes:** ch7_31_endtoend 8/10 (§7.31.8; P1 first run, P6 dwd retries) ·
ch7_31_compat_rerun 6/6 (P1–P2 + addendum P3–P6) · ch7_31_egress_shape_rerun 3/5 (P4 aiodns share, P5
ratio band) · ch7_31_remaining_rerun 5/6 (unstripped ±4 MB missed by 1.3) · t3_credentialed 5/6 (P2
equality) · t4_auditlog_wiring 5/6 (open prediction, qualified) · t5_api_surface_uniform 8/8 ·
item12_footprint_rerun 10/11 (A6 single-sandbox half) · w1_push_loop 8/9 (P7 backlog 278) ·
w1_step2_real_platform 8/8 · w1_step2b_commands 8/8 · w2a_local_tcp 7/8 (baseline) · w2b 8/8 ·
w2c_bytecode_cache 5/6 (B4 platform-deps warm) · w2d_token_refresh 6/6 · flood_cutoff 7/8 (F6 benchmark).

**Row 3 — 7–13 Oct (96 / 102), 10 notes:** f48_f49 18/19 (unpredicted survivor, supervisor kill) ·
e2e_functional_retest 42/45 (STATE 2026-10-09) · f54 4/4 · f56 3/3 · f57 5/6 (A3 harness) · f57c 3/4
(C2 the fix crashed; held at -f57d) · f58 6/6 · f59 5/5 · f60 4/4 · t06_true_pair 6/6.

**Not counted (pass/fail criteria for fixes and checks), 8 notes:** fault_injection, review_fixes,
integrity_consistency, final_pass, f45, f08_t06, minor_findings, tests_bite_20261007.

Scoring rule, as §7.31.8: a prediction is scored against the run it was about (first run), even if it
held after a fix. Where a note's count is stated by the working report, that count is used.

## Changed from the old draft
- "Six of eight wrong" now the first row only; all 229 counted predictions scored (plan: not eight).
- Old P7 "per-integration declared beats blanket ✅" was not one of the registered eight; dropped.
- "29 suites", "75 integrations", "nineteen threats" brought to current figures; outputs point at Table 3.3.
- **Long-term outcome rewritten:** the old draft said a check inside Home Assistant's loader would be the
  better design. That contradicts §9's first decision ([9]: an in-process check can be reached by the
  code it restricts). Now: the platform adopts a process boundary, and makes its per-domain user policy
  configurable (R3).
- Challenge "mediator must hold an unscoped credential" was stale after F45; now "acts as an ordinary user".
- Pointers to §14/§15.2 removed.

## For Younes
1. **Approved §8.6 is slightly off on the prediction notes.** It says "34 such notes, and a script checks
   that each note was committed before its first result". There are 35 files, and `verify/prereg.py`
   checks 29: its glob `*_prediction.md` misses the two dated notes (`tests_bite_prediction_20261007`,
   `f48_f49_prediction_20261007`), three report UNCHECKED (f08_t06, final_pass, minor_findings: no result
   path named), and integrity_consistency is skipped by design. Checked by hand: tests_bite's note
   (17:32) precedes its first results (19:46). Options: reword §8.6 to "29 of them", or widen the glob and
   add the three to `RESULTS` before the week-5 rerun.
2. §6.2 says isolation, equal compatibility and refusal "held in every prediction that tested them".
   True of every miss listed above; confirm you're happy to state it.
3. A logic-model figure (inputs → activities → outputs → outcomes) is conventional for this section;
   none is drafted. Add one to the figure list?
