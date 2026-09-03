"""What must a mediator actually do to serve egress? Measured, before it is built.

§9.5 leaves one decision open and §7.18 informed it with the *declared* answer: 81% of the
corpus declares a network reach, split 41% cloud and 41% local. That settles whether to build
an egress path. It does not settle **what the path has to be**, and the design as scoped in
§5.10.3 makes three assumptions that have never been tested against a running integration:

  1. that egress is **hostnames** — the clause has no port field at all;
  2. that a name becomes an address through `socket.getaddrinfo`, which is where a mediator
     would interpose to satisfy T11's resolve-then-pin;
  3. that egress means **outbound TCP** — §5.10.3's clause cannot express UDP, multicast, or
     an inbound listener.

Each assumption, if wrong, changes the artifact rather than the prose. That is why this runs
before the proxy and not after it.

## The method, and the wall it walks around

Each integration is set up in a **full unconfined Home Assistant with real network access** and
driven through its own config flow, with `netshape` recording every resolution, connection,
datagram, TLS wrap, bind and multicast join, attributed to the integration or to the platform.

§7.18 closed by saying no observational method can answer questions about egress, because
demand appears at setup and 26 of 37 need a credential first (§7.17.1). That holds for *how
much*. It does not hold for *what shape*, because *a config flow validates a credential by
making the call*: a wrong key still produces the resolution, the connection and the handshake,
and is refused only at the last step. The mechanisms a mediator must implement have all run by
the time the 401 arrives.

**What this therefore cannot claim**: polling frequency, sustained connection counts, or how
many integrations would use egress in service. It claims the *repertoire* — which protocols,
which ports, which resolution paths, and whether anything listens.

## Credentials

Invalid by construction and non-secret by construction: no account exists behind any of them
and none is a real key's shape beyond field-name plausibility. `host` fields are answered with
**127.0.0.1**, which refuses immediately rather than hanging, so a local-protocol integration
reveals the port and transport it wanted without the run waiting on a timeout — and, usefully,
exercises exactly the non-public destination T10 is about.

Usage:

    python3 -m confine.egress_shape --corpus ~/r2exp/corpus \\
        --python ~/r2exp/ha314/bin/python --uv ~/.local/bin/uv \\
        --platform-deps ~/r2exp/platform-deps \\
        --json results/pi5_egress_shape.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .compat import (component_requirements, declared_components_of, declared_requirements,
                     find_ha_components, install_requirements)
from .endtoend import WORLD

HERE = Path(__file__).resolve().parent

# Answers to the field names config flows actually use, chosen so that a flow proceeds far
# enough to make its call. Precedence in `fill_schema` is override → default → first choice, so
# a name absent here still gets whatever the integration itself proposed.
CREDENTIALS: dict[str, object] = {
    "username": "probe@example.invalid",
    "user": "probe@example.invalid",
    "email": "probe@example.invalid",
    "password": "not-a-real-password",
    "pin": "0000",
    "code": "000000",
    "api_key": "0" * 32,
    "apikey": "0" * 32,
    "token": "0" * 40,
    "access_token": "0" * 40,
    "api_token": "0" * 40,
    "key": "0" * 32,
    "secret": "0" * 32,
    "client_id": "0" * 20,
    "client_secret": "0" * 32,
    # Refuses instantly instead of hanging, and reveals the port the integration wanted.
    "host": "127.0.0.1",
    "ip_address": "127.0.0.1",
    "address": "127.0.0.1",
    "device_ip": "127.0.0.1",
}

# The sample, and why each is in it. Selected from the 37-integration head corpus of §7.12 to
# span the *mechanisms* a proxy would have to serve rather than to be representative by count —
# §7.4.1's rule that a named set with its selection stated beats a rate that will not scale.
SAMPLE: dict[str, str] = {
    # Cloud-facing: the half §5.8.2's scope item 2 serves directly.
    "pirateweather":  "cloud_polling, no vendor library — the plainest HTTPS-to-an-API case",
    "nordpool":       "cloud_polling, public API needing no account — may complete for real",
    "dwd_weather":    "cloud_polling via httpx rather than aiohttp — a second HTTP stack",
    "solcast_solar":  "cloud_polling behind an API key — the refused-credential path",
    "alexa_media":    "cloud_polling with a login proxy; the corpus's most complex auth",
    "waste_collection_schedule": "cloud_polling, many source modules — breadth of destinations",
    # Local-facing: the half served only behind §5.10.3's non-public flag (T10).
    "localtuya":      "local_push, raw TCP on 6668 plus UDP broadcast discovery — not HTTP",
    "solarman":       "local_polling, Modbus TCP on a non-standard port — tests assumption 1",
    "midea_ac_lan":   "local_push, UDP discovery then TCP — tests assumption 3",
    "bambu_lab":      "local_push, MQTT over TLS on 8883 and FTPS — neither is HTTP",
    "frigate":        "local_push, local HTTP plus an MQTT broker",
    "sonoff":         "local_push with zeroconf — the multicast case §7.17.4 stumbled on",
}


def run_one(domain: str, component: Path, python: Path, uv: str | None,
            platform_deps: Path | None, settle: float, timeout: float,
            full_events: bool, strace: bool) -> dict:
    """One integration, unconfined, recorded. Mirrors `endtoend.run_one_unconfined`'s setup so
    the two runs differ in instrumentation and in nothing else."""
    root = Path(tempfile.mkdtemp(prefix=f"shape-{domain}-"))
    started = time.monotonic()
    try:
        config = root / "config"
        (config / "custom_components").mkdir(parents=True)
        shutil.copytree(component, config / "custom_components" / domain)
        for name in ("sandbox_runtime.py", "netshape.py", "netshape_runtime.py"):
            shutil.copy2(HERE / name, root / name)

        deps = root / "deps"
        wanted = declared_components_of(component)
        extra = component_requirements(wanted, find_ha_components(python))
        install_note = "skipped"
        if uv:
            try:
                install_requirements(declared_requirements(component) + extra, deps,
                                     python, uv)
                install_note = "ok"
            except (subprocess.TimeoutExpired, OSError) as err:
                install_note = f"{type(err).__name__}"
        deps.mkdir(parents=True, exist_ok=True)

        spec_file = root / "spec.json"
        spec_file.write_text(json.dumps({
            "domain": domain, "config_dir": str(config),
            "deps_dir": str(deps),
            "setup_components": wanted,
            "world": {k: list(v) for k, v in WORLD.items()},
            "settle_seconds": settle,
            "full_events": full_events,
            "menu_choice": {},
            "flow_input": CREDENTIALS}))

        path = [str(deps)] + ([str(platform_deps)] if platform_deps else [])
        env = {**os.environ, "PYTHONPATH": ":".join(path)}

        command = [str(python), str(root / "netshape_runtime.py"), str(spec_file)]
        trace_file = root / "strace.txt"
        if strace:
            # The kernel's account, against which the in-process recorder is checked. It
            # attributes nothing, which is exactly why the two are run together: `netshape`
            # says who and why, `strace` says whether anything was missed.
            command = ["strace", "-f", "-qq", "-e", "trace=network",
                       "-o", str(trace_file)] + command

        try:
            proc = subprocess.run(command, capture_output=True, text=True,
                                  timeout=timeout, env=env, cwd=str(root))
        except subprocess.TimeoutExpired:
            return {"domain": domain, "level": "timeout",
                    "seconds": round(time.monotonic() - started, 1)}
        text = (proc.stdout or "").strip()
        kernel = _summarise_strace(trace_file) if strace else None
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if not text:
        tail = (proc.stderr or "").strip().splitlines()
        return {"domain": domain, "level": "no_report",
                "error": tail[-1][:200] if tail else "",
                "seconds": round(time.monotonic() - started, 1)}
    report = json.loads(text.splitlines()[-1])
    if "fatal" in report:
        return {"domain": domain, "level": "fatal",
                "error": report["fatal"].strip().splitlines()[-1][:200],
                "seconds": round(time.monotonic() - started, 1)}
    report["install"] = install_note
    report["seconds"] = round(time.monotonic() - started, 1)
    report["why_selected"] = SAMPLE.get(domain, "")
    if kernel is not None:
        report["kernel"] = kernel
    return report


def _summarise_strace(path: Path) -> dict:
    """Connect and sendto destinations as the kernel saw them.

    Deliberately coarse. The point is not to reproduce `netshape` from syscalls but to answer
    one question: did anything reach the network that the in-process recorder did not see?
    """
    if not path.exists():
        return {"available": False}
    families: dict[str, int] = {}
    ports: dict[str, int] = {}
    calls: dict[str, int] = {}
    try:
        with open(path, errors="replace") as handle:
            for line in handle:
                name = line.split("(", 1)[0].split()[-1] if "(" in line else ""
                if name in ("connect", "sendto", "bind", "socket", "recvfrom"):
                    calls[name] = calls.get(name, 0) + 1
                if "sin_port=htons(" in line:
                    port = line.split("sin_port=htons(", 1)[1].split(")", 1)[0]
                    ports[port] = ports.get(port, 0) + 1
                for family in ("AF_INET6", "AF_INET", "AF_UNIX", "AF_NETLINK", "AF_PACKET"):
                    if family in line:
                        families[family] = families.get(family, 0) + 1
                        break
    except OSError:
        return {"available": False}
    return {"available": True, "calls": calls,
            "families": dict(sorted(families.items(), key=lambda kv: -kv[1])),
            "ports": dict(sorted(ports.items(), key=lambda kv: -int(kv[1]))[:20])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", required=True, type=Path)
    ap.add_argument("--python", required=True, type=Path)
    ap.add_argument("--uv", default=shutil.which("uv"))
    ap.add_argument("--platform-deps", type=Path)
    ap.add_argument("--domains", nargs="*",
                    help="override the sample; default is SAMPLE, in its stated order")
    ap.add_argument("--settle", type=float, default=20.0,
                    help="seconds to let coordinators run after the flow")
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--full-events", action="store_true",
                    help="keep the whole event list, not only the summary")
    ap.add_argument("--strace", action="store_true",
                    help="also record the kernel's account, to bound the recorder's blind spot")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    domains = args.domains or list(SAMPLE)
    reports: list[dict] = []
    for index, domain in enumerate(domains, 1):
        candidates = sorted(args.corpus.glob(f"{domain}/**/{domain}"))
        component = candidates[0] if candidates else None
        if component is None or not component.is_dir():
            found = sorted(p.parent for p in args.corpus.glob(f"{domain}/**/manifest.json"))
            component = found[0] if found else None
        if component is None:
            print(f"[{index}/{len(domains)}] {domain}: not in the corpus", file=sys.stderr)
            reports.append({"domain": domain, "level": "absent"})
            continue
        print(f"[{index}/{len(domains)}] {domain} …", file=sys.stderr, flush=True)
        report = run_one(domain, component, args.python, args.uv, args.platform_deps,
                         args.settle, args.timeout, args.full_events, args.strace)
        shape = report.get("netshape") or {}
        print(f"    {report.get('level', 'ran')}: {shape.get('events', 0)} events, "
              f"{len(shape.get('destinations') or [])} destinations, "
              f"{report.get('seconds')}s", file=sys.stderr, flush=True)
        reports.append(report)

    out = {"arm": "unconfined-recorded", "sample": SAMPLE, "reports": reports}
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(out, indent=1))
        print(f"\nwrote {args.json}", file=sys.stderr)
    else:
        print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
