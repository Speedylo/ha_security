#!/bin/bash
# Final rerun, steps 5, 7, 8 and 9 (step 6 is read from step 1's logs), from the clone of final-2026-10.
# Starts only when steps 2–4 have finished AND their gates hold; otherwise it writes why and stops.
# (A) is restarted from the clone before the steps that use it, and is DOWN for every run with an
# unconfined arm (rule 3, F56): compat's baseline arms, every egress/local/oauth subject, step 8.
# Step 7 re-issues verify/phase2_l23.sh's commands against this clone because that script `cd`s into
# the frozen tree ~/r2exp/verify/v2; and its supervisor gets F57's approval, as F61's fix does.
R=~/r2exp/final-run/out; G=$R/gates.txt
until grep -q ALLDONE $R/step04_fuzz/summary.txt 2>/dev/null; do sleep 30; done
: > "$G"; ok=1
surv=$(grep 'failed_suites=0$' $R/step02_mutants/framework_results.txt | cut -d' ' -f1 | tr '\n' ' ')
[ "$surv" = "M25 " ] || { echo "gate: framework survivors [$surv], expected [M25 ]" >> "$G"; ok=0; }
[ "$(grep -c 'patch failed' $R/step02_mutants/framework_results.txt)" = 0 ] || { echo "gate: a patch failed" >> "$G"; ok=0; }
[ "$(grep -c failed_suites= $R/step02_mutants/framework_results.txt)" = 50 ] || { echo "gate: not 50 framework mutants" >> "$G"; ok=0; }
for m in M18a M18b M18c; do grep -q "^$m failed_suites=[1-9]" $R/step02_mutants/bridge/run.txt || { echo "gate: $m not killed" >> "$G"; ok=0; }
  grep -q "^$m bridge_in_A=mutated" $R/step02_mutants/bridge/run.txt || { echo "gate: $m not loaded in (A)" >> "$G"; ok=0; }; done
grep -q "^control failed_suites=0" $R/step02_mutants/bridge/run.txt || { echo "gate: bridge control failed" >> "$G"; ok=0; }
grep -q "^faults_py exit=0" $R/step03_faults_pi/summary.txt || { echo "gate: faults.py on the Pi" >> "$G"; ok=0; }
grep -q FAIL $R/step03_faults_pi/fixed/results.txt && { echo "gate: faults_pi_fixed has FAIL" >> "$G"; ok=0; }
grep -q "^fuzz exit=0" $R/step04_fuzz/summary.txt || { echo "gate: fuzz" >> "$G"; ok=0; }
[ $ok = 1 ] || { echo "STOPPED $(date -Is)" >> "$G"; exit 1; }
echo "gates held $(date -Is)" >> "$G"

T=~/r2exp/final/v2; P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; U=~/r2exp/corpus_uniform; PD=~/r2exp/platform-deps
run="systemd-run --user --scope -q python3 -u -m"
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-2400} "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
begin() { OUT=$R/$1; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"; echo "start $(date -Is) commit $(git -C "$T" rev-parse HEAD) tag $(git -C "$T" describe --tags) dirty=$(git -C "$T" status --porcelain | wc -l)" >> "$S"; }
end() { echo "dirty after=$(git -C "$T" status --porcelain | wc -l)" >> "$S"; echo "end $(date -Is)" >> "$S"; echo ALLDONE >> "$S"; }
cd "$T/framework" || exit 2

# -- step 5: compatibility, both corpora, both arms, (A) down
begin step05_compat
step house_a_down python3 -m confine.house_a down
TO=14400 step c1_baseline $run confine.compat --corpus $C --python $P --profile baseline --platform-deps $PD --json "$OUT/c1_baseline.json"
TO=14400 step c1_declared_core $run confine.compat --corpus $C --python $P --profile declared --platform-deps $PD --json "$OUT/c1_declared_core.json"
TO=14400 step uniform_baseline $run confine.compat --corpus $U --python $P --profile baseline --platform-deps $PD --json "$OUT/uniform_baseline.json"
TO=14400 step uniform_confined $run confine.compat --corpus $U --python $P --profile declared --platform-deps $PD --json "$OUT/uniform_confined.json"
end

# -- step 7: the end-to-end subjects
begin step07_e2e
step house_a_up python3 -m confine.house_a up
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
for s in nordpool dwd_weather pirateweather; do step egress_$s $run confine.endtoend_egress --subject $s --corpus $C --python $P --json "$OUT/egress_$s.json"; done
for s in smhi_brandrisk regensburg_transport; do step egress_$s $run confine.endtoend_egress --subject $s --corpus $U --python $P --json "$OUT/egress_$s.json"; done
step local_midea_ac_lan $run confine.endtoend_local --corpus $C --python $P --subject midea_ac_lan --json "$OUT/local_midea_ac_lan.json"
step local_localtuya $run confine.endtoend_local --corpus $C --python $P --subject localtuya --json "$OUT/local_localtuya.json"
step oauth_trakt $run confine.endtoend_oauth --corpus $U --python $P --json "$OUT/oauth_trakt.json"
end

# -- step 8: the functional retest, (A) still down
begin step08_retest
python3 -m confine.house_a status >> "$OUT/house_a_status.log" 2>&1
step endtoend_function $run confine.endtoend_function --corpus $C --python $P --json "$OUT/retest.json"
(cd .. && python3 verify/retest_e2e_verdicts.py "$OUT/retest.json") > "$OUT/verdicts.txt" 2>&1; echo "verdicts exit=$?" >> "$S"
end

# -- step 9: T06's pair (its script takes (A) down, then up --fresh)
begin step09_t06
step pair bash ../experiments/pair_subscriptions/run.sh "$OUT/pair"
python3 -m confine.house_a status >> "$OUT/house_a_status.log" 2>&1
end
