"""How much of the corpus reaches for UDP, counted over 77 integrations rather than 12.

§7.24.4 found UDP in one integration of twelve and recommended refusing it. That recommendation
rested on a denominator too small to carry it: twelve integrations, driven through config flows
rather than run in service, is not evidence about what an ecosystem needs. The objection is
correct and this is the answer to it.

**Method.** Parse every `.py` file in each integration with `ast` and record the markers that
can only mean datagram networking — `SOCK_DGRAM`, `create_datagram_endpoint`, a
`DatagramProtocol` subclass, `sendto`/`recvfrom`, and the broadcast and multicast socket options.
The same pass records stream markers for contrast, so the answer is a *share* and not a count in
isolation.

Run over both corpora the report already defends: the 37 most-installed (§7.12) and the 40
uniform-sample (§7.23). They overlap in 2, so the population is 75 distinct integrations.

**Why static, when §7.24 was dynamic.** They fail in opposite directions, which is the point.
Running an integration proves a code path is taken but only the paths the run reached — §7.24
never got 6 of 12 past their login screens. Reading the source sees every path but cannot tell a
live one from dead code. **A marker found statically is a capability the author wrote down; a
call seen dynamically is one that actually ran.** Neither alone answers "does the ecosystem need
UDP", and the pair brackets it: static is an upper bound, dynamic a lower one.

`midea_ac_lan` is the calibration. §7.24 caught it sending 18 datagrams from
`config_flow.py:406`, its own source, so this scan must find it. A scanner that misses a case the
dynamic arm proved is broken, and one that finds only that case has no reach.

**The blind spot was not hypothetical, and finding that out is the main result.** The first run
scanned integrations' own source only, and the calibration check failed: it did not find
`midea_ac_lan`. The reason is that `config_flow.py:406` calls `discover()` from **`midea-lan`, a
declared dependency** — the integration's own source contains no datagram code whatever. The
dynamic recorder charged it to the integration because that was the integration's frame on the
stack, which is correct attribution of *responsibility* and says nothing about where the socket
code lives.

So an own-source scan systematically undercounts, and it undercounts in exactly the place local
device protocols live: the vendor library an integration declares precisely so it does not have
to implement the protocol itself. `--deps` therefore installs each integration's declared
requirements and scans those too, reporting the two populations separately, because they are
different claims: **own-source UDP is code the author wrote; dependency UDP is a capability the
author's chosen library needs, which the sandbox must serve just the same.**

Usage:
    python3 udp_demand.py ~/r2exp/corpus ~/r2exp/corpus_uniform
    python3 udp_demand.py --deps --python ~/r2exp/ha314/bin/python --uv ~/.local/bin/uv \\
        ~/r2exp/corpus ~/r2exp/corpus_uniform
"""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "framework"))
from confine.compat import RESOLVE_BEFORE  # noqa: E402  (F13: the same fixed resolution moment)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "framework"))
from confine.provenance import record_run  # noqa: E402  (F14)

# Markers that mean datagrams and cannot mean anything else.
UDP_NAMES = {"SOCK_DGRAM", "DatagramProtocol", "DatagramTransport"}
UDP_CALLS = {"create_datagram_endpoint", "sendto", "recvfrom", "recvfrom_into"}
UDP_OPTIONS = {"SO_BROADCAST", "IP_ADD_MEMBERSHIP", "IP_DROP_MEMBERSHIP",
               "IP_MULTICAST_TTL", "IP_MULTICAST_LOOP", "IP_MULTICAST_IF",
               "IPV6_JOIN_GROUP", "IPV6_LEAVE_GROUP", "IPV6_MULTICAST_HOPS"}

# The same for streams, so the result is a share rather than a bare count.
TCP_NAMES = {"SOCK_STREAM"}
TCP_CALLS = {"create_connection", "open_connection", "create_server", "connect_ex"}

# **Packages whose datagram code is almost certainly not the integration's reason for
# installing them.** A static scan of a dependency tree finds every marker in it, including in
# code paths nothing calls: `botocore` is the AWS SDK, `anyio` a general async runtime,
# `psutil` a system-information library, `pytest_asyncio` a *test* framework. Each contains
# datagram support somewhere; none is why an integration declared it.
#
# Excluding them is a judgement and is therefore made explicit and by name rather than folded
# into the total. The result is reported as a **range**: own-source is what an author certainly
# wrote, device-protocol dependencies are what an author's chosen protocol library needs, and
# the raw figure including these is the ceiling.
GENERAL_PURPOSE = {"anyio", "botocore", "psutil", "pytest_asyncio", "pyric", "urllib3",
                   "requests", "httpx", "h11", "certifi", "attrs", "setuptools"}


def scan_file(path: Path) -> dict[str, list[str]]:
    """Markers in one file, each with the line that carries it."""
    try:
        tree = ast.parse(path.read_text(errors="replace"))
    except (SyntaxError, ValueError, OSError):
        return {}

    found: dict[str, list[str]] = {}

    def note(kind: str, marker: str, lineno: int) -> None:
        found.setdefault(kind, []).append(f"{marker}@{path.name}:{lineno}")

    for node in ast.walk(tree):
        # `socket.SOCK_DGRAM`, `SO_BROADCAST`, a bare `SOCK_DGRAM` import — all attribute or
        # name references, so both node types are checked rather than assuming one style.
        name = None
        if isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, ast.Name):
            name = node.id
        if name is not None:
            if name in UDP_NAMES:
                note("udp", name, node.lineno)
            elif name in UDP_OPTIONS:
                note("udp_option", name, node.lineno)
            elif name in TCP_NAMES:
                note("tcp", name, node.lineno)

        if isinstance(node, ast.Call):
            func = node.func
            called = getattr(func, "attr", None) or getattr(func, "id", None)
            if called in UDP_CALLS:
                note("udp", called, node.lineno)
            elif called in TCP_CALLS:
                note("tcp", called, node.lineno)

        # A class inheriting DatagramProtocol is the asyncio idiom and would otherwise be
        # counted only by the base-name reference above; kept explicit so the reason is legible.
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = getattr(base, "attr", None) or getattr(base, "id", None)
                if base_name in UDP_NAMES:
                    note("udp", f"class {node.name}({base_name})", node.lineno)

    return found


def scan_integration(root: Path) -> dict:
    markers: dict[str, list[str]] = {}
    files = 0
    for path in sorted(root.rglob("*.py")):
        files += 1
        for kind, hits in scan_file(path).items():
            markers.setdefault(kind, []).extend(hits)
    udp = markers.get("udp", []) + markers.get("udp_option", [])
    return {"domain": root.name, "py_files": files,
            "udp": udp, "tcp": markers.get("tcp", []),
            "uses_udp": bool(udp), "uses_tcp": bool(markers.get("tcp"))}


def iot_class_of(root: Path) -> str:
    for manifest in root.rglob("manifest.json"):
        try:
            return json.loads(manifest.read_text()).get("iot_class") or "none"
        except (ValueError, OSError):
            return "unreadable"
    return "none"


def declared_requirements(root: Path) -> list[str]:
    for manifest in root.rglob("manifest.json"):
        try:
            return list(json.loads(manifest.read_text()).get("requirements") or [])
        except (ValueError, OSError):
            return []
    return []


def scan_dependencies(root: Path, python: str, uv: str, timeout: float = 300.0) -> dict:
    """Install what the integration declares, and scan that for the same markers.

    Installed into a throwaway directory per integration rather than a shared one, so that a
    package pulled in by one integration cannot be attributed to another — the same collision
    §7.24.8 records the credential set falling into.
    """
    requirements = declared_requirements(root)
    if not requirements:
        return {"declared": 0, "installed": False, "udp": [], "note": "no requirements declared"}

    target = Path(tempfile.mkdtemp(prefix=f"udpdeps-{root.name}-"))
    try:
        try:
            subprocess.run([uv, "pip", "install", "--python", python, "--target", str(target),
                            "--quiet", "--exclude-newer", RESOLVE_BEFORE, *requirements],
                           capture_output=True, text=True, timeout=timeout, check=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as err:
            return {"declared": len(requirements), "installed": False, "udp": [],
                    "note": type(err).__name__}

        markers: list[str] = []
        packages: set[str] = set()
        for path in sorted(target.rglob("*.py")):
            hits = scan_file(path)
            found = hits.get("udp", []) + hits.get("udp_option", [])
            if found:
                relative = path.relative_to(target)
                packages.add(relative.parts[0])
                markers.extend(f"{relative.parts[0]}:{m}" for m in found[:2])
        return {"declared": len(requirements), "installed": True,
                "udp": markers[:8], "packages": sorted(packages), "note": ""}
    finally:
        shutil.rmtree(target, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("corpora", nargs="*",
                    default=["~/r2exp/corpus", "~/r2exp/corpus_uniform"])
    ap.add_argument("--deps", action="store_true",
                    help="also install and scan each integration's declared requirements")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--uv", default=shutil.which("uv") or "uv")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    corpora = [Path(p).expanduser() for p in args.corpora]
    seen: dict[str, dict] = {}
    origin: dict[str, list[str]] = {}

    for corpus in corpora:
        if not corpus.is_dir():
            print(f"missing: {corpus}", file=sys.stderr)
            continue
        for entry in sorted(corpus.iterdir()):
            if not entry.is_dir():
                continue
            origin.setdefault(entry.name, []).append(corpus.name)
            if entry.name in seen:
                continue
            report = scan_integration(entry)
            report["iot_class"] = iot_class_of(entry)
            if args.deps:
                print(f"  deps: {entry.name} …", file=sys.stderr, flush=True)
                report["deps"] = scan_dependencies(entry, args.python, args.uv)
            seen[entry.name] = report

    reports = list(seen.values())
    udp = [r for r in reports if r["uses_udp"]]
    def protocol_packages(report: dict) -> list[str]:
        return [p for p in ((report.get("deps") or {}).get("packages") or [])
                if p not in GENERAL_PURPOSE]

    dep_udp = [r for r in reports if (r.get("deps") or {}).get("udp")]
    dep_protocol = [r for r in reports if protocol_packages(r)]
    either = [r for r in reports if r["uses_udp"] or (r.get("deps") or {}).get("udp")]
    likely = [r for r in reports if r["uses_udp"] or protocol_packages(r)]

    print(f"# UDP demand across {len(reports)} distinct integrations")
    print(f"\nCorpora: {', '.join(c.name for c in corpora)}; "
          f"{sum(1 for v in origin.values() if len(v) > 1)} appear in both.\n")

    print(f"| Where the datagram code is | Integrations | Share |")
    print(f"|---|---|---|")
    print(f"| the integration's own source | {len(udp)} | "
          f"{len(udp) / len(reports) * 100:.0f}% |")
    if args.deps:
        scanned = [r for r in reports if (r.get("deps") or {}).get("installed")]
        no_reqs = [r for r in reports if (r.get("deps") or {}).get("declared") == 0]
        failed = [r for r in reports
                  if (r.get("deps") or {}).get("declared") and
                  not (r.get("deps") or {}).get("installed")]
        print(f"| a **device-protocol dependency** | {len(dep_protocol)} | "
              f"{len(dep_protocol) / len(reports) * 100:.0f}% |")
        print(f"| **own source or a protocol library** | **{len(likely)}** | "
              f"**{len(likely) / len(reports) * 100:.0f}%** |")
        print(f"| any dependency, incl. general-purpose (ceiling) | {len(either)} | "
              f"{len(either) / len(reports) * 100:.0f}% |")
        print(f"\nDependency scan: {len(scanned)} installed, {len(no_reqs)} declare no "
              f"requirements, {len(failed)} failed to install.\n")
    else:
        print("\n*(own source only — run with `--deps` for the other half)*\n")

    print("## By declared iot_class\n")
    print("| `iot_class` | total | with UDP | share |")
    print("|---|---|---|---|")
    by_class: Counter = Counter(r["iot_class"] for r in reports)
    udp_by_class: Counter = Counter(r["iot_class"] for r in udp)
    for name, total in by_class.most_common():
        hits = udp_by_class.get(name, 0)
        print(f"| `{name}` | {total} | {hits} | {hits / total * 100:.0f}% |")

    print("\n## The integrations, and what was found\n")
    print("| Integration | `iot_class` | markers |")
    print("|---|---|---|")
    for report in sorted(udp, key=lambda r: r["domain"]):
        markers = ", ".join(sorted(set(report["udp"]))[:4])
        print(f"| `{report['domain']}` | {report['iot_class']} | {markers} |")

    if args.deps and dep_udp:
        print("\n## Datagram code found in declared dependencies\n")
        print("| Integration | `iot_class` | packages |")
        print("|---|---|---|")
        for report in sorted(dep_udp, key=lambda r: r["domain"]):
            protocol = protocol_packages(report)
            general = [p for p in (report["deps"].get("packages") or [])
                       if p in GENERAL_PURPOSE]
            marks = ", ".join(f"**{p}**" for p in protocol[:4])
            if general:
                marks += (", " if marks else "") + ", ".join(f"{p} (general)"
                                                             for p in general[:3])
            print(f"| `{report['domain']}` | {report['iot_class']} | {marks} |")

    calibration = seen.get("midea_ac_lan")
    print("\n## Calibration\n")
    if calibration is None:
        print("`midea_ac_lan` is not in these corpora — the scan is uncalibrated.")
    elif calibration["uses_udp"]:
        print(f"`midea_ac_lan` is found in its **own source**: "
              f"{', '.join(sorted(set(calibration['udp']))[:3])}.")
    elif (calibration.get("deps") or {}).get("udp"):
        print(f"`midea_ac_lan` has **no datagram code of its own** and is found in a declared "
              f"dependency: {', '.join((calibration['deps'].get('packages') or [])[:3])}. This "
              f"is the calibration passing in the more informative way — §7.24 observed the "
              f"datagrams and charged them to `config_flow.py:406`, which is where the *call* "
              f"is made, not where the socket code lives. An own-source scan alone would have "
              f"reported this integration as needing no UDP.")
    elif args.deps:
        print("**`midea_ac_lan` is found in neither its source nor its dependencies, and §7.24 "
              "watched it send 18 datagrams. The scanner is wrong and its figures should not "
              "be used.**")
    else:
        print("`midea_ac_lan` is not in its own source. Re-run with `--deps` before drawing "
              "any conclusion — that is where §7.24's observed datagrams turned out to live.")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({"reports": reports}, indent=1))
        record_run(args.json)  # F14: how this result was produced, beside it
        print(f"\nwrote {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
