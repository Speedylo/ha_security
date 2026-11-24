#!/bin/bash
# Fixed clone (HEAD): (A) fresh, preflight, every suite twice (P3 of the banner prediction).
source ~/r2exp/banner-20261124/drivers/common.sh
begin post_suites
cd "$T/framework" || exit 2
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up --fresh
step preflight systemd-run --user --scope -q python3 -m confine.preflight
cd "$T"
TO=5400 step suites_1 bash experiments/selftests/suites_all.sh "$OUT/suites_1"
TO=5400 step suites_2 bash experiments/selftests/suites_all.sh "$OUT/suites_2"
for n in 1 2; do echo "suites_$n failed=$(grep -c 'exit=[^0]' "$OUT/suites_$n/summary.txt") of $(grep -c 'exit=' "$OUT/suites_$n/summary.txt")" >> "$S"; done
fin
echo RUNDONE >> $R/run.done
