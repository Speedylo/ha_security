#!/bin/bash
# Final rerun, steps 3 (Pi half) and 4, started once step 2 has finished.
# Step 3 runs from the clone of fix-2026-10-f61 (F61: the fault harnesses lacked F57's approval step);
# step 4 from the clone of final-2026-10. Driver kept outside both clones.
until grep -q ALLDONE ~/r2exp/final-run/out/step02_mutants/summary.txt 2>/dev/null; do sleep 30; done
P=~/r2exp/ha314/bin/python
step() { local S=$1 name=$2; shift 2; local t=$(date +%s); timeout 2400 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
# -- step 3, Pi half
T=~/r2exp/final-f61/v2; OUT=~/r2exp/final-run/out/step03_faults_pi; mkdir -p "$OUT"; S3="$OUT/summary.txt"; : > "$S3"
echo "start $(date -Is) commit $(git -C "$T" rev-parse HEAD) tag $(git -C "$T" describe --tags) dirty=$(git -C "$T" status --porcelain | wc -l)" >> "$S3"
cd "$T/framework" || exit 2
step "$S3" house_a_down python3 -m confine.house_a down
step "$S3" house_a_up python3 -m confine.house_a up
step "$S3" faults_py python3 ../verify/faults.py --json "$OUT/faults_pi.json"
step "$S3" faults_pi_fixed bash ../verify/faults_pi_fixed.sh "$T/framework" "$OUT/fixed"
python3 -m confine.house_a status | grep -qx up || { echo "(A) not up after faults_pi_fixed; brought up again" >> "$S3"; step "$S3" house_a_up_after python3 -m confine.house_a up; }
echo "dirty after=$(git -C "$T" status --porcelain | wc -l)" >> "$S3"
echo "end $(date -Is)" >> "$S3"; echo ALLDONE >> "$S3"
# -- step 4
T=~/r2exp/final/v2; OUT=~/r2exp/final-run/out/step04_fuzz; mkdir -p "$OUT"; S4="$OUT/summary.txt"; : > "$S4"
echo "start $(date -Is) commit $(git -C "$T" rev-parse HEAD) tag $(git -C "$T" describe --tags) dirty=$(git -C "$T" status --porcelain | wc -l)" >> "$S4"
cd "$T/framework" || exit 2
step "$S4" fuzz python3 ../verify/fuzz_mediator.py --json "$OUT/fuzz.json"
echo "end $(date -Is)" >> "$S4"; echo ALLDONE >> "$S4"
