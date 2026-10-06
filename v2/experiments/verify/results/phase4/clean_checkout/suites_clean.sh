#!/bin/bash
# Phase 4.2: suites_all.sh at verify-2026-10, changed only in where it runs and writes:
# from the clean clone ~/r2exp/clean, logs outside it.
cd ~/r2exp/clean/v2/framework; out=~/r2exp/verify/phase4_clean/suites; mkdir -p "$out"; P=~/r2exp/ha314/bin/python
: > "$out/summary.txt"
for f in confine/selftest.py confine/selftest_*.py; do m=$(basename $f .py)
  case $m in selftest_bridge|selftest_egress_sandboxed|selftest_gc|selftest_reads) extra="--python $P" ;; *) extra="" ;; esac
  t=$(date +%s); timeout 1500 systemd-run --user --scope -q python3 -m confine.$m $extra > "$out/$m.log" 2>&1
  echo "$m exit=$? seconds=$(( $(date +%s) - t ))" >> "$out/summary.txt"
done; echo ALLDONE >> "$out/summary.txt"
