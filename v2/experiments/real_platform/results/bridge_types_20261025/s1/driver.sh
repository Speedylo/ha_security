#!/bin/bash
# Bridge step 1 (notes/bridge_types_step1_prediction_20261025.md), from the clone of bridge-s1, (A) up --fresh.
O=~/r2exp/bridge-run/s1; T=~/r2exp/bridge-s1/v2; S=$O/summary.txt
cd $T/framework || exit 1
echo "start $(date -Is) commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" > $S
~/r2exp/ha314/bin/python -c "import sys; sys.path.insert(0, \"ha_bridge\"); import confine_bridge, confine_bridge.button, confine_bridge.text, confine_bridge.select, confine_bridge.number; print(confine_bridge.PLATFORMS)" > $O/import.log 2>&1; echo "import exit=$?" >> $S
timeout 120 python3 -m confine.house_a down > $O/house_a_down.log 2>&1; echo "house_a_down exit=$?" >> $S
timeout 300 python3 -m confine.house_a up --fresh > $O/house_a_up.log 2>&1; echo "house_a_up exit=$?" >> $S
timeout 300 python3 -m confine.selftest_bridge_types > $O/selftest_bridge_types.log 2>&1; echo "bridge_types exit=$?" >> $S
timeout 5400 bash $T/experiments/selftests/suites_all.sh $O/suites > $O/suites.log 2>&1; echo "suites exit=$?" >> $S
echo "suites failed=$(grep -vc "exit=0\|ALLDONE\|framework:" $O/suites/summary.txt) of $(grep -c exit= $O/suites/summary.txt)" >> $S
grep -h "confine_bridge" ~/r2exp/house_a/home-assistant.log 2>/dev/null | grep -c "ERROR" | sed "s/^/bridge errors in (A) log: /" >> $S
echo "dirty after=$(git status --porcelain | wc -l)" >> $S; echo "end $(date -Is)" >> $S; echo ALLDONE >> $S
