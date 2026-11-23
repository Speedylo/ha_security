"""Per-integration comparison of a confined compat run with final2's (1 Nov). Exit 0 iff no difference."""
import json, sys

def key(e):
    return {"level": e["level"], "platforms": sorted(e.get("platforms") or []),
            "components_setup": e.get("components_setup"),
            "egress": sorted({(a.get("kind"), a.get("host"), a.get("port")) for a in e.get("egress_attempts") or []}),
            "oom": e.get("oom"), "durable_ok": (e.get("durable") or {}).get("ok"),
            "source_changed": (e.get("integrity") or {}).get("source_changed")}

old, new = (json.load(open(p)) for p in sys.argv[1:3])
diffs = 0
for arm in ("arm_a", "arm_b"):
    o = {e["domain"]: e for e in old.get(arm) or []}; n = {e["domain"]: e for e in new.get(arm) or []}
    for d in sorted(set(o) | set(n)):
        if d not in o or d not in n:
            print(f"{arm} {d}: only in {'new' if d in n else 'final2'}"); diffs += 1; continue
        ko, kn = key(o[d]), key(n[d])
        changed = {k: (ko[k], kn[k]) for k in ko if ko[k] != kn[k]}
        if changed:
            diffs += 1; print(f"{arm} {d}: " + "; ".join(f"{k} {a} -> {b}" for k, (a, b) in changed.items()))
        blob = json.dumps(n[d])
        if "Operation not permitted" in blob or "EPERM" in blob:
            print(f"{arm} {d}: note: 'Operation not permitted' appears in the new record")
    print(f"{arm}: {len(n)} integrations, levels " + ", ".join(f"{l} {sum(1 for e in n.values() if e['level']==l)}" for l in sorted({e['level'] for e in n.values()})))
print(f"c1 final2 {old.get('c1')}\nc1 new    {new.get('c1')}")
print(f"DIFFERENCES {diffs}")
sys.exit(1 if diffs else 0)
