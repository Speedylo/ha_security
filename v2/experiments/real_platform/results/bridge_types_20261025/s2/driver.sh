#!/bin/bash
# Bridge step 2 (notes/bridge_types_step2_prediction_20261025.md): K5 from the clone of bridge-s2-pre; the rest from bridge-s2.
O=~/r2exp/bridge-run/s2; S=$O/summary.txt
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-600} "$@" > "$O/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd ~/r2exp/bridge-s2-pre/v2/framework || exit 1
echo "start $(date -Is) pre commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" > $S
step commands_pre python3 -m confine.selftest_commands
cd ~/r2exp/bridge-s2/v2/framework || exit 1
echo "post commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" >> $S
step commands python3 -m confine.selftest_commands
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up --fresh
step bridge_types python3 -m confine.selftest_bridge_types
TO=5400 step suites bash ~/r2exp/bridge-s2/v2/experiments/selftests/suites_all.sh $O/suites
echo "suites failed=$(grep -vc "exit=0\|ALLDONE\|framework:" $O/suites/summary.txt) of $(grep -c exit= $O/suites/summary.txt)" >> $S
echo "bridge errors in (A) log: $(grep ERROR ~/r2exp/houseA/home-assistant.log | grep -c confine_bridge)" >> $S
for d in bridge-s2-pre bridge-s2; do echo "$d dirty after=$(git -C ~/r2exp/$d status --porcelain | wc -l)" >> $S; done
echo "end $(date -Is)" >> $S; echo ALLDONE >> $S
