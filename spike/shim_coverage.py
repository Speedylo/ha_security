#!/usr/bin/env python3
"""Measure the shim against the surface data from hacs_api_surface.py.

Imports every module in the shim, collects the public names it actually exposes,
and replays surface_out/integrations.json against that set: which integrations
could import cleanly today, and which symbols are still missing.

Import success is a necessary, not sufficient, condition — an integration can
import everything it needs and still depend on lifecycle behaviour the shim does
not reproduce. Treat this as an upper bound on compatibility, and the count of
integrations actually executed end-to-end as the lower bound.

    ./shim_coverage.py --top 25
"""

from __future__ import annotations

import argparse
import json
import pkgutil
import sys
import urllib.request
from collections import Counter
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR / "shim"))

DEFAULT_SURFACE = SPIKE_DIR.parent / "surface_out" / "integrations.json"


def shim_symbols() -> set[str]:
    """Every ``module:name`` the shim can satisfy."""
    import homeassistant

    provided: set[str] = set()
    modules = ["homeassistant"]
    for info in pkgutil.walk_packages(homeassistant.__path__, prefix="homeassistant."):
        modules.append(info.name)

    for module_name in modules:
        if module_name.rsplit(".", 1)[-1].startswith("_"):
            continue
        try:
            module = __import__(module_name, fromlist=["__name__"])
        except Exception as err:  # noqa: BLE001
            print(f"warning: shim module {module_name} failed to import: {err}", file=sys.stderr)
            continue
        provided.add(f"{module_name}:<module>")
        for name in dir(module):
            if not name.startswith("_") or name == "__version__":
                provided.add(f"{module_name}:{name}")
    return provided


ANALYTICS_URL = "https://analytics.home-assistant.io/custom_integrations.json"
ANALYTICS_CACHE = SPIKE_DIR / ".ha_analytics.json"


def load_installs() -> dict[str, int]:
    """Installed-integration counts published by Home Assistant's own analytics.

    Keyed by integration domain, which is exactly what hacs_api_surface.py
    records, so the two join directly. This is opt-in telemetry, so treat it as
    a lower bound and a relative measure rather than a census — but it is the
    only public signal of which integrations people actually run, and repo
    counts are a badly misleading substitute for it.
    """
    if ANALYTICS_CACHE.exists() and ANALYTICS_CACHE.stat().st_size > 0:
        raw = json.loads(ANALYTICS_CACHE.read_text(encoding="utf-8"))
    else:
        # The endpoint 403s urllib's default User-Agent, so identify properly.
        request = urllib.request.Request(
            ANALYTICS_URL, headers={"User-Agent": "hacs-sandbox-research/0.1"}
        )
        with urllib.request.urlopen(request, timeout=30) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        ANALYTICS_CACHE.write_text(json.dumps(raw), encoding="utf-8")
    return {domain: entry.get("total", 0) for domain, entry in raw.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--surface", default=str(DEFAULT_SURFACE))
    parser.add_argument("--pattern", default="polling_sensor", help="pattern to score, or 'all'")
    parser.add_argument("--top", type=int, default=25, help="how many missing symbols to list")
    parser.add_argument(
        "--installs",
        action="store_true",
        help="also weight coverage by real installed base (HA analytics)",
    )
    args = parser.parse_args()

    provided = shim_symbols()
    integrations = json.loads(Path(args.surface).read_text(encoding="utf-8"))
    installs = load_installs() if args.installs else {}
    if args.pattern != "all":
        integrations = [item for item in integrations if item.get("pattern") == args.pattern]

    missing_counter: Counter[str] = Counter()
    fully_covered = 0
    gaps: list[tuple[int, str]] = []
    covered_installs = total_installs = 0

    for integration in integrations:
        missing = [symbol for symbol in integration["symbols"] if symbol not in provided]
        seats = installs.get(integration.get("domain", ""), 0)
        total_installs += seats
        if not missing:
            fully_covered += 1
            covered_installs += seats
        else:
            missing_counter.update(missing)
            gaps.append((len(missing), integration["repo"]))

    total = len(integrations)
    share = (fully_covered / total * 100) if total else 0.0
    print(f"shim exposes {len(provided)} importable names")
    print(f"pattern '{args.pattern}': {fully_covered}/{total} integrations import cleanly ({share:.1f}%)")

    if args.installs:
        weighted = (covered_installs / total_installs * 100) if total_installs else 0.0
        print(
            f"weighted by installed base: {covered_installs:,}/{total_installs:,} "
            f"installs covered ({weighted:.1f}%)"
        )
        print(
            "  ^ the number that answers 'how much of the real world does this run'. "
            "Repo counts treat a 43,000-install integration and a 3-install one alike."
        )

    if gaps:
        gaps.sort()
        median_missing = gaps[len(gaps) // 2][0]
        print(f"median missing symbols among the rest: {median_missing}")
        print("\nclosest to running:")
        for count, repo in gaps[:10]:
            print(f"  {count:3d}  {repo}")
        print(f"\ntop {args.top} missing symbols (by number of integrations blocked):")
        for symbol, count in missing_counter.most_common(args.top):
            print(f"  {count:3d}  {symbol}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
