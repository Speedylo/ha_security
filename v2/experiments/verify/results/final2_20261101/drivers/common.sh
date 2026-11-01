# Second final rerun (notes/final_rerun2_prediction_20261101.md), shared by every chunk's driver.
# Drivers live outside the clone so the tagged tree stays clean. A chunk run again keeps its earlier
# attempt, renamed (rule 5).
T=~/r2exp/final2/v2; R=~/r2exp/final2-run/out; P=~/r2exp/ha314/bin/python
C=~/r2exp/corpus; U=~/r2exp/corpus_uniform; PD=~/r2exp/platform-deps; AUG=~/r2exp/t2/platform-deps-aug
run="systemd-run --user --scope -q python3 -u -m"
begin() {
  OUT=$R/$1; [ -e "$OUT" ] && mv "$OUT" "$OUT.attempt_$(date +%Y%m%dT%H%M%S)"
  mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
  echo "start $(date -Is) uptime $(uptime -p) commit $(git -C "$T" rev-parse HEAD) tag $(git -C "$T" describe --tags) dirty=$(git -C "$T" status --porcelain | wc -l) host $(hostname) kernel $(uname -r)" >> "$S"
}
keep() { cp ~/r2exp/houseA/home-assistant.log "$OUT/a_after_$1.log" 2>/dev/null; }
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-2400} "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t )) $(date -Is)" >> "$S"; keep "$name"; }
fin() { echo "dirty after=$(git -C "$T" status --porcelain | wc -l)" >> "$S"; echo "end $(date -Is)" >> "$S"; echo ALLDONE >> "$S"; }
