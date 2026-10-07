#!/bin/bash
# Mutants of the bridge (M18a–c, notes/tests_bite_prediction_20261007.md), on the Pi.
# Usage: bash run_bridge_mutants.sh PRISTINE_V2 OUTDIR
#   PRISTINE_V2  a clean checkout's v2/ at the tag under test
#   OUTDIR       one directory per mutant with every suite's log and a summary, then `control/`
# Unlike run_mutants.sh, the code under test runs inside (A): `house_a up` copies the bridge from the
# tree it is run from, so (A) is brought up from each mutated copy, and from the pristine tree last
# for the control run. Settings as in 4.3: 300 s per suite; each run has its own TMPDIR on disk.
SRC=${1:?pristine v2}; OUT=${2:?outdir}; P=~/r2exp/ha314/bin/python
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
WORK=${MUT_WORK:-~/r2exp/tb/work}
mkdir -p "$OUT" "$WORK"; OUT=$(cd "$OUT" && pwd)

suites() {  # $1 framework dir, $2 log dir
  mkdir -p "$2"; : > "$2/summary.txt"
  ( cd "$1" && for f in confine/selftest.py confine/selftest_*.py; do s=$(basename $f .py)
      case $s in selftest_bridge|selftest_egress_sandboxed|selftest_gc|selftest_reads|selftest_supervise) extra="--python $P" ;; *) extra="" ;; esac
      timeout 300 systemd-run --user --scope -q python3 -m confine.$s $extra > "$2/$s.log" 2>&1
      echo "$s exit=$?" >> "$2/summary.txt"
    done )
}

( cd "$SRC/framework" && python3 -m confine.house_a down ) > "$OUT/down_first.log" 2>&1
for patch in "$HERE"/${MUT_ONLY:-M18*}.patch; do
  m=$(basename "$patch" .patch); dest="$WORK/$m"
  [ -e "$dest" ] && { echo "$m: $dest exists, skipped" >> "$OUT/run.txt"; continue; }
  mkdir -p "$dest/tmp" && cp -r "$SRC/framework" "$SRC/experiments" "$dest/"
  ( cd "$dest" && patch -s -p1 < "$patch" ) || { echo "$m: patch failed" >> "$OUT/run.txt"; continue; }
  o="$OUT/$m"; mkdir -p "$o"
  ( cd "$dest/framework" && python3 -m confine.house_a up ) > "$o/house_a_up.log" 2>&1
  echo "$m house_a_up exit=$?" >> "$OUT/run.txt"
  # The bridge (A) loaded must be the mutated one: compare (A)'s copy with the mutated source.
  if cmp -s "$dest/framework/ha_bridge/confine_bridge/__init__.py" ~/r2exp/houseA/custom_components/confine_bridge/__init__.py; then
    echo "$m bridge_in_A=mutated" >> "$OUT/run.txt"
  else
    echo "$m bridge_in_A=NOT_MUTATED" >> "$OUT/run.txt"
  fi
  TMPDIR="$dest/tmp" suites "$dest/framework" "$o"
  failed=$(grep -cv 'exit=0' "$o/summary.txt")
  echo "$m failed_suites=$failed" >> "$OUT/run.txt"
  ( cd "$dest/framework" && python3 -m confine.house_a down ) >> "$o/house_a_up.log" 2>&1
done

# Control: (A) from the pristine tree, all suites unmutated.
mkdir -p "$WORK/control/tmp"
( cd "$SRC/framework" && python3 -m confine.house_a up ) > "$OUT/control_up.log" 2>&1
echo "control house_a_up exit=$?" >> "$OUT/run.txt"
TMPDIR="$WORK/control/tmp" suites "$SRC/framework" "$OUT/control"
echo "control failed_suites=$(grep -cv 'exit=0' "$OUT/control/summary.txt")" >> "$OUT/run.txt"
echo ALLDONE >> "$OUT/run.txt"
