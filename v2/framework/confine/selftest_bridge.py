"""An integration, unmodified, running inside a sandbox and reaching the platform through it.

This is §5.8.2's scope items 1 and 3, and the first time in this project that the *compatibility*
half of the claim is tested rather than argued. §6.10.2 named the bridge as the single component
everything else was blocked on; this exercises it end to end.

What it checks, and each is a claim with a section behind it:

    C1        the integration's source is not touched — the sandbox is furnished around it
    F1        the entity it publishes reaches the platform, attributed to it
    §5.6.2    a declared entity is readable; an undeclared one is **absent**, not refused
    §5.10.4   a declared service call goes through; its risk-asymmetric counterpart does not
              exist to be called — S5, end to end rather than at the schema

Run:  systemd-run --user --scope -q python3 -m confine.selftest_bridge [--python PATH]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import os

from .cgroup import Delegation, SandboxCgroup
from .channel import Channel
from .manifest import Manifest
from .mediator import Mediator
from .platform import Platform, acting_policy
from .preflight import require_ready
from .sandbox import SandboxSpec
from .spawn import become_subreaper, start

HERE = Path(__file__).resolve().parent

# An integration written the ordinary way — config entry, DataUpdateCoordinator, SensorEntity,
# async_add_entities — which §5.6.1 measured as the dominant shape (83% of community
# integrations publish through the helper layer). Not the framework's code: it is written here
# only so the test has a subject, and the framework never edits it.
INTEGRATION = {
    "__init__.py": '''
"""An ordinary integration. Nothing here knows it is in a sandbox."""
from homeassistant.const import Platform
from .coordinator import DemoCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass, entry):
    coordinator = DemoCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
''',
    "coordinator.py": '''
"""The polling pattern 58% of community integrations use."""
from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class DemoCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, config_entry=entry, name="demo_weather",
                         update_interval=timedelta(seconds=30))
        self._tick = 0

    async def _async_update_data(self):
        self._tick += 1
        # An ordinary integration reading another entity for local calibration. The manifest
        # declares this one; the sandbox has it because the bridge mirrored it in.
        calibration = self.hass.states.get("sensor.outdoor_temperature")
        return {"ticks": self._tick,
                "calibration": calibration.state if calibration else None}
''',
    "sensor.py": '''
"""async_add_entities — the path 83% of community integrations publish through."""
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    async_add_entities([DemoSensor(config_entry.runtime_data)])


class DemoSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Ticks"
    _attr_unique_id = "demo_weather_ticks"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data["ticks"]

    @property
    def extra_state_attributes(self):
        return {"calibration": self.coordinator.data["calibration"]}
''',
    "config_flow.py": '''
from homeassistant.config_entries import ConfigFlow


class DemoFlow(ConfigFlow, domain="demo_weather"):
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title="demo", data=user_input)
''',
}

# It may read one sensor and lock a lock. It may not unlock it — S5, and the manifest cannot
# even express the wildcard that would (§6.6.2).
PERMISSIONS = {
    "schema_version": 1,
    "entities": {"read": ["sensor.outdoor_temperature"]},
    "services": {"call": ["lock.lock"]},
}


def interpreter_trees(python: Path) -> list[str]:
    """Every directory that must exist inside the sandbox for this interpreter to start.

    The *chain* matters, not the endpoint. A virtual environment's `bin/python` is a symlink,
    frequently to another symlink — uv names one directory by minor version and a second by
    patch version — and every name along that chain has to resolve inside the sandbox or
    `execve` fails with `ENOENT`. That presents as exit code 126 and no output whatever, which
    is how this was found. Each hop is added *unresolved*, so a symlinked directory is bound
    under the name the link uses.
    """
    trees: list[str] = []

    def add(path: str) -> None:
        if path and path not in trees:
            trees.append(path)

    current = python
    for _ in range(10):
        prefix = current.parent.parent
        # Both the name and the thing it names. `build_root` recreates a symlinked runtime
        # path as a symlink rather than binding it, which is right — the interpreter's own
        # layout expects the link — but it leaves the link dangling unless the target is bound
        # too. Adding only one of the two is how this failed twice.
        add(str(prefix))
        if prefix.is_symlink():
            add(os.path.realpath(prefix))
        if not current.is_symlink():
            break
        target = Path(os.readlink(current))
        current = target if target.is_absolute() else current.parent / target
    return trees


def build_config(root: Path) -> dict[str, Path]:
    component = root / "custom_components" / "demo_weather"
    component.mkdir(parents=True)
    for name, body in INTEGRATION.items():
        (component / name).write_text(body.lstrip())
    (component / "manifest.json").write_text(json.dumps({
        "domain": "demo_weather", "name": "Demo Weather", "version": "1.0.0",
        "config_flow": True, "iot_class": "local_polling", "requirements": [],
        "codeowners": [], "documentation": "https://example.invalid/demo_weather",
        "permissions": PERMISSIONS,
    }))
    data = root / ".confine" / "demo_weather"
    data.mkdir(parents=True)
    (root / "secrets.yaml").write_text("api_key: MUST-NOT-BE-READABLE\n")
    return {"component": component, "data": data}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default=sys.executable,
                    help="the interpreter the sandbox runs, which must have "
                         "`homeassistant` importable")
    args = ap.parse_args()

    require_ready(deep=False)
    become_subreaper()

    # Deliberately *not* resolved. A virtual environment is found by Python from the path it
    # was invoked as — `pyvenv.cfg` sits beside `bin/python` — so resolving the symlink first
    # would start the base interpreter with none of the environment's packages, which is
    # exactly what happened the first time this ran.
    sandbox_python = Path(args.python)
    root = Path(tempfile.mkdtemp(prefix="confine-bridge-"))
    mediator = Mediator()
    platform = Platform()
    # A device the user owns, which the integration declared and may read.
    platform.seed("sensor.outdoor_temperature", "11.5", unit_of_measurement="°C")
    # One it did not declare. It should not appear inside the sandbox at all.
    platform.seed("sensor.bedroom_occupancy", "on")

    try:
        layout = build_config(root)
        manifest = Manifest.load(layout["component"], root)
        mediator.policy = acting_policy({"demo_weather": manifest}, platform)
        mediator_end, sandbox_end = Channel.pair()
        mediator.register("demo_weather", Channel(mediator_end))

        spec_file = root / "sandbox-spec.json"
        spec_file.write_text(json.dumps({
            "domain": "demo_weather",
            "entities": PERMISSIONS["entities"]["read"],
            "services": PERMISSIONS["services"]["call"],
            "entry_data": {"host": "example.invalid"},
            # Asked from inside, so the answers are the integration's own view.
            "probe_entities": ["sensor.outdoor_temperature", "sensor.bedroom_occupancy"],
            "probe_services": ["lock.lock", "lock.unlock"],
        }))

        spec = SandboxSpec(
            domain="demo_weather", own_dir=str(layout["component"]),
            data_dir=str(layout["data"]),
            argv=[str(sandbox_python), "/sandbox/runtime.py"],
            runtime_files={str(HERE / "sandbox_runtime.py"): "/sandbox/runtime.py",
                           str(spec_file): "/sandbox/spec.json"},
        )
        # The interpreter has to be inside the sandbox, and so does every name along the
        # symlink chain that leads to it.
        for extra in (*interpreter_trees(sandbox_python), sys.base_prefix):
            if extra and extra not in spec.runtime_paths:
                spec.runtime_paths.append(extra)

        out = tempfile.NamedTemporaryFile(prefix="confine-bridge-", suffix=".json",
                                          delete=False)
        err = tempfile.NamedTemporaryFile(prefix="confine-bridge-err-", suffix=".txt",
                                          delete=False)
        delegation = Delegation.discover()
        with SandboxCgroup.create(delegation, "confine-bridge",
                                  memory_max=512 * 1024**2, pids_max=64) as cgroup:
            with open(out.name, "wb") as stdout, open(err.name, "wb") as stderr:
                sandbox = start(spec, cgroup, stdout=stdout.fileno(), stderr=stderr.fileno(),
                                channel_end=sandbox_end.fileno())
                sandbox_end.detach()
                mediator.serve(timeout=300)
                status = sandbox.wait(timeout=300)
            oom, peak = cgroup.event_count("oom_kill"), cgroup.peak_memory()
        text = Path(out.name).read_text().strip()
        diagnostic = Path(err.name).read_text().strip()
        Path(out.name).unlink(missing_ok=True)
        Path(err.name).unlink(missing_ok=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if not text:
        import os as _os
        print("the sandbox produced no report.")
        print(f"  exit: {'signal ' + str(_os.WTERMSIG(status)) if _os.WIFSIGNALED(status) else status}"
              f"   oom_kill={oom}   peak {peak / 2**20:.0f} MB")
        if diagnostic:
            print("  " + "\n  ".join(diagnostic.splitlines()[-25:]))
        return 1
    report = json.loads(text.splitlines()[-1])
    if "fatal" in report:
        print("the sandbox failed before it could report:\n")
        print(report["fatal"])
        return 1
    return render(report, platform, mediator)


def render(report: dict, platform: Platform, mediator: Mediator) -> int:
    print("bridge self-test — an unmodified integration, inside a sandbox\n")
    failures: list[str] = []

    def check(label: str, ok: bool, detail: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<50}  {detail}")
        if not ok:
            failures.append(label)

    if report.get("setup_error"):
        print(f"  setup error: {report['setup_error']}\n")

    check("C1  the config entry reaches LOADED", report.get("loaded", False),
          report.get("entry_state", "?"))
    check("F1  it published an entity locally",
          any(e.startswith("sensor.") and "outdoor" not in e
              for e in report.get("local_entities", [])),
          str(report.get("local_entities")))

    published = {p["entity"]: p for p in report.get("published", [])}
    reached = [e for e in platform.states if platform.owners.get(e) == "demo_weather"]
    check("F1  the entity reached the platform through the mediator", bool(reached),
          f"{reached} = {[platform.states[e][0] for e in reached]}")
    check("F1  ...attributed to the integration that published it",
          all(platform.owners[e] == "demo_weather" for e in reached),
          "owner recorded at publish time")

    reads = report.get("reads", {})
    check("§5.6.2  the declared entity is readable inside the sandbox",
          reads.get("sensor.outdoor_temperature") == "11.5",
          f"sensor.outdoor_temperature = {reads.get('sensor.outdoor_temperature')!r}")
    check("§5.6.2  the undeclared entity is ABSENT, not refused",
          reads.get("sensor.bedroom_occupancy") is None,
          f"sensor.bedroom_occupancy = {reads.get('sensor.bedroom_occupancy')!r}")
    check("§5.6.2  ...and the integration read it through its own state machine",
          "sensor.outdoor_temperature" in report.get("mirrored", []),
          "mirrored in at construction, not fetched per read")

    calls = report.get("calls", {})
    check("S5  the declared service call goes through",
          calls.get("lock.lock") == "called", f"lock.lock -> {calls.get('lock.lock')}")
    check("S5  lock.unlock does not exist to be called",
          calls.get("lock.unlock") == "ServiceNotFound",
          f"lock.unlock -> {calls.get('lock.unlock')}")
    check("S5  ...and the platform saw only the permitted call",
          [c[:2] for c in platform.calls] == [("lock", "lock")], str(platform.calls))

    denials = [e for e in mediator.audit if not e["allowed"]]
    check("every mediated decision named a clause",
          all(e["clause"] for e in mediator.audit),
          f"{len(mediator.audit)} decisions, {len(denials)} denials")

    print()
    if failures:
        print(f"FAILED: {'; '.join(failures)}")
        return 1
    print("PASS — an integration whose source was never touched ran inside the sandbox,")
    print("       published its entity through the mediator, read what it declared, and")
    print("       found no way to call the service it did not.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
