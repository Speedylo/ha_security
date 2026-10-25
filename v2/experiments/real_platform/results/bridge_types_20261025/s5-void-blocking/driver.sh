#!/bin/bash
# Bridge step 5 (notes/bridge_types_step5_prediction_20261025.md). Pre: the house's test from bridge-s5-pre, (A) fresh with
# the old configuration. Post: from bridge-s5, (A) fresh with the dimmable light; the house's test; the fifteen with
# --platform real (each harness stops (A) around its unconfined arm); every suite.
O=~/r2exp/bridge-run/s5; S=$O/summary.txt; P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; U=~/r2exp/corpus_uniform
run="systemd-run --user --scope -q python3 -u -m"
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-1800} "$@" > "$O/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t )) $(date -Is)" >> "$S"; }
cd ~/r2exp/bridge-s5-pre/v2/framework || exit 1
echo "start $(date -Is) pre commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" > $S
step house_a_down_pre python3 -m confine.house_a down
step house_a_up_pre python3 -m confine.house_a up --fresh
step real_house_pre python3 -m confine.selftest_real_house
cd ~/r2exp/bridge-s5/v2/framework || exit 1
echo "post commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" >> $S
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up --fresh
step real_house python3 -m confine.selftest_real_house
TO=5400 step function $run confine.endtoend_function --corpus $C --python $P --platform real --json "$O/function.json"
for s in nordpool dwd_weather pirateweather waste_collection_schedule; do step egress_$s $run confine.endtoend_egress --subject $s --corpus $C --python $P --platform real --json "$O/egress_$s.json"; done
for s in smhi_brandrisk regensburg_transport; do step egress_$s $run confine.endtoend_egress --subject $s --corpus $U --python $P --platform real --json "$O/egress_$s.json"; done
for s in midea_ac_lan localtuya; do step local_$s $run confine.endtoend_local --corpus $C --python $P --subject $s --platform real --json "$O/local_$s.json"; done
step oauth_trakt $run confine.endtoend_oauth --corpus $U --python $P --platform real --json "$O/oauth_trakt.json"
echo "house_a before suites: $(python3 -m confine.house_a status 2>&1 | tail -1)" >> $S
TO=5400 step suites bash ~/r2exp/bridge-s5/v2/experiments/selftests/suites_all.sh $O/suites
echo "suites failed=$(grep -vc "exit=0\|ALLDONE\|framework:" $O/suites/summary.txt) of $(grep -c exit= $O/suites/summary.txt)" >> $S
echo "bridge errors in (A) log: $(grep ERROR ~/r2exp/houseA/home-assistant.log | grep -c confine_bridge)" >> $S
for d in bridge-s5-pre bridge-s5; do echo "$d dirty after=$(git -C ~/r2exp/$d status --porcelain | wc -l)" >> $S; done
echo "end $(date -Is)" >> $S; echo ALLDONE >> $S
