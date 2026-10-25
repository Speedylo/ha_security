#!/bin/bash
# F65 U1-U3 (notes/f65_source_ip_prediction_20261025.md): the uniform 40 with the shim, from the clone of f65b-fix, (A) down.
OUT=~/r2exp/f65-run/uniform; T=~/r2exp/f65b-fix/v2; S=$OUT/summary.txt
cd $T/framework || exit 1
echo "start $(date -Is) commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" > $S
echo "house_a $(python3 -m confine.house_a status)" >> $S
timeout 14400 systemd-run --user --scope -q python3 -u -m confine.compat --corpus ~/r2exp/corpus_uniform --python ~/r2exp/ha314/bin/python \
  --profile declared --platform-deps ~/r2exp/platform-deps --egress --json $OUT/uniform_egress.json > $OUT/uniform_egress.log 2>&1
echo "uniform_egress exit=$? $(date -Is)" >> $S
echo "dirty after=$(git status --porcelain | wc -l)" >> $S; echo ALLDONE >> $S
