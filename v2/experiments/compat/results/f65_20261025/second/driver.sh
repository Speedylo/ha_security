#!/bin/bash
# F65 R2, R3, R4 (second route) (notes/f65_source_ip_prediction_20261025.md), from the clone of f65b-fix.
# (A) up for the suites, as in the final rerun's step 1; down for compat and for the waste run, which has an unconfined arm (F56).
OUT=~/r2exp/f65-run/second; T=~/r2exp/f65b-fix/v2; S=$OUT/summary.txt
cd $T/framework || exit 1
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-2400} "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
echo "start $(date -Is) commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" > $S
step house_a_up python3 -m confine.house_a up
TO=5400 step suites bash $T/experiments/selftests/suites_all.sh $OUT/suites
echo "suites failed=$(grep -vc "exit=0\|ALLDONE\|framework:" $OUT/suites/summary.txt) of $(grep -c exit= $OUT/suites/summary.txt)" >> $S
step house_a_down python3 -m confine.house_a down
TO=14400 step compat_egress systemd-run --user --scope -q python3 -u -m confine.compat --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python --profile declared --platform-deps ~/r2exp/platform-deps --egress --json $OUT/compat_egress.json
step waste systemd-run --user --scope -q python3 -m confine.endtoend_egress --subject waste_collection_schedule --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python --json $OUT/waste.json
echo "dirty after=$(git status --porcelain | wc -l)" >> $S; echo "end $(date -Is)" >> $S; echo ALLDONE >> $S
