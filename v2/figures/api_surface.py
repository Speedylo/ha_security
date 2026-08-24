#!/usr/bin/env python3
"""What do integrations actually ask the platform for?

§5.9 settled who writes the manifest. §5.10 has to say what the manifest can express, and
granularity is a security property (S5), not a formatting choice. Choosing it needs evidence
about which of the platform handles integrations actually use, and how:

  - a capability nearly every integration needs cannot be the thing a manifest denies;
    denying it would mean confining nothing
  - a capability almost nobody uses can be denied by default at no compatibility cost, and
    is where confinement is cheapest
  - a capability used at one granularity but declared at another is where S5's asymmetry
    problem lives — `lock.unlock` arriving free with `lock.lock`

`notes/ch5_evidence_ha_coupling.md` §4 enumerated nine handles reachable from `hass`. This
script measures which are used, by how many integrations, and at what granularity.

**Method.** Every `.py` file is parsed with Python's `ast` module and walked for attribute
chains rooted at `hass` or `self.hass`, plus subscripts of `hass.data`. Parsing rather than
grepping matters: `# hass.services.async_call` in a comment, or the string
"hass.states.async_set" in a docstring, are not uses, and a regex counts them. Files that
fail to parse are counted and reported rather than silently skipped.

**What it cannot see.** Dynamic access — `getattr(hass, name)`, dispatch through a variable
that happens to hold the object — is invisible to static parsing. Every count here is
therefore a *lower bound* on use, which is the conservative direction for a compatibility
argument: it can only understate how much a confinement would break.

Run:  python3 api_surface.py --root <dir-of-integration-dirs> [--label core] [--json out.json]
"""

from __future__ import annotations

import argparse
import ast
import collections
import json
import sys
from pathlib import Path

# The nine handles of ch5_evidence_ha_coupling.md §4, in its order, mapped to the attribute
# that reaches each from `hass`.
HANDLES = {
    "data": "Shared mutable store — every integration's runtime state",
    "bus": "Event bus — fire any event, subscribe to all",
    "services": "Service registry — call any registered service",
    "states": "State machine — read and write every entity",
    "config": "Config, including config.path() into the config directory",
    "auth": "Auth manager — users and tokens",
    "http": "HTTP component — register routes on the running server",
    "config_entries": "Every integration's stored configuration and credentials",
    "loop": "Event loop / executor — schedule on the platform's own threads",
}
# Reached by method on `hass` itself rather than by a sub-object.
EXECUTOR_CALLS = {"async_add_executor_job", "async_add_job", "async_create_task"}

# Entity platforms are not "other integrations" in the coupling sense: importing
# `homeassistant.components.sensor` is how an integration declares it provides sensors.
# Importing `homeassistant.components.mqtt` is genuine cross-integration reach.
ENTITY_PLATFORMS = {
    "sensor", "binary_sensor", "switch", "light", "climate", "cover", "fan", "lock",
    "media_player", "camera", "vacuum", "water_heater", "alarm_control_panel", "button",
    "number", "select", "text", "update", "siren", "humidifier", "valve", "lawn_mower",
    "date", "datetime", "time", "event", "image", "notify", "todo", "weather", "remote",
    "device_tracker", "scene", "stt", "tts", "wake_word", "ai_task", "assist_satellite",
    "calendar", "conversation", "image_processing", "geo_location",
}


# The names a reference to the platform root travels under. `self._hass` is a common
# convention and missing it under-counted `hass.states` use by a third in the first run of
# this measurement; `opp` is the Open Peer Power fork's name, which some community
# integrations still carry.
HASS_NAMES = {"hass", "_hass", "opp", "_opp"}


def chain_of(node: ast.Attribute) -> list[str] | None:
    """Return ['hass', 'states', 'async_set'] for a chain rooted at a platform reference.

    Roots recognised: a bare name (`hass`), an attribute (`self.hass`, `self._hass`,
    `coordinator.hass`), under any of the names in HASS_NAMES.
    """
    parts: list[str] = []          # outermost attribute first
    cur: ast.expr = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value

    if isinstance(cur, ast.Name) and cur.id in HASS_NAMES:
        # A bare reference: hass.states.get
        parts.append("hass")
    else:
        # A reference held on something else: self.hass.states.get,
        # self.coordinator.hass.states.get. The loop above has already consumed the
        # `hass` attribute into `parts`, so the root must be recovered from there —
        # taking the innermost match, and discarding whatever it hangs off.
        idx = max((i for i, p in enumerate(parts) if p in HASS_NAMES), default=-1)
        if idx < 0:
            return None
        parts = parts[: idx + 1]
        parts[idx] = "hass"
    return list(reversed(parts))


class Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.handles: set[str] = set()
        self.members: collections.Counter = collections.Counter()
        self.service_domains: collections.Counter = collections.Counter()
        self.calls_services = False
        self.registers_services = False
        self.foreign_components: set[str] = set()

    def visit_Attribute(self, node: ast.Attribute) -> None:
        chain = chain_of(node)
        if chain and len(chain) >= 2:
            handle = chain[1]
            if handle in HANDLES:
                self.handles.add(handle)
                if len(chain) >= 3:
                    self.members[f"{handle}.{chain[2]}"] += 1
            elif handle in EXECUTOR_CALLS:
                self.handles.add("loop")
                self.members[f"loop.{handle}"] += 1
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        chain = chain_of(node.func) if isinstance(node.func, ast.Attribute) else None
        if chain and len(chain) >= 3 and chain[1] == "services":
            if chain[2].startswith("async_call") or chain[2] == "call":
                self.calls_services = True
                # First positional argument is the service's domain.
                if node.args and isinstance(node.args[0], ast.Constant) \
                        and isinstance(node.args[0].value, str):
                    self.service_domains[node.args[0].value] += 1
            elif chain[2].startswith("async_register") or chain[2] == "register":
                self.registers_services = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module.startswith("homeassistant.components."):
            comp = node.module.split(".")[2]
            if comp not in ENTITY_PLATFORMS:
                self.foreign_components.add(comp)
        self.generic_visit(node)


def scan_integration(path: Path) -> dict | None:
    v = Visitor()
    files = parsed = failed = 0
    for py in path.rglob("*.py"):
        files += 1
        try:
            v.visit(ast.parse(py.read_text(encoding="utf-8", errors="replace")))
            parsed += 1
        except SyntaxError:
            failed += 1
    if files == 0:
        return None
    own = path.name
    return {
        "domain": own,
        "files": files, "parsed": parsed, "failed": failed,
        "handles": sorted(v.handles),
        "members": dict(v.members),
        "calls_services": v.calls_services,
        "registers_services": v.registers_services,
        "service_domains": dict(v.service_domains),
        "foreign_components": sorted(c for c in v.foreign_components if c != own),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True,
                    help="directory whose children are integration directories")
    ap.add_argument("--label", default="unlabelled", help="name for this corpus")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    dirs = sorted(p for p in args.root.iterdir() if p.is_dir() and not p.name.startswith("."))
    results = [r for p in dirs if (r := scan_integration(p))]
    n = len(results)
    if not n:
        print(f"no integrations found under {args.root}", file=sys.stderr)
        return 1

    handle_counts = collections.Counter()
    for r in results:
        handle_counts.update(r["handles"])
    member_counts = collections.Counter()
    for r in results:
        for m in r["members"]:
            member_counts[m] += 1
    svc_domains = collections.Counter()
    for r in results:
        svc_domains.update(r["service_domains"])
    foreign = collections.Counter()
    for r in results:
        foreign.update(r["foreign_components"])

    parse_failures = sum(r["failed"] for r in results)
    total_files = sum(r["files"] for r in results)

    print(f"API surface — corpus '{args.label}', {n} integrations, "
          f"{total_files} files ({parse_failures} unparseable)")
    print()
    print(f"{'handle':<18} {'integrations':>12} {'share':>7}   what it confers")
    for h, desc in HANDLES.items():
        c = handle_counts.get(h, 0)
        print(f"  hass.{h:<13} {c:>10}   {c * 100 / n:5.1f}%   {desc[:44]}")

    print()
    print("most-used members (share of integrations using each):")
    for m, c in member_counts.most_common(15):
        print(f"  hass.{m:<34} {c:>5}  {c * 100 / n:5.1f}%")

    callers = sum(1 for r in results if r["calls_services"])
    registrars = sum(1 for r in results if r["registers_services"])
    cross = sum(1 for r in results if r["foreign_components"])
    print()
    print(f"calls services            {callers:>5}  {callers * 100 / n:5.1f}%")
    print(f"registers services        {registrars:>5}  {registrars * 100 / n:5.1f}%")
    print(f"imports another component {cross:>5}  {cross * 100 / n:5.1f}%")
    if svc_domains:
        print("\nservice domains called (by literal first argument):")
        for d, c in svc_domains.most_common(12):
            print(f"  {d:<22} {c:>5}")
    if foreign:
        print("\nmost-imported other components:")
        for d, c in foreign.most_common(10):
            print(f"  {d:<22} {c:>5}")

    if args.json:
        args.json.write_text(json.dumps({
            "label": args.label, "n": n,
            "files": total_files, "unparseable": parse_failures,
            "handles": {h: handle_counts.get(h, 0) for h in HANDLES},
            "handle_share": {h: round(handle_counts.get(h, 0) * 100 / n, 1) for h in HANDLES},
            "members": dict(member_counts.most_common(40)),
            "calls_services": callers, "registers_services": registrars,
            "cross_component": cross,
            "service_domains": dict(svc_domains.most_common(40)),
            "foreign_components": dict(foreign.most_common(40)),
            "per_integration": results,
        }, indent=2) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
