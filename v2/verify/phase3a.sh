#!/bin/bash
# Phase 3a: the measurements judged exactly, on the frozen tree. One log per step, one summary line each.
cd ~/r2exp/verify/v2/framework
OUT=~/r2exp/verify/v2/experiments/verify/results/phase3a; mkdir -p "$OUT"; S="$OUT/summary.txt"
[ -s "$S" ] && mv "$S" "$OUT/summary_attempt$(date +%s).txt"; : > "$S"
P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; U=~/r2exp/corpus_uniform; D=~/r2exp/platform-deps
run="systemd-run --user --scope -q python3 -u -m"
step() { local name=$1; shift; local t=$(date +%s); timeout 3600 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }

step c1_baseline              $run confine.compat --corpus $C --python $P --profile baseline --json "$OUT/c1_baseline.json"
step c1_declared_core         $run confine.compat --corpus $C --python $P --profile declared --platform-deps $D --json "$OUT/c1_declared_core.json"
step uniform_baseline         $run confine.compat --corpus $U --python $P --profile baseline --json "$OUT/uniform_baseline.json"
step uniform_confined         $run confine.compat --corpus $U --python $P --profile declared --platform-deps $D --json "$OUT/uniform_confined.json"
step compat_minimal           $run confine.compat --corpus $C --python $P --profile minimal --json "$OUT/compat_minimal.json"
step compat_unstripped        $run confine.compat --corpus $C --python $P --profile unstripped --platform-deps $D --json "$OUT/compat_unstripped_currentdeps.json"
step api_surface_hacs         $P ../figures/api_surface.py --root $C --label hacs --json "$OUT/api_surface_hacs.json"
step api_surface_uniform      $P ../figures/api_surface.py --root $U --label hacs-uniform40 --json "$OUT/api_surface_uniform.json"
step entity_visibility        $run confine.selftest_reads --python $P --json "$OUT/pi5_s3.json"
step gc_attack                $run confine.selftest_gc --python $P --json "$OUT/pi5_s1.json"
step adversary_confined       $run confine.selftest_adversary
step adversary_unconfined     $run confine.selftest_adversary_baseline
step egress_shape             python3 -u -m confine.egress_shape --corpus $C --python $P --uv ~/.local/bin/uv --platform-deps $D --settle 20 --strace --full-events --json "$OUT/pi5_egress_shape.json"
echo ALLDONE >> "$S"
