#!/bin/bash
# Bridge batch B3, rerun after T22 accepts a kept time for notify and event (bridge-b3b).
O=~/r2exp/bridge-run/b3b; S=$O/summary.txt
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-600} "$@" > "$O/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd ~/r2exp/bridge-b3b/v2/framework || exit 1
echo "start $(date -Is) commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" > $S
step commands python3 -m confine.selftest_commands
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up --fresh
step bridge_types python3 -m confine.selftest_bridge_types
TO=5400 step suites bash ~/r2exp/bridge-b3b/v2/experiments/selftests/suites_all.sh $O/suites
echo "suites failed=$(grep -vc "exit=0\|ALLDONE\|framework:" $O/suites/summary.txt) of $(grep -c exit= $O/suites/summary.txt)" >> $S
echo "bridge errors in (A) log: $(grep ERROR ~/r2exp/houseA/home-assistant.log | grep -c confine_bridge)" >> $S
echo "bridge-b3b dirty after=$(git -C ~/r2exp/bridge-b3b status --porcelain | wc -l)" >> $S
echo "end $(date -Is)" >> $S; echo ALLDONE >> $S
