#!/bin/bash
# The final pass before the cut-off (notes/final_pass_prediction.md), on a fresh clone of
# verify-2026-10-final at ~/r2exp/verify-final: (A) restarted from that clone, every suite twice
# (exit criterion 3), then Phase 3's timing steps as the pass `final` (exit criterion 4).
T=~/r2exp/verify-final/v2; OUT=~/r2exp/verify/final; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
step() { local name=$1; shift; local t=$(date +%s); timeout 3600 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd "$T/framework" || exit 2
step house_a_restart python3 -m confine.house_a restart
cd "$T" || exit 2
step suites_1 bash experiments/selftests/suites_all.sh "$OUT/suites_1"
step suites_2 bash experiments/selftests/suites_all.sh "$OUT/suites_2"
step timing env ROOT="$T" PASS_DIR=final bash verify/phase3_timing.sh final
echo ALLDONE >> "$S"
