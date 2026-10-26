#!/bin/bash
# Switch state mirror (notes/switch_state_mirror_prediction_20261026.md). Fails first: selftest_bridge_types
# --restart at switch-mirror-pre, (A) fresh from that clone. Then at switch-mirror: the same; the
# function set against (A) (fresh); every suite. (A)'s log is copied after every step.
O=~/r2exp/sw-run; S=$O/summary.txt; P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus
keep() { cp ~/r2exp/houseA/home-assistant.log "$O/a_after_$1.log" 2>/dev/null; cp ~/r2exp/houseA/home-assistant.log.1 "$O/a_after_$1.log.1" 2>/dev/null; }
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-1800} "$@" > "$O/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t )) $(date -Is)" >> "$S"; keep "$name"; }
fresh() { step house_a_down_$1 python3 -m confine.house_a down; step house_a_up_$1 python3 -m confine.house_a up --fresh; }
echo "start $(date -Is)" > $S
cd ~/r2exp/switch-mirror-pre/v2/framework || exit 1
echo "switch-mirror-pre commit $(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l)" >> $S
fresh pre; step bridge_types_pre python3 -m confine.selftest_bridge_types --restart
cd ~/r2exp/switch-mirror/v2/framework || exit 1
echo "switch-mirror commit $(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l) lan $(hostname -I)" >> $S
fresh fix; step bridge_types_fix python3 -m confine.selftest_bridge_types --restart
fresh function
TO=5400 step function systemd-run --user --scope -q python3 -u -m confine.endtoend_function --corpus $C --python $P --platform real --json "$O/function.json"
TO=5400 step suites bash ~/r2exp/switch-mirror/v2/experiments/selftests/suites_all.sh $O/suites
echo "suites failed=$(grep -vc "exit=0\|ALLDONE\|framework:" $O/suites/summary.txt) of $(grep -c exit= $O/suites/summary.txt)" >> $S
for d in switch-mirror-pre switch-mirror; do echo "$d dirty after=$(git -C ~/r2exp/$d status --porcelain | wc -l)" >> $S; done
echo "end $(date -Is)" >> $S; echo ALLDONE >> $S
