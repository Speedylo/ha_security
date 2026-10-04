#!/bin/bash
# Every selftest suite against the current framework, with the interpreter the four sandbox-spawning
# suites need. One log per suite and one summary line per suite.
cd ~/r2exp/v2/framework; out=~/r2exp/t2/suites_followup_20261004; mkdir -p "$out"; P=~/r2exp/ha314/bin/python
: > "$out/summary.txt"
for f in confine/selftest.py confine/selftest_*.py; do m=$(basename $f .py)
  case $m in selftest_bridge|selftest_egress_sandboxed|selftest_gc|selftest_reads) extra="--python $P" ;; *) extra="" ;; esac
  timeout 1500 systemd-run --user --scope -q python3 -m confine.$m $extra > "$out/$m.log" 2>&1
  echo "$m exit=$?" >> "$out/summary.txt"
done; echo ALLDONE >> "$out/summary.txt"
