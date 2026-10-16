#!/bin/bash
# Final rerun, steps 10–12, from the clone of final-2026-10, started on a fresh boot.
# Step 10: verify/phase3_timing.sh five times with ROOT set to the clone (verify/final_timing.sh names the
#   old verify-final clone); each pass writes under the clone's results/phase3_timing/final_rerun_passN.
# Step 11: the commands of experiments/unstrip/results/item12_20261003/depth.sh against the clone
#   (that script cds into ~/r2exp/v2, a stale tree), output here.
# Step 12: figures/api_surface.py over the rebuilt top-150 sample (in_sample rows of
#   figures/hacs_top150_manifest.json) and over the uniform corpus, under Python 3.14 as the originals.
T=~/r2exp/final/v2; R=~/r2exp/final-run/out; P=~/r2exp/ha314/bin/python; D=~/r2exp/t2/platform-deps-aug
begin() { OUT=$R/$1; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"; echo "start $(date -Is) uptime $(uptime -p) commit $(git -C "$T" rev-parse HEAD) tag $(git -C "$T" describe --tags) dirty=$(git -C "$T" status --porcelain | wc -l)" >> "$S"; }
step() { local name=$1; shift; local t=$(date +%s); timeout 3600 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
end() { echo "dirty after=$(git -C "$T" status --porcelain | wc -l)" >> "$S"; echo "end $(date -Is)" >> "$S"; echo ALLDONE >> "$S"; }

begin step10_timing
cd "$T/framework" && step house_a_up python3 -m confine.house_a up
cd "$T"
for n in 1 2 3 4 5; do
  step pass$n env ROOT="$T" PASS_DIR=final_rerun_pass$n bash verify/phase3_timing.sh $n
  sleep 60
done
end

begin step11_depth
cd "$T/experiments/unstrip" || exit 2
for round in 1 2 3; do
  for point in none two four ten; do
    case $point in
      none) a="--profile minimal" ;; two) a="--components http,websocket_api" ;;
      four) a="--components frontend,http,websocket_api,lovelace" ;; ten) a="--profile unstripped" ;;
    esac
    step depth_${point}_r$round systemd-run --user --scope -q python3 scale.py --count 6 --python $P $a \
      --platform-deps $D --json "$OUT/depth_${point}_r$round.json"
    sleep 20
  done
done
end

begin step12_api_surface
cd "$T/figures"
step hacs $P api_surface.py --root ~/r2exp/final-run/top150 --label hacs-top150 --json "$OUT/api_surface_hacs.json"
step uniform $P api_surface.py --root ~/r2exp/corpus_uniform --label hacs-uniform40 --json "$OUT/api_surface_uniform.json"
end
