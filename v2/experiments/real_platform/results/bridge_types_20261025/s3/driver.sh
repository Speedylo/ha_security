#!/bin/bash
# Bridge step 3 (notes/bridge_types_step3_prediction_20261025.md). Pre: both suites from bridge-s3-pre, (A) fresh with that bridge.
# Post: from bridge-s3, (A) fresh with the new bridge; the real-house suite alone, then every suite (which runs it again on the same (A)).
O=~/r2exp/bridge-run/s3; S=$O/summary.txt
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-600} "$@" > "$O/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd ~/r2exp/bridge-s3-pre/v2/framework || exit 1
echo "start $(date -Is) pre commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" > $S
step commands_pre python3 -m confine.selftest_commands
step house_a_down_pre python3 -m confine.house_a down
step house_a_up_pre python3 -m confine.house_a up --fresh
step bridge_types_pre python3 -m confine.selftest_bridge_types
cd ~/r2exp/bridge-s3/v2/framework || exit 1
echo "post commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" >> $S
step commands python3 -m confine.selftest_commands
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up --fresh
step bridge_types python3 -m confine.selftest_bridge_types
TO=5400 step suites bash ~/r2exp/bridge-s3/v2/experiments/selftests/suites_all.sh $O/suites
echo "suites failed=$(grep -vc "exit=0\|ALLDONE\|framework:" $O/suites/summary.txt) of $(grep -c exit= $O/suites/summary.txt)" >> $S
echo "bridge errors in (A) log: $(grep ERROR ~/r2exp/houseA/home-assistant.log | grep -c confine_bridge)" >> $S
echo "unit system now: $(python3 -m confine.house_a status 2>&1 | head -1)" >> $S
for d in bridge-s3-pre bridge-s3; do echo "$d dirty after=$(git -C ~/r2exp/$d status --porcelain | wc -l)" >> $S; done
echo "end $(date -Is)" >> $S; echo ALLDONE >> $S
