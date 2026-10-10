#!/bin/bash
# F58's regression (notes/f58_shared_space_prediction.md R2–R5), on a fresh clone of fix-2026-10-f58 at
# ~/r2exp/f58/tag. R2, the egress suite; R3, the predicate on the suites' Python and on ha314's;
# R4, the egress mutants (M04's text moved, M38 new); R5, nordpool end to end. R6 (all suites) runs
# with F57's regression, at a tag that contains this one.
T=~/r2exp/f58/tag/v2; OUT=~/r2exp/f58/out/regress; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; run="systemd-run --user --scope -q python3 -u -m"
step() { local name=$1; shift; local t=$(date +%s); timeout 2400 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd "$T/framework" || exit 2
step r2_selftest_egress $run confine.selftest_egress
R3='import sys; sys.path.insert(0, "."); from confine.egress import is_public
for a in ["93.184.216.34","1.1.1.1","2606:4700:4700::1111","100.64.0.1","100.86.243.57","100.127.255.254","::ffff:100.64.0.1","192.168.1.50","224.0.0.251","ff02::fb","240.0.0.5","100.63.255.255","100.128.0.0"]: print(a, is_public(a))
print(sys.version.split()[0])'
step r3_python3 python3 -c "$R3"
step r3_ha314 $P -c "$R3"
step r5_egress_nordpool $run confine.endtoend_egress --subject nordpool --corpus $C --python $P --json "$OUT/egress_nordpool.json"
cd "$T"
MUT_ONLY="M0[456]" MUT_WORK=~/r2exp/f58/mut bash verify/mutants/run_mutants.sh "$T" "$OUT/mutants" > /dev/null 2>&1
MUT_ONLY="M25" MUT_WORK=~/r2exp/f58/mut bash verify/mutants/run_mutants.sh "$T" "$OUT/mutants" > /dev/null 2>&1
MUT_ONLY="M38" MUT_WORK=~/r2exp/f58/mut bash verify/mutants/run_mutants.sh "$T" "$OUT/mutants" > /dev/null 2>&1
echo "mutants: $(grep -v ALLDONE "$OUT/mutants/run.txt" | tr '\n' ' ')" >> "$S"
echo ALLDONE >> "$S"
