#!/bin/bash
# Every selftest suite against the framework in the checkout this script belongs to, with the
# interpreter the four sandbox-spawning suites need. One log per suite and one summary line per suite.
#
# Usage: bash suites_all.sh OUTDIR [HA_PYTHON]
#   HA_PYTHON defaults to ~/r2exp/ha314/bin/python (REPRODUCE.md step 4).
#
# Until 2026-10-06 this script began `cd ~/r2exp/v2/framework`, so run from any other checkout it
# tested that working tree instead, and still reported success (finding F19).
out=${1:?usage: suites_all.sh OUTDIR [HA_PYTHON]}; P=${2:-~/r2exp/ha314/bin/python}
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$out"; out=$(cd "$out" && pwd)
cd "$here/../../framework" || exit 2
: > "$out/summary.txt"
echo "framework: $(pwd)" >> "$out/summary.txt"
for f in confine/selftest.py confine/selftest_*.py; do m=$(basename $f .py)
  case $m in selftest_bridge|selftest_egress_sandboxed|selftest_gc|selftest_reads|selftest_supervise) extra="--python $P" ;; *) extra="" ;; esac
  timeout 1500 systemd-run --user --scope -q python3 -m confine.$m $extra > "$out/$m.log" 2>&1
  echo "$m exit=$?" >> "$out/summary.txt"
done; echo ALLDONE >> "$out/summary.txt"
