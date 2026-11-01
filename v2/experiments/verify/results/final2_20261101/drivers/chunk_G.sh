#!/bin/bash
# Chunk G: step 8b, the fifteen against the real (A), as B5 (notes/bridge_kinds_b5_prediction_20261031.md).
source ~/r2exp/final2-run/drivers/common.sh
begin chunkG_step08b_real
cd "$T/framework" || exit 2
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up --fresh
echo "lan $(hostname -I)" >> "$S"
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
