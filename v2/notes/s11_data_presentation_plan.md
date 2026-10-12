# §11 Data presentation — plan and decisions (2026-10-12)

Budget 1,100 words, 4 pp. The template gives a heading only. §12 relies on §11 for: the three assertions
and their falsifiers, the fourth falsifier, the paired design, and the rule that no aggregate "threats
controlled" figure is reported (`notes/s12_results_plan.md`, "Owed by §11").

**Sources, rebuilt from the working report, not from the 2026-09-08 draft:** `report/07_evaluation.md`
§7.1 (criteria dated 2026-09-02), §7.2 (assertions A/B/C), §7.7 (falsifiers, fourth falsifier), §7.9
(threats to validity), §7.23.1 (corpora table); `experiments/verify/results/phase3_timing/verdicts.md`
and `final_f45_stats.txt` (five passes, tolerances); `experiments/verify/timing_stats.py` (the interval);
`REPRODUCE.md` "What you need" (environment).

**Structure:** opening; 11.1 claim and falsifiers (Table 11.1); 11.2 paired design; 11.3 environment
and corpora (Tables 11.2, 11.3); 11.4 instruments and statistics; 11.5 how results are presented.

**Kept out, because §8 already says it:** the claim register and its tiers (§8.6), prediction notes
(§8.6), mutants and faults (§8.6), no independent adversary (§8.7). §11 names the tiers' wording rule
in one clause only.

**Checked against source while drafting:**
- Both arms call one function, `inspect()` in `sandbox_runtime.py:876`; `compat.run_one_baseline`
  sets up `homeassistant` + `default_config` + the declared components and their requirements.
  The first baseline failed `alarmo` (declares `mqtt`), which passed confined (`compat.py:401`).
- Two interpreters: the supervisor and mediator on the OS's Python 3.13.5, Home Assistant and the
  sandboxes on 3.14.7 (`REPRODUCE.md`; result files record both). The 2026-09-08 draft named only
  3.14.7.
- Kernel `6.12.47+rpt-rpi-2712`, Raspberry Pi OS (Debian 13 trixie), Pi 5 4 GB.
- Timing: five passes (pass 1–3 at `verify-2026-10`, three boots; `final`; `final_f45`). Tolerances
  fixed before pass 1: ±20% on timings, ±5% on memory, judged on the median across passes. p99 is
  per pass. **The "bootstrap 95% interval" of a median of five resamples five values, so it is close
  to their range** (the script's own docstring says so); §11 says that, and §12 reports the range.
- Corpora: figures as §7.23.1 after its correction (head median 16,294, total 998,478, "twenty-one
  times").
- 26 of 37 head-corpus integrations need a credential before their configuration flow completes
  (§7.17.1's ceiling of eleven).

**Numbers that move at the final rerun:** none quoted here except the pass count (five, unless the
rerun adds a sixth) and the adversary's 38 attempts.

**2026-10-12 (later): checklist pass with the academic-research-writer skill** (Younes: always load it for
report writing; §11 had been drafted without it). Fixed: the uncited falsifiability principle recast as
the project's procedure (no Popper reference added; offer it if wanted); "unconfined arm" defined in 11.1
before Table 11.1 uses it; [1] on the telemetry's missing spread; [5] on HACS; **[49]** kernel proc docs
for PSS (definition quoted, checked); **[50]** Efron 1979 for the bootstrap (Crossref). Voice: no first
person. 1,298 prose words.

**2026-10-12: Popper [51] cited in 11.1** ("Following Popper's criterion of falsifiability [51]"), the principle recast earlier now carries its source; the argument itself sits in §8.1 rule 3.
