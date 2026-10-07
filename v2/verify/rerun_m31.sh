#!/bin/bash
# After M31's survival: the 27 suites twice on the moved tag, then M31–M35 (notes/f48_f49_prediction_20261007.md, addendum).
T=~/r2exp/verify-tests/v2; OUT=~/r2exp/verify/regress_tests_m31; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
cd "$T"
for n in 1 2; do bash experiments/selftests/suites_all.sh "$OUT/suites_$n"; echo "suites_$n failed=$(grep -c 'exit=[^0]' "$OUT/suites_$n/summary.txt") of $(grep -c 'exit=' "$OUT/suites_$n/summary.txt")" >> "$S"; done
for m in M31 M32 M33 M34 M35; do
  MUT_ONLY=$m MUT_WORK=~/r2exp/tb/work_m31 bash verify/mutants/run_mutants.sh "$T" "$OUT/mutants" > /dev/null 2>&1
  (cd framework && python3 -m confine.house_a status) | grep -qx up || (cd framework && python3 -m confine.house_a up >> "$OUT/house_a_reup.log" 2>&1; echo "$m: (A) brought up again" >> "$S")
done
grep failed_suites "$OUT/mutants/run.txt" >> "$S"; echo ALLDONE >> "$S"
