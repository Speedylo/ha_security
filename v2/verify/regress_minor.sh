#!/bin/bash
# The regression for F10, F13 and F14 (notes/minor_findings_prediction.md), on a fresh clone of
# verify-2026-10-minor (~/r2exp/verify-minor): every suite twice, then nordpool end to end twice. The two
# installs must resolve identical versions (F13), each result must have its .run.json (F14), and the
# resolved list is compared with the unpinned run of verify-2026-10-f08. Needs (A) up.
T=~/r2exp/verify-minor/v2; OUT=~/r2exp/verify/regress_minor; mkdir -p "$OUT"; S="$OUT/summary.txt"; : > "$S"
P=~/r2exp/ha314/bin/python; C=~/r2exp/corpus; run="systemd-run --user --scope -q python3 -u -m"
step() { local name=$1; shift; local t=$(date +%s); timeout 2400 "$@" > "$OUT/$name.log" 2>&1; echo "$name exit=$? seconds=$(( $(date +%s) - t ))" >> "$S"; }
cd "$T" || exit 2
step suites_1 bash experiments/selftests/suites_all.sh "$OUT/suites_1"
step suites_2 bash experiments/selftests/suites_all.sh "$OUT/suites_2"
cd framework
step nordpool_1 $run confine.endtoend_egress --subject nordpool --corpus $C --python $P --json "$OUT/nordpool_1.json"
step nordpool_2 $run confine.endtoend_egress --subject nordpool --corpus $C --python $P --json "$OUT/nordpool_2.json"
step pinned python3 - "$OUT" ~/r2exp/verify/regress_f08/egress_nordpool.json <<'PY'
import json, sys
from pathlib import Path
out, unpinned = Path(sys.argv[1]), Path(sys.argv[2])
def resolved(path):
    reports = json.loads(Path(path).read_text())["reports"]
    lists = {arm: [r["identity"].get("resolved") for r in rep.get("durable_raw") or [] if r.get("kind") == "run"]
             for arm, rep in reports.items()}
    before = {arm: (rep.get("install") or {}).get("resolved_before") for arm, rep in reports.items()}
    return lists, before
ok = True
(l1, b1), (l2, b2) = resolved(out / "nordpool_1.json"), resolved(out / "nordpool_2.json")
same = l1 == l2 and all(l1.values())
ok &= same
print(f"{'ok  ' if same else 'FAIL'} two pinned installs resolve identical versions "
      f"({ {a: len(v[0]) for a, v in l1.items()} })")
pinned_ok = set(b1.values()) == {"2026-10-06T00:00:00Z"} == set(b2.values())
ok &= pinned_ok
print(f"{'ok  ' if pinned_ok else 'FAIL'} each install records the moment it resolved against: {b1}")
for name in ("nordpool_1.json", "nordpool_2.json"):
    rec = out / (name + ".run.json")
    has = rec.exists() and "--subject" in json.loads(rec.read_text())["argv"]
    ok &= has
    print(f"{'ok  ' if has else 'FAIL'} {name} has its run record with the command line")
lu, _ = resolved(unpinned)
a = next(iter(l1)); p, u = set(l1[a][0]), set(lu.get(a, [[]])[0])
print(f"note against the unpinned run of verify-2026-10-f08: {len(p - u)} pinned-only, {len(u - p)} unpinned-only")
for x in sorted(p ^ u):
    print(f"       {'pinned  ' if x in p else 'unpinned'} {x}")
sys.exit(0 if ok else 1)
PY
echo ALLDONE >> "$S"
