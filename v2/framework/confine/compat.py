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
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import replace
from pathlib import Path

from .audit import attach
from .audit import summarise as durable_summary
from .cgroup import Delegation, SandboxCgroup
from .channel import Channel
from .manifest import Manifest
from .mediator import Mediator
from .platform import Platform, acting_policy
from .preflight import require_ready
from .sandbox import SandboxSpec
from .integrity import TreeState, compare
from .integrity import summarise as integrity_summary
from .selftest_bridge import interpreter_trees
from .spawn import Sandbox, SandboxFailed, become_subreaper, start

HERE = Path(__file__).resolve().parent

MODULE_RE = re.compile(r"No module named '([^']+)'")

# Where an integration's own dependencies appear inside its sandbox. §5.2 records that Home
# Assistant installs an integration's `requirements` at setup; under R2 they belong to the
# sandbox and to nothing else, so each gets its own directory and no two share one.
DEPS = "/sandbox/deps"
# The platform's own optional components live here. Shared between sandboxes read-only, and
# deliberately: these are Home Assistant's packages, not any integration's, and the sandbox
# already shares the `homeassistant` library itself the same way. An integration's *own*
# dependencies stay in DEPS, one directory per sandbox.
PLATFORM_DEPS = "/sandbox/platform-deps"

# What "un-stripping toward http" means concretely (§6.12). Ordered so a failure is attributable
# to the component that caused it rather than to the cascade behind it.
UNSTRIPPED = ["http", "websocket_api", "frontend", "lovelace", "panel_custom", "repairs",
              "media_source", "notify", "mqtt", "stream"]


def install_requirements(requirements: list[str], target: Path, python: Path,
                         uv: str, timeout: int = 300, compile_bytecode: bool = False) -> dict:
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
         "--target", str(target),
         # W2 (c): `uv` does not compile bytecode by default, and inside the sandbox this tree is
         # read-only, so without it every confined start compiles these modules again.
         *(["--compile-bytecode"] if compile_bytecode else []), *requirements],
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


def core_requirements(ha_components: Path | None,
                      root: str = "default_config") -> list[str]:
    """The packages a *stock* Home Assistant has installed, computed from the platform's source.

    §6.13.2 found that six integrations import `numpy` or `PyTurboJPEG` without declaring
    either, and work in the wild only because some core component dragged those wheels into the
    shared environment. "Some core component" is not a specification, so this makes it one: the
    dependency closure of `default_config` — the component set a default installation sets up —
    and the union of the `requirements` those components declare.

    This is the honest reading of "what an integration may assume is present". It is bounded
    (57 components, 39 packages on 2026.8.3), derived from source rather than typed, and it
    grants nothing an ordinary installation does not already grant. What it costs is that the
    sandbox then contains code no integration declared, which is §5.6.2's whole complaint —
    hence a separate profile and a measurement rather than a default.
    """
    if ha_components is None:
        return []
    seen: set[str] = set()
    stack = [root]
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        try:
            data = json.loads((ha_components / name / "manifest.json").read_text())
        except (OSError, ValueError):
            continue
        seen.add(name)
        stack += (data.get("dependencies") or []) + (data.get("after_dependencies") or [])
    wanted: set[str] = set()
    for name in seen:
        try:
            data = json.loads((ha_components / name / "manifest.json").read_text())
        except (OSError, ValueError):
            continue
        wanted |= set(data.get("requirements") or [])
    return sorted(wanted)


def find_ha_components(python: Path) -> Path | None:
    """Locate `homeassistant/components` inside the interpreter the sandbox will run."""
    for lib in sorted(python.parent.parent.glob("lib/python*/site-packages")):
        candidate = lib / "homeassistant" / "components"
        if candidate.is_dir():
            return candidate
    return None


def declared_components_of(component: Path) -> list[str]:
    """The components an integration says it needs, in manifest order and without duplicates."""
    try:
        data = json.loads((component / "manifest.json").read_text())
    except (OSError, ValueError):
        return []
    return list(dict.fromkeys((data.get("dependencies") or [])
                              + (data.get("after_dependencies") or [])))


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
        # It only counts as a component problem if a component it declared actually failed.
        # Once every declared component sets up and the module is *still* missing, nothing
        # about the instance explains it — the integration imports something neither it nor
        # any component it names provides. An earlier version of this function stopped at
        # "it declares components", which mislabelled six residual failures under the
        # un-stripped profile and would have blamed the design for them.
        setup = entry.get("components_setup") or {}
        # Measured against what the integration *declared*, not against what happened to be
        # attempted. A profile that sets up ten components successfully says nothing about an
        # eleventh the integration asked for and nobody tried.
        unmet = [c for c in declared_components if setup.get(c) is not True]
        if unmet:
            return "needs_component", f"{root} <- {'/'.join(unmet[:3])}"
        return "undeclared_dependency", root

    if modules:
        return "dependency_install_failed", modules[0].split(".")[0]
    if "SyntaxError" in text or "requires Python" in text:
        return "interpreter", text[:80]
    return "other", text[:120]


def run_one(domain: str, component: Path, corpus_root: Path, sandbox_python: Path,
            delegation: Delegation, uv: str | None,
            setup_components: list[str] | None = None,
            extra_requirements: list[str] | None = None,
            profile: str = "minimal", platform_deps: Path | None = None) -> dict:
    """One integration, one sandbox. Nothing is shared between them but the corpus on disk."""
    root = Path(tempfile.mkdtemp(prefix=f"compat-{domain}-"))
    mediator = Mediator()
    # T4: the durable log, engaged and reconciled. Every compatibility figure in this report was
    # produced with decisions recorded only in memory; this is the first run where they are not.
    audit_dir = attach(mediator, f"compat-audit-{domain}-")
    durable: dict = {}
    integrity = None
    try:
        own = root / "custom_components" / domain
        own.parent.mkdir(parents=True)
        shutil.copytree(component, own)
        # §7.28 / C1. What runs here is the copy, and `sandbox.py` mounts it read-only, so the
        # tree to re-hash afterwards is the **copy** and not the fetched original — diffing the
        # original would compare a tree nothing opened. Retention is unnecessary because the
        # two are distinct directories and both still exist at comparison time.
        original = TreeState.capture(component)
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
        mediator.register(domain, Channel(mediator_end), component=own, installed=deps_dir)

        spec_file = root / "sandbox-spec.json"
        components = list(setup_components or [])
        if profile == "unstripped":
            components = UNSTRIPPED + [c for c in components if c not in UNSTRIPPED]
        spec_file.write_text(json.dumps({
            "domain": domain, "mode": "inspect", "entities": [], "services": [],
            # The authentication manager is wired for every profile but the bare minimal one.
            # §6.12.3 measured it at 0.1 MB, and without it `http` cannot set up at all — which
            # is why the first per-integration arm reached 57% rather than what it should have.
            "auth": profile in ("unstripped", "declared"),
            # §7.18: record what each integration tries to reach at import, so the demand for
            # an egress proxy is measured rather than inferred from `iot_class` alone.
            "record_egress": True,
            "setup_components": components}))
        spec = SandboxSpec(
            domain=domain, own_dir=str(own), data_dir=str(data),
            argv=[str(sandbox_python), "/sandbox/runtime.py"],
            runtime_files={str(HERE / "sandbox_runtime.py"): "/sandbox/runtime.py",
                           str(spec_file): "/sandbox/spec.json",
                           str(deps_dir): DEPS},
            env={"PYTHONPATH": DEPS})
        # Bound for any profile that was given one, not only `unstripped`. §6.13.4's
        # measurement is `declared` plus this directory, and the two are independent knobs:
        # one decides which components set up, the other which packages exist.
        if platform_deps:
            spec.runtime_files[str(platform_deps)] = PLATFORM_DEPS
            spec.env["PYTHONPATH"] = f"{DEPS}:{PLATFORM_DEPS}"
        for extra in (*interpreter_trees(sandbox_python), sys.base_prefix):
            if extra and extra not in spec.runtime_paths:
                spec.runtime_paths.append(extra)

        out = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        err = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        # §7.22: the bound applied here is the integration's own `resources` clause where it
        # declares one, and the framework's default where it does not. Until §7.21.1 this was
        # a literal, so every figure in §6.11–§6.14 was measured against the harness's limit
        # rather than the declaration — which is what made S9 unverifiable from the outside.
        limits = manifest.resources
        spec.tmp_size_mb = limits.disk_mb
        with SandboxCgroup.create(delegation, f"compat-{domain}"[:60], limits) as cgroup:
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
        # Before the `finally` removes the copy. A source change here would not be a C1
        # finding but a containment one: it would mean the read-only mount held nothing.
        integrity = compare(original, TreeState.capture(own)).as_dict()
    except (SandboxFailed, OSError, TimeoutError) as err:
        return {"domain": domain, "level": "sandbox_failed", "error": str(err)[:200]}
    finally:
        shutil.rmtree(root, ignore_errors=True)
        durable = durable_summary(mediator, audit_dir)

    if not text:
        return {"domain": domain, "level": "no_report", "oom": oom, "status": status,
                "install": install, "integrity": integrity, "durable": durable,
                "error": diagnostic.splitlines()[-1][:200] if diagnostic else ""}
    report = json.loads(text.splitlines()[-1])
    if "fatal" in report:
        return {"domain": domain, "level": "fatal", "install": install,
                "integrity": integrity, "durable": durable,
                "error": report["fatal"].splitlines()[-1][:200]}
    report["integrity"] = integrity
    report["durable"] = durable
    report["oom"] = oom
    report["peak_mb"] = round(peak / 2**20, 1)
    report["install"] = install
    report["setup_components"] = setup_components or []
    report["profile"] = profile
    return report


def run_one_baseline(domain: str, component: Path, sandbox_python: Path,
                     uv: str | None, platform_deps: Path | None = None,
                     setup_components: list[str] | None = None,
                     extra_requirements: list[str] | None = None,
                     timeout: int = 600) -> dict:
    """One integration against a full, **unconfined** Home Assistant. §7.4.1's baseline arm.

    Structurally parallel to `run_one` and deliberately so: same corpus copy, same dependency
    installation, same measurement function, same result shape. What is absent is the whole
    of the confinement — no namespaces, no seccomp, no cgroup, no mount view, no mediator and
    no bridge. That absence is the independent variable, and it is the only one.

    **The declared components are set up here as well, and the first version of this function
    did not do that.** `default_config` is what a stock installation sets up, but it does not
    contain `mqtt`, so `alarmo` — which declares it — failed against the "full" instance while
    passing under confinement, where the `declared` profile sets up exactly what the manifest
    asks for. A baseline stingier than the arm it is being compared against does not decompose
    the figure, it inverts it. What a real installation running this integration looks like is
    a stock install *plus* whatever that integration needs, so that is what this builds.
    """
    root = Path(tempfile.mkdtemp(prefix=f"baseline-{domain}-"))
    try:
        deps_dir = root / "deps"
        install = {"ok": True, "installed": [], "note": "not attempted"}
        if uv:
            try:
                install = install_requirements(
                    declared_requirements(component) + list(extra_requirements or []),
                    deps_dir, sandbox_python, uv)
            except (subprocess.TimeoutExpired, OSError) as err:
                install = {"ok": False, "installed": [], "error": str(err)[:200]}
        deps_dir.mkdir(parents=True, exist_ok=True)

        config_dir = root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        spec_file = root / "baseline-spec.json"
        spec_file.write_text(json.dumps({
            "domain": domain,
            "config_dir": str(config_dir),
            "component_dir": str(component),
            "setup_components": (["homeassistant", "default_config"]
                                 + [c for c in (setup_components or [])
                                    if c not in ("homeassistant", "default_config")]),
        }))

        # Both runtime files are copied beside each other and run from there, which mirrors
        # what the sandbox does — it binds `sandbox_runtime.py` in as a standalone script at
        # `/sandbox/runtime.py`, not as part of a package. Putting `confine/` on the path
        # instead would shadow the standard library: `confine/platform.py` masks `platform`,
        # which `multidict` imports on the way into `aiohttp`, and Home Assistant then fails
        # to import for a reason that has nothing to do with the integration under test.
        for name in ("sandbox_runtime.py", "baseline_runtime.py"):
            shutil.copy2(HERE / name, root / name)

        path = [str(deps_dir)]
        if platform_deps:
            path.append(str(platform_deps))
        env = {**os.environ, "PYTHONPATH": ":".join(path)}
        # §7.28 / C1, and **this is the arm the check exists for.** The integration is about to
        # be imported by a full, unconfined Home Assistant from the fetched tree itself — no
        # copy, no read-only mount, full authority over its own source. `retain` keeps the
        # pre-run bytes because the comparison is of this directory against itself afterwards,
        # by which time the original content would otherwise be unrecoverable.
        original = TreeState.capture(component, retain=True)
        try:
            proc = subprocess.run(
                [str(sandbox_python), str(root / "baseline_runtime.py"), str(spec_file)],
                capture_output=True, text=True, timeout=timeout, env=env, cwd=str(root))
        except subprocess.TimeoutExpired:
            # Checked on the timeout path too: an integration that hung is not one that can be
            # assumed to have left its source alone.
            return {"domain": domain, "level": "timeout", "install": install,
                    "integrity": compare(original, TreeState.capture(component)).as_dict(),
                    "error": f"exceeded {timeout}s"}
        integrity = compare(original, TreeState.capture(component)).as_dict()
        text = (proc.stdout or "").strip()
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if not text:
        tail = (proc.stderr or "").strip().splitlines()
        return {"domain": domain, "level": "no_report", "install": install,
                "integrity": integrity, "error": tail[-1][:200] if tail else ""}
    try:
        report = json.loads(text.splitlines()[-1])
    except ValueError:
        return {"domain": domain, "level": "no_report", "install": install,
                "integrity": integrity, "error": text.splitlines()[-1][:200]}
    if "fatal" in report:
        return {"domain": domain, "level": "fatal", "install": install,
                "integrity": integrity,
                "error": report["fatal"].strip().splitlines()[-1][:200]}
    report["install"] = install
    report["integrity"] = integrity
    report["profile"] = "baseline"
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
    ap.add_argument("--profile",
                    choices=["minimal", "unstripped", "declared", "baseline"],
                    default="minimal",
                    help="minimal: §6.3.2's instance. unstripped: the blanket ten-component "
                         "profile of §6.12. declared: auth, plus only the components this "
                         "integration's own manifest asks for. baseline: §7.4.1's arm — a "
                         "full, UNCONFINED Home Assistant, which is what decomposes the "
                         "confined figure into the corpus's failures and the design's")
    ap.add_argument("--platform-deps", type=Path,
                    help="a directory of packages bound read-only into every sandbox and shared "
                         "between them, as the `homeassistant` library already is. Combine with "
                         "--profile declared for §6.13.4's measurement")
    ap.add_argument("--print-core-requirements", action="store_true",
                    help="print the default_config closure's requirements and exit, so the "
                         "--platform-deps directory is built from the platform's source rather "
                         "than from a list somebody typed")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    if args.print_core_requirements:
        for requirement in core_requirements(find_ha_components(Path(args.python))):
            print(requirement)
        return 0

    baseline = args.profile == "baseline"
    delegation = None
    if not baseline:
        # None of this applies to the unconfined arm, and requiring it would make the baseline
        # impossible to run on a host that cannot host a sandbox — which would defeat the
        # point of having a baseline at all.
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
    print(f"  ARM A — the {args.profile} instance\n")
    results = []
    for index, component in enumerate(components, 1):
        wanted, extra = [], []
        if args.profile in ("declared", "baseline"):
            wanted = declared_components_of(component)
            extra = component_requirements(wanted, find_ha_components(sandbox_python))
        if baseline:
            report = run_one_baseline(component.name, component, sandbox_python, uv,
                                      platform_deps=args.platform_deps,
                                      setup_components=wanted, extra_requirements=extra)
        else:
            report = run_one(component.name, component, args.corpus, sandbox_python,
                             delegation, uv, profile=args.profile,
                             platform_deps=args.platform_deps,
                             setup_components=wanted, extra_requirements=extra)
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
        key = "peak_rss_mb" if baseline else "peak_mb"
        peaks = [r[key] for r in rows if r.get(key)]
        if peaks:
            peaks.sort()
            note = " (RSS, not comparable to cgroup peak)" if baseline else ""
            print(f"    peak memory               median {peaks[len(peaks) // 2]:.0f} MB, "
                  f"max {peaks[-1]:.0f} MB{note}")
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
    # Arm B asks whether a *fuller* instance fixes a failure. The baseline instance is
    # already as full as a stock installation gets, so there is nothing to make fuller and the
    # retry would measure nothing.
    retry = ([] if baseline else
             [r for r in results if r["category"] == "needs_component"])
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
                             extra_requirements=extra, profile=args.profile,
                             platform_deps=args.platform_deps)
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

    # ---- C1 ------------------------------------------------------------------------
    # §7.28 / §8.7 #4. Until this ran, C1 rested on reading two lines of the harness: that the
    # confined arm copies and mounts read-only, and that no modification had ever been
    # observed. Neither is a count, and §7.4.1 had claimed one for months.
    # T4 — the durable record beside the in-memory one, for every sandbox that ran.
    logged = [r.get("durable") for r in results + arm_b if r.get("durable")]
    if logged:
        bad = [r["domain"] for r in results + arm_b if r.get("durable") and not r["durable"]["ok"]]
        print(f"\n  S7 — the durable audit log, engaged ({len(logged)} sandboxes)")
        print(f"    run records                       {sum(d['runs'] for d in logged)}")
        print(f"    decisions recorded durably        {sum(d['decisions'] for d in logged)}")
        print(f"    chains or reconciliation failing  {len(bad)} {bad[:6] if bad else ''}")

    c1 = integrity_summary(results + arm_b)
    print(f"\n  C1 — integrations run unmodified ({'baseline' if baseline else 'confined'} arm)")
    if not c1["integrations_checked"]:
        print("    no tree was hashed — the check did not run")
    else:
        print(f"    trees hashed before and after     {c1['integrations_checked']}")
        print(f"    with changed source               {c1['source_changed']}")
        print(f"    total diff lines                  {c1['total_diff_lines']}")
        print(f"    trees that gained bytecode only   {c1['trees_gaining_bytecode']}")
        if c1["lines_unknown"]:
            print(f"    ** files whose lines could not be counted: {c1['lines_unknown']}")
        if c1["domains_with_changes"]:
            print(f"    ** CHANGED: {', '.join(c1['domains_with_changes'])}")
            if not baseline:
                print("    ** in the confined arm this is a containment failure, not a "
                      "compatibility one: the copy is mounted read-only")

    if args.json:
        args.json.write_text(json.dumps(
            {"arm_a": results, "arm_b": arm_b, "c1": c1}, indent=2) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
