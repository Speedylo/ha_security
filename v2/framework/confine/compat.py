"""Run real community integrations through the sandbox, one at a time, and classify what happens.

This is §5.6.5's second re-decision trigger, and §6.11.3 calls it the one most likely to fire:

    "Real community integrations fail against a minimal instance for reasons a *fuller*
     instance would fix" — which would mean the stripping, not the architecture, is what
     breaks compatibility, and R1 would then be no worse.

**A pass/fail number would be useless here, and worse than useless if quoted.** An integration
that fails to import because a package it depends on was never installed has said nothing about
R2. So every failure is classified by *what* failed, and the classification is the result:

    dependency_missing      a package in the integration's own `requirements` is absent.
                            §6.11.2's dependency-installation gap, not a confinement finding
    needs_component         it imports `homeassistant.components.X` for some X the minimal
                            instance does not have. **This is the trigger.**
    interpreter             a syntax or version error — the integration does not support the
                            Python or Home Assistant release under test
    other                   anything else, reported verbatim rather than bucketed

§3.5's N2 requires "executed end-to-end" be reported separately from "imports-clean", so the
run reports levels rather than a verdict: found, imports_clean, platforms_clean.

Run:  systemd-run --user --scope -q python3 -m confine.compat \\
          --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from .cgroup import Delegation, SandboxCgroup
from .channel import Channel
from .manifest import Manifest
from .mediator import Mediator
from .platform import Platform, acting_policy
from .preflight import require_ready
from .sandbox import SandboxSpec
from .selftest_bridge import interpreter_trees
from .spawn import Sandbox, SandboxFailed, become_subreaper, start

HERE = Path(__file__).resolve().parent

MODULE_RE = re.compile(r"No module named '([^']+)'")

# Where an integration's own dependencies appear inside its sandbox. §5.2 records that Home
# Assistant installs an integration's `requirements` at setup; under R2 they belong to the
# sandbox and to nothing else, so each gets its own directory and no two share one.
DEPS = "/sandbox/deps"


def install_requirements(requirements: list[str], target: Path, python: Path,
                         uv: str, timeout: int = 300) -> dict:
    """Install an integration's declared dependencies into a directory of its own.

    Faithful to the design rather than convenient for the test: §5.2 has Home Assistant
    installing `requirements` at setup, and under R2 that install belongs inside the sandbox.
    Doing it per integration rather than into one shared directory also means an integration
    cannot see another's dependencies, which a shared directory would quietly grant.
    """
    target.mkdir(parents=True, exist_ok=True)
    if not requirements:
        return {"ok": True, "installed": [], "note": "no requirements declared"}
    proc = subprocess.run(
        [uv, "pip", "install", "--quiet", "--python", str(python),
         "--target", str(target), *requirements],
        capture_output=True, text=True, timeout=timeout)
    installed = sorted(p.name.split("-")[0] for p in target.glob("*.dist-info"))
    if proc.returncode != 0:
        return {"ok": False, "installed": installed,
                "error": (proc.stderr or proc.stdout).strip().splitlines()[-1][:200]
                if (proc.stderr or proc.stdout).strip() else "install failed"}
    # The resolved set, which is what §6.8.1 says the third identity component needs and does
    # not yet have. Recorded here so that gap can be closed from a real measurement.
    return {"ok": True, "installed": installed,
            "resolved": sorted(p.name.removesuffix(".dist-info")
                               for p in target.glob("*.dist-info"))}


def component_requirements(names: list[str], ha_components: Path | None) -> list[str]:
    """The packages Home Assistant would install for each component, from its own manifests.

    A real installation does not ship its components' dependencies; it installs them when the
    component is set up (`homeassistant.requirements`). So a sandbox that sets up `mqtt`
    without `paho-mqtt` is not a fuller instance, it is a differently broken one — and arm B
    would measure the packaging rather than the architecture if this were skipped.
    """
    if ha_components is None:
        return []
    wanted: list[str] = []
    for name in names:
        manifest = ha_components / name / "manifest.json"
        try:
            data = json.loads(manifest.read_text())
        except (OSError, ValueError):
            continue
        wanted += list(data.get("requirements") or [])
        # One level of transitive component dependency, which is where `frontend` and
        # `websocket_api` come from. Deeper than that and the set is most of the platform.
        for nested in (data.get("dependencies") or []):
            nested_manifest = ha_components / nested / "manifest.json"
            try:
                wanted += list(json.loads(nested_manifest.read_text())
                               .get("requirements") or [])
            except (OSError, ValueError):
                continue
    return sorted(set(wanted))


def find_ha_components(python: Path) -> Path | None:
    """Locate `homeassistant/components` inside the interpreter the sandbox will run."""
    for lib in sorted(python.parent.parent.glob("lib/python*/site-packages")):
        candidate = lib / "homeassistant" / "components"
        if candidate.is_dir():
            return candidate
    return None


def declared_requirements(component: Path) -> list[str]:
    try:
        return list(json.loads((component / "manifest.json").read_text())
                    .get("requirements", []) or [])
    except (OSError, ValueError):
        return []


def classify(entry: dict) -> tuple[str, str]:
    """Turn one failure into a category and the detail that justifies it.

    The order matters and encodes an argument. A missing Python module is not automatically a
    packaging problem: Home Assistant installs a component's `requirements` when that component
    is set up, so an integration that declares `dependencies: ["mqtt"]` gets `paho-mqtt`
    *because mqtt was set up*. In a minimal instance it is not, and the module is missing. That
    failure belongs to §5.6.5's second trigger — "fails for reasons a fuller instance would
    fix" — and calling it a packaging gap would hide the finding.
    """
    level = entry.get("level")
    if level in ("imports_clean", "platforms_clean"):
        return "ok", ""

    text = entry.get("error", "") or ""
    if not text and entry.get("platform_errors"):
        text = "; ".join(f"{k}: {v}" for k, v in entry["platform_errors"].items())

    modules = MODULE_RE.findall(text)
    declared_components = [c for c in (entry.get("dependencies") or [])
                           + (entry.get("after_dependencies") or [])]
    declared_packages = {
        r.split("==")[0].split(">=")[0].split("<")[0].split("[")[0].strip().lower().replace("-", "_")
        for r in entry.get("requirements", [])}
    installed = {i.lower().replace("-", "_") for i in
                 (entry.get("install", {}) or {}).get("installed", [])}

    for module in modules:
        root = module.split(".")[0]
        if module.startswith("homeassistant.components."):
            return "needs_component", module.split(".")[2]
        key = root.lower().replace("-", "_")
        if key in declared_packages and key not in installed:
            return "dependency_install_failed", root
        if declared_components:
            # It declares components it did not get. Those components' own requirements are
            # where this module would have come from in a full installation.
            return "needs_component", f"{root} <- {'/'.join(declared_components[:3])}"
        return "undeclared_dependency", root

    if modules:
        return "dependency_install_failed", modules[0].split(".")[0]
    if "SyntaxError" in text or "requires Python" in text:
        return "interpreter", text[:80]
    return "other", text[:120]


def run_one(domain: str, component: Path, corpus_root: Path, sandbox_python: Path,
            delegation: Delegation, uv: str | None,
            setup_components: list[str] | None = None,
            extra_requirements: list[str] | None = None) -> dict:
    """One integration, one sandbox. Nothing is shared between them but the corpus on disk."""
    root = Path(tempfile.mkdtemp(prefix=f"compat-{domain}-"))
    mediator = Mediator()
    try:
        own = root / "custom_components" / domain
        own.parent.mkdir(parents=True)
        shutil.copytree(component, own)
        data = root / ".confine" / domain
        data.mkdir(parents=True)

        install = {"ok": True, "installed": [], "note": "not attempted"}
        deps_dir = root / "deps"
        if uv:
            try:
                install = install_requirements(
                    declared_requirements(component) + list(extra_requirements or []),
                    deps_dir, sandbox_python, uv)
            except (subprocess.TimeoutExpired, OSError) as err:
                install = {"ok": False, "installed": [], "error": str(err)[:200]}
        deps_dir.mkdir(parents=True, exist_ok=True)

        manifest = Manifest.load(own, root)
        mediator.policy = acting_policy({domain: manifest}, Platform())
        mediator_end, sandbox_end = Channel.pair()
        mediator.register(domain, Channel(mediator_end))

        spec_file = root / "sandbox-spec.json"
        spec_file.write_text(json.dumps({
            "domain": domain, "mode": "inspect", "entities": [], "services": [],
            "setup_components": setup_components or []}))
        spec = SandboxSpec(
            domain=domain, own_dir=str(own), data_dir=str(data),
            argv=[str(sandbox_python), "/sandbox/runtime.py"],
            runtime_files={str(HERE / "sandbox_runtime.py"): "/sandbox/runtime.py",
                           str(spec_file): "/sandbox/spec.json",
                           str(deps_dir): DEPS},
            env={"PYTHONPATH": DEPS})
        for extra in (*interpreter_trees(sandbox_python), sys.base_prefix):
            if extra and extra not in spec.runtime_paths:
                spec.runtime_paths.append(extra)

        out = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        err = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        with SandboxCgroup.create(delegation, f"compat-{domain}"[:60],
                                  memory_max=640 * 1024**2, pids_max=64) as cgroup:
            with open(out.name, "wb") as stdout, open(err.name, "wb") as stderr:
                sandbox: Sandbox = start(spec, cgroup, stdout=stdout.fileno(),
                                         stderr=stderr.fileno(),
                                         channel_end=sandbox_end.fileno())
                sandbox_end.detach()
                mediator.serve(timeout=180)
                status = sandbox.wait(timeout=180)
            oom, peak = cgroup.event_count("oom_kill"), cgroup.peak_memory()
        text = Path(out.name).read_text().strip()
        diagnostic = Path(err.name).read_text().strip()
        Path(out.name).unlink(missing_ok=True)
        Path(err.name).unlink(missing_ok=True)
    except (SandboxFailed, OSError, TimeoutError) as err:
        return {"domain": domain, "level": "sandbox_failed", "error": str(err)[:200]}
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if not text:
        return {"domain": domain, "level": "no_report", "oom": oom, "status": status,
                "install": install,
                "error": diagnostic.splitlines()[-1][:200] if diagnostic else ""}
    report = json.loads(text.splitlines()[-1])
    if "fatal" in report:
        return {"domain": domain, "level": "fatal", "install": install,
                "error": report["fatal"].splitlines()[-1][:200]}
    report["oom"] = oom
    report["peak_mb"] = round(peak / 2**20, 1)
    report["install"] = install
    report["setup_components"] = setup_components or []
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--uv", default=str(Path.home() / ".local/bin/uv"),
                    help="uv, used to install each integration's declared requirements into a "
                         "directory of its own (§5.2). --no-install skips it")
    ap.add_argument("--no-install", action="store_true")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    require_ready(deep=False)
    become_subreaper()
    delegation = Delegation.discover()
    sandbox_python = Path(args.python)

    uv = None if args.no_install else args.uv
    if uv and not Path(uv).exists():
        print(f"no uv at {uv}; dependencies will not be installed", file=sys.stderr)
        uv = None
    components = sorted(p for p in args.corpus.iterdir() if p.is_dir())
    if args.limit:
        components = components[: args.limit]

    print(f"compatibility — {len(components)} community integrations, one sandbox each\n")
    print("  ARM A — the minimal instance §6.3.2 measured\n")
    results = []
    for index, component in enumerate(components, 1):
        report = run_one(component.name, component, args.corpus, sandbox_python,
                         delegation, uv)
        category, detail = classify(report)
        report["category"] = category
        results.append(report)
        mark = "ok  " if category == "ok" else "    "
        print(f"  [{index:2}/{len(components)}] {mark}{component.name:<24} "
              f"{report.get('level', '?'):<24} {category:<26} {detail[:30]}")

    def summarise(rows: list[dict], label: str) -> dict:
        levels = Counter(r.get("level") for r in rows)
        clean = levels["imports_clean"] + levels["platforms_clean"]
        n = max(len(rows), 1)
        print(f"\n  {label}")
        print(f"    imports-clean or better   {clean:3}/{len(rows)}   {clean * 100 / n:.0f}%")
        print(f"    platforms-clean           {levels['platforms_clean']:3}/{len(rows)}   "
              f"{levels['platforms_clean'] * 100 / n:.0f}%")
        peaks = [r["peak_mb"] for r in rows if r.get("peak_mb")]
        if peaks:
            peaks.sort()
            print(f"    peak memory               median {peaks[len(peaks) // 2]:.0f} MB, "
                  f"max {peaks[-1]:.0f} MB")
        return {"clean": clean, "n": len(rows), "levels": dict(levels)}

    arm_a = summarise(results, "arm A")
    categories = Counter(r["category"] for r in results)
    print()
    for category, count in categories.most_common():
        if category != "ok":
            print(f"    {category:<26} {count:3}")

    # ---- ARM B ---------------------------------------------------------------------
    # Everything that failed because the instance was minimal, retried with the components
    # it declared. §5.6.5's trigger asks whether a *fuller* instance would fix these; this
    # answers it by making the instance fuller and looking, rather than by reasoning.
    retry = [r for r in results if r["category"] == "needs_component"]
    arm_b: list[dict] = []
    if retry:
        print(f"\n  ARM B — the same {len(retry)}, with the components they declare\n")
        by_domain = {c.name: c for c in components}
        ha_components = find_ha_components(sandbox_python)
        for index, row in enumerate(retry, 1):
            wanted = list(dict.fromkeys((row.get("dependencies") or [])
                                        + (row.get("after_dependencies") or [])))
            extra = component_requirements(wanted, ha_components)
            report = run_one(row["domain"], by_domain[row["domain"]], args.corpus,
                             sandbox_python, delegation, uv, setup_components=wanted,
                             extra_requirements=extra)
            category, detail = classify(report)
            report["category"] = category
            report["arm"] = "B"
            arm_b.append(report)
            mark = "ok  " if category == "ok" else "    "
            failed_setup = [k for k, v in (report.get("components_setup") or {}).items()
                            if v is not True]
            print(f"  [{index:2}/{len(retry)}] {mark}{row['domain']:<24} "
                  f"{report.get('level', '?'):<24} {category:<26} "
                  f"{('components failed: ' + ','.join(failed_setup[:2])) if failed_setup else detail[:30]}")
        summarise(arm_b, "arm B")

    print(f"\n  §5.6.5 trigger 2 — 'real integrations fail for reasons a fuller instance "
          f"would fix'")
    print(f"    failed on the minimal instance for that reason: {len(retry)}/{len(results)}")
    if arm_b:
        fixed = sum(1 for r in arm_b if r["category"] == "ok")
        print(f"    fixed by setting up their declared components: {fixed}/{len(arm_b)}")
        print(f"    -> the trigger {'FIRES' if fixed else 'does not fire'}: a fuller instance "
              f"{'does' if fixed else 'does not'} fix them")

    if args.json:
        args.json.write_text(json.dumps({"arm_a": results, "arm_b": arm_b}, indent=2) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
