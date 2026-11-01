#!/bin/bash
# Chunk C: steps 2b and 2c, the control and M51–M88 (M51b included) through run_kind_mutants.sh.
source ~/r2exp/final2-run/drivers/common.sh
begin chunkC_step02bc
cd "$T" || exit 2
TO=14400 step kinds env MUT_WORK=~/r2exp/final2-run/km bash verify/mutants/run_kind_mutants.sh "$T" "$OUT/kinds"
grep -v ALLDONE "$OUT/kinds/run.txt" | cut -c1-200 >> "$S"
fin
