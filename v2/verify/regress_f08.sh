#!/bin/bash
# The regression for F08 (notes/f08_t06_prediction.md), on a fresh clone of verify-2026-10-f08
# (~/r2exp/verify-f08): every suite twice, nordpool end to end (a real install, whose run record
# must now list its resolved versions), and the supervisor's own path (drive_demo; its run records
# must list [], since it installs nothing). Needs (A) up.
T=~/r2exp/verify-f08/v2; OUT=~/r2exp/verify/regress_f08; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; run="systemd-run --user --scope -q python3 -u -m"
step() { local name=$1; shift; local t=$(date +%s); timeout 2400 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd "$T" || exit 2
step suites_1 bash experiments/selftests/suites_all.sh "$OUT/suites_1"
step suites_2 bash experiments/selftests/suites_all.sh "$OUT/suites_2"
cd framework
step egress_nordpool $run confine.endtoend_egress --subject nordpool --corpus $C --python $P --json "$OUT/egress_nordpool.json"
A="$OUT/drive_audit"
systemd-run --user --scope -q python3 -u -m confine.supervise --component ../experiments/flood/demo_flood --python $P --audit-dir "$A" > "$OUT/supervise.log" 2>&1 &
for _ in $(seq 120); do grep -q "started (run 1" "$OUT/supervise.log" && break; sleep 1; done; sleep 10
step drive_demo env PYTHONPATH=. python3 ../experiments/flood/drive_demo.py "$OUT/supervise.log" "$A"
sup=$(grep -o "durable log [^;]*" "$OUT/supervise.log" | head -1 | sed 's/.*decisions-[0-9T]*-\([0-9]*\)\.jsonl/\1/')
[ -n "$sup" ] && kill -TERM "$sup"; sleep 5
step resolved python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1]); ok = True
reports = json.loads((out / "egress_nordpool.json").read_text())["reports"]
for arm, report in reports.items():
    runs = [r for r in report.get("durable_raw") or [] if r.get("kind") == "run"]
    for r in runs:
        resolved = r["identity"].get("resolved")
        good = isinstance(resolved, list) and len(resolved) > 0 and all("==" in x for x in resolved)
        ok &= good
        print(f"nordpool arm {arm}: {'ok  ' if good else 'FAIL'} {len(resolved or [])} resolved, e.g. {(resolved or [])[:3]}")
for log in sorted((out / "drive_audit").glob("decisions*.jsonl")):
    for line in log.read_text().splitlines():
        r = json.loads(line)
        if r.get("kind") == "run":
            good = r["identity"].get("resolved") == []
            ok &= good
            print(f"supervisor run: {'ok  ' if good else 'FAIL'} resolved={r['identity'].get('resolved')}")
sys.exit(0 if ok else 1)
PY
echo ALLDONE >> "$S"
