#!/bin/bash
# The regression for F48, F49 and F52 (notes/f48_f49_prediction_20261007.md), on a clone of
# verify-2026-10-tests at ~/r2exp/verify-tests. Then every mutant: the new M19–M37 first, the
# original 18 (their files are unchanged; re-run because the suites changed), and M18a–c last
# (run_bridge_mutants.sh, which ends with (A) up from the pristine tree and an unmutated control).
#
# Not re-run: the timing steps. The only framework change is F52, a message on a refusal path
# (`channel.py`), which no timed path takes. `nordpool` is, by the standing rule after any change
# on the channel or mediator path.
T=~/r2exp/verify-tests/v2; OUT=~/r2exp/verify/regress_tests; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; run="systemd-run --user --scope -q python3 -u -m"
step() { local name=$1; shift; local t=$(date +%s); timeout 2400 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd "$T/framework" || exit 2
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up
cd "$T"
step suites_1 bash experiments/selftests/suites_all.sh "$OUT/suites_1"
step suites_2 bash experiments/selftests/suites_all.sh "$OUT/suites_2"
for n in 1 2; do echo "suites_$n failed=$(grep -c 'exit=[^0]' "$OUT/suites_$n/summary.txt") of $(grep -c 'exit=' "$OUT/suites_$n/summary.txt")" >> "$S"; done
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
echo REGRESSION_DONE >> "$S"

cd "$T"
M="$OUT/mutants"; mkdir -p "$M"
for m in M19 M20 M21 M22 M23 M24 M25 M26 M27 M28 M29 M30 M31 M32 M33 M34 M35 M36 M37 \
         M01 M02 M03 M04 M05 M06 M07 M08a M08b M09 M10 M11 M12 M13 M14 M15 M16 M17; do
  MUT_ONLY=$m MUT_WORK=~/r2exp/tb/work_tests bash verify/mutants/run_mutants.sh "$T" "$M" > /dev/null 2>&1
  # A mutant of the supervisor suite can leave (A) stopped mid-restart; the next mutant needs it up.
  (cd framework && python3 -m confine.house_a status) | grep -qx up || \
    (cd framework && python3 -m confine.house_a up >> "$OUT/house_a_reup.log" 2>&1; echo "$m: (A) brought up again" >> "$S")
done
MUT_WORK=~/r2exp/tb/work_tests_bridge bash verify/mutants/run_bridge_mutants.sh "$T" "$OUT/bridge_mutants" > /dev/null 2>&1
echo ALLDONE >> "$S"
