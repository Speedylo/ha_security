#!/bin/bash
# F57's regression (notes/f57_approval_gate_prediction.md A2–A5), on a fresh clone of fix-2026-10-f57
# at ~/r2exp/f57/tag. A2, the new suite; A3, (A) up, every suite twice (28 with selftest_approval);
# A4, nordpool end to end; A5, every mutant in a file this change touches, M39 and M40 new.
# The tag contains F58's fix, so A3 is also F58's R6.
T=~/r2exp/f57/tag/v2; OUT=~/r2exp/f57/out/regress; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; run="systemd-run --user --scope -q python3 -u -m"
step() { local name=$1; shift; local t=$(date +%s); timeout 2400 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd "$T/framework" || exit 2
step a2_selftest_approval $run confine.selftest_approval
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up
cd "$T"
step suites_1 bash experiments/selftests/suites_all.sh "$OUT/suites_1"
step suites_2 bash experiments/selftests/suites_all.sh "$OUT/suites_2"
for n in 1 2; do echo "suites_$n failed=$(grep -c 'exit=[^0]' "$OUT/suites_$n/summary.txt") of $(grep -c 'exit=' "$OUT/suites_$n/summary.txt")" >> "$S"; done
cd framework
step a4_egress_nordpool $run confine.endtoend_egress --subject nordpool --corpus $C --python $P --json "$OUT/egress_nordpool.json"
cd "$T"
for m in M01 M03 M08a M08b M17 M19 M20 M21 M31 M32 M33 M34 M35 M39 M40; do
  MUT_ONLY="$m" MUT_WORK=~/r2exp/f57/mut bash verify/mutants/run_mutants.sh "$T" "$OUT/mutants" > /dev/null 2>&1
done
echo "mutants: $(grep -v ALLDONE "$OUT/mutants/run.txt" | tr '\n' ' ')" >> "$S"
(cd framework && python3 -m confine.house_a status) | grep -qx up || echo "(A) not up at the end" >> "$S"
echo ALLDONE >> "$S"
