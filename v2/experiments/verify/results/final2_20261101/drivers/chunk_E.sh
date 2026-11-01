#!/bin/bash
# Chunk E: step 5, compatibility, both corpora, both arms, (A) down.
source ~/r2exp/final2-run/drivers/common.sh
begin chunkE_step05_compat
cd "$T/framework" || exit 2
step house_a_down python3 -m confine.house_a down
TO=14400 step c1_baseline $run confine.compat --corpus $C --python $P --profile baseline --platform-deps $PD --json "$OUT/c1_baseline.json"
TO=14400 step c1_declared_core $run confine.compat --corpus $C --python $P --profile declared --platform-deps $PD --json "$OUT/c1_declared_core.json"
TO=14400 step uniform_baseline $run confine.compat --corpus $U --python $P --profile baseline --platform-deps $PD --json "$OUT/uniform_baseline.json"
TO=14400 step uniform_confined $run confine.compat --corpus $U --python $P --profile declared --platform-deps $PD --json "$OUT/uniform_confined.json"
fin
