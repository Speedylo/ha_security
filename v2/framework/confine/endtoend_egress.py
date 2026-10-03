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

**§7.31 generalised it from one subject to a table** (`SUBJECTS`), because §8.4.2's lesson —
real unmodified code finds what instruments written from the design's assumptions cannot — had
been applied exactly once. The three added subjects were chosen by **network stack**: `requests`
and `httpx` had never been spawned confined. Predictions in `notes/ch7_31_endtoend_prediction.md`,
committed before the first run. `nordpool` stays the default, so the command below is unchanged.

A subject with more than one host gets **arm D**: only some of its hosts declared. It is the
first arm that can show the grant is per destination rather than per integration.

Run, on the C4 device, inside a systemd user scope:

    systemd-run --user --scope -q python3 -m confine.endtoend_egress \\
        --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python \\
        --json ~/capstone/v2/experiments/end_to_end/results/pi5_nordpool_egress.json

    # §7.31 — one subject per run; --corpus is wherever that subject lives
    systemd-run --user --scope -q python3 -m confine.endtoend_egress --subject dwd_weather \\
        --corpus ~/r2exp/corpus --python ~/r2exp/ha314/bin/python \\
        --json ~/capstone/v2/experiments/end_to_end/results/pi5_dwd_weather_egress.json
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

# Each subject's flow input is the integration's own, fed to `async_configure` as the UI would;
# every field not named here takes the integration's default. `egress` is read from the
# integration's source, never from a run — a clause inferred from what arm A happened to reach
# would make arm B's success circular. `numeric` says what counts as a *fetched* value: a number
# for a price, a forecast or an index; any real state for a departure board.
#
# A coordinator's first fetch is scheduled after `async_start`, not during the flow, so a run with
# no settle window reports only what configuration touched and misses the polling F2 is about.
# §7.25 used 8 s against a static host; §7.27 used 25 s for one small JSON document. `dwd_weather`
# downloads and unzips a station's MOSMIX file in an executor, so it gets longer.
SUBJECTS: dict[str, dict] = {
    "nordpool": {
        # §7.27. `region` is `vol.Required` and chosen from the integration's own list.
        "egress": ["dataportal-api.nordpoolgroup.com:443"],
        "flow_input": {"region": "SE1", "currency": "EUR"},
        "numeric": True, "settle": 25.0,
    },
    "smhi_brandrisk": {
        # §7.31. aiohttp via `async_get_clientsession` — nordpool's shape, on two hosts. The
        # warnings host is non-critical in its own code (`except Exception`, debug log).
        "egress": ["opendata-download-metfcst.smhi.se:443",
                   "opendata-download-warnings.smhi.se:443"],
        "partial": ["opendata-download-metfcst.smhi.se:443"],
        # Its own validation rejects anything outside Sweden, and the default is HA's.
        "flow_input": {"latitude": 59.33, "longitude": 18.07},
        "numeric": True, "settle": 40.0,
    },
    "regensburg_transport": {
        # §7.31. `requests` in an executor *during the flow* (the stop search), then a bare
        # `aiohttp.ClientSession()` in the sensor. Two stacks, one host.
        "egress": ["efa.rvv.de:443"],
        "flow_input": {"search": "Arnulfsplatz"},
        "select_first": ["selected_stop"],
        # Its delay sensor ends every update with `= 0` whatever it fetched (`sensor.py:255`),
        # so only the departure carries evidence. Polled every 120 s with no update before
        # add, so the first poll needs a window longer than that — 40 s saw none in any arm.
        "evidence": "next_departure",
        "numeric": False, "settle": 150.0,
    },
    "dwd_weather": {
        # §7.31. `httpx`, synchronous, in an executor, after setup — the flow itself is offline.
        # Station 10865 is München-Stadt, which carries reports as well as forecasts.
        #
        # **`www.dwd.de` is deliberately left out.** This list was written from reading the
        # source before the first run and it missed that host (the library's text-report
        # fetch); arm A's recorder found it by name. Adding it now would turn a measured miss
        # into a clause inferred from a run — the circularity this table's header rules out.
        "egress": ["opendata.dwd.de:443"],
        "flow_input": {"station_id": "10865"},
        # Its numeric sensors are disabled by default; what it publishes enabled is the weather
        # entity and two timestamps — the forecast's issue time and the last measurement's —
        # which exist only if the download succeeded (arm C: `ForecastDownloadError`).
        "evidence": "_time_", "numeric": False, "settle": 60.0,
    },
}


def arms_for(subject: dict) -> dict[str, dict]:
    """B and C for every subject; D where the subject has hosts to withhold."""
    arms = {
        "confined_declared": {
            "label": "B  confined, every host declared",
            "permissions": {"schema_version": 1, "network": {"egress": subject["egress"]}},
        },
        "confined_undeclared": {
            "label": "C  confined, clause absent",
            "permissions": {"schema_version": 1},
        },
    }
    if subject.get("partial"):
        arms["confined_partial"] = {
            "label": "D  confined, some hosts declared",
            "permissions": {"schema_version": 1,
                            "network": {"egress": subject["partial"]}},
        }
    return arms


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


def run_confined(component: Path, domain: str, subject: dict, arm: str, permissions: dict,
                 python: Path, delegation: Delegation, uv: str | None,
                 platform_deps: Path | None) -> dict:
    root = Path(tempfile.mkdtemp(prefix=f"e2e-egress-{arm}-"))
    # The audit log lives **outside** `root`, because `root` is removed in the `finally` below
    # and the records are read after it. Keeping it inside meant `records()` found an empty
    # directory and reported no decisions at all — a harness fault that presented exactly as
    # "the mediator logged nothing", which is §6.4.5's warning in its most literal form.
    audit_dir = Path(tempfile.mkdtemp(prefix=f"e2e-egress-audit-{arm}-"))
    mediator = Mediator()
    try:
        own = root / "custom_components" / domain
        own.parent.mkdir(parents=True)
        shutil.copytree(component, own)
        # Beside the integration, never inside its own manifest.json — §5.9.4's provenance
        # rule, and rewriting the integration's file would breach C1.
        (root / "custom_components" / f"{domain}.permissions.json").write_text(
            json.dumps(permissions))
        data = root / ".confine" / domain
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
        mediator.policy = acting_policy({domain: manifest}, platform,
                                        broker=broker, relay=relay)
        mediator_end, sandbox_end = Channel.pair()
        mediator.register(domain, Channel(mediator_end))

        spec_file = root / "spec.json"
        spec_file.write_text(json.dumps({
            "domain": domain, "mode": "flow", "auth": True,
            "entities": [], "services": [], "setup_components": wanted,
            "egress": True, "settle_seconds": subject["settle"],
            "menu_choice": {}, "flow_input": subject["flow_input"],
            "select_first": subject.get("select_first", [])}))

        runtime_files = {str(HERE / "sandbox_runtime.py"): "/sandbox/runtime.py",
                         str(HERE / "egress_shim.py"): "/sandbox/egress_shim.py",
                         str(spec_file): "/sandbox/spec.json",
                         str(deps): DEPS}
        spec = SandboxSpec(
            domain=domain, own_dir=str(own), data_dir=str(data),
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


def run_unconfined(component: Path, domain: str, subject: dict, python: Path, uv: str | None,
                   platform_deps: Path | None) -> dict:
    """Arm A. Same integration, same flow input, same profile, no sandbox and no mediator."""
    root = Path(tempfile.mkdtemp(prefix="e2e-egress-base-"))
    try:
        config = root / "config"
        (config / "custom_components").mkdir(parents=True)
        shutil.copytree(component, config / "custom_components" / domain)
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
            "domain": domain, "config_dir": str(config), "setup_components": wanted,
            "world": {}, "record_egress": True, "settle_seconds": subject["settle"],
            "menu_choice": {}, "flow_input": subject["flow_input"],
            "select_first": subject.get("select_first", [])}))

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


#: States an entity holds when nothing was fetched. A departure board's state is a string, so
#: for a non-numeric subject *fetched* means "holds a state other than these".
NO_VALUE = {None, "", "unknown", "unavailable", "None"}


def _fetched(report: dict, numeric: bool = True, domain: str | None = None,
             evidence: str | None = None) -> list[dict]:
    """Published entities carrying a value the integration could only have got from its API.

    `numeric` is §7.27's original test — a number, as a price is. For a subject whose output is
    text it falls back to *any real state*, which is weaker, and arm C is what tells whether it
    is too weak: if C publishes a "fetched" value with no network, the predicate is wrong and
    the run says so rather than passing.
    """
    out = []
    for entry in report.get("published") or []:
        # Arm A has no boundary, so its `published` is the whole state machine; only entities
        # the registry attributes to this integration count (`platform`, from §7.31).
        if domain and "platform" in entry and entry["platform"] != domain:
            continue
        if evidence and evidence not in str(entry.get("entity")):
            continue
        state = entry.get("state")
        if numeric:
            try:
                float(str(state))
            except (TypeError, ValueError):
                continue
        elif state in NO_VALUE:
            continue
        out.append(entry)
    return out


def _egress(report: dict, allowed: bool) -> list[dict]:
    return [d for d in (report.get("logged") or [])
            if d.get("op") == "network.egress" and bool(d.get("allowed")) is allowed]


def _reachable(target: str) -> str | None:
    """None if `target` answers at all from this host, else why not. An HTTP error is an answer."""
    host, _, port = target.rpartition(":")
    try:
        urllib.request.urlopen(f"https://{host}:{port}/", timeout=15)
    except urllib.error.HTTPError:
        return None
    except OSError as err:
        return str(err)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--subject", default="nordpool", choices=sorted(SUBJECTS))
    ap.add_argument("--corpus", type=Path)
    ap.add_argument("--python", type=Path)
    # Re-evaluate the checks over a run already recorded, without running anything. The
    # checks are arguments about the data; when one is found to be wrong, the data stands.
    ap.add_argument("--recheck", type=Path, metavar="RESULT_JSON")
    ap.add_argument("--uv", default=str(Path.home() / ".local/bin/uv"))
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    recorded = json.loads(args.recheck.read_text()) if args.recheck else None
    domain = recorded["integration"] if recorded else args.subject
    subject = SUBJECTS[domain]
    declared_set = set(subject["egress"])
    arms = arms_for(subject)

    def fetched_in(report: dict) -> list[dict]:
        return _fetched(report, subject["numeric"], domain, subject.get("evidence"))

    if recorded:
        print(f"re-checking {args.recheck} — nothing is run\n")
        return evaluate(domain, subject, declared_set, fetched_in, recorded["reports"],
                        recorded.get("unreachable_before_run") or {}, args.json, recorded)
    if not (args.corpus and args.python):
        ap.error("--corpus and --python are required unless --recheck is given")
    component = args.corpus / domain
    if not component.is_dir():
        print(f"{domain} is not in {args.corpus}")
        return 2

    # Fail informatively rather than silently. This measurement proves nothing about
    # confinement if the API is down or the host has no route to it, and that must not be
    # reported as a compatibility failure of the design. Only the first host is required:
    # a subject's later hosts may be non-critical to it, and an outage there is a fact about
    # the run (recorded below), not a reason to refuse it.
    unreachable = {t: why for t in subject["egress"] if (why := _reachable(t))}
    if subject["egress"][0] in unreachable:
        print(f"cannot reach {subject['egress'][0]} from this host at all: "
              f"{unreachable[subject['egress'][0]]}\n"
              "this measurement requires real internet access and cannot proceed.")
        return 2

    require_ready(deep=False)
    become_subreaper()
    delegation = Delegation.discover()
    uv = args.uv if Path(args.uv).exists() else None
    platform_deps = Path.home() / "r2exp/platform-deps"
    platform_deps = platform_deps if platform_deps.is_dir() else None

    print(f"F2 against a real integration's real API — {domain} → {', '.join(subject['egress'])}\n")

    reports: dict[str, dict] = {}
    print("  A  unconfined baseline ...", flush=True)
    reports["unconfined"] = run_unconfined(component, domain, subject, args.python, uv,
                                           platform_deps)
    for arm, spec in arms.items():
        print(f"  {spec['label']} ...", flush=True)
        reports[arm] = run_confined(component, domain, subject, arm, spec["permissions"],
                                    args.python, delegation, uv, platform_deps)
    return evaluate(domain, subject, declared_set, fetched_in, reports, unreachable, args.json)


def evaluate(domain: str, subject: dict, declared_set: set, fetched_in, reports: dict,
             unreachable: dict, out: Path | None, recorded: dict | None = None) -> int:
    """The table and the checks, over four reports however they were obtained."""
    base, declared, undeclared = (reports["unconfined"], reports["confined_declared"],
                                  reports["confined_undeclared"])

    print("\n  arm                          entry            published  fetched  egress decisions")
    for key, report in reports.items():
        entry = (report.get("entries") or [{}])
        state = entry[0].get("state", report.get("level", "—")) if entry else "—"
        decisions = [d for d in (report.get("logged") or [])
                     if d.get("op") == "network.egress"]
        print(f"  {key:<28} {str(state).split('.')[-1]:<16} "
              f"{len(report.get('published') or []):>9}  {len(fetched_in(report)):>7}  "
              f"{''.join('T' if d['allowed'] else 'F' for d in decisions) or '—'}")
    for key, report in reports.items():
        flow = report.get("flow") or {}
        if flow.get("error") or flow.get("errors") or report.get("setup_errors"):
            print(f"  {key}: flow={flow.get('type')} errors={flow.get('errors')} "
                  f"error={flow.get('error')} setup={report.get('setup_errors')}")

    # Where arm A went, by name where the recorder can see one (§7.18's blind spot: names
    # resolved through `aiodns` appear only as the address they connect to).
    seen = sorted({str(a.get("host")) for a in (base.get("egress_attempts") or [])
                   if a.get("phase") == "integration" and a.get("kind") == "resolve"})
    print(f"\n  A resolved, attributed to the integration: {seen or '—'}")
    if unreachable:
        print(f"  unreachable from this host before the run: {unreachable}")

    results: list = []
    print()

    # Arm A first: without it, a confined failure cannot be told from an integration that is
    # broken on this release — the misattribution a baseline has stopped three times already.
    check(results, base.get("loaded"),
          f"A — {domain} loads unconfined on this release, so there is something to confine",
          f"{base.get('level', '')} {str(base.get('error', ''))[:200]} flow={base.get('flow')}")
    check(results, bool(fetched_in(base)),
          "A — and publishes a fetched value unconfined",
          f"published={(base.get('published') or [])[:8]}")

    check(results, declared.get("oom_kill", 1) == 0,
          "B — the confined arm stayed inside its memory limit",
          f"oom_kill={declared.get('oom_kill')}")
    check(results, declared.get("loaded"),
          "**F2** — a real community integration's config entry reached LOADED while confined",
          f"{declared.get('level', '')} {str(declared.get('error', ''))[:300]} "
          f"flow={declared.get('flow')}")

    fetched = fetched_in(declared)
    check(results, bool(fetched),
          "**F2** — it published a fetched value through the mediator, from its own call to "
          "its own API",
          f"published={(declared.get('published') or [])[:8]}")
    base_values = {e["entity"]: e["state"] for e in fetched_in(base)}
    for entry in fetched[:3]:
        print(f"       {entry['entity']} = {entry['state']}  "
              f"(A: {base_values.get(entry['entity'], '—')})")
    # §7.27's claim was not that a value appeared but that it was *the same number*. Added in
    # §7.31 after `regensburg_transport` passed on a sensor's own fallback `0`, which arm C could
    # not catch because C's flow failed before any entity existed.
    check(results, any(base_values.get(e["entity"]) == e["state"] for e in fetched),
          "**F2** — and at least one value equals arm A's, fetched from the same API minutes apart",
          f"B={[(e['entity'], e['state']) for e in fetched[:4]]} A={list(base_values.items())[:4]}")

    allowed = _egress(declared, True)
    check(results, bool(allowed),
          "B — the mediator's own durable record shows it granted a declared destination",
          f"logged={declared.get('logged')}")
    if allowed:
        check(results, all(d.get("target") in declared_set for d in allowed),
              "B — every granted destination is one the manifest names, host **and port**",
              str([d.get("target") for d in allowed]))
    check(results, not _egress(declared, False),
          "B — and nothing the integration asked for was refused (the declared set is complete)",
          str([(d.get("target"), d.get("clause")) for d in _egress(declared, False)]))
    check(results, not declared.get("audit_breaks"),
          "B — that record's hash and MAC chains both verify (S7)",
          str(declared.get("audit_breaks")))

    # Arm C — the control that makes B evidence rather than a coincidence.
    denied = _egress(undeclared, False)
    granted_b = {d.get("target") for d in allowed}
    check(results, not fetched_in(undeclared),
          "**C** — with the clause removed, no fetched value crosses the boundary",
          f"fetched={fetched_in(undeclared)[:6]}")
    # **Overlap, and the check has been wrong twice.** §7.27's form required every refusal to
    # be the one declared host, which `dwd_weather` broke by being refused `www.dwd.de`, a
    # host its declaration missed. The second form required C to refuse *every* host B was
    # granted, which `smhi_brandrisk` broke: refused its critical host first, it raises
    # `UpdateFailed` and never asks for the second. What C must show is narrower and is what
    # the control is for — a destination B was granted is one C was refused.
    check(results, bool(denied) and bool(granted_b & {d.get("target") for d in denied}),
          "**C** — and the mediator refused the destinations it granted in B",
          f"logged={undeclared.get('logged')}")
    if denied:
        check(results, all(d.get("clause") == "/permissions/network/egress" for d in denied),
              "**C** — each refusal names the clause, S6's denial by absence",
              str([d.get("clause") for d in denied]))

    # Arm D — only where some hosts can be withheld while the integration still works.
    partial = reports.get("confined_partial")
    if partial is not None:
        kept = set(subject["partial"])
        p_allowed, p_denied = _egress(partial, True), _egress(partial, False)
        check(results, bool(fetched_in(partial)),
              "**D** — with only some hosts declared, the integration still publishes",
              f"published={(partial.get('published') or [])[:8]}")
        check(results, bool(p_allowed) and all(d.get("target") in kept for d in p_allowed),
              "**D** — every grant is to a host D declares",
              str([d.get("target") for d in p_allowed]))
        check(results, bool(p_denied)
              and all(d.get("target") in declared_set - kept for d in p_denied)
              and all(d.get("clause") == "/permissions/network/egress" for d in p_denied),
              "**D** — and the withheld host is refused by itself, by absence, in the same run",
              str([(d.get("target"), d.get("clause")) for d in p_denied]))

    check(results, bool(fetched) and not fetched_in(undeclared),
          "**the difference between B and C is the mediated path and nothing else** — same "
          "integration, flow, profile, host and minute")

    passed = sum(1 for r in results if r)
    print(f"\n  {passed}/{len(results)} checks passed")

    if out:
        record = recorded or {
            "integration": domain, "egress": subject["egress"],
            "partial": subject.get("partial"), "flow_input": subject["flow_input"],
            "select_first": subject.get("select_first"), "settle_seconds": subject["settle"],
            "unreachable_before_run": unreachable, "reports": reports}
        key = "rechecked" if recorded else "checks"
        record[key] = {"passed": passed, "total": len(results)}
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2) + "\n")
        print(f"  wrote {out}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
