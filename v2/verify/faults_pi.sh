#!/bin/bash
# Verification 4.5, the two faults that need the house and the supervisor (notes/fault_injection_prediction.md):
#   FI1  (A) stops while a confined integration runs under the supervisor, then comes back
#   FI4  the supervisor (and so the mediator) is killed with SIGKILL, then started again
# Usage: bash faults_pi.sh FRAMEWORK_DIR OUTDIR. Needs (A) up. Every process is found by an exact pattern
# (bracketed, so pgrep never matches its own shell) and killed by the PID recorded, never by pattern.
F=${1:?framework dir}; OUT=${2:?outdir}; P=~/r2exp/ha314/bin/python
mkdir -p "$OUT"; R="$OUT/results.txt"; : > "$R"
sandboxes() { pgrep -f '/sandbox/runtime[.]py' | tr '\n' ' '; }
supervisors() { pgrep -f 'confine[.]supervise' | tr '\n' ' '; }
wait_for() { local file=$1 text=$2 limit=$3; for _ in $(seq "$limit"); do grep -q "$text" "$file" 2>/dev/null && return 0; sleep 1; done; return 1; }
start_supervisor() {  # $1: log file, $2: audit dir
  ( cd "$F" && exec systemd-run --user --scope -q python3 -u -m confine.supervise \
      --component ../experiments/flood/demo_flood --python "$P" --audit-dir "$2" ) > "$1" 2>&1 &
}
say() { echo "$*" | tee -a "$R"; }

cd "$F" || exit 2
say "before: supervisors [$(supervisors)] sandboxes [$(sandboxes)]"

# -- FI1 ---------------------------------------------------------------------------------------
start_supervisor "$OUT/fi1_supervisor.log" "$OUT/fi1_audit"
wait_for "$OUT/fi1_supervisor.log" "started (run 1" 120 || say "FI1: the sandbox never started"
sleep 5
say "FI1 running: supervisors [$(supervisors)] sandboxes [$(sandboxes)]"
python3 -m confine.house_a down >> "$OUT/fi1_house.log" 2>&1
say "FI1 (A) stopped at $(date +%T)"
for _ in $(seq 30); do [ -z "$(supervisors)" ] && break; sleep 1; done
say "FI1 after (A) stopped: supervisors [$(supervisors)] sandboxes [$(sandboxes)]"
python3 -m confine.house_a up >> "$OUT/fi1_house.log" 2>&1
say "FI1 (A) back at $(date +%T): $(python3 -m confine.house_a status 2>&1 | tail -1)"
sleep 30
say "FI1 30 s after (A) returned: supervisors [$(supervisors)] sandboxes [$(sandboxes)]"
say "FI1 supervisor log tail:"; tail -5 "$OUT/fi1_supervisor.log" | tee -a "$R"
for pid in $(supervisors) $(sandboxes); do kill -TERM "$pid" 2>/dev/null; done; sleep 3

# -- FI4 ---------------------------------------------------------------------------------------
start_supervisor "$OUT/fi4_supervisor_1.log" "$OUT/fi4_audit"
wait_for "$OUT/fi4_supervisor_1.log" "started (run 1" 120 || say "FI4: the sandbox never started"
sleep 5
sup=$(supervisors); box=$(sandboxes)
say "FI4 running: supervisors [$sup] sandboxes [$box]"
for pid in $sup; do kill -KILL "$pid"; done
say "FI4 supervisor SIGKILLed at $(date +%T)"
sleep 10
say "FI4 10 s later: supervisors [$(supervisors)] sandboxes [$(sandboxes)] (were [$box])"
start_supervisor "$OUT/fi4_supervisor_2.log" "$OUT/fi4_audit"
wait_for "$OUT/fi4_supervisor_2.log" "started (run 1" 120 || say "FI4: the second supervisor's sandbox never started"
sleep 5
say "FI4 after the restart: supervisors [$(supervisors)] sandboxes [$(sandboxes)]"
say "FI4 audit log verifies: $(cd "$F" && python3 -c "
import sys; from pathlib import Path; from confine.audit import AuditLog
logs = sorted(Path('$OUT/fi4_audit').rglob('*.jsonl'))
print([(p.name, len(AuditLog(path=p).verify())) for p in logs])")"
for pid in $(supervisors) $(sandboxes); do kill -TERM "$pid" 2>/dev/null; done; sleep 3
say "after cleanup: supervisors [$(supervisors)] sandboxes [$(sandboxes)]"
say ALLDONE
