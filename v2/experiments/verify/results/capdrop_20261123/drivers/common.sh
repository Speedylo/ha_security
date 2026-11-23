# Capability-drop Pi run (F76), 2026-11-23 (notes/capdrop_prediction_20261123.md). Modelled on the
# seccomp-fix and final2 drivers; drivers live outside the clones. The fix is UNCOMMITTED: the clone is
# HEAD ab2af16 plus three files copied in, whose sha256 is recorded in every summary.
B=~/r2exp/capdrop-20261123; T=$B/clone/v2; TP=$B/pre/v2; R=$B/out; P=~/r2exp/ha314/bin/python
C=~/r2exp/corpus; U=~/r2exp/corpus_uniform; PD=~/r2exp/platform-deps
run="systemd-run --user --scope -q python3 -u -m"
begin() {
  OUT=$R/$1; [ -e "$OUT" ] && mv "$OUT" "$OUT.attempt_$(date +%Y%m%dT%H%M%S)"
  mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
  echo "start $(date -Is) uptime $(uptime -p) commit $(git -C "$T" rev-parse HEAD) dirty=$(git -C "$T" status --porcelain | wc -l) host $(hostname) kernel $(uname -r) arch $(uname -m)" >> "$S"
  (cd "$T/framework/confine" && sha256sum capabilities.py enter.py selftest_adversary.py) >> "$S"
}
keep() { cp ~/r2exp/houseA/home-assistant.log "$OUT/a_after_$1.log" 2>/dev/null; }
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-2400} "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t )) $(date -Is)" >> "$S"; keep "$name"; }
fin() { echo "dirty after=$(git -C "$T" status --porcelain | wc -l)" >> "$S"; echo "end $(date -Is)" >> "$S"; echo ALLDONE >> "$S"; }
