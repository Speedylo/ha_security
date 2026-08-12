#!/usr/bin/env python3
"""
hacs_api_surface.py — measure the Home Assistant API surface used by HACS integrations.

Purpose
-------
The feasibility of a sandboxing framework for Home Assistant integrations rests on one
empirical question:

    If I reimplement only the N most-used symbols of Home Assistant's internal API,
    how many real community integrations run unmodified?

This script answers that. It downloads custom integrations from the HACS default
catalogue, parses every Python file with `ast`, records which `homeassistant.*` symbols
each integration imports, classifies each integration by architectural pattern, and
computes a coverage curve: integrations fully covered vs. size of the implemented
symbol budget.

Nothing is executed. Files are parsed straight out of the downloaded tarball in memory;
untrusted code is never run and never written to disk as an importable module.

Usage
-----
    python3 hacs_api_surface.py                      # quick run, 150 repos
    python3 hacs_api_surface.py --limit 0            # whole catalogue (slow)
    python3 hacs_api_surface.py --pattern polling_sensor --budget 25
    python3 hacs_api_surface.py --exclude-trivial    # ignore constants/exceptions

Set GITHUB_TOKEN in the environment to raise API rate limits (optional).

Outputs (written to ./surface_out/)
-----------------------------------
    symbols.csv        every symbol, how many integrations import it
    coverage.csv       the coverage curve (budget size -> integrations covered)
    integrations.json  per-integration detail: symbols, pattern, tags
    nearmiss.csv       integrations just outside the budget + what they're missing

Stdlib only. No pip install required.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import os
import sys
import tarfile
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from pathlib import Path

HACS_DEFAULT_LIST = "https://raw.githubusercontent.com/hacs/default/master/integration"
CACHE_DIR = Path("./.hacs_cache")
OUT_DIR = Path("./surface_out")

# Modules whose symbols are cheap to reimplement: plain constants, exception classes,
# and type aliases. Behavioural API (coordinators, entities, helpers) is the real cost.
TRIVIAL_MODULE_PREFIXES = (
    "homeassistant.const",
    "homeassistant.exceptions",
    "homeassistant.helpers.typing",
    "homeassistant.util.dt",
)

# Entity platforms that only publish data outward (no commands from HA).
READ_ONLY_PLATFORMS = {"sensor", "binary_sensor", "weather", "air_quality", "calendar"}

# Entity platforms that accept commands from HA.
ACTUATOR_PLATFORMS = {
    "switch", "light", "climate", "cover", "fan", "lock", "vacuum",
    "media_player", "number", "select", "button", "humidifier", "water_heater",
    "siren", "valve", "lawn_mower", "text", "alarm_control_panel",
}

# Method names that indicate the integration receives commands.
COMMAND_METHODS = {
    "async_turn_on", "async_turn_off", "turn_on", "turn_off",
    "async_set_native_value", "async_press", "async_select_option",
    "async_open_cover", "async_close_cover", "async_set_temperature",
    "async_lock", "async_unlock", "async_set_value",
}

DISCOVERY_MODULES = ("zeroconf", "ssdp", "dhcp", "bluetooth", "usb")


# --------------------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------------------

def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "hacs-api-surface/1.0"})
    token = os.environ.get("GITHUB_TOKEN")
    if token and "github" in url:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_repo_list() -> list[str]:
    """The HACS default catalogue: a JSON array of 'owner/repo' strings."""
    raw = _get(HACS_DEFAULT_LIST)
    repos = json.loads(raw)
    if not isinstance(repos, list):
        raise ValueError("unexpected HACS catalogue format")
    return [r for r in repos if isinstance(r, str) and "/" in r]


def fetch_tarball(repo: str) -> bytes | None:
    """Download a repo tarball, caching it so re-runs are instant."""
    cache_path = CACHE_DIR / (repo.replace("/", "__") + ".tar.gz")
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path.read_bytes()

    for url in (
        f"https://codeload.github.com/{repo}/tar.gz/HEAD",
        f"https://api.github.com/repos/{repo}/tarball",
    ):
        try:
            data = _get(url)
            if data:
                cache_path.write_bytes(data)
                return data
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            continue
    return None


# --------------------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------------------

@dataclass
class Integration:
    repo: str
    domain: str = ""
    symbols: set[str] = field(default_factory=set)
    platforms: set[str] = field(default_factory=set)
    methods: set[str] = field(default_factory=set)
    n_files: int = 0
    n_lines: int = 0
    pattern: str = "unknown"
    tags: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        d = asdict(self)
        d["symbols"] = sorted(self.symbols)
        d["platforms"] = sorted(self.platforms)
        d["methods"] = sorted(self.methods)
        return d


class _Collector(ast.NodeVisitor):
    """Collects homeassistant.* imports and defined method names from one module."""

    def __init__(self) -> None:
        self.symbols: set[str] = set()
        self.methods: set[str] = set()

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # node.level > 0 means a relative import (the integration's own code) - skip.
        if node.level == 0 and node.module and node.module.startswith("homeassistant"):
            for alias in node.names:
                self.symbols.add(f"{node.module}:{alias.name}")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.startswith("homeassistant"):
                self.symbols.add(f"{alias.name}:<module>")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.methods.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.methods.add(node.name)
        self.generic_visit(node)


def analyze_tarball(repo: str, blob: bytes) -> Integration | None:
    """Parse every custom_components/*.py inside the tarball, without extracting it."""
    integ = Integration(repo=repo)
    try:
        tar = tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz")
    except (tarfile.TarError, EOFError):
        return None

    with tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith(".py"):
                continue
            parts = member.name.split("/")
            if "custom_components" not in parts:
                continue
            # .../custom_components/<domain>/<file>.py
            idx = parts.index("custom_components")
            if idx + 1 < len(parts):
                integ.domain = integ.domain or parts[idx + 1]
            if member.size > 2_000_000:  # skip absurd files
                continue

            try:
                fh = tar.extractfile(member)
                if fh is None:
                    continue
                source = fh.read().decode("utf-8", errors="replace")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeError, tarfile.TarError, ValueError):
                continue

            collector = _Collector()
            collector.visit(tree)
            integ.symbols |= collector.symbols
            integ.methods |= collector.methods
            integ.n_files += 1
            integ.n_lines += source.count("\n")

    if integ.n_files == 0:
        return None

    for sym in integ.symbols:
        module = sym.split(":", 1)[0]
        if module.startswith("homeassistant.components."):
            integ.platforms.add(module.split(".")[2])

    classify(integ)
    return integ


def classify(integ: Integration) -> None:
    """Assign a primary architectural pattern plus descriptive tags."""
    modules = {s.split(":", 1)[0] for s in integ.symbols}
    names = {s.split(":", 1)[1] for s in integ.symbols}

    has_coordinator = "DataUpdateCoordinator" in names or "CoordinatorEntity" in names
    has_oauth = any("oauth2" in m for m in modules)
    has_discovery = any(d in m for m in modules for d in DISCOVERY_MODULES)
    has_mqtt = "homeassistant.components.mqtt" in modules
    has_dispatcher = any("dispatcher" in m for m in modules)
    takes_commands = bool(integ.methods & COMMAND_METHODS)
    actuator_platforms = integ.platforms & ACTUATOR_PLATFORMS
    readonly_platforms = integ.platforms & READ_ONLY_PLATFORMS

    tags = []
    if has_coordinator:
        tags.append("coordinator")
    if has_oauth:
        tags.append("oauth")
    if has_discovery:
        tags.append("discovery")
    if has_mqtt or has_dispatcher:
        tags.append("push")
    if "config_flow" in {m.split(".")[-1] for m in modules} or "async_step_user" in integ.methods:
        tags.append("config_flow")
    integ.tags = tags

    # Most specific signal wins.
    if has_oauth:
        integ.pattern = "oauth_cloud"
    elif has_discovery:
        integ.pattern = "local_discovery"
    elif takes_commands or actuator_platforms:
        integ.pattern = "actuator"
    elif has_mqtt or has_dispatcher:
        integ.pattern = "push_stream"
    elif has_coordinator and readonly_platforms:
        integ.pattern = "polling_sensor"
    elif readonly_platforms:
        integ.pattern = "sensor_other"
    else:
        integ.pattern = "other"


# --------------------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------------------

def is_trivial(symbol: str) -> bool:
    module = symbol.split(":", 1)[0]
    return module.startswith(TRIVIAL_MODULE_PREFIXES)


def coverage_curve(
    integrations: list[Integration], ranked: list[str], max_budget: int
) -> list[tuple[int, int, float]]:
    """For each budget size N, how many integrations import nothing outside the top N?"""
    sets = [i.symbols for i in integrations]
    total = len(sets) or 1
    curve = []
    implemented: set[str] = set()
    for n, sym in enumerate(ranked[:max_budget], start=1):
        implemented.add(sym)
        covered = sum(1 for s in sets if s <= implemented)
        curve.append((n, covered, 100.0 * covered / total))
    return curve


def near_misses(
    integrations: list[Integration], budget_set: set[str], slack: int
) -> list[tuple[str, list[str]]]:
    """Integrations that would be covered if we added just a few more symbols."""
    out = []
    for integ in integrations:
        missing = sorted(integ.symbols - budget_set)
        if 0 < len(missing) <= slack:
            out.append((integ.repo, missing))
    return out


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--limit", type=int, default=150,
                   help="how many repos to analyse (0 = the whole catalogue)")
    p.add_argument("--workers", type=int, default=12, help="parallel downloads")
    p.add_argument("--pattern", default="polling_sensor",
                   help="pattern to compute the coverage curve for, or 'all'")
    p.add_argument("--budget", type=int, default=25,
                   help="symbol budget to report near-misses against")
    p.add_argument("--exclude-trivial", action="store_true",
                   help="ignore constants/exceptions when computing coverage")
    p.add_argument("--max-budget", type=int, default=120, help="longest coverage curve to compute")
    args = p.parse_args()

    CACHE_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(exist_ok=True)

    print("Fetching HACS default catalogue ...", flush=True)
    try:
        repos = fetch_repo_list()
    except Exception as exc:
        print(f"  failed: {exc}", file=sys.stderr)
        return 1
    if args.limit:
        repos = repos[: args.limit]
    print(f"  {len(repos)} repositories to analyse\n", flush=True)

    integrations: list[Integration] = []
    failed = 0

    def work(repo: str) -> Integration | None:
        blob = fetch_tarball(repo)
        return analyze_tarball(repo, blob) if blob else None

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(work, r): r for r in repos}
        for done, fut in enumerate(as_completed(futures), start=1):
            repo = futures[fut]
            try:
                result = fut.result()
            except Exception:
                result = None
            if result:
                integrations.append(result)
            else:
                failed += 1
            if done % 25 == 0 or done == len(repos):
                print(f"  {done}/{len(repos)} processed "
                      f"({len(integrations)} parsed, {failed} skipped)", flush=True)

    if not integrations:
        print("\nNo integrations could be parsed. Check network access.", file=sys.stderr)
        return 1

    # ---- pattern breakdown -----------------------------------------------------------
    patterns = Counter(i.pattern for i in integrations)
    print(f"\n{'='*68}\nPATTERN BREAKDOWN  ({len(integrations)} integrations parsed)\n{'='*68}")
    for name, count in patterns.most_common():
        print(f"  {name:<18} {count:>5}   {100*count/len(integrations):>5.1f}%")

    # ---- select the subset to measure ------------------------------------------------
    if args.pattern == "all":
        subset = integrations
        label = "all integrations"
    else:
        subset = [i for i in integrations if i.pattern == args.pattern]
        label = f"pattern '{args.pattern}'"
    if not subset:
        print(f"\nNo integrations matched {label}. Try --pattern all.", file=sys.stderr)
        return 1

    # Optionally drop cheap symbols from the coverage question.
    def relevant(symbols: set[str]) -> set[str]:
        return {s for s in symbols if not is_trivial(s)} if args.exclude_trivial else set(symbols)

    for integ in subset:
        integ.symbols = relevant(integ.symbols)

    freq = Counter()
    for integ in subset:
        freq.update(integ.symbols)
    ranked = [s for s, _ in freq.most_common()]

    print(f"\n{'='*68}\nMOST-USED SYMBOLS  ({label}, {len(subset)} integrations)\n{'='*68}")
    for sym, count in freq.most_common(30):
        print(f"  {count:>4}  {100*count/len(subset):>5.1f}%  {sym}")

    sizes = sorted(len(i.symbols) for i in subset)
    median = sizes[len(sizes) // 2]
    print(f"\n  distinct symbols across subset : {len(freq)}")
    print(f"  median symbols per integration : {median}")
    print(f"  max symbols in one integration : {sizes[-1]}")

    # ---- the coverage curve: the number that decides feasibility ---------------------
    curve = coverage_curve(subset, ranked, args.max_budget)
    print(f"\n{'='*68}\nCOVERAGE CURVE — integrations fully runnable vs. symbols implemented\n{'='*68}")
    print(f"  {'budget':>7}  {'covered':>8}  {'share':>7}")
    for n, covered, pct in curve:
        if n <= 10 or n % 10 == 0:
            print(f"  {n:>7}  {covered:>8}  {pct:>6.1f}%")

    for target in (25, 50, 75, 90):
        hit = next((n for n, _, pct in curve if pct >= target), None)
        msg = f"{hit} symbols" if hit else f"not reached within {args.max_budget}"
        print(f"  {target}% of integrations fully covered by: {msg}")

    # ---- what to implement next ------------------------------------------------------
    budget_set = set(ranked[: args.budget])
    misses = near_misses(subset, budget_set, slack=3)
    blocking = Counter()
    for _, missing in misses:
        blocking.update(missing)

    print(f"\n{'='*68}\nCHEAPEST WINS — beyond a {args.budget}-symbol budget\n{'='*68}")
    print(f"  {len(misses)} integrations are within 3 symbols of running.")
    print("  Highest-value symbols to add next:")
    for sym, count in blocking.most_common(15):
        print(f"    unblocks {count:>3}  {sym}")

    # ---- write artefacts -------------------------------------------------------------
    with (OUT_DIR / "symbols.csv").open("w", encoding="utf-8") as fh:
        fh.write("symbol,integrations,share_pct,trivial\n")
        for sym, count in freq.most_common():
            fh.write(f'"{sym}",{count},{100*count/len(subset):.2f},{is_trivial(sym)}\n')

    with (OUT_DIR / "coverage.csv").open("w", encoding="utf-8") as fh:
        fh.write("budget,integrations_covered,share_pct\n")
        for n, covered, pct in curve:
            fh.write(f"{n},{covered},{pct:.2f}\n")

    with (OUT_DIR / "nearmiss.csv").open("w", encoding="utf-8") as fh:
        fh.write("repo,missing_count,missing_symbols\n")
        for repo, missing in sorted(misses, key=lambda x: len(x[1])):
            fh.write(f'"{repo}",{len(missing)},"{" | ".join(missing)}"\n')

    with (OUT_DIR / "integrations.json").open("w", encoding="utf-8") as fh:
        json.dump([i.to_json() for i in integrations], fh, indent=2)

    print(f"\nWrote symbols.csv, coverage.csv, nearmiss.csv, integrations.json to {OUT_DIR}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
