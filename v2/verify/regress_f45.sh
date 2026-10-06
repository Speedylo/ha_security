#!/bin/bash
# The regression for F45 (notes/f45_prediction.md), on a fresh clone of verify-2026-10-f45 at
# ~/r2exp/verify-f45: (A) brought up from the clone (new bridge, the mediator's own user), every suite
# twice, (A)'s restart suite, the supervisor's path (drive_demo), the fault and review cases, nordpool
# end to end, arm P (f45_policy.py), and the timing steps as the pass `final_f45`. Needs (A) up.
T=~/r2exp/verify-f45/v2; OUT=~/r2exp/verify/regress_f45; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; run="systemd-run --user --scope -q python3 -u -m"
step() { local name=$1; shift; local t=$(date +%s); timeout 2400 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd "$T/framework" || exit 2
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up
cd "$T"
step suites_1 bash experiments/selftests/suites_all.sh "$OUT/suites_1"
step suites_2 bash experiments/selftests/suites_all.sh "$OUT/suites_2"
cd framework
step real_platform_restart $run confine.selftest_real_platform --restart
step egress_nordpool $run confine.endtoend_egress --subject nordpool --corpus $C --python $P --json "$OUT/egress_nordpool.json"
A="$OUT/drive_audit"
systemd-run --user --scope -q python3 -u -m confine.supervise --component ../experiments/flood/demo_flood --python $P --audit-dir "$A" > "$OUT/supervise.log" 2>&1 &
for _ in $(seq 120); do grep -q "started (run 1" "$OUT/supervise.log" && break; sleep 1; done; sleep 10
step drive_demo env PYTHONPATH=. python3 ../experiments/flood/drive_demo.py "$OUT/supervise.log" "$A"
sup=$(grep -o "durable log [^;]*" "$OUT/supervise.log" | head -1 | sed 's/.*decisions-[0-9T]*-\([0-9]*\)\.jsonl/\1/')
[ -n "$sup" ] && kill -TERM "$sup"; sleep 5
step faults_pi_fixed bash ../verify/faults_pi_fixed.sh "$T/framework" "$OUT/faults_pi_fixed"
step review_pi bash ../verify/review_pi.sh "$T/framework" "$OUT/review_pi"
step f45_policy python3 ../verify/f45_policy.py --json "$OUT/f45_policy.json"
cd "$T"
step timing env ROOT="$T" PASS_DIR=final_f45 bash verify/phase3_timing.sh final_f45
echo ALLDONE >> "$S"
