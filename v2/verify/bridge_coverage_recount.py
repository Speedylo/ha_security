#!/usr/bin/env python3
"""Which kinds of device the bridge can show, per integration of the head corpus (bridge batch B5).

`notes/bridge_kinds_b5_prediction_20261031.md`, decision 3. The 2026-10-27 count
(`notes/bridge_coverage_count_20261027.md`) counted a kind when the integration has a file named
after it, against `PLATFORM_NAMES` (`framework/confine/sandbox_runtime.py`). That counts files that
are not platforms: `alarmo/event.py` fires bus events and sets up no entity. Here a kind counts only
when its file defines a platform's setup function (`async_setup_entry`, `async_setup_platform` or
`setup_platform`) at module level, by `def` or by assignment (`localtuya` assigns a `partial`), read
with `ast`: nothing in the corpus is imported or run. A notify file that instead defines
`get_service`/`async_get_service` is Home Assistant's legacy notify platform, which the bridge does
not stand in for (batch B3): it counts as its own kind, `notify (legacy)`. A file that does not parse
is an error, not a missing platform; run it with the Python the corpus targets (3.14). Whether a
platform is set up at run time depends on the integration's options (dwd_weather's camera exists
only for a map entry); that is not counted.

Both rules are printed: the file rule first, as a control that this input gives the 2026-10-27
figures (249 kind uses), then the platform rule. Bridged kinds are read from the bridge's own
`const.py`, not copied.

    python3 -I verify/bridge_coverage_recount.py CORPUS_DIR
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parent.parent
SETUP = {"async_setup_entry", "async_setup_platform", "setup_platform"}
LEGACY_NOTIFY = {"get_service", "async_get_service"}


def _assigned(path: Path, name: str):
    return next(ast.literal_eval(node.value) for node in ast.parse(path.read_text()).body
                if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name)


KINDS = list(dict.fromkeys(_assigned(V2 / "framework/confine/sandbox_runtime.py", "PLATFORM_NAMES")))
BRIDGED = set(_assigned(V2 / "framework/ha_bridge/confine_bridge/const.py", "SUPPORTED"))


def defined(path: Path) -> set[str]:
    """The names a module defines at its top level, by `def` or by assignment."""
    names: set[str] = set()
    for node in ast.parse(path.read_text(errors="replace")).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def platform_kind(path: Path, kind: str) -> str | None:
    """`kind` if the file sets up a platform of it, `notify (legacy)` for a legacy notify."""
    names = defined(path)
    if names & SETUP:
        return kind
    if kind == "notify" and names & LEGACY_NOTIFY:
        return "notify (legacy)"
    return None


def report(label: str, kinds: dict[str, list[str]]) -> None:
    uses = sum(len(k) for k in kinds.values())
    bridged = sum(1 for k in kinds.values() for kind in k if kind in BRIDGED)
    full = sorted(name for name, k in kinds.items() if all(kind in BRIDGED for kind in k))
    missing: dict[str, list[str]] = {}
    for name, k in kinds.items():
        for kind in k:
            if kind not in BRIDGED:
                missing.setdefault(kind, []).append(name)
    print(f"\n== {label}")
    print(f"kind uses {uses}, bridged {bridged} ({100 * bridged / uses:.0f}%)")
    print(f"only bridged kinds: {len(full)} of {len(kinds)}: {', '.join(full)}")
    print(f"unbridged kinds: {len(missing)}")
    for kind, names in sorted(missing.items(), key=lambda item: (-len(item[1]), item[0])):
        print(f"  {kind:<20} {len(names)}: {', '.join(sorted(names))}")


def main(corpus: Path) -> int:
    integrations = sorted(p for p in corpus.iterdir() if (p / "manifest.json").is_file())
    print(f"corpus {corpus}: {len(integrations)} integrations; kinds bridged: {len(BRIDGED)}")
    by_file = {p.name: [k for k in KINDS if (p / f"{k}.py").is_file()] for p in integrations}
    by_platform = {p.name: [found for k in by_file[p.name]
                            if (found := platform_kind(p / f"{k}.py", k)) is not None]
                   for p in integrations}
    report("file rule (2026-10-27's), today's bridge", by_file)
    report("platform rule (B5), today's bridge", by_platform)
    print("\nfiles named after a kind that set up no platform of it:")
    for name in by_file:
        for kind in sorted(set(by_file[name]) - set(by_platform[name])):
            print(f"  {name}/{kind}.py" + ("  (a legacy notify platform)"
                                           if "notify (legacy)" in by_platform[name]
                                           and kind == "notify" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
