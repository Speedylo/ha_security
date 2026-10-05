#!/bin/bash
# Phase 2, L2 and L3, on the frozen tree. One log per step, one summary line per step.
cd ~/r2exp/verify/v2/framework
OUT=~/r2exp/verify/v2/experiments/verify/results/phase2/l23; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; U=~/r2exp/corpus_uniform
step() { local name=$1; shift; local t=$(date +%s); timeout 2400 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
run() { systemd-run --user --scope -q python3 -u -m "$@"; }

# L2
step real_platform_restart run confine.selftest_real_platform --restart
python3 -m confine.house_a status >> "$OUT/house_a_status.log" 2>&1
A=$HOME/r2exp/verify-supervise-audit
systemd-run --user --scope -q python3 -u -m confine.supervise --component ../experiments/flood/demo_flood --python $P --audit-dir $A > "$OUT/supervise.log" 2>&1 &
SUP=$!; sleep 25
step drive_demo env PYTHONPATH=. python3 ../experiments/flood/drive_demo.py "$OUT/supervise.log" $A
kill -TERM $SUP; sleep 5; cp $A/decisions.jsonl "$OUT/supervise_decisions.jsonl" 2>/dev/null

# L3, stand-in and (A)
step e2e_standin run confine.endtoend --corpus $C --python $P --json "$OUT/e2e_standin.json"
step e2e_real_thermal run confine.endtoend --corpus $C --python $P --only thermal_comfort --push --platform real --json "$OUT/e2e_real_thermal.json"
step e2e_real_adaptive run confine.endtoend --corpus $C --python $P --only adaptive_lighting --push --platform real --command --json "$OUT/e2e_real_adaptive.json"

# L3, egress
for s in nordpool dwd_weather pirateweather; do step egress_$s run confine.endtoend_egress --subject $s --corpus $C --python $P --json "$OUT/egress_$s.json"; done
for s in smhi_brandrisk regensburg_transport; do step egress_$s run confine.endtoend_egress --subject $s --corpus $U --python $P --json "$OUT/egress_$s.json"; done

# L3, local devices and OAuth
step local_midea_ac_lan run confine.endtoend_local --corpus $C --python $P --subject midea_ac_lan --json "$OUT/local_midea_ac_lan.json"
step local_localtuya run confine.endtoend_local --corpus $C --python $P --subject localtuya --json "$OUT/local_localtuya.json"
step oauth_trakt run confine.endtoend_oauth --corpus $U --python $P --json "$OUT/oauth_trakt.json"
echo ALLDONE >> "$S"
