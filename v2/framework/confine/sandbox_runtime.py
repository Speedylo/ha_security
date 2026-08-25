"""Runs **inside** the sandbox. Bound read-only at `/sandbox/runtime.py` and executed there.

This is the other half of §5.6's R2 decision. §5.6.3 established that a real, stripped Home
Assistant can be constructed and that an ordinary integration runs against it; §6.3 measured
what that costs and corrected how it is started. What was missing is the piece that connects
that instance to anything: the **bridge**.

The bridge is small on purpose, and its shape follows from §5.6.2 rather than from convenience:

  - **Declared services are registered; nothing else is.** The sandbox's service registry
    starts empty (§6.3.2 measured that it is *literally* empty). The bridge registers one
    handler per `services.call` clause, each of which forwards to the mediator. An undeclared
    service is not refused — `hass.services.async_call` raises `ServiceNotFound`, because
    there is nothing registered to call. Denial is the registry's shape.
  - **Declared entities are mirrored in; nothing else is.** The local state machine starts
    empty. The bridge asks the mediator for each declared entity and sets it locally. An
    undeclared entity is absent, so the integration reads `None` rather than being refused.
  - **What the integration publishes is forwarded out.** A state change for an entity the
    integration created becomes an `entity.publish` request. What the mediator does with it is
    step 5 of §5.11.3, on the far side.

**It imports nothing from `confine`.** The framing is thirty lines and is reimplemented here,
which §6.5.1 already argued is a property worth having: the sandbox's half of the protocol
needs no library, so it can be reviewed on its own. It also means the trusted code inside the
sandbox is exactly this file.

**The mediator remains the authority.** The declared clauses arrive in the spec so that the
bridge can construct local handlers, never so that it can decide anything: every forwarded
request is checked again by the mediator, which is §5.13's layering rather than duplication.
A bridge that trusted its copy of the manifest would be an in-process enforcement point, which
§5.3 eliminated.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import struct
import sys
import traceback
from pathlib import Path

SPEC_PATH = "/sandbox/spec.json"
COMPONENT = "/sandbox/component"
DATA = "/sandbox/data"


# --------------------------------------------------------------------------- the channel

class Channel:
    """The sandbox's only route out. Four-byte big-endian length, then a JSON object."""

    def __init__(self, fd: int) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, fileno=fd)

    def request(self, message: dict) -> dict:
        payload = json.dumps(message).encode()
        self.sock.sendall(struct.pack(">I", len(payload)) + payload)
        header = b""
        while len(header) < 4:
            chunk = self.sock.recv(4 - len(header))
            if not chunk:
                raise ConnectionError("the mediator closed the channel")
            header += chunk
        (length,) = struct.unpack(">I", header)
        body = b""
        while len(body) < length:
            chunk = self.sock.recv(length - len(body))
            if not chunk:
                raise ConnectionError("the mediator closed the channel mid-frame")
            body += chunk
        return json.loads(body)


# ------------------------------------------------------------------ the minimal instance

async def build_hass(config_dir: str):
    """Construct a Home Assistant without `bootstrap`, and start it in the platform's order.

    This is §5.6.3's recipe with §6.3.2's and §6.3.3's corrections applied: the base
    `homeassistant` component is **not** set up, and the instance is started with
    `async_start()` *after* everything is in place rather than by setting a flag.
    `experiments/r2_footprint/measure.py` deliberately still carries the original so that
    §5.6.3's published figures stay reproducible.
    """
    from homeassistant import config_entries, loader
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import (
        area_registry, category_registry, condition, device_registry, entity,
        entity_registry, floor_registry, issue_registry, label_registry, restore_state,
        translation, trigger,
    )
    from homeassistant.util.hass_dict import HassKey
    from homeassistant.util.unit_system import METRIC_SYSTEM

    hass = HomeAssistant(config_dir)
    hass.config.skip_pip = True
    hass.config.skip_pip_packages = []
    hass.config.latitude = 51.5
    hass.config.longitude = -0.12
    hass.config.elevation = 0
    hass.config.units = METRIC_SYSTEM
    await hass.config.async_set_time_zone("UTC")
    hass.data[loader.DATA_CUSTOM_COMPONENTS] = None

    hass.config_entries = config_entries.ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()

    entity.async_setup(hass)
    loader.async_setup(hass)
    await condition.async_setup(hass)
    await trigger.async_setup(hass)
    hass.data[translation.TRANSLATION_FLATTEN_CACHE] = translation._TranslationCache(hass)  # noqa: SLF001
    device_registry.async_setup(hass)
    for reg in (area_registry, category_registry, device_registry, entity_registry,
                floor_registry, issue_registry, label_registry, restore_state):
        await reg.async_load(hass)
    hass.data[HassKey("bootstrap_registries_loaded")] = None
    return hass


# ------------------------------------------------------------------------------ the bridge

class Bridge:
    """Everything that crosses the sandbox boundary, in one object."""

    def __init__(self, hass, channel: Channel, spec: dict) -> None:
        self.hass = hass
        self.channel = channel
        self.domain = spec["domain"]
        self.declared_services: list[str] = spec.get("services", [])
        self.declared_entities: list[str] = spec.get("entities", [])
        self.mirrored: set[str] = set()
        self.published: list[dict] = []
        self.refused: list[dict] = []

    # -- inbound ---------------------------------------------------------------------

    def mirror_declared_entities(self) -> None:
        """Ask the mediator for each declared entity and set it in the local state machine.

        Only what the manifest declares is mirrored, so an undeclared entity is *absent*
        rather than refused — §5.6.2's structural denial, on the read path.
        """
        for entity_id in self.declared_entities:
            answer = self.channel.request({"op": "entity.read", "entity": entity_id})
            if answer.get("ok"):
                self.hass.states.async_set(entity_id, answer.get("state"),
                                           answer.get("attributes") or {})
                self.mirrored.add(entity_id)
            else:
                self.refused.append({"op": "entity.read", "target": entity_id,
                                     "clause": answer.get("clause")})

    # -- outbound --------------------------------------------------------------------

    def register_declared_services(self) -> None:
        """Register one local handler per declared `domain.service`, and nothing else.

        An integration calling a service it did not declare gets `ServiceNotFound` from Home
        Assistant's own registry. That is not this framework refusing it — there is nothing
        there to call, which is the property §5.6.2 argues for and §6.3.2 measured.
        """
        for clause in self.declared_services:
            service_domain, _, service_name = clause.partition(".")
            if not service_domain or not service_name:
                continue
            self.hass.services.async_register(
                service_domain, service_name, self._forward_service_call)

    async def _forward_service_call(self, call) -> None:
        answer = self.channel.request({
            "op": "service.call", "service": f"{call.domain}.{call.service}",
            "data": {k: v for k, v in call.data.items() if isinstance(v, (str, int, float))},
        })
        if not answer.get("ok"):
            # The mediator's decision is the authority; the local registration is only what
            # made the call expressible. A refusal here means the two disagree, which is a
            # supervisor bug rather than an integration one — so it is loud.
            self.refused.append({"op": "service.call",
                                 "target": f"{call.domain}.{call.service}",
                                 "clause": answer.get("clause")})
            from homeassistant.exceptions import HomeAssistantError
            raise HomeAssistantError(
                f"{call.domain}.{call.service} was refused by the mediator: "
                f"{answer.get('reason')}")

    def watch_local_state(self) -> None:
        """Forward what the integration publishes, and nothing that was mirrored in."""
        from homeassistant.const import EVENT_STATE_CHANGED

        @callback_shim
        def _changed(event) -> None:
            entity_id = event.data.get("entity_id")
            new = event.data.get("new_state")
            if entity_id in self.mirrored or new is None:
                return
            answer = self.channel.request({
                "op": "entity.publish", "entity": entity_id, "state": new.state,
                "attributes": {k: v for k, v in new.attributes.items()
                               if isinstance(v, (str, int, float, bool, type(None)))},
            })
            self.published.append({"entity": entity_id, "state": new.state,
                                   "accepted": bool(answer.get("ok")),
                                   "clause": answer.get("clause")})

        self.hass.bus.async_listen(EVENT_STATE_CHANGED, _changed)


def callback_shim(func):
    """`homeassistant.core.callback`, imported lazily so this file parses without it."""
    from homeassistant.core import callback
    return callback(func)


# --------------------------------------------------------------------------------- main

def place_component(domain: str) -> None:
    """Make the integration visible where Home Assistant looks for it.

    The platform loads a custom integration from `<config_dir>/custom_components/<domain>`,
    and `/sandbox/component` is not that path. Rather than mount the code twice, the writable
    data directory — which is the sandbox's configuration directory — gets a symbolic link to
    the read-only one. The code the platform imports is therefore still the read-only copy.
    """
    custom = Path(DATA) / "custom_components"
    custom.mkdir(parents=True, exist_ok=True)
    link = custom / domain
    if not link.exists():
        link.symlink_to(COMPONENT)


# The platform names Home Assistant recognises. An integration declares a platform by having
# a module of that name, so the set of files is what says which platforms to try importing.
PLATFORM_NAMES = (
    "sensor", "binary_sensor", "switch", "light", "climate", "cover", "fan", "lock",
    "media_player", "camera", "vacuum", "water_heater", "alarm_control_panel", "button",
    "number", "select", "text", "update", "siren", "humidifier", "valve", "device_tracker",
    "calendar", "notify", "todo", "weather", "remote", "scene", "image", "event", "time",
    "date", "datetime", "button", "conversation", "image_processing",
)


async def inspect(hass, domain: str) -> dict:
    """Ask, in order, the three questions N2 requires be reported separately.

    §3.5's N2 says "executed end-to-end" must be reported apart from "imports-clean", because
    the two measure different things and reporting only the larger flatters the result. This
    is that separation, one level at a time, so a failure is attributable to a level rather
    than to "it did not work".
    """
    from homeassistant import loader

    result: dict = {"domain": domain}
    try:
        integration = await loader.async_get_integration(hass, domain)
    except Exception as err:  # noqa: BLE001
        result["level"] = "not_found"
        result["error"] = f"{type(err).__name__}: {err}"[:200]
        return result

    result["requirements"] = list(getattr(integration, "requirements", []) or [])
    result["dependencies"] = list(getattr(integration, "dependencies", []) or [])
    result["after_dependencies"] = list(getattr(integration, "after_dependencies", []) or [])

    # L1 — does the integration's own module import inside the sandbox?
    try:
        await integration.async_get_component()
    except Exception as err:  # noqa: BLE001
        result["level"] = "import_failed"
        result["error"] = f"{type(err).__name__}: {err}"[:300]
        return result
    result["level"] = "imports_clean"

    # L2 — do its entity platforms import? This is where a dependency on another component
    # shows up, which is exactly what §5.6.5's second trigger is about.
    present = [name for name in PLATFORM_NAMES
               if (Path(COMPONENT) / f"{name}.py").is_file()]
    result["platforms"] = present
    failed = {}
    for name in present:
        try:
            await integration.async_get_platform(name)
        except Exception as err:  # noqa: BLE001
            failed[name] = f"{type(err).__name__}: {err}"[:200]
    if failed:
        result["level"] = "platform_import_failed"
        result["platform_errors"] = failed
        return result
    result["level"] = "platforms_clean"
    return result


async def run() -> dict:
    spec = json.loads(Path(SPEC_PATH).read_text())
    channel = Channel(int(os.environ["CONFINE_CHANNEL_FD"]))
    result: dict = {"domain": spec["domain"]}

    place_component(spec["domain"])
    hass = await build_hass(DATA)

    # Optionally set up the components the integration says it depends on. §6.3.2 dropped the
    # base component because nothing needed it; a real integration's `dependencies` are a
    # different claim, and whether the sandbox must honour them is what §5.6.5's second
    # trigger asks.
    wanted = spec.get("setup_components") or []
    if wanted:
        from homeassistant.setup import async_setup_component
        result["components_setup"] = {}
        for name in wanted:
            try:
                result["components_setup"][name] = bool(
                    await async_setup_component(hass, name, {}))
            except Exception as err:  # noqa: BLE001
                result["components_setup"][name] = f"{type(err).__name__}: {err}"[:120]

    bridge = Bridge(hass, channel, spec)

    # Order, and it is the order §5.6.2 implies: the sandbox is furnished with exactly what
    # was declared *before* the integration runs, so that what it finds is already the whole
    # of what it may have.
    bridge.register_declared_services()
    bridge.mirror_declared_entities()
    bridge.watch_local_state()

    from homeassistant.config_entries import ConfigEntryState, ConfigEntry, SOURCE_USER

    if spec.get("mode") == "inspect":
        result.update(await inspect(hass, spec["domain"]))
        await hass.async_stop()
        return result

    entry = ConfigEntry(version=1, minor_version=1, domain=spec["domain"],
                        title=spec["domain"], data=spec.get("entry_data", {}),
                        source=SOURCE_USER, options={}, unique_id=None,
                        discovery_keys={}, subentries_data=())
    try:
        await hass.config_entries.async_add(entry)
        await hass.async_block_till_done()
    except Exception as err:  # noqa: BLE001 — a failed setup is a compatibility result
        result["setup_error"] = f"{type(err).__name__}: {err}"

    # §6.3.3: start last, after every component is set up.
    await hass.async_start()
    await hass.async_block_till_done()

    result["entry_state"] = str(entry.state)
    result["loaded"] = entry.state is ConfigEntryState.LOADED
    result["local_entities"] = sorted(s.entity_id for s in hass.states.async_all())
    result["mirrored"] = sorted(bridge.mirrored)
    result["published"] = bridge.published
    result["refused"] = bridge.refused

    # What the integration can and cannot reach, asked from inside rather than inferred.
    probes = spec.get("probe_entities", [])
    result["reads"] = {e: (hass.states.get(e).state if hass.states.get(e) else None)
                       for e in probes}
    calls = {}
    for clause in spec.get("probe_services", []):
        service_domain, _, service_name = clause.partition(".")
        try:
            await hass.services.async_call(service_domain, service_name, {}, blocking=True)
            calls[clause] = "called"
        except Exception as err:  # noqa: BLE001
            calls[clause] = f"{type(err).__name__}"
    result["calls"] = calls

    await hass.async_stop()
    return result


def main() -> int:
    try:
        result = asyncio.run(run())
    except Exception:  # noqa: BLE001 — the traceback is the compatibility result
        print(json.dumps({"fatal": traceback.format_exc()[-1500:]}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
