#!/bin/bash
# 4.12: branch coverage of the 26 suites on the Pi (notes/tests_bite_prediction_20261007.md).
# Usage: bash run_coverage.sh OUTDIR   (expects a clean clone of the tag at ~/r2exp/tb/covsrc)
# (A) is brought up from that clone with measurement on, so the bridge inside (A) is measured too:
# `house_a` starts hass with PYTHONPATH=houseA-deps, so the start-up hook is copied there for this
# run only, and houseA-deps is checksummed before and after to show it is left as found.
OUT=${1:?outdir}; mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
SRC=~/r2exp/tb/covsrc/v2; COV=~/r2exp/tb/cov; DEPS=~/r2exp/houseA-deps
log() { echo "$(date +%H:%M:%S) $*" >> "$OUT/run.txt"; }
( cd "$DEPS" && find . -type f -print0 | sort -z | xargs -0 sha256sum ) > "$OUT/deps_before.sha256"
( cd "$SRC/framework" && python3 -m confine.house_a down ) > "$OUT/house_a.log" 2>&1
[ -e "$DEPS/sitecustomize.py" ] && { log "houseA-deps already has a sitecustomize.py; stopping"; exit 1; }
cp "$COV/sitecustomize.py" "$DEPS/sitecustomize.py"
export COVERAGE_PROCESS_START=$COV/coveragerc PYTHONPATH=$COV/site
t=$(date +%s)
( cd "$SRC/framework" && python3 -m confine.house_a up ) >> "$OUT/house_a.log" 2>&1
log "house_a up exit=$? seconds=$(( $(date +%s) - t ))"
t=$(date +%s)
bash "$SRC/experiments/selftests/suites_all.sh" "$OUT/suites"
log "suites failed=$(grep -c 'exit=[^0]' "$OUT/suites/summary.txt") seconds=$(( $(date +%s) - t ))"
( cd "$SRC/framework" && python3 -m confine.house_a down ) >> "$OUT/house_a.log" 2>&1
unset COVERAGE_PROCESS_START PYTHONPATH
rm ~/r2exp/houseA-deps/sitecustomize.py
( cd "$DEPS" && find . -type f -print0 | sort -z | xargs -0 sha256sum ) > "$OUT/deps_after.sha256"
cmp -s "$OUT/deps_before.sha256" "$OUT/deps_after.sha256" && log "houseA-deps unchanged" || log "houseA-deps CHANGED"
ls "$COV/data" | wc -l | xargs -I{} sh -c 'echo "$(date +%H:%M:%S) data files={}" >> "$0/run.txt"' "$OUT"
cd "$COV/data" && export PYTHONPATH=$COV/lib/py313 COVERAGE_RCFILE=$COV/coveragerc
python3 -m coverage combine --keep -q > "$OUT/combine.log" 2>&1
python3 -m coverage report --show-missing --skip-empty > "$OUT/report.txt" 2>&1
python3 -m coverage json -o "$OUT/coverage.json" > /dev/null 2>&1
log ALLDONE
