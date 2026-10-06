#!/bin/bash
# The regression for F28–F31, on a fresh clone of verify-2026-10-faults (~/r2exp/verify-faults):
# every suite twice, nordpool end to end, (A)'s restart suite, the supervisor's own path under a user
# (drive_demo), then the fault cases with their fixes' criteria. Needs (A) up.
T=~/r2exp/verify-faults/v2; OUT=~/r2exp/verify/regress_faults; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; run="systemd-run --user --scope -q python3 -u -m"
step() { local name=$1; shift; local t=$(date +%s); timeout 2400 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd "$T" || exit 2
step suites_1 bash experiments/selftests/suites_all.sh "$OUT/suites_1"
step suites_2 bash experiments/selftests/suites_all.sh "$OUT/suites_2"
cd framework
step egress_nordpool $run confine.endtoend_egress --subject nordpool --corpus $C --python $P --json "$OUT/egress_nordpool.json"
step real_platform_restart $run confine.selftest_real_platform --restart
A="$OUT/drive_audit"
systemd-run --user --scope -q python3 -u -m confine.supervise --component ../experiments/flood/demo_flood --python $P --audit-dir "$A" > "$OUT/supervise.log" 2>&1 &
for _ in $(seq 120); do grep -q "started (run 1" "$OUT/supervise.log" && break; sleep 1; done; sleep 10
step drive_demo env PYTHONPATH=. python3 ../experiments/flood/drive_demo.py "$OUT/supervise.log" "$A"
for pid in $(pgrep -f 'confine[.]supervise'); do kill -TERM "$pid"; done; sleep 5
step faults python3 ../verify/faults.py --json "$OUT/faults.json"
step faults_pi_fixed bash ../verify/faults_pi_fixed.sh "$T/framework" "$OUT/faults_pi_fixed"
echo ALLDONE >> "$S"
