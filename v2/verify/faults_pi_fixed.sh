#!/bin/bash
# Verification 4.5, FI1 and FI4 again after the F29, F30 and F31 fixes, judged against the criteria in
# notes/fault_injection_prediction.md ("The fixes"). `faults_pi.sh` is the run that found them, kept as it ran.
# Usage: bash faults_pi_fixed.sh FRAMEWORK_DIR OUTDIR. Needs (A) up. Processes are found by bracketed
# patterns and killed by recorded PID.
F=${1:?framework dir}; OUT=${2:?outdir}; P=~/r2exp/ha314/bin/python
mkdir -p "$OUT"; R="$OUT/results.txt"; : > "$R"
sandboxes() { pgrep -f '/sandbox/runtime[.]py' | tr '\n' ' '; }
supervisors() { pgrep -f 'confine[.]supervise' | tr '\n' ' '; }
count() { echo $# ; }
wait_for() { local file=$1 text=$2 limit=$3; for _ in $(seq "$limit"); do grep -q "$text" "$file" 2>/dev/null && return 0; sleep 1; done; return 1; }
start_supervisor() {
  ( cd "$F" && exec systemd-run --user --scope -q python3 -u -m confine.supervise \
      --component ../experiments/flood/demo_flood --python "$P" --audit-dir "$2" ) > "$1" 2>&1 &
}
say() { echo "$*" | tee -a "$R"; }
judge() { if [ "$2" = "$3" ]; then say "  ok    $1 — $4"; else say "  FAIL  $1 — $4 (expected $3, got $2)"; fi; }

cd "$F" || exit 2
say "before: supervisors [$(supervisors)] sandboxes [$(sandboxes)]"

# -- FI1 with F29: (A) goes away and comes back ---------------------------------------------------
start_supervisor "$OUT/fi1_supervisor.log" "$OUT/fi1_audit"
wait_for "$OUT/fi1_supervisor.log" "started (run 1" 120 || say "FI1: the sandbox never started"
sleep 5
python3 -m confine.house_a down >> "$OUT/fi1_house.log" 2>&1
wait_for "$OUT/fi1_supervisor.log" "went away" 30
sleep 3
judge "FI1 while (A) is down, no sandbox runs" "$(count $(sandboxes))" 0 "sandboxes [$(sandboxes)]"
judge "FI1 and the supervisor is still there" "$(count $(supervisors))" 1 "supervisors [$(supervisors)]"
python3 -m confine.house_a up >> "$OUT/fi1_house.log" 2>&1
back=$(date +%s)
wait_for "$OUT/fi1_supervisor.log" "started (run 2" 90
say "FI1 the integration was running again $(( $(date +%s) - back )) s after (A) answered"
sleep 5
judge "FI1 within 60 s of (A) returning, one supervisor" "$(count $(supervisors))" 1 "[$(supervisors)]"
judge "FI1 and one sandbox" "$(count $(sandboxes))" 1 "[$(sandboxes)]"
judge "FI1 no traceback in the supervisor's log" "$(grep -c Traceback "$OUT/fi1_supervisor.log")" 0 "plain lines only"
for pid in $(supervisors); do kill -TERM "$pid"; done; sleep 5
for pid in $(sandboxes); do kill -TERM "$pid" 2>/dev/null; done; sleep 2

# -- FI4 with F30 and F31: the supervisor is SIGKILLed, then started again ------------------------
start_supervisor "$OUT/fi4_supervisor_1.log" "$OUT/fi4_audit"
wait_for "$OUT/fi4_supervisor_1.log" "started (run 1" 120 || say "FI4: the sandbox never started"
sleep 5
for pid in $(supervisors); do kill -KILL "$pid"; done
sleep 10
judge "FI4 10 s after the SIGKILL, no sandbox is left" "$(count $(sandboxes))" 0 "[$(sandboxes)]"
start_supervisor "$OUT/fi4_supervisor_2.log" "$OUT/fi4_audit"
wait_for "$OUT/fi4_supervisor_2.log" "started (run 1" 120 || say "FI4: the second supervisor's sandbox never started"
sleep 5
judge "FI4 after the restart, exactly one sandbox" "$(count $(sandboxes))" 1 "[$(sandboxes)]"
breaks=$(cd "$F" && python3 -c "
from pathlib import Path; from confine.audit import AuditLog
logs = sorted(Path('$OUT/fi4_audit').glob('decisions*.jsonl'))
bad = sum(1 for p in logs for b in AuditLog(path=p).verify() if b.kind != 'mac')
print(f'{len(logs)} {bad}')")
judge "FI4 one log file per start" "${breaks% *}" 2 "files: ${breaks% *}"
judge "FI4 no sequence, link or hash break in any of them" "${breaks#* }" 0 "MAC breaks of the killed run are expected (§6.8.4)"
for pid in $(supervisors); do kill -TERM "$pid"; done; sleep 5
for pid in $(sandboxes); do kill -TERM "$pid" 2>/dev/null; done; sleep 2

# -- F30's backstop: a stale cgroup with a process in it ------------------------------------------
planted=$(cd "$F" && systemd-run --user --scope -q python3 -c "
from confine.cgroup import Delegation, SandboxCgroup, spawn_confined
cg = SandboxCgroup.create(Delegation.discover(), 'sup-demo_flood-9')
import subprocess; print(spawn_confined(['sleep', '600'], cg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).pid)" 2>>"$OUT/backstop.err")
say "F30 planted pid $planted in a stale sup-demo_flood-9"
start_supervisor "$OUT/backstop_supervisor.log" "$OUT/backstop_audit"
wait_for "$OUT/backstop_supervisor.log" "started (run 1" 120
judge "F30 the starting supervisor killed the planted process" "$(kill -0 "$planted" 2>/dev/null && echo alive || echo gone)" gone "pid $planted"
judge "F30 and said so" "$(grep -c 'cleared 1 sandbox cgroup' "$OUT/backstop_supervisor.log")" 1 "$(grep cleared "$OUT/backstop_supervisor.log")"
for pid in $(supervisors); do kill -TERM "$pid"; done; sleep 5
for pid in $(sandboxes); do kill -TERM "$pid" 2>/dev/null; done; sleep 2
say "after cleanup: supervisors [$(supervisors)] sandboxes [$(sandboxes)]"
say ALLDONE
# Exit 1 when any judged line failed, so a runner that reads exit codes sees it (4.12, F48).
grep -q "^  FAIL" "$R" && exit 1
exit 0
