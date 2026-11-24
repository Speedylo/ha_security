# F77 (change banner) Pi run, 2026-11-24 (notes/banner_prediction_20261124.md, P3). Modelled on
# capdrop-20261123. The fix is COMMITTED (219d0ce; HEAD a55734f): the clone is HEAD, unmodified.
B=~/r2exp/banner-20261124; T=$B/clone/v2; R=$B/out
begin() {
  OUT=$R/$1; [ -e "$OUT" ] && mv "$OUT" "$OUT.attempt_$(date +%Y%m%dT%H%M%S)"
  mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
  echo "start $(date -Is) uptime $(uptime -p) commit $(git -C "$T" rev-parse HEAD) dirty=$(git -C "$T" status --porcelain | wc -l) host $(hostname) kernel $(uname -r) arch $(uname -m)" >> "$S"
}
keep() { cp ~/r2exp/houseA/home-assistant.log "$OUT/a_after_$1.log" 2>/dev/null; }
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-2400} "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t )) $(date -Is)" >> "$S"; keep "$name"; }
fin() { echo "dirty after=$(git -C "$T" status --porcelain | wc -l)" >> "$S"; echo "end $(date -Is)" >> "$S"; echo ALLDONE >> "$S"; }
