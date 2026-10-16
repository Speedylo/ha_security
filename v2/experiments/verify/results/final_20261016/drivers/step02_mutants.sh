#!/bin/bash
# Final rerun, step 2: all 53 mutants against the clone of final-2026-10. The 50 framework mutants one at
# a time through run_mutants.sh (fresh copy each), then M18a–c through run_bridge_mutants.sh, whose
# mutated code runs inside (A) and whose control run brings (A) back up from the pristine clone.
T=~/r2exp/final/v2; OUT=~/r2exp/final-run/out/step02_mutants; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
echo "start $(date -Is) commit $(git -C "$T" rev-parse HEAD) dirty=$(git -C "$T" status --porcelain | wc -l)" >> "$S"
cd "$T" || exit 2
for p in verify/mutants/M*.patch; do m=$(basename "$p" .patch)
  case $m in M18*) continue ;; esac
  MUT_ONLY="$m" MUT_WORK=~/r2exp/final-run/mut bash verify/mutants/run_mutants.sh "$T" "$OUT/framework" > /dev/null 2>&1
done
MUT_WORK=~/r2exp/final-run/mut-bridge bash verify/mutants/run_bridge_mutants.sh "$T" "$OUT/bridge" > "$OUT/bridge.log" 2>&1
grep -v ALLDONE "$OUT/framework/run.txt" > "$OUT/framework_results.txt"
echo "framework mutants: $(grep -c failed_suites= "$OUT/framework_results.txt") run, survived (failed_suites=0): $(grep 'failed_suites=0$' "$OUT/framework_results.txt" | cut -d' ' -f1 | tr '\n' ' '), patch failed: $(grep -c 'patch failed' "$OUT/framework_results.txt")" >> "$S"
echo "bridge: $(grep -v ALLDONE "$OUT/bridge/run.txt" | tr '\n' ';')" >> "$S"
(cd framework && python3 -m confine.house_a status) | grep -qx up || echo "(A) not up at the end" >> "$S"
echo "end $(date -Is)" >> "$S"; echo ALLDONE >> "$S"
