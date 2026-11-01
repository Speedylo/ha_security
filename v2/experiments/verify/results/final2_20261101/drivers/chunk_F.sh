#!/bin/bash
# Chunk F: steps 7 and 8 as on 16 October, plus waste_collection_schedule (both arms) and alarmo's
# verdicts. (A) is down for every unconfined arm (rule 3, F56).
source ~/r2exp/final2-run/drivers/common.sh
begin chunkF_step07_e2e
cd "$T/framework" || exit 2
step house_a_down_first python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up --fresh
step real_platform_restart $run confine.selftest_real_platform --restart
python3 -m confine.house_a status >> "$OUT/house_a_status.log" 2>&1
A=$OUT/supervise-audit; mkdir -p "$A"
python3 -c 'import sys; from pathlib import Path
from confine.describe import record_approval
from confine.manifest import Manifest, Provenance
c = Path(sys.argv[1]).resolve()
record_approval(c, Path(sys.argv[2]), Manifest(c.name, Provenance.DERIVED, {"schema_version": 1}))' \
  ../experiments/flood/demo_flood "$OUT/approvals.jsonl" >> "$OUT/approval.log" 2>&1; echo "approval exit=$?" >> "$S"
systemd-run --user --scope -q python3 -u -m confine.supervise --component ../experiments/flood/demo_flood --python $P --audit-dir $A \
  --approvals "$OUT/approvals.jsonl" --keep-dir "$OUT/kept" > "$OUT/supervise.log" 2>&1 &
SUP=$!; echo "supervisor pid $SUP" >> "$S"; sleep 25
step drive_demo env PYTHONPATH=. python3 ../experiments/flood/drive_demo.py "$OUT/supervise.log" $A
kill -TERM $SUP; sleep 5
step e2e_real_thermal $run confine.endtoend --corpus $C --python $P --only thermal_comfort --push --platform real --json "$OUT/e2e_real_thermal.json"
step e2e_real_adaptive $run confine.endtoend --corpus $C --python $P --only adaptive_lighting --push --platform real --command --json "$OUT/e2e_real_adaptive.json"
step house_a_down python3 -m confine.house_a down
step e2e_standin $run confine.endtoend --corpus $C --python $P --json "$OUT/e2e_standin.json"
for s in nordpool dwd_weather pirateweather waste_collection_schedule; do step egress_$s $run confine.endtoend_egress --subject $s --corpus $C --python $P --json "$OUT/egress_$s.json"; done
for s in smhi_brandrisk regensburg_transport; do step egress_$s $run confine.endtoend_egress --subject $s --corpus $U --python $P --json "$OUT/egress_$s.json"; done
step local_midea_ac_lan $run confine.endtoend_local --corpus $C --python $P --subject midea_ac_lan --json "$OUT/local_midea_ac_lan.json"
step local_localtuya $run confine.endtoend_local --corpus $C --python $P --subject localtuya --json "$OUT/local_localtuya.json"
step oauth_trakt $run confine.endtoend_oauth --corpus $U --python $P --json "$OUT/oauth_trakt.json"
fin
STEP7=$OUT

begin chunkF_step08_retest
cd "$T/framework" || exit 2
python3 -m confine.house_a status >> "$OUT/house_a_status.log" 2>&1
TO=5400 step endtoend_function $run confine.endtoend_function --corpus $C --python $P --json "$OUT/retest.json"
(cd .. && python3 verify/retest_e2e_verdicts.py "$OUT/retest.json") > "$OUT/verdicts_retest.txt" 2>&1; echo "verdicts_retest exit=$?" >> "$S"
(cd .. && python3 verify/e2e_ext_verdicts.py "$OUT/retest.json" "$STEP7/egress_waste_collection_schedule.json") > "$OUT/verdicts_e2e_ext.txt" 2>&1; echo "verdicts_e2e_ext exit=$?" >> "$S"
fin
