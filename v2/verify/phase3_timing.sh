#!/bin/bash
# Phase 3, one timing pass (3b = pass 1, 3c = pass 2, 3d = pass 3), on the frozen tree.
# Usage: bash phase3_timing.sh <pass>. Every disk-backed figure uses ~/r2exp/disktmp (ext4), never /tmp (tmpfs).
PASS=${1:?pass number}
# ROOT and PASS_DIR let the final pass run the same steps on another tag's clone (verify/final_timing.sh).
ROOT=${ROOT:-~/r2exp/verify/v2}; E=$ROOT/experiments; F=$ROOT/framework
OUT=$E/verify/results/phase3_timing/${PASS_DIR:-pass$PASS}; mkdir -p "$OUT"; S="$OUT/summary.txt"
[ -s "$S" ] && mv "$S" "$OUT/summary_attempt$(date +%s).txt"; : > "$S"
P=~/r2exp/ha314/bin/python; DISK=~/r2exp/disktmp; AUG=~/r2exp/t2/platform-deps-aug
scope="systemd-run --user --scope -q"
step() { local name=$1 dir=$2; shift 2; local t=$(date +%s); ( cd "$dir" && timeout 3600 "$@" ) > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
{ echo "pass $PASS"; date -Iseconds; uptime -p; findmnt -n -o FSTYPE -T $DISK; free -m | sed -n 2p; } > "$OUT/conditions.txt"

step latency_scale     $E/mediation_latency $scope python3 scale.py --json "$OUT/latency_scale.json"
step durability        $E/durability        $scope python3 measure.py --scratch $DISK --json "$OUT/durability.json"
step footprint_single  $E/r2_footprint      $P measure.py --builder corrected --json "$OUT/footprint_single.json"
step footprint_scale   $E/r2_footprint      $P measure_scale.py --builder corrected --count 6 --json "$OUT/footprint_scale.json"
for point in none two four ten; do
  case $point in
    none) a="--profile minimal" ;; two) a="--components http,websocket_api" ;;
    four) a="--components frontend,http,websocket_api,lovelace" ;; ten) a="--profile unstripped" ;;
  esac
  step depth_$point $E/unstrip $scope python3 scale.py --count 3 --python $P $a --platform-deps $AUG --json "$OUT/depth_$point.json"
  sleep 20
done
step push_suite        $F $scope python3 -m confine.selftest_push
step real_platform     $F $scope python3 -m confine.selftest_real_platform
step flood_disk        $F env TMPDIR=$DISK $scope python3 -m confine.selftest_flood
for mode in default compile cold; do
  case $mode in default) a="" ;; compile) a="--compile-bytecode" ;; cold) a="--cold" ;; esac
  step bytecode_$mode  $F $scope python3 -u -m confine.endtoend --corpus ~/r2exp/corpus --python $P --only powercalc --bytecode $a --json "$OUT/bytecode_$mode.json"
done
# A user's command into a confined integration (§7.38). Added before pass 2; pass 1's sample is
# phase 2's L3 run of the same command on the same tag (verify/timing_stats.py says so).
step e2e_real_adaptive $F $scope python3 -u -m confine.endtoend --corpus ~/r2exp/corpus --python $P --only adaptive_lighting --push --platform real --command --json "$OUT/e2e_real_adaptive.json"
echo ALLDONE >> "$S"
