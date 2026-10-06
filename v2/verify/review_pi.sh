#!/bin/bash
# Verification 4.7, the cases of notes/review_fixes_prediction.md that need real supervisors on the Pi:
#   P1  F32  a manifest declaring 192 MB gets 192 MB through the supervisor's launch path
#   P2  R10  a second supervisor started beside a live one leaves the first one's sandbox running
#   P3  R2   after a SIGKILL and a restart, both starts' reports are kept
#   P4  R7   the house's Home Assistant reports itself running before the mediator uses it
# Usage: bash review_pi.sh FRAMEWORK_DIR OUTDIR. Needs (A) up. Processes are found by bracketed patterns
# and killed by recorded PID.
F=${1:?framework dir}; OUT=${2:?outdir}; P=~/r2exp/ha314/bin/python
mkdir -p "$OUT"; R="$OUT/results.txt"; : > "$R"; NOTHING='{"schema_version": 1}'
sandboxes() { pgrep -f '/sandbox/runtime[.]py' | tr '\n' ' '; }
supervisors() { pgrep -f 'confine[.]supervise' | tr '\n' ' '; }
count() { echo $# ; }
wait_for() { local file=$1 text=$2 limit=$3; for _ in $(seq "$limit"); do grep -q "$text" "$file" 2>/dev/null && return 0; sleep 1; done; return 1; }
start_supervisor() {  # $1 log, $2 audit dir, $3 permissions
  ( cd "$F" && exec systemd-run --user --scope -q python3 -u -m confine.supervise \
      --component ../experiments/flood/demo_flood --python "$P" --audit-dir "$2" \
      --permissions "${3:-$NOTHING}" ) > "$1" 2>&1 &
}
say() { echo "$*" | tee -a "$R"; }
judge() { if [ "$2" = "$3" ]; then say "  ok    $1 — $4"; else say "  FAIL  $1 — $4 (expected $3, got $2)"; fi; }
stop_all() { for pid in $(supervisors); do kill -TERM "$pid"; done; sleep 5
             for pid in $(sandboxes); do kill -TERM "$pid" 2>/dev/null; done; sleep 2; }
parent=$(cd "$F" && python3 -c "from confine.cgroup import Delegation; print(Delegation.discover().parent)")

cd "$F" || exit 2
say "before: supervisors [$(supervisors)] sandboxes [$(sandboxes)]"

# -- P1 (F32) -------------------------------------------------------------------------------------
start_supervisor "$OUT/p1_supervisor.log" "$OUT/p1_audit" \
  '{"schema_version": 1, "resources": {"memory_mb": 192}}'
wait_for "$OUT/p1_supervisor.log" "started (run 1" 120 || say "P1: the sandbox never started"
mem=$(cat "$parent"/sup-demo_flood-*/memory.max 2>/dev/null | head -1)
judge "P1 a declared 192 MB is the sandbox's memory.max" "$mem" 201326592 "memory.max $mem"
stop_all

# -- P2 (R10) -------------------------------------------------------------------------------------
start_supervisor "$OUT/p2_first.log" "$OUT/p2_audit_first"
wait_for "$OUT/p2_first.log" "started (run 1" 120 || say "P2: the first sandbox never started"
sleep 3; first_box=$(sandboxes)
start_supervisor "$OUT/p2_second.log" "$OUT/p2_audit_second"
wait_for "$OUT/p2_second.log" "started (run 1\|refus\|not started" 120
sleep 5
judge "P2 the first supervisor's sandbox is still running" \
  "$(for pid in $first_box; do kill -0 "$pid" 2>/dev/null && echo alive || echo gone; done)" alive "pid $first_box"
judge "P2 and the first supervisor did not report it exited" \
  "$(grep -c 'exited by itself' "$OUT/p2_first.log")" 0 "$(grep 'exited' "$OUT/p2_first.log")"
stop_all

# -- P3 (R2) --------------------------------------------------------------------------------------
start_supervisor "$OUT/p3_supervisor_1.log" "$OUT/p3_audit"
wait_for "$OUT/p3_supervisor_1.log" "started (run 1" 120 || say "P3: the sandbox never started"
sleep 5
for pid in $(supervisors); do kill -KILL "$pid"; done; sleep 10
start_supervisor "$OUT/p3_supervisor_2.log" "$OUT/p3_audit"
wait_for "$OUT/p3_supervisor_2.log" "started (run 1" 120 || say "P3: the second sandbox never started"
sleep 3
judge "P3 two report files, one per start" "$(ls "$OUT/p3_audit"/demo_flood-*.json 2>/dev/null | wc -l)" 2 \
  "$(ls "$OUT/p3_audit" | tr '\n' ' ')"
stop_all

# -- P4 (R7) --------------------------------------------------------------------------------------
judge "P4 (A) reports itself RUNNING to the mediator's connection" \
  "$(cd "$F" && python3 -c "
from confine.real_platform import RealPlatform
p = RealPlatform(); print(p.call({'type': 'get_config'}).get('state')); p.close()" 2>&1 | tail -1)" RUNNING ""

say "after cleanup: supervisors [$(supervisors)] sandboxes [$(sandboxes)]"
say ALLDONE
