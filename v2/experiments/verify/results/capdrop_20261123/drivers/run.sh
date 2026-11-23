#!/bin/bash
# 1) adversary suite on unchanged HEAD (pre clone): the four capability attempts expected to LEAK (P1 on aarch64)
# 2) fixed clone: (A) fresh, preflight, every suite twice (P3)
# 3) the 77 confined measurements (final2 chunk E, confined arms only, (A) down), compared with final2
# 4) the fifteen against the real (A) (final2 chunk G), with its verdict scripts
source ~/r2exp/capdrop-20261123/drivers/common.sh
begin pre_adversary
cd "$TP/framework" || exit 2
echo "pre: HEAD enter.py, new selftest_adversary.py only: $(git -C "$TP" status --porcelain | tr "\n" " ")" >> "$S"
step adversary_head systemd-run --user --scope -q python3 -m confine.selftest_adversary
fin
begin post_suites
cd "$T/framework" || exit 2
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up --fresh
step preflight systemd-run --user --scope -q python3 -m confine.preflight
cd "$T"
TO=5400 step suites_1 bash experiments/selftests/suites_all.sh "$OUT/suites_1"
TO=5400 step suites_2 bash experiments/selftests/suites_all.sh "$OUT/suites_2"
for n in 1 2; do echo "suites_$n failed=$(grep -c 'exit=[^0]' "$OUT/suites_$n/summary.txt") of $(grep -c 'exit=' "$OUT/suites_$n/summary.txt")" >> "$S"; done
fin
begin compat
cd "$T/framework" || exit 2
step house_a_down python3 -m confine.house_a down
TO=14400 step c1_declared_core $run confine.compat --corpus $C --python $P --profile declared --platform-deps $PD --json "$OUT/c1_declared_core.json"
TO=14400 step uniform_confined $run confine.compat --corpus $U --python $P --profile declared --platform-deps $PD --json "$OUT/uniform_confined.json"
for a in c1_declared_core uniform_confined; do
  python3 $B/drivers/compare.py $B/final2/$a.json "$OUT/$a.json" > "$OUT/compare_$a.txt" 2>&1; echo "compare_$a exit=$?" >> "$S"
done
fin
begin real
cd "$T/framework" || exit 2
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up --fresh
step real_house python3 -m confine.selftest_real_house
TO=5400 step function $run confine.endtoend_function --corpus $C --python $P --platform real --json "$OUT/function.json"
for s in nordpool dwd_weather pirateweather waste_collection_schedule; do step egress_$s $run confine.endtoend_egress --subject $s --corpus $C --python $P --platform real --json "$OUT/egress_$s.json"; done
for s in smhi_brandrisk regensburg_transport; do step egress_$s $run confine.endtoend_egress --subject $s --corpus $U --python $P --platform real --json "$OUT/egress_$s.json"; done
for s in midea_ac_lan localtuya; do step local_$s $run confine.endtoend_local --corpus $C --python $P --subject $s --platform real --json "$OUT/local_$s.json"; done
step oauth_trakt $run confine.endtoend_oauth --corpus $U --python $P --platform real --json "$OUT/oauth_trakt.json"
cd "$T" || exit 2
python3 verify/bridge_step5_verdicts.py "$OUT" > "$OUT/verdicts_bridge_step5.txt" 2>&1; echo "verdicts_bridge_step5 exit=$?" >> "$S"
python3 verify/retest_e2e_verdicts.py "$OUT/function.json" > "$OUT/verdicts_retest_e2e.txt" 2>&1; echo "verdicts_retest exit=$?" >> "$S"
python3 verify/e2e_ext_verdicts.py "$OUT/function.json" "$OUT/egress_waste_collection_schedule.json" > "$OUT/verdicts_e2e_ext.txt" 2>&1; echo "verdicts_e2e_ext exit=$?" >> "$S"
fin
echo RUNDONE >> $R/run.done
