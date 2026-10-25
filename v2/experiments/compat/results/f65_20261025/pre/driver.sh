#!/bin/bash
# F65 Q3 (notes/f65_source_ip_prediction_20261025.md): the final rerun's compat measurement with the shim, before the fix.
OUT=~/r2exp/f65-run/pre; T=~/r2exp/f65-pre/v2
cd $T/framework || exit 1
echo "start $(date -Is) commit $(git rev-parse HEAD) tag $(git describe --tags) dirty=$(git status --porcelain | wc -l)" > $OUT/summary.txt
timeout 14400 systemd-run --user --scope -q python3 -u -m confine.compat --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python \
  --profile declared --platform-deps ~/r2exp/platform-deps --egress --json $OUT/compat_egress.json > $OUT/compat_egress.log 2>&1
echo "compat_egress exit=$? $(date -Is)" >> $OUT/summary.txt
echo "dirty after=$(git status --porcelain | wc -l)" >> $OUT/summary.txt; echo ALLDONE >> $OUT/summary.txt
