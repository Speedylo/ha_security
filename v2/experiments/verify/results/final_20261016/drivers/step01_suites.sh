#!/bin/bash
# Final rerun, step 1 (notes/final_rerun_prediction.md): (A) restarted from the clone of final-2026-10,
# the preflight, then every suite twice. Driver kept outside the clone so the tagged tree stays clean.
T=~/r2exp/final/v2; OUT=~/r2exp/final-run/out/step01_suites; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
step() { local name=$1; shift; local t=$(date +%s); timeout 2400 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
echo "start $(date -Is) commit $(git -C "$T" rev-parse HEAD) tag $(git -C "$T" describe --tags) dirty=$(git -C "$T" status --porcelain | wc -l) host $(hostname) kernel $(uname -r)" >> "$S"
cd "$T/framework" || exit 2
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up
step preflight systemd-run --user --scope -q python3 -m confine.preflight
cd "$T"
step suites_1 bash experiments/selftests/suites_all.sh "$OUT/suites_1"
step suites_2 bash experiments/selftests/suites_all.sh "$OUT/suites_2"
for n in 1 2; do echo "suites_$n failed=$(grep -c 'exit=[^0]' "$OUT/suites_$n/summary.txt") of $(grep -c 'exit=' "$OUT/suites_$n/summary.txt")" >> "$S"; done
(cd framework && python3 -m confine.house_a status) | grep -qx up || echo "(A) not up at the end" >> "$S"
echo "end $(date -Is)" >> "$S"; echo ALLDONE >> "$S"
