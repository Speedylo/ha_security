"""F2 against a real integration's real API — §7.25's synthetic coordinator, replaced.

§7.25 evaluated F2 and S4 with two purpose-built coordinators polling `example.com` and
`example.net` from inside real namespaces, and §7.25.5 stated the limit in its own words:

    Whether the egress path holds up against a real community integration's actual API
    (rather than a synthetic coordinator polling a stable IANA host) is a different, larger
    measurement that §7.10's schedule did not include and this section does not substitute for.

This is that measurement, on the one integration in the head corpus that makes it possible.

**Why `nordpool`, and why the selection is not a convenience.** §7.17.1 measured the ceiling on
any end-to-end arm: 26 of 37 integrations need an API key, token, password, username, host or
email before their own config flow can complete, and an unconfined baseline meets the identical
wall. The eleven that need none are overwhelmingly the ones that need no network either — three
of §7.17's five declare `iot_class: calculated`, which is why that section could not see egress
at all (§7.18). `nordpool` is the intersection: **`cloud_polling`, and configurable from a price
region alone.** §7.24 recorded it completing its own flow unconfined, reaching
`dataportal-api.nordpoolgroup.com:443` over TLS with `check_hostname` set, and creating a LOADED
config entry — on `region` and `currency` and nothing else. It has exactly one endpoint, declared
once in `aio_price.py`, so the manifest clause is a fact about the integration rather than a guess.

**Three arms, because two would not settle the question.**

    A  unconfined baseline      is it working at all today, on this release and this host?
    B  confined, host declared  does it work through the mediator's egress path?
    C  confined, clause absent  does removing the grant remove the capability?

Arm C is the one that makes arm B evidence. §6.4.5's rule is that an absence is not proof
confinement worked until the grant is shown to have arrived; the converse binds just as hard
here — **a success is not proof the mediator supplied the connection unless withdrawing the
declaration withdraws it.** Without arm C, a sandbox whose network namespace had silently leaked
would produce exactly arm B's result. With it, the difference between B and C is the mediated
path and nothing else: same integration, same flow input, same profile, same host, same minute.

The evidence for C's denial is the **mediator's own audit record**, not the sandbox's report of
itself, on §7.25.2's reasoning that a confined process is the party whose self-report should not
be trusted for this.

Run, on the C4 device, inside a systemd user scope:

    systemd-run --user --scope -q python3 -m confine.endtoend_egress \\
        --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python \\
        --json ~/capstone/v2/experiments/end_to_end/results/pi5_nordpool_egress.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import replace
from pathlib import Path

from .audit import AuditLog
from .cgroup import Delegation, SandboxCgroup
from .channel import Channel
from .compat import (DEPS, PLATFORM_DEPS, component_requirements, core_requirements,
                     declared_components_of, declared_requirements, find_ha_components,
                     install_requirements)
from .egress import EgressBroker
from .manifest import Manifest
from .mediator import Mediator
from .platform import Platform, acting_policy
from .preflight import require_ready
from .sandbox import SandboxSpec
from .selftest_bridge import interpreter_trees
from .spawn import Sandbox, SandboxFailed, become_subreaper, start
from .udp_relay import UdpRelay

HERE = Path(__file__).resolve().parent

DOMAIN = "nordpool"
HOST = "dataportal-api.nordpoolgroup.com"
PORT = 443

# The integration's own flow input, not the harness's. `region` is `vol.Required` and chosen
# from the integration's own list; everything else in its schema carries a default. Fed to
# `async_configure` exactly as the UI would.
FLOW_INPUT = {"region": "SE1", "currency": "EUR"}

# A coordinator's first fetch is scheduled after `async_start`, not during the flow, so a run
# with no settle window reports only what configuration touched and misses the polling F2 is
# about. §7.25 used 8 s against a static host; a real API over TLS from a Pi wants more.
SETTLE = 25.0

ARMS: dict[str, dict] = {
    "confined_declared": {
        "label": "B  confined, host declared",
        "permissions": {"schema_version": 1,
                        "network": {"egress": [f"{HOST}:{PORT}"]}},
    },
    "confined_undeclared": {
        "label": "C  confined, clause absent",
        "permissions": {"schema_version": 1},
    },
}


def check(results: list, condition: bool, name: str, detail: str = "") -> None:
    results.append(bool(condition))
    print(f"  {'ok  ' if condition else 'FAIL'} {name}")
    if detail and not condition:
        print(f"       {detail}")


def _requirements(component: Path, python: Path) -> tuple[list[str], list[str]]:
    """§6.14.6's recommended profile: what the integration declares, plus the core package set.

    The same profile §7.12 and §7.23 measured, so this arm is comparable with the compatibility
    figures rather than being a fourth thing. Held identical across all three arms.
    """
    ha = find_ha_components(python)
    wanted = declared_components_of(component)
    packages = (declared_requirements(component)
                + component_requirements(wanted, ha)
                + core_requirements(ha))
    return wanted, list(dict.fromkeys(packages))


def run_confined(component: Path, arm: str, python: Path, delegation: Delegation,
                 uv: str | None, platform_deps: Path | None) -> dict:
    root = Path(tempfile.mkdtemp(prefix=f"e2e-egress-{arm}-"))
    # The audit log lives **outside** `root`, because `root` is removed in the `finally` below
    # and the records are read after it. Keeping it inside meant `records()` found an empty
    # directory and reported no decisions at all — a harness fault that presented exactly as
    # "the mediator logged nothing", which is §6.4.5's warning in its most literal form.
    audit_dir = Path(tempfile.mkdtemp(prefix=f"e2e-egress-audit-{arm}-"))
    mediator = Mediator()
    try:
        own = root / "custom_components" / DOMAIN
        own.parent.mkdir(parents=True)
        shutil.copytree(component, own)
        # Beside the integration, never inside its own manifest.json — §5.9.4's provenance
        # rule, and rewriting the integration's file would breach C1.
        (root / "custom_components" / f"{DOMAIN}.permissions.json").write_text(
            json.dumps(ARMS[arm]["permissions"]))
        data = root / ".confine" / DOMAIN
        data.mkdir(parents=True)

        deps = root / "deps"
        wanted, packages = _requirements(component, python)
        install = {"ok": True, "installed": [], "note": "not attempted"}
        if uv:
            try:
                install = install_requirements(packages, deps, python, uv, timeout=900)
            except (subprocess.TimeoutExpired, OSError) as err:
                install = {"ok": False, "installed": [], "error": str(err)[:200]}
        deps.mkdir(parents=True, exist_ok=True)

        # The mediator writes a real audit log here, and the destinations reported below are
        # read back out of it. §7.25.2 took the denial evidence from `mediator.audit` — an
        # in-memory list — which carries the verdict and the clause but not the destination.
        # The durable record carries both, so the strongest available evidence for *which host*
        # was granted is the one S7 already commits to, and taking it from there rather than
        # from a second in-memory structure is what F3 means by attributable.
        mediator.log = AuditLog(path=audit_dir / "decisions.jsonl")
        platform = Platform()
        broker = EgressBroker(connect_timeout=20.0)
        relay = UdpRelay()
        manifest = Manifest.load(own, root)
        mediator.policy = acting_policy({DOMAIN: manifest}, platform,
                                        broker=broker, relay=relay)
        mediator_end, sandbox_end = Channel.pair()
        mediator.register(DOMAIN, Channel(mediator_end))

        spec_file = root / "spec.json"
        spec_file.write_text(json.dumps({
            "domain": DOMAIN, "mode": "flow", "auth": True,
            "entities": [], "services": [], "setup_components": wanted,
            "egress": True, "settle_seconds": SETTLE,
            "menu_choice": {}, "flow_input": FLOW_INPUT}))

        runtime_files = {str(HERE / "sandbox_runtime.py"): "/sandbox/runtime.py",
                         str(HERE / "egress_shim.py"): "/sandbox/egress_shim.py",
                         str(spec_file): "/sandbox/spec.json",
                         str(deps): DEPS}
        spec = SandboxSpec(
            domain=DOMAIN, own_dir=str(own), data_dir=str(data),
            argv=[str(python), "/sandbox/runtime.py"],
            runtime_files=runtime_files, env={"PYTHONPATH": DEPS})
        if platform_deps:
            spec.runtime_files[str(platform_deps)] = PLATFORM_DEPS
            spec.env["PYTHONPATH"] = f"{DEPS}:{PLATFORM_DEPS}"
        for tree in (*interpreter_trees(python), sys.base_prefix):
            if tree and tree not in spec.runtime_paths:
                spec.runtime_paths.append(tree)

        out = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        err = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        limits = replace(manifest.resources, memory_mb=max(manifest.resources.memory_mb, 640))
        spec.tmp_size_mb = limits.disk_mb
        # Explicit lifetime rather than `with`, per §7.25.3: the cgroup must outlive the call
        # that starts the sandbox and be read for `oom_kill` before it is removed.
        cgroup = SandboxCgroup.create(delegation, f"e2e-egress-{arm}"[:60], limits)
        try:
            with open(out.name, "wb") as stdout, open(err.name, "wb") as stderr:
                sandbox: Sandbox = start(spec, cgroup, stdout=stdout.fileno(),
                                         stderr=stderr.fileno(),
                                         channel_end=sandbox_end.fileno())
                sandbox_end.detach()
                mediator.serve(timeout=420)
                sandbox.wait(timeout=420)
            oom = cgroup.event_count("oom_kill")
        finally:
            cgroup.remove()
        text = Path(out.name).read_text().strip()
        diagnostic = Path(err.name).read_text().strip()
        Path(out.name).unlink(missing_ok=True)
        Path(err.name).unlink(missing_ok=True)
    except (SandboxFailed, OSError, TimeoutError) as err:
        return {"arm": arm, "level": "sandbox_failed", "error": str(err)[:300]}
    finally:
        shutil.rmtree(root, ignore_errors=True)

    audit = [{"identity": d.get("identity"), "op": d.get("op"),
              "allowed": d.get("allowed"), "clause": d.get("clause")}
             for d in mediator.audit]
    try:
        logged = [{"op": r.get("op"), "target": r.get("target"), "allowed": r.get("allowed"),
                   "clause": r.get("clause")}
                  for r in (mediator.log.records() if mediator.log is not None else [])
                  if r.get("kind") == "decision"]
        breaks = [str(b) for b in mediator.log.verify(mediator.log.key)] if mediator.log else []
    finally:
        shutil.rmtree(audit_dir, ignore_errors=True)
    if not text:
        tail = diagnostic.splitlines()
        return {"arm": arm, "level": "no_report", "install": install, "audit": audit,
                "logged": logged, "oom_kill": oom, "error": "\n".join(tail[-12:])[:900]}
    report = json.loads(text.splitlines()[-1])
    if "fatal" in report:
        return {"arm": arm, "level": "fatal", "install": install, "audit": audit,
                "logged": logged, "oom_kill": oom, "error": report["fatal"].strip().splitlines()[-1][:300]}
    report["arm"] = arm
    report["install"] = install
    report["audit"] = audit
    report["logged"] = logged
    report["audit_breaks"] = breaks
    report["oom_kill"] = oom
    return report


def run_unconfined(component: Path, python: Path, uv: str | None,
                   platform_deps: Path | None) -> dict:
    """Arm A. Same integration, same flow input, same profile, no sandbox and no mediator."""
    root = Path(tempfile.mkdtemp(prefix="e2e-egress-base-"))
    try:
        config = root / "config"
        (config / "custom_components").mkdir(parents=True)
        shutil.copytree(component, config / "custom_components" / DOMAIN)
        for name in ("sandbox_runtime.py", "endtoend_unconfined.py"):
            shutil.copy2(HERE / name, root / name)

        deps = root / "deps"
        wanted, packages = _requirements(component, python)
        if uv:
            try:
                install_requirements(packages, deps, python, uv, timeout=900)
            except (subprocess.TimeoutExpired, OSError):
                pass
        deps.mkdir(parents=True, exist_ok=True)

        spec_file = root / "spec.json"
        spec_file.write_text(json.dumps({
            "domain": DOMAIN, "config_dir": str(config), "setup_components": wanted,
            "world": {}, "record_egress": True, "settle_seconds": SETTLE,
            "menu_choice": {}, "flow_input": FLOW_INPUT}))

        path = [str(deps)] + ([str(platform_deps)] if platform_deps else [])
        env = {**os.environ, "PYTHONPATH": ":".join(path)}
        try:
            proc = subprocess.run(
                [str(python), str(root / "endtoend_unconfined.py"), str(spec_file)],
                capture_output=True, text=True, timeout=900, env=env, cwd=str(root))
        except subprocess.TimeoutExpired:
            return {"arm": "unconfined", "level": "timeout"}
        text = (proc.stdout or "").strip()
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if not text:
        tail = (proc.stderr or "").strip().splitlines()
        return {"arm": "unconfined", "level": "no_report",
                "error": "\n".join(tail[-12:])[:900]}
    report = json.loads(text.splitlines()[-1])
    if "fatal" in report:
        return {"arm": "unconfined", "level": "fatal",
                "error": report["fatal"].strip().splitlines()[-1][:300]}
    report["arm"] = "unconfined"
    return report


def _priced(report: dict) -> list[dict]:
    """Published sensors carrying a numeric state — the integration's actual output."""
    out = []
    for entry in report.get("published") or []:
        state = entry.get("state")
        try:
            float(str(state))
        except (TypeError, ValueError):
            continue
        out.append(entry)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--python", required=True, type=Path)
    ap.add_argument("--uv", default=str(Path.home() / ".local/bin/uv"))
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    component = args.corpus / DOMAIN
    if not component.is_dir():
        print(f"{DOMAIN} is not in {args.corpus}")
        return 2

    # Fail informatively rather than silently. This measurement proves nothing about
    # confinement if the API is down or the host has no route to it, and that must not be
    # reported as a compatibility failure of the design.
    try:
        urllib.request.urlopen(f"https://{HOST}/", timeout=15)
    except urllib.error.HTTPError:
        pass                                             # a real HTTP response, e.g. 404
    except OSError as err:
        print(f"cannot reach {HOST} from this host at all: {err}\n"
              "this measurement requires real internet access and cannot proceed.")
        return 2

    require_ready(deep=False)
    become_subreaper()
    delegation = Delegation.discover()
    uv = args.uv if Path(args.uv).exists() else None
    platform_deps = Path.home() / "r2exp/platform-deps"
    platform_deps = platform_deps if platform_deps.is_dir() else None

    print(f"F2 against a real integration's real API — {DOMAIN} → {HOST}:{PORT}\n")

    reports: dict[str, dict] = {}
    print("  A  unconfined baseline ...", flush=True)
    reports["unconfined"] = run_unconfined(component, args.python, uv, platform_deps)
    for arm in ARMS:
        print(f"  {ARMS[arm]['label']} ...", flush=True)
        reports[arm] = run_confined(component, arm, args.python, delegation, uv, platform_deps)

    base, declared, undeclared = (reports["unconfined"], reports["confined_declared"],
                                  reports["confined_undeclared"])

    print("\n  arm                          entry            published  priced  egress decisions")
    for key, report in reports.items():
        entry = (report.get("entries") or [{}])
        state = entry[0].get("state", report.get("level", "—")) if entry else "—"
        decisions = [d for d in (report.get("logged") or [])
                     if d.get("op") == "network.egress"]
        print(f"  {key:<28} {str(state).split('.')[-1]:<16} "
              f"{len(report.get('published') or []):>9}  {len(_priced(report)):>6}  "
              f"{''.join('T' if d['allowed'] else 'F' for d in decisions) or '—'}")

    results: list = []
    print()

    # Arm A first: without it, a confined failure cannot be told from an integration that is
    # broken on this release — the misattribution a baseline has stopped three times already.
    check(results, base.get("loaded"),
          "A — nordpool loads unconfined on this release, so there is something to confine",
          f"{base.get('level', '')} {str(base.get('error', ''))[:200]}")

    check(results, declared.get("oom_kill", 1) == 0,
          "B — the confined arm stayed inside its memory limit",
          f"oom_kill={declared.get('oom_kill')}")
    check(results, declared.get("loaded"),
          "**F2** — a real community integration's config entry reached LOADED while confined",
          f"{declared.get('level', '')} {str(declared.get('error', ''))[:300]}")

    priced = _priced(declared)
    check(results, bool(priced),
          "**F2** — it published a numeric price through the mediator, computed from its own "
          "fetch of its own API",
          f"published={[p.get('entity') for p in (declared.get('published') or [])][:6]}")
    if priced:
        print(f"       {priced[0]['entity']} = {priced[0]['state']}  "
              f"(+{len(priced) - 1} more priced sensors)")

    allowed = [d for d in (declared.get("logged") or [])
               if d.get("op") == "network.egress" and d.get("allowed")]
    check(results, bool(allowed),
          "B — the mediator's own durable record shows it granted the declared destination",
          f"logged={declared.get('logged')}")
    if allowed:
        check(results, all(d.get("target") == f"{HOST}:{PORT}" for d in allowed),
              "B — every granted destination is the one the manifest names, host **and port**",
              str([d.get("target") for d in allowed]))
    check(results, not declared.get("audit_breaks"),
          "B — and that record's hash and MAC chains both verify (S7)",
          str(declared.get("audit_breaks")))

    # Arm C — the control that makes B evidence rather than a coincidence.
    denied = [d for d in (undeclared.get("logged") or [])
              if d.get("op") == "network.egress" and not d.get("allowed")]
    check(results, not _priced(undeclared),
          "**C** — with the clause removed, nothing priced crosses the boundary",
          f"priced={[p.get('entity') for p in _priced(undeclared)]}")
    check(results, bool(denied) and all(d.get("target") == f"{HOST}:{PORT}" for d in denied),
          "**C** — and the mediator refused the same destination it granted in B",
          f"logged={undeclared.get('logged')}")
    if denied:
        check(results, all(d.get("clause") == "/permissions/network/egress" for d in denied),
              "**C** — each refusal names the clause, S6's denial by absence",
              str([d.get("clause") for d in denied]))

    check(results, bool(priced) and not _priced(undeclared),
          "**the difference between B and C is the mediated path and nothing else** — same "
          "integration, flow, profile, host and minute")

    passed = sum(1 for r in results if r)
    print(f"\n  {passed}/{len(results)} checks passed")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(
            {"integration": DOMAIN, "host": HOST, "port": PORT, "flow_input": FLOW_INPUT,
             "settle_seconds": SETTLE, "reports": reports,
             "checks": {"passed": passed, "total": len(results)}}, indent=2) + "\n")
        print(f"  wrote {args.json}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
