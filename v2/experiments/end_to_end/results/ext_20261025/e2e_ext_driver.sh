#!/bin/bash
# E2E extension (notes/e2e_extension_prediction_20261025.md): both runs from the clone of e2e-ext-2026-10.
# Kept outside the clone so the tagged tree stays clean.
set -u
OUT=~/r2exp/e2e-ext-run/out
cd ~/r2exp/e2e-ext/v2/framework || exit 1
echo "start $(date -Is) commit $(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l)" > $OUT/summary.txt
systemd-run --user --scope -q python3 -m confine.endtoend_function --corpus ~/r2exp/corpus \
  --python ~/r2exp/ha314/bin/python --only alarmo --json $OUT/alarmo.json > $OUT/alarmo.log 2>&1
echo "alarmo exit=$? $(date -Is)" >> $OUT/summary.txt
systemd-run --user --scope -q python3 -m confine.endtoend_egress --subject waste_collection_schedule \
  --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python --json $OUT/waste.json > $OUT/waste.log 2>&1
echo "waste exit=$? $(date -Is)" >> $OUT/summary.txt
echo "dirty after=$(git status --porcelain | wc -l)" >> $OUT/summary.txt
echo ALLDONE >> $OUT/summary.txt
