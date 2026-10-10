#!/bin/bash
# F54's regression (notes/f54_list_target_prediction.md P2–P4), on a fresh clone of fix-2026-10-f54
# at ~/r2exp/f54/tag. P2, the bridge suite alone; P3, (A) up, every suite twice, nordpool end to
# end, and the two mutants whose patches F54 moved (M08a, M08b); P4, the retest's scheduler
# variants in both arms, the command of retest_20261009 otherwise.
T=~/r2exp/f54/tag/v2; OUT=~/r2exp/f54/out/regress; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; run="systemd-run --user --scope -q python3 -u -m"
step() { local name=$1; shift; local t=$(date +%s); timeout 2400 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd "$T/framework" || exit 2
step p2_selftest_bridge $run confine.selftest_bridge --python $P
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up
cd "$T"
step suites_1 bash experiments/selftests/suites_all.sh "$OUT/suites_1"
step suites_2 bash experiments/selftests/suites_all.sh "$OUT/suites_2"
for n in 1 2; do echo "suites_$n failed=$(grep -c 'exit=[^0]' "$OUT/suites_$n/summary.txt") of $(grep -c 'exit=' "$OUT/suites_$n/summary.txt")" >> "$S"; done
cd framework
step egress_nordpool $run confine.endtoend_egress --subject nordpool --corpus $C --python $P --json "$OUT/egress_nordpool.json"
step p4_scheduler $run confine.endtoend_function --corpus $C --python $P --only scheduler,scheduler-no-read,scheduler-no-service --json "$OUT/p4_scheduler.json"
cd "$T"
MUT_ONLY="M08[ab]" MUT_WORK=~/r2exp/f54/mut bash verify/mutants/run_mutants.sh "$T" "$OUT/mutants" > /dev/null 2>&1
echo "mutants: $(tr '\n' ' ' < "$OUT/mutants/run.txt")" >> "$S"
(cd framework && python3 -m confine.house_a status) | grep -qx up || echo "(A) not up at the end" >> "$S"
echo ALLDONE >> "$S"
