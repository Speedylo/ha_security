"""Install every evaluated integration's dependencies with the new installer; compare with the record."""
import json, sys, tempfile, shutil
from pathlib import Path
from confine.compat import install_requirements, declared_requirements, declared_components_of, component_requirements, find_ha_components
from confine.spawn import become_subreaper

python = Path.home() / "r2exp/ha314/bin/python"
uv = str(Path.home() / ".local/bin/uv")
rec_dir = Path(sys.argv[1])
become_subreaper()
out = []
for record, corpus, arm in (("c1_declared_core.json", "corpus", "arm_a"), ("uniform_confined.json", "corpus_uniform", None)):
    d = json.load(open(rec_dir / record))
    rows = d[arm] if arm else (d.get("arm_a") or d.get("results") or d)
    for row in rows:
        dom = row["domain"]; comp = Path.home() / "r2exp" / corpus / dom
        if not comp.exists():
            out.append({"sample": corpus, "domain": dom, "status": "no corpus dir"}); continue
        wanted = declared_components_of(comp)
        reqs = declared_requirements(comp) + component_requirements(wanted, find_ha_components(python))
        t = Path(tempfile.mkdtemp(prefix="cmp-"))
        try:
            new = install_requirements(reqs, t / "deps", python, uv, timeout=900)
        finally:
            shutil.rmtree(t, ignore_errors=True)
        old = (row.get("install") or {})
        same = sorted(old.get("resolved") or []) == sorted(new.get("resolved") or [])
        out.append({"sample": corpus, "domain": dom, "old_ok": old.get("ok"), "new_ok": new.get("ok"),
                    "same": same, "built": new.get("built_in_sandbox"), "error": new.get("error"),
                    "only_old": sorted(set(old.get("resolved") or []) - set(new.get("resolved") or [])),
                    "only_new": sorted(set(new.get("resolved") or []) - set(old.get("resolved") or []))})
        print(json.dumps(out[-1]), flush=True)
json.dump(out, open("compare_resolved.json", "w"), indent=1)
