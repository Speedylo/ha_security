#!/bin/bash
# Bridge step 5, the function set against (A) after F69's fix (notes/f69_zombie_stop_prediction_20261025.md Z2;
# notes/bridge_types_step5_prediction_20261025.md E1-E3 for the six). From bridge-s5d, (A) fresh.
O=~/r2exp/bridge-run/s5d; S=$O/summary.txt; P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-1800} "$@" > "$O/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t )) $(date -Is)" >> "$S"; cp ~/r2exp/houseA/home-assistant.log "$O/a_after_$name.log" 2>/dev/null; }
cd ~/r2exp/s5d/v2/framework || exit 1
echo "start $(date -Is) commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" > $S
step house_a_test python3 -m confine.selftest_house_a
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up --fresh
TO=5400 step function systemd-run --user --scope -q python3 -u -m confine.endtoend_function --corpus $C --python $P --platform real --json "$O/function.json"
echo "dirty after=$(git status --porcelain | wc -l)" >> $S; echo "end $(date -Is)" >> $S; echo ALLDONE >> $S
