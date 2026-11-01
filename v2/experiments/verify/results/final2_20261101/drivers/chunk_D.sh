#!/bin/bash
# Chunk D: step 3 (Pi half), step 4, step 9, step 12 (after fetching the head sample at its pinned
# commits), step 14.
source ~/r2exp/final2-run/drivers/common.sh
begin chunkD_step03_pi
cd "$T/framework" || exit 2
step house_a_down python3 -m confine.house_a down
step house_a_up python3 -m confine.house_a up --fresh
step faults_py python3 ../verify/faults.py --json "$OUT/faults_pi.json"
step faults_pi_fixed bash ../verify/faults_pi_fixed.sh "$T/framework" "$OUT/fixed"
python3 -m confine.house_a status | grep -qx up || { echo "(A) not up after faults_pi_fixed; brought up again" >> "$S"; step house_a_up_after python3 -m confine.house_a up --fresh; }
fin

begin chunkD_step04_fuzz
cd "$T/framework" || exit 2
step fuzz python3 ../verify/fuzz_mediator.py --json "$OUT/fuzz.json"
fin

begin chunkD_step09_t06
cd "$T/framework" || exit 2
step pair bash ../experiments/pair_subscriptions/run.sh "$OUT/pair"
python3 -m confine.house_a status >> "$OUT/house_a_status.log" 2>&1
fin

begin chunkD_step12_api_surface
TOP=~/r2exp/final2-run/top150
if [ ! -e "$TOP" ]; then
  step fetch_top150 $P -c 'import json, sys; from pathlib import Path
sys.path.insert(0, sys.argv[1]); import fetch_hacs_corpus as f
rows = [r for r in json.loads(Path(sys.argv[2]).read_text())["repositories"] if r.get("in_sample")]
out = Path(sys.argv[3]); out.mkdir(parents=True)
bad = [r["domain"] for r in rows if not f.fetch_one({k: r[k] for k in ("domain", "repo", "commit")}, out)["ok"]]
print(f"{len(rows)} in the sample, {len(rows) - len(bad)} fetched, failed: {bad}"); sys.exit(1 if bad else 0)' \
    "$T/figures" "$T/figures/hacs_top150_manifest.json" "$TOP"
fi
cd "$T/figures" || exit 2
step hacs $P api_surface.py --root "$TOP" --label hacs-top150 --json "$OUT/api_surface_hacs.json"
step uniform $P api_surface.py --root "$U" --label hacs-uniform40 --json "$OUT/api_surface_uniform.json"
for n in hacs uniform; do $P -c 'import json, sys; a, b = (json.load(open(p)) for p in sys.argv[1:3]); print(sys.argv[3], "IDENTICAL" if a == b else "DIFFERENT in " + str([k for k in a if a.get(k) != b.get(k)]))' "$OUT/api_surface_$n.json" "$T/figures/api_surface_$n.json" $n >> "$S"; done
fin

begin chunkD_step14_coverage
cd "$T" || exit 2
step recount $P -I verify/bridge_coverage_recount.py "$C"
fin
