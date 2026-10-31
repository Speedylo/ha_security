#!/bin/bash
# Mutants M51–M79 of the bridge's new kinds (notes/kinds_tests_bite_prediction_20261031.md), on the Pi.
# Usage: bash run_kind_mutants.sh PRISTINE_V2 OUTDIR
# The two suites that test the new kinds run against each mutant: selftest_commands (offline) and
# selftest_bridge_types against an (A) brought up fresh from the mutated tree, so (A) runs the
# mutated bridge. The pristine tree runs first, as the control. A mutant is killed when either suite
# exits non-zero; its FAIL lines are kept, or, if a suite crashed, its error line.
# MUT_ONLY="M51b M64 ..." runs only those (MUT_WORK then names a fresh work directory).
SRC=${1:?pristine v2}; OUT=${2:?outdir}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
WORK=${MUT_WORK:-~/r2exp/km/work}
mkdir -p "$OUT" "$WORK"; OUT=$(cd "$OUT" && pwd)

two_suites() {  # $1 framework dir, $2 log dir
  mkdir -p "$2"
  ( cd "$1" && timeout 600 python3 -m confine.selftest_commands > "$2/commands.log" 2>&1
    echo "commands exit=$?" > "$2/summary.txt"
    python3 -m confine.house_a down > "$2/house_a_down.log" 2>&1
    python3 -m confine.house_a up --fresh > "$2/house_a_up.log" 2>&1
    echo "house_a_up exit=$?" >> "$2/summary.txt"
    timeout 600 python3 -m confine.selftest_bridge_types > "$2/bridge_types.log" 2>&1
    echo "bridge_types exit=$?" >> "$2/summary.txt" )
}

echo "start $(date -Is) pristine $(git -C "$SRC" rev-parse HEAD) $(git -C "$SRC" describe --tags)" > "$OUT/run.txt"
two_suites "$SRC/framework" "$OUT/control"
echo "control $(tr '\n' ' ' < "$OUT/control/summary.txt")" >> "$OUT/run.txt"
if [ -n "$MUT_ONLY" ]; then patches=$(for m in $MUT_ONLY; do echo "$HERE/$m.patch"; done)
else patches=$(ls "$HERE"/M[5-7][0-9]*.patch); fi
for patch in $patches; do
  m=$(basename "$patch" .patch); case $m in M5[0]) continue ;; esac; dest="$WORK/$m"
  [ -e "$dest" ] && { echo "$m: $dest exists, skipped" >> "$OUT/run.txt"; continue; }
  mkdir -p "$dest" && cp -r "$SRC/framework" "$SRC/experiments" "$dest/"
  ( cd "$dest" && patch -s -p1 < "$patch" ) || { echo "$m: patch failed" >> "$OUT/run.txt"; continue; }
  o="$OUT/$m"; two_suites "$dest/framework" "$o"
  target=$(sed -n 's#^+++ b/framework/ha_bridge/confine_bridge/\([a-z_]*\.py\).*#\1#p' "$patch")
  if [ -n "$target" ]; then
    cmp -s "$dest/framework/ha_bridge/confine_bridge/$target" ~/r2exp/houseA/custom_components/confine_bridge/$target \
      && echo "bridge_in_A=mutated" >> "$o/summary.txt" || echo "bridge_in_A=NOT_MUTATED" >> "$o/summary.txt"
  fi
  failed=$(grep -c 'exit=[1-9]' "$o/summary.txt")
  echo "$m failed=$failed $(tr '\n' ' ' < "$o/summary.txt") fails: $(grep -h FAIL "$o/commands.log" "$o/bridge_types.log" | sed 's/^ *FAIL *//' | cut -c1-70 | head -3 | tr '\n' '|')$(grep -h -m1 -E '^[A-Za-z]+(Error|Exception):' "$o/commands.log" "$o/bridge_types.log" | sed 's/^/crash: /' | tr '\n' '|')" >> "$OUT/run.txt"
done
( cd "$SRC/framework" && python3 -m confine.house_a down && python3 -m confine.house_a up --fresh ) > "$OUT/restore.log" 2>&1
echo "end $(date -Is)" >> "$OUT/run.txt"; echo ALLDONE >> "$OUT/run.txt"
