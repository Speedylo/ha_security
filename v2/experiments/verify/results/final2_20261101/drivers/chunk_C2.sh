#!/bin/bash
# Chunk C2: M72–M88 again. In chunk C the Pi's disk filled (chunk B's mutant work copies) before
# M72 was copied, so M72–M88 reported "patch failed" without being run. Same runner, same code.
source ~/r2exp/final2-run/drivers/common.sh
begin chunkC2_step02c
cd "$T" || exit 2
echo "disk before $(df -h / | tail -1)" >> "$S"
TO=7200 step kinds env MUT_WORK=~/r2exp/final2-run/km2 \
  MUT_ONLY="M72 M73 M74 M75 M76 M77 M78 M79 M80 M81 M82 M83 M84 M85 M86 M87 M88" \
  bash verify/mutants/run_kind_mutants.sh "$T" "$OUT/kinds"
grep -a -v ALLDONE "$OUT/kinds/run.txt" | cut -c1-200 >> "$S"
echo "disk after $(df -h / | tail -1)" >> "$S"
fin
