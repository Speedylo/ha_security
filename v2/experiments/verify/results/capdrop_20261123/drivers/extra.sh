#!/bin/bash
# After run.sh: (1) nordpool rerun on the fixed clone (its live-value check failed once: price moved?);
# (2) timing control: the same step from the pre clone (HEAD enter.py, no capability drop), right after,
# to see whether the 2-3x longer install-bearing steps come from the 22 Nov install fix, not the drop.
source ~/r2exp/capdrop-20261123/drivers/common.sh
until [ -e $R/run.done ]; do sleep 30; done
begin extra
cd "$T/framework" || exit 2
python3 -m confine.house_a status >> "$OUT/house_a_status.log" 2>&1
step egress_nordpool_fixed_rerun $run confine.endtoend_egress --subject nordpool --corpus $C --python $P --platform real --json "$OUT/egress_nordpool_fixed_rerun.json"
cd "$TP/framework" || exit 2
echo "next step from pre: $(git -C "$TP" rev-parse --short HEAD) $(git -C "$TP" status --porcelain | tr "\n" " ")" >> "$S"
step egress_nordpool_pre_control $run confine.endtoend_egress --subject nordpool --corpus $C --python $P --platform real --json "$OUT/egress_nordpool_pre_control.json"
fin
echo EXTRADONE >> $R/extra.done
