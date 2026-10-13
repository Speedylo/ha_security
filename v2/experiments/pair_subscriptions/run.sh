#!/bin/sh
# T06's pair (notes/t06_true_pair_prediction.md): both arms on the Pi, in order.
# Run from the clone's root:  experiments/pair_subscriptions/run.sh <out-dir>
set -eu
OUT=$(realpath "${1:?usage: run.sh <out-dir>}")
mkdir -p "$OUT"
cd "$(dirname "$0")/../../framework"
git describe --tags --always > "$OUT/commit.txt"
python3 -m confine.house_a down
python3 -m confine.pair_subscriptions --arm unconfined --out "$OUT/unconfined.json"
python3 -m confine.house_a up --fresh
python3 -m confine.pair_subscriptions --arm confined --out "$OUT/confined.json"
