"""Share of integrations that build on Home Assistant's helper layer.

Two counts per corpus:
  grep   - any .py file contains the text "homeassistant.helpers" (the 24 Aug method, same
           five patterns, so the result is comparable with 1,356/1,482)
  import - any .py file has a real import statement of homeassistant.helpers or a submodule
           (parsed with ast: comments and strings do not count); a file that fails to parse
           is counted and reported

Usage: python helper_layer.py --root DIR --label NAME --json OUT
"""
import argparse, ast, json, os, platform, socket, sys, time

PATTERNS = ["homeassistant.helpers", "DataUpdateCoordinator", "async_add_entities",
            "hass.data", "hass.states.async_set"]


def imports_helpers(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name == "homeassistant.helpers" or a.name.startswith("homeassistant.helpers.")
                   for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            m = node.module
            if m == "homeassistant.helpers" or m.startswith("homeassistant.helpers."):
                return True
            if m == "homeassistant" and any(a.name == "helpers" for a in node.names):
                return True
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--json", required=True)
    a = p.parse_args()
    dirs = sorted(d for d in os.listdir(a.root)
                  if os.path.isdir(os.path.join(a.root, d)) and not d.startswith((".", "__")))
    per, grep_n, imp_n, failed = {}, {k: 0 for k in PATTERNS}, 0, []
    for d in dirs:
        texts, imp, hits = [], False, set()
        for base, _, files in os.walk(os.path.join(a.root, d)):
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(base, f)
                src = open(path, encoding="utf-8", errors="replace").read()
                hits |= {k for k in PATTERNS if k in src}
                try:
                    imp = imp or imports_helpers(ast.parse(src))
                except SyntaxError:
                    failed.append(os.path.relpath(path, a.root))
        for k in hits:
            grep_n[k] += 1
        imp_n += imp
        per[d] = {"grep": sorted(hits), "imports_helpers": imp}
    n = len(dirs)
    out = {
        "label": a.label, "root": a.root, "n_directories": n,
        "grep": {k: {"n": v, "share": round(100 * v / n, 1)} for k, v in grep_n.items()},
        "imports_helpers": {"n": imp_n, "share": round(100 * imp_n / n, 1)},
        "unparseable_files": failed,
        "without_helper_import": [d for d in dirs if not per[d]["imports_helpers"]],
        "per_integration": per,
        "run": {"argv": sys.argv, "python": platform.python_version(), "host": socket.gethostname(),
                "machine": platform.machine(), "time": time.strftime("%Y-%m-%dT%H:%M:%S%z")},
    }
    json.dump(out, open(a.json, "w"), indent=1)
    print(a.label, "n =", n)
    for k, v in out["grep"].items():
        print(f"  grep {k:24} {v['n']:5}  {v['share']}%")
    print(f"  import homeassistant.helpers   {imp_n:5}  {out['imports_helpers']['share']}%")
    print("  unparseable files:", len(failed))
    print("  without a helper import:", out["without_helper_import"][:20])


if __name__ == "__main__":
    main()
