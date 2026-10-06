#!/bin/bash
# F03's regression, on a fresh clone of verify-2026-10-f03 (~/r2exp/verify-f03): every suite, then
# nordpool end to end (the rule after any mediator change), judged against the frozen tag's logs.
T=~/r2exp/verify-f03/v2; OUT=~/r2exp/verify/regress_f03; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus
cd "$T/framework"
for f in confine/selftest.py confine/selftest_*.py; do m=$(basename $f .py)
  case $m in selftest_bridge|selftest_egress_sandboxed|selftest_gc|selftest_reads) extra="--python $P" ;; *) extra="" ;; esac
  t=$(date +%s); timeout 1500 systemd-run --user --scope -q python3 -m confine.$m $extra > "$OUT/$m.log" 2>&1
  echo "$m exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"
done
t=$(date +%s); timeout 2400 systemd-run --user --scope -q python3 -u -m confine.endtoend_egress --subject nordpool --corpus $C --python $P --json "$OUT/egress_nordpool.json" > "$OUT/egress_nordpool.log" 2>&1
echo "egress_nordpool exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"
echo ALLDONE >> "$S"
