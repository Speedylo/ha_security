#!/bin/bash
# Chunk B: step 2a, mutants M01–M50 one at a time through run_mutants.sh (it globs M*, which now also
# matches M51–M88, so each is named), then M18a–c through run_bridge_mutants.sh (mutated code in (A)).
source ~/r2exp/final2-run/drivers/common.sh
begin chunkB_step02a
cd "$T" || exit 2
for p in verify/mutants/M*.patch; do m=$(basename "$p" .patch)
  case $m in M18*|M5[1-9]*|M[6-9][0-9]*) continue ;; esac
  MUT_ONLY="$m" MUT_WORK=~/r2exp/final2-run/mut bash verify/mutants/run_mutants.sh "$T" "$OUT/framework" > /dev/null 2>&1
done
MUT_WORK=~/r2exp/final2-run/mut-bridge bash verify/mutants/run_bridge_mutants.sh "$T" "$OUT/bridge" > "$OUT/bridge.log" 2>&1
grep -v ALLDONE "$OUT/framework/run.txt" > "$OUT/framework_results.txt"
echo "framework mutants: $(grep -c failed_suites= "$OUT/framework_results.txt") run, survived (failed_suites=0): $(grep 'failed_suites=0$' "$OUT/framework_results.txt" | cut -d' ' -f1 | tr '\n' ' '), patch failed: $(grep -c 'patch failed' "$OUT/framework_results.txt")" >> "$S"
echo "bridge: $(grep -v ALLDONE "$OUT/bridge/run.txt" | tr '\n' ';')" >> "$S"
(cd framework && python3 -m confine.house_a status) | grep -qx up || echo "(A) not up at the end" >> "$S"
fin
