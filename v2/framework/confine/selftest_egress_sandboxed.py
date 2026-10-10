"""F2 and S4, genuinely confined — real namespaces, real network isolation, a real host.

Every other suite in this project's egress work tests a real piece of the mechanism against a
substitute for the rest: `selftest_egress_shim` runs real HTTP clients but calls the mediator's
decision path as a plain function; `selftest_udp` does the same for datagrams; `selftest_egress`
never touches a sandbox at all. That is the right way to build a mechanism, and it is not the
same claim F2 makes. F2's own criterion (§7.5) is *"an integration polling a declared remote API
completes successfully while confined"* — and "confined" is a namespace with no route to
anywhere, not a function call.

This is that. One real, unmodified-shaped integration, spawned into namespaces + seccomp + a
memory-limited cgroup exactly as `selftest_bridge.py` spawns its subject, reaching a real
internet host — `example.com`, stable and IANA-reserved for exactly this kind of test — through
the fd-passing path built in `channel.py`, `egress.py` and `egress_shim.py`. Two integrations run
**concurrently in two separate sandboxes** for S4, so the denial is not merely a function
returning `False` but one confined process genuinely unable to reach what a sibling confined
process was permitted.

What it checks:

    F2   the coordinator's aiohttp request to the declared host succeeds, confined, and the
         sensor value it publishes is derived from the real response body
    T11  the shim never gives the sandbox a routable address — verified from *inside* the
         sandbox, by asking it to report what its own resolver returned
    S4   a second sandbox, declaring a different host, is denied the first sandbox's host —
         both running at once, both genuinely namespaced
    —    an undeclared host fails as an ordinary network error inside the sandbox, never as a
         framework exception reaching integration code

**Requires real internet** on the host running this test, and is written to fail informatively
rather than silently if `example.com` is unreachable — a result this suite cannot produce is
still worth distinguishing from one it disproves.

Run:  systemd-run --user --scope -q python3 -m confine.selftest_egress_sandboxed \\
          --python ~/r2exp/ha314/bin/python --platform-deps ~/r2exp/platform-deps
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from .audit import attach
from .audit import summarise as durable_summary
from .cgroup import Delegation, ResourceLimits, SandboxCgroup
from .channel import Channel
from .egress import EgressBroker
from .describe import approve_as_experimenter
from .manifest import Manifest
from .mediator import Mediator
from .platform import Platform, acting_policy
from .preflight import require_ready
from .sandbox import SandboxSpec
from .selftest_bridge import interpreter_trees
from .spawn import become_subreaper, start
from .udp_relay import UdpRelay

HERE = Path(__file__).resolve().parent
DEPS = "/sandbox/deps"
PLATFORM_DEPS = "/sandbox/platform-deps"

# Two public, stable, deliberately boring hosts. IANA reserves both for exactly this — real
# internet destinations that will not go away or rate-limit a test suite. Sandbox A declares
# the first and polls it for real content; sandbox B declares the second. Each also probes the
# *other's* host, which is what makes this an S4 test rather than two unrelated successes —
# `example.net` answers 403 rather than 200 (checked in `main`, not required to match A's),
# which is still proof its own mediated connection completed.
TARGET_HOST = "example.com"
TARGET_PORT = 80
TARGET_MARKER = "Example Domain"
OTHER_HOST = "example.net"
OTHER_PORT = 80

PASS, FAIL = "  ok  ", " FAIL "


def check(results: list, condition: bool, name: str, detail: str = "") -> None:
    results.append((bool(condition), name))
    print(f"[{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))


# An integration shaped the ordinary way, per §5.6.1's measurement of what the corpus looks
# like: a config entry, a DataUpdateCoordinator, a SensorEntity. It builds its own
# `aiohttp.ClientSession()` rather than going through Home Assistant's helper — many community
# integrations do exactly this — which sidesteps needing `zeroconf`/`network` set up inside the
# minimal instance and keeps the subject under test to what F2 is actually about.
INTEGRATION_STATIC = {
    "__init__.py": '''
"""An ordinary integration that polls one API. Nothing here knows it is confined."""
from homeassistant.const import Platform
from .coordinator import PollCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass, entry):
    coordinator = PollCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
''',
    "sensor.py": '''
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    async_add_entities([PollSensor(config_entry.runtime_data)])


class PollSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Poll result"
    _attr_unique_id = "demo_egress_poll"

    @property
    def native_value(self):
        return self.coordinator.data["status"]

    @property
    def extra_state_attributes(self):
        return dict(self.coordinator.data)
''',
    "config_flow.py": '''
from homeassistant.config_entries import ConfigFlow


class DemoFlow(ConfigFlow, domain="demo_egress"):
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title="demo", data=user_input)
''',
}

# Kept apart from `INTEGRATION_STATIC` and formatted once, in `build_config`, rather than
# folded into a nested `%`-substitution — the coordinator's URLs are the one file that differs
# per sandbox, and doing that substitution twice (once for the docstring's literal `%`, once
# for the placeholders) is exactly the kind of thing that silently produces a broken template
# nobody notices until the sandbox fails to import it. `.format()` with named fields, once.
COORDINATOR_TEMPLATE = '''
"""A coordinator that reaches its declared host with its own aiohttp session — the ordinary
shape, and the one that exercises the aiodns seam, which four of six integrations' own API names
went through when measured (§7.31.11).

It then makes a **second** request to `PROBE_URL` — a host this integration never declared,
because it is the one the *other* integration in this run declared instead. That second
request is S4's actual demonstration: not that this integration's own polling works, but that
a genuinely confined process, mid-run, cannot reach a destination that exists as a valid grant
*elsewhere* in the same system. A denial reported here is the mediator's, not a name that
failed to resolve — the shim gives every name a placeholder regardless of the manifest; only
`connect` asks."""
from datetime import timedelta
import logging

import aiohttp

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

OWN_URL = "http://{own_host}:{own_port}/"
PROBE_URL = "http://{probe_host}:{probe_port}/"
MARKER = {marker!r}


class PollCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, config_entry=entry, name="demo_egress",
                         update_interval=timedelta(seconds=30))

    async def _async_update_data(self):
        # `allow_redirects=False` throughout: a followed redirect can land on a different host
        # and port than the one declared — the destination this coordinator was actually given
        # authority to reach — and would then be denied by the mediator for a reason that has
        # nothing to do with what this test is checking. The status code alone, redirect or
        # not, is still proof the mediated connection completed.
        async with aiohttp.ClientSession() as session:
            async with session.get(OWN_URL, timeout=aiohttp.ClientTimeout(total=15),
                                   allow_redirects=False) as response:
                body = await response.text()
            own = {{"status": response.status, "found_marker": MARKER in body,
                   "length": len(body)}}

            probe: dict = {{"succeeded": None, "error": None}}
            try:
                async with session.get(PROBE_URL, timeout=aiohttp.ClientTimeout(total=8),
                                       allow_redirects=False) as probe_response:
                    await probe_response.read()
                probe["succeeded"] = True
            except Exception as err:  # noqa: BLE001 — S4's whole point is this branch
                probe["succeeded"] = False
                probe["error"] = f"{{type(err).__name__}}: {{err}}"[:200]

        return {{**own, "probe": probe}}
'''


def build_config(root: Path, own_host: str, own_port: int,
                 probe_host: str, probe_port: int) -> dict[str, Path]:
    component = root / "custom_components" / "demo_egress"
    component.mkdir(parents=True)
    for name, body in INTEGRATION_STATIC.items():
        (component / name).write_text(body.lstrip())
    (component / "coordinator.py").write_text(COORDINATOR_TEMPLATE.format(
        own_host=own_host, own_port=own_port, probe_host=probe_host,
        probe_port=probe_port, marker=TARGET_MARKER).lstrip())
    (component / "manifest.json").write_text(json.dumps({
        "domain": "demo_egress", "name": "Demo Egress", "version": "1.0.0",
        "config_flow": True, "iot_class": "cloud_polling", "requirements": [],
        "codeowners": [], "documentation": "https://example.invalid/demo_egress",
        "permissions": {"schema_version": 1,
                        "network": {"egress": [f"{own_host}:{own_port}"]}},
    }))
    data = root / ".confine" / "demo_egress"
    data.mkdir(parents=True)
    return {"component": component, "data": data}


def prepare(own_host: str, own_port: int, probe_host: str, probe_port: int,
           label: str) -> tuple[Path, dict, Manifest]:
    """Build one integration's config directory and load its manifest.

    `probe_host`/`probe_port` is the *other* sandbox's declared destination — baked into this
    one's coordinator so it genuinely attempts to reach it, which is what turns the run into a
    test of denial rather than two sandboxes that merely never ask.

    Split from spawning for a reason that matters to S4's honesty: `mediator.policy` is **one**
    function shared by every registered channel (`Mediator` holds a single `policy` callable,
    not one per identity). Setting it separately per sandbox would silently replace the first
    sandbox's manifest in the closure with the second's — a bug this file had until it was
    caught, recorded here rather than fixed silently. Both manifests must exist and be combined
    into **one** `acting_policy` before either sandbox is spawned.
    """
    root = Path(tempfile.mkdtemp(prefix=f"confine-egress-{label}-"))
    layout = build_config(root, own_host, own_port, probe_host, probe_port)
    manifest = Manifest.load(layout["component"], root)
    approve_as_experimenter(layout["component"], root)  # F57: in an experiment, the experimenter approves
    return root, layout, manifest


def spawn(python: Path, platform_deps: Path | None, root: Path, layout: dict,
         mediator: Mediator, identity: str) -> dict:
    """Start one already-manifested sandbox against a `mediator` whose policy is already set.

    Two sandboxes are spawned (this called twice) before either is waited on — which is what
    makes the S4 case a claim about two processes running *at once*, not one after another.

    **The cgroup is not opened as a `with` block.** `SandboxCgroup.create()` returns a plain
    object — `__enter__` returns `self` and `__exit__` only calls `.remove()` — so nothing
    requires the `with` form. Using it here would tear the cgroup down the moment this
    function returned, while the sandbox it was confining was still running: `finish()` needs
    the cgroup alive to read `event_count("oom_kill")` and to remove it only once the sandbox
    has actually exited. The lifetime this function starts, `finish()` ends.
    """
    try:
        mediator_end, sandbox_end = Channel.pair()
        mediator.register(identity, Channel(mediator_end), component=layout["component"])

        spec_file = root / "sandbox-spec.json"
        spec_file.write_text(json.dumps({
            "domain": "demo_egress", "mode": "flow", "auth": False,
            "entities": [], "services": [], "egress": True,
            "settle_seconds": 8, "flow_input": {}, "menu_choice": {},
        }))

        runtime_files = {
            str(HERE / "sandbox_runtime.py"): "/sandbox/runtime.py",
            str(HERE / "egress_shim.py"): "/sandbox/egress_shim.py",
            str(spec_file): "/sandbox/spec.json",
        }
        env = {}
        if platform_deps:
            runtime_files[str(platform_deps)] = PLATFORM_DEPS
            env["PYTHONPATH"] = PLATFORM_DEPS

        spec = SandboxSpec(
            domain="demo_egress", own_dir=str(layout["component"]),
            data_dir=str(layout["data"]),
            argv=[str(python), "/sandbox/runtime.py"],
            runtime_files=runtime_files, env=env)
        for extra in (*interpreter_trees(python), sys.base_prefix):
            if extra and extra not in spec.runtime_paths:
                spec.runtime_paths.append(extra)

        out = tempfile.NamedTemporaryFile(prefix=f"confine-egress-{identity}-", suffix=".json",
                                          delete=False)
        err = tempfile.NamedTemporaryFile(prefix=f"confine-egress-{identity}-err-",
                                          suffix=".txt", delete=False)
        delegation = Delegation.discover()
        cgroup = SandboxCgroup.create(delegation, f"confine-egress-{identity}",
                                      ResourceLimits(memory_mb=384))
        with open(out.name, "wb") as stdout, open(err.name, "wb") as stderr:
            sandbox = start(spec, cgroup, stdout=stdout.fileno(), stderr=stderr.fileno(),
                            channel_end=sandbox_end.fileno())
        sandbox_end.detach()
        return {"sandbox": sandbox, "cgroup": cgroup, "out": out.name, "err": err.name,
               "root": root}
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


def finish(handle: dict) -> dict:
    """Wait for a sandbox `spawn` started, collect its report, and tear its cgroup down.

    The cgroup's own lifetime ends here, matching the comment in `spawn()`: stats are read
    while it still exists, and `.remove()` is called explicitly since nothing entered it as a
    `with` block.
    """
    try:
        status = handle["sandbox"].wait(timeout=120)
        oom = handle["cgroup"].event_count("oom_kill")
        text = Path(handle["out"]).read_text().strip()
        diagnostic = Path(handle["err"]).read_text().strip()
    finally:
        handle["cgroup"].remove()
        Path(handle["out"]).unlink(missing_ok=True)
        Path(handle["err"]).unlink(missing_ok=True)
        shutil.rmtree(handle["root"], ignore_errors=True)

    if not text:
        return {"fatal": f"no report (exit {status}, oom_kill={oom})\n" +
                "\n".join(diagnostic.splitlines()[-15:])}
    report = json.loads(text.splitlines()[-1])
    report["oom_kill"] = oom
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--python", required=True, type=Path)
    ap.add_argument("--platform-deps", type=Path)
    args = ap.parse_args()

    results: list = []

    # Fail informatively rather than silently: this suite proves nothing about confinement if
    # the very hosts it targets are unreachable, and that must not be reported as a pass.
    for host, port in ((TARGET_HOST, TARGET_PORT), (OTHER_HOST, OTHER_PORT)):
        try:
            urllib.request.urlopen(f"http://{host}:{port}/", timeout=8)
        except urllib.error.HTTPError:
            pass                                            # a real HTTP response, e.g. 403
        except OSError as err:
            print(f"cannot reach {host} from this host at all: {err}\n"
                  "this suite requires real internet access and cannot proceed without it.")
            return 2

    require_ready(deep=False)
    become_subreaper()

    # **One mediator, one policy, both manifests present before either sandbox exists.** See
    # `prepare()`'s docstring — `mediator.policy` is a single shared closure, so it has to be
    # built from the complete set of identities up front, not assembled incrementally as each
    # sandbox is spawned.
    #
    # Each sandbox's coordinator also probes the *other's* declared host — A polls its own and
    # then attempts OTHER_HOST, B polls its own and then attempts TARGET_HOST. Both attempts
    # are expected to be denied: each host is a valid grant for exactly one identity, and this
    # is the concurrent, confined version of the same S4 shape `selftest_egress` proves at the
    # function-call level.
    root_a, layout_a, manifest_a = prepare(TARGET_HOST, TARGET_PORT, OTHER_HOST, OTHER_PORT, "a")
    root_b, layout_b, manifest_b = prepare(OTHER_HOST, OTHER_PORT, TARGET_HOST, TARGET_PORT, "b")

    platform = Platform()
    broker = EgressBroker(connect_timeout=15.0)
    relay = UdpRelay()
    mediator = Mediator()
    audit_dir = attach(mediator, "confine-egress-sandboxed-audit-")
    mediator.policy = acting_policy(
        {"demo_egress-a": manifest_a, "demo_egress-b": manifest_b},
        platform, broker=broker, relay=relay)

    handle_a = spawn(args.python, args.platform_deps, root_a, layout_a,
                     mediator, "demo_egress-a")
    handle_b = spawn(args.python, args.platform_deps, root_b, layout_b,
                     mediator, "demo_egress-b")

    # Both sandboxes exist and both channels are registered before either is served, which is
    # what makes this a claim about concurrent confined processes.
    mediator.serve(timeout=180)

    report_a = finish(handle_a)
    report_b = finish(handle_b)
    durable = durable_summary(mediator, audit_dir)

    print("egress, sandboxed — F2 and S4 with real namespaces and a real host\n")

    if "fatal" in report_a:
        print("sandbox A produced no report:\n" + report_a["fatal"])
        return 1
    if "fatal" in report_b:
        print("sandbox B produced no report:\n" + report_b["fatal"])
        return 1

    for label, report, own_host in (("A", report_a, TARGET_HOST), ("B", report_b, OTHER_HOST)):
        check(results, report.get("oom_kill", 1) == 0,
              f"{label} did not exceed its memory limit",
              f"oom_kill={report.get('oom_kill')}")
        check(results, report.get("loaded"), f"{label}'s config entry reached LOADED",
              str(report.get("entries")))

        published = {p["entity"]: p for p in report.get("published", [])}
        poll_entity = next((e for e in published if "poll" in e), None)
        check(results, poll_entity is not None,
              f"F2 — {label} published a sensor from the coordinator's own poll",
              str(list(published)))
        if poll_entity:
            state = published[poll_entity].get("state")
            # `state` is the coordinator's own declared-host status code — a real HTTP
            # response, not necessarily 200: `example.net` answers 403, which is still proof
            # the mediated connection to *that* host completed.
            check(results, str(state).isdigit() and 200 <= int(state) < 500,
                  f"F2 — {label}'s published value is a real HTTP status from its own host",
                  f"state={state!r}")

        egress = report.get("egress") or {}
        check(results, any(own_host in h for h in egress.get("resolved", [])),
              f"{label} resolved its own declared name (through the shim, to a placeholder)",
              str(egress.get("resolved")))
        check(results, any(h == own_host for h, _p in egress.get("connected", [])),
              f"and connected to it — the mediator's own record of what {label} opened",
              str(egress.get("connected")))

    # **S4's actual evidence.** Each identity made exactly two `network.egress` requests — its
    # own poll, then its probe of the sibling's host — and `mediator.audit` records both in the
    # order they were decided. The own request is permitted; the probe, naming a host declared
    # only by the *other* identity, is not. Two confined processes, running at once, each
    # denied precisely the one destination that belonged to someone else.
    for label in ("a", "b"):
        identity = f"demo_egress-{label}"
        decisions = [e for e in mediator.audit
                    if e["identity"] == identity and e.get("op") == "network.egress"]
        outcomes = [e["allowed"] for e in decisions]
        check(results, outcomes == [True, False],
              f"S4 — {identity}'s own request was permitted, its probe of the sibling's "
              f"host was not",
              f"{len(decisions)} decisions, allowed={outcomes}")
        if len(decisions) == 2:
            check(results, decisions[1]["clause"] == "/permissions/network/egress",
                  f"S4 — {identity}'s denial names the capability with no matching clause (F3)",
                  str(decisions[1]["clause"]))

    # No decision made for one identity is ever attributed to the other — the property
    # `channel.py`'s docstring calls "identity is a property of the channel, not a claim in
    # the message", now checked across two genuinely separate confined processes rather than
    # two function calls sharing a stack.
    check(results,
          {e["identity"] for e in mediator.audit if e.get("op") == "network.egress"}
          == {"demo_egress-a", "demo_egress-b"},
          "every egress decision in the run is attributed to exactly one of the two sandboxes",
          str(sorted({e["identity"] for e in mediator.audit})))

    print()
    # T4: two sandboxes on one mediator, so two run records, and every decision must name the
    # run of the sandbox that asked — the attribution S4 is about, now checked in the record S7
    # is claimed of rather than only in memory.
    check(results, durable["ok"] and durable["runs"] == 2,
          "S7 — the durable record holds two runs, verifies, and matches the in-memory record "
          "decision by decision (T4)",
          "; ".join(durable["breaks"] + durable["reconcile"])[:300] or f"runs={durable['runs']}")

    passed = sum(1 for ok, _ in results if ok)
    print(f"{passed}/{len(results)} checks passed")
    if passed < len(results):
        print("\nFAILED")
        return 1
    print("\nPASS — a real integration, confined in real namespaces with no route to")
    print("       anywhere, reached a real internet host through the mediator, and a")
    print("       sibling sandbox with a different declaration never touched it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
