#!/bin/bash
# Bridge step 5, complete run, with F66 and F67 (notes/bridge_types_step5_prediction_20261025.md,
# notes/f66_unknown_state_prediction_20261025.md, notes/f67_timestamp_prediction_20261025.md).
# Fails first: the real-house suite at f66-pre and at f67-pre, each with (A) fresh from that clone.
# Then everything from bridge-s5c. (A)'s log is copied after every step, since a restart rotates it.
O=~/r2exp/bridge-run/s5c; S=$O/summary.txt; P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; U=~/r2exp/corpus_uniform
run="systemd-run --user --scope -q python3 -u -m"
keep() { cp ~/r2exp/houseA/home-assistant.log "$O/a_after_$1.log" 2>/dev/null; cp ~/r2exp/houseA/home-assistant.log.1 "$O/a_after_$1.log.1" 2>/dev/null; }
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-1800} "$@" > "$O/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t )) $(date -Is)" >> "$S"; keep "$name"; }
fresh() { step house_a_down_$1 python3 -m confine.house_a down; step house_a_up_$1 python3 -m confine.house_a up --fresh; }
echo "start $(date -Is)" > $S
for tag in f66-pre f67-pre; do
  cd ~/r2exp/s5c-$tag/v2/framework || exit 1
  echo "$tag commit $(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l)" >> $S
  fresh $tag; step bridge_types_$tag python3 -m confine.selftest_bridge_types
done
cd ~/r2exp/s5c-bridge-s5c/v2/framework || exit 1
echo "bridge-s5c commit $(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l) lan $(hostname -I)" >> $S
fresh main
step real_house python3 -m confine.selftest_real_house
step bridge_types python3 -m confine.selftest_bridge_types
TO=5400 step function $run confine.endtoend_function --corpus $C --python $P --platform real --json "$O/function.json"
for s in nordpool dwd_weather pirateweather waste_collection_schedule; do step egress_$s $run confine.endtoend_egress --subject $s --corpus $C --python $P --platform real --json "$O/egress_$s.json"; done
for s in smhi_brandrisk regensburg_transport; do step egress_$s $run confine.endtoend_egress --subject $s --corpus $U --python $P --platform real --json "$O/egress_$s.json"; done
for s in midea_ac_lan localtuya; do step local_$s $run confine.endtoend_local --corpus $C --python $P --subject $s --platform real --json "$O/local_$s.json"; done
step oauth_trakt $run confine.endtoend_oauth --corpus $U --python $P --platform real --json "$O/oauth_trakt.json"
echo "house_a before suites: $(python3 -m confine.house_a status 2>&1 | tail -1)" >> $S
TO=5400 step suites bash ~/r2exp/s5c-bridge-s5c/v2/experiments/selftests/suites_all.sh $O/suites
echo "suites failed=$(grep -vc "exit=0\|ALLDONE\|framework:" $O/suites/summary.txt) of $(grep -c exit= $O/suites/summary.txt)" >> $S
for d in s5c-f66-pre s5c-f67-pre s5c-bridge-s5c; do echo "$d dirty after=$(git -C ~/r2exp/$d status --porcelain | wc -l)" >> $S; done
echo "end $(date -Is)" >> $S; echo ALLDONE >> $S
