#!/bin/bash
# F68 (notes/f68_designate_await_prediction_20261026.md). Fails first: selftest_real_platform at
# f68-pre with (A) fresh from that clone. Then at f68-fix: (A) fresh, selftest_real_platform, every
# suite. (A)'s log is copied after every step and searched for the never-awaited warning.
O=~/r2exp/f68-run; S=$O/summary.txt
keep() { cp ~/r2exp/houseA/home-assistant.log "$O/a_after_$1.log" 2>/dev/null; cp ~/r2exp/houseA/home-assistant.log.1 "$O/a_after_$1.log.1" 2>/dev/null; }
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-1800} "$@" > "$O/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t )) $(date -Is)" >> "$S"; keep "$name"; }
fresh() { step house_a_down_$1 python3 -m confine.house_a down; step house_a_up_$1 python3 -m confine.house_a up --fresh; }
awaited() { echo "$1 never-awaited lines in (A)'s log: $(cat $O/a_after_$2.log $O/a_after_$2.log.1 2>/dev/null | grep -c 'async_get_user.*never awaited')" >> $S; }
echo "start $(date -Is)" > $S
cd ~/r2exp/f68-pre/v2/framework || exit 1
echo "f68-pre commit $(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l)" >> $S
fresh pre; step real_platform_pre python3 -m confine.selftest_real_platform; awaited pre real_platform_pre
cd ~/r2exp/f68-fix/v2/framework || exit 1
echo "f68-fix commit $(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l) lan $(hostname -I)" >> $S
fresh fix; step real_platform_fix python3 -m confine.selftest_real_platform; awaited fix real_platform_fix
TO=5400 step suites bash ~/r2exp/f68-fix/v2/experiments/selftests/suites_all.sh $O/suites
awaited suites suites
echo "suites failed=$(grep -vc "exit=0\|ALLDONE\|framework:" $O/suites/summary.txt) of $(grep -c exit= $O/suites/summary.txt)" >> $S
for d in f68-pre f68-fix; do echo "$d dirty after=$(git -C ~/r2exp/$d status --porcelain | wc -l)" >> $S; done
echo "end $(date -Is)" >> $S; echo ALLDONE >> $S
