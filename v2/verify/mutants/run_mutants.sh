#!/bin/bash
# Phase 4.3: every mutant against every suite, on the Pi. Usage: bash run_mutants.sh PRISTINE_V2 OUTDIR
#   PRISTINE_V2  a clean checkout's v2/ (its framework passes 26/26 unmutated)
#   OUTDIR       one directory per mutant, each with every suite's log and a summary
# Each mutant runs in a fresh copy of framework/ and experiments/, so no mutant sees another's change.
# A suite gets 300 s here rather than suites_all.sh's 1500: unmutated, the longest takes about 20 s,
# and a mutant that removes a stopping condition (M11's cut-off) can make a suite run until killed.
SRC=${1:?pristine v2}; OUT=${2:?outdir}; P=~/r2exp/ha314/bin/python
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
WORK=${MUT_WORK:-~/r2exp/mutants/work}   # MUT_WORK and MUT_ONLY re-run a subset in a fresh place
mkdir -p "$OUT" "$WORK"
for patch in "$HERE"/${MUT_ONLY:-M*}.patch; do
  m=$(basename "$patch" .patch); dest="$WORK/$m"
  [ -e "$dest" ] && { echo "$m: $dest exists, skipped" >> "$OUT/run.txt"; continue; }
  mkdir -p "$dest" && cp -r "$SRC/framework" "$SRC/experiments" "$dest/"
  ( cd "$dest" && patch -s -p1 < "$patch" ) || { echo "$m: patch failed" >> "$OUT/run.txt"; continue; }
  o="$OUT/$m"; mkdir -p "$o" "$dest/tmp"; : > "$o/summary.txt"; export TMPDIR="$dest/tmp"  # each mutant its own (4.3's note)
  cd "$dest/framework"
  for f in confine/selftest.py confine/selftest_*.py; do s=$(basename $f .py)
    case $s in selftest_bridge|selftest_egress_sandboxed|selftest_gc|selftest_reads|selftest_supervise) extra="--python $P" ;; *) extra="" ;; esac
    timeout 300 systemd-run --user --scope -q python3 -m confine.$s $extra > "$o/$s.log" 2>&1
    echo "$s exit=$?" >> "$o/summary.txt"
  done
  failed=$(grep -cv 'exit=0' "$o/summary.txt")
  echo "$m failed_suites=$failed" >> "$OUT/run.txt"
done
echo ALLDONE >> "$OUT/run.txt"
