#!/bin/bash
# Bridge batch B4b (notes/bridge_kinds_b4b_prediction_20261031.md). Pre: offline suites and the bridge-types suite from bridge-b4b-pre, (A) fresh with that bridge.
# Post: from bridge-b4b, (A) fresh with the new bridge; offline suites, the bridge-types suite, then every suite.
O=~/r2exp/bridge-run/b4b; S=$O/summary.txt; mkdir -p $O
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-600} "$@" > "$O/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd ~/r2exp/bridge-b4b-pre/v2/framework || exit 1
echo "start $(date -Is) pre commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" > $S
step commands_pre python3 -m confine.selftest_commands
step queries_pre python3 -m confine.selftest_queries
step house_a_down_pre python3 -m confine.house_a down
step house_a_up_pre python3 -m confine.house_a up --fresh
step bridge_types_pre python3 -m confine.selftest_bridge_types
cd ~/r2exp/bridge-b4b/v2/framework || exit 1
echo "post commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" >> $S
step commands python3 -m confine.selftest_commands
step queries python3 -m confine.selftest_queries
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up --fresh
step bridge_types python3 -m confine.selftest_bridge_types
TO=5400 step suites bash ~/r2exp/bridge-b4b/v2/experiments/selftests/suites_all.sh $O/suites
echo "suites failed=$(grep -vc "exit=0\|ALLDONE\|framework:" $O/suites/summary.txt) of $(grep -c exit= $O/suites/summary.txt)" >> $S
echo "bridge errors in (A) log: $(grep ERROR ~/r2exp/houseA/home-assistant.log | grep -c confine_bridge)" >> $S
grep -n "confine_bridge\|camera\|image" ~/r2exp/houseA/home-assistant.log | grep -i "error\|warn" | tail -20 > $O/houseA_camera_image_errors.txt
echo "unit system now: $(python3 -m confine.house_a status 2>&1 | head -1)" >> $S
for d in bridge-b4b-pre bridge-b4b; do echo "$d dirty after=$(git -C ~/r2exp/$d status --porcelain | wc -l)" >> $S; done
echo "end $(date -Is)" >> $S; echo ALLDONE >> $S
