# Run directories from the Pi, archived 2026-10-15

`r2exp_runs_20261015.tar.gz` (2,087 files, 10.2 MB; sha256
`3668efac966b1b5b0c57d31b4561c348042a90201d17ee03ed1c2f437a3a11bb`) holds every file from six run
directories on the reference device (`~/r2exp/tb`, `f16`, `f57`, `f57d`, `f59`, `mutants`) whose content
was not already in this repository, except copies of code: fetched corpora, pristine and mutated framework
trees, and coverage's own package installs, all of which are regenerated from the repository or upstream.
The six directories were then deleted to free space for the final rerun.

What it adds to the committed summaries:
- full per-suite logs of the F59 and F57c/F57d regressions and their mutant runs (`f59/out`, `f57d/out`,
  `f57/out`), behind `results/f59/regress` and `results/f57c/regress_f57d`;
- raw branch-coverage data (`tb/cov/data`) behind the 74% figure in `results/phase4/coverage`;
- run scripts and driver logs (`f59/k1.sh`, `f57/chain.sh`, `f57d/regress.sh`, `tb/m18c_check.sh`,
  `tb/mutants/run_bridge_mutants.sh`, `tb/*.log`, `*.nohup`) and two working files
  (`tb/selftest_real_platform.new.py`, `f16/api_surface_671795d.py`);
- the F16 rebuild's outputs (`f16/*.json`) and per-mutant timing stats (`mutants/final/*/…/stats.json`).

`r2exp_runs_20261015.files.txt` lists every path. Before it left the device the archive's full contents
were scanned for each credential value in `~/.config/capstone/` (20 values, 0 hits).
