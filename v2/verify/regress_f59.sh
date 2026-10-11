#!/bin/bash
# F59's regression (notes/f59_kept_storage_prediction.md K2–K5), on a fresh clone of fix-2026-10-f59
# at ~/r2exp/f59/tag. K2, the new suite; K3, (A) restarted from the tag (so it runs the bridge with
# F57c's issue), every suite twice (29 with selftest_keep); K4, nordpool end to end; K5, every mutant
# in a file this change touches (sandbox.py, sandbox_runtime.py, supervise.py), M45–M49 new, and F60's M50 (D4).
T=~/r2exp/f59/tag/v2; OUT=~/r2exp/f59/out/regress; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; run="systemd-run --user --scope -q python3 -u -m"
step() { local name=$1; shift; local t=$(date +%s); timeout 2400 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd "$T/framework" || exit 2
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up
step k2_selftest_keep $run confine.selftest_keep --python $P
cd "$T"
step suites_1 bash experiments/selftests/suites_all.sh "$OUT/suites_1"
step suites_2 bash experiments/selftests/suites_all.sh "$OUT/suites_2"
for n in 1 2; do echo "suites_$n failed=$(grep -c 'exit=[^0]' "$OUT/suites_$n/summary.txt") of $(grep -c 'exit=' "$OUT/suites_$n/summary.txt")" >> "$S"; done
cd framework
step k4_egress_nordpool $run confine.endtoend_egress --subject nordpool --corpus $C --python $P --json "$OUT/egress_nordpool.json"
cd "$T"
for m in M14 M15 M31 M32 M33 M34 M35 M41 M42 M45 M46 M47 M48 M49 M50; do
  MUT_ONLY="$m" MUT_WORK=~/r2exp/f59/mut bash verify/mutants/run_mutants.sh "$T" "$OUT/mutants" > /dev/null 2>&1
done
echo "mutants: $(grep -v ALLDONE "$OUT/mutants/run.txt" | tr '\n' ' ')" >> "$S"
(cd framework && python3 -m confine.house_a status) | grep -qx up || echo "(A) not up at the end" >> "$S"
echo ALLDONE >> "$S"
