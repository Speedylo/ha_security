#!/bin/bash
# Chunk H: steps 10 and 11, on a fresh boot (Younes reboots the Pi just before). Step 10 runs
# verify/phase3_timing.sh five times with ROOT set to the clone; each pass writes under the clone's
# results/phase3_timing/final2_passN (so the clone is dirty after, as on 16 October). Step 11 re-issues
# item12_20261003/depth.sh's commands against the clone.
source ~/r2exp/final2-run/drivers/common.sh
begin chunkH_step10_timing
cd "$T/framework" && step house_a_up python3 -m confine.house_a up --fresh
cd "$T"
for n in 1 2 3 4 5; do
  TO=3600 step pass$n env ROOT="$T" PASS_DIR=final2_pass$n bash verify/phase3_timing.sh $n
  sleep 60
done
fin

begin chunkH_step11_depth
cd "$T/experiments/unstrip" || exit 2
for round in 1 2 3; do
  for point in none two four ten; do
    case $point in
      none) a="--profile minimal" ;; two) a="--components http,websocket_api" ;;
      four) a="--components frontend,http,websocket_api,lovelace" ;; ten) a="--profile unstripped" ;;
    esac
    TO=3600 step depth_${point}_r$round systemd-run --user --scope -q python3 scale.py --count 6 --python $P $a \
      --platform-deps $AUG --json "$OUT/depth_${point}_r$round.json"
    sleep 20
  done
done
fin
