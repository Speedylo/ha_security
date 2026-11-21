# Seccomp fix Pi run (F72-F75), 2026-11-21. Modelled on final2's drivers; drivers live outside the clones.
T=~/r2exp/seccomp-fix/clone/v2; TP=~/r2exp/seccomp-fix/pre/v2; R=~/r2exp/seccomp-fix/out; P=~/r2exp/ha314/bin/python
begin() {
  OUT=$R/$1; [ -e "$OUT" ] && mv "$OUT" "$OUT.attempt_$(date +%Y%m%dT%H%M%S)"
  mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
  echo "start $(date -Is) uptime $(uptime -p) commit $(git -C "$T" rev-parse HEAD) dirty=$(git -C "$T" status --porcelain | wc -l) host $(hostname) kernel $(uname -r) arch $(uname -m) io_uring_disabled $(cat /proc/sys/kernel/io_uring_disabled)" >> "$S"
}
keep() { cp ~/r2exp/houseA/home-assistant.log "$OUT/a_after_$1.log" 2>/dev/null; }
step() { local name=$1; shift; local t=$(date +%s); timeout ${TO:-2400} "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t )) $(date -Is)" >> "$S"; keep "$name"; }
fin() { echo "dirty after=$(git -C "$T" status --porcelain | wc -l)" >> "$S"; echo "end $(date -Is)" >> "$S"; echo ALLDONE >> "$S"; }
