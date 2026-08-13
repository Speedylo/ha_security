#!/usr/bin/env python3
"""Measure what a framework-published entity lacks compared to a native one.

The framework publishes entities into Home Assistant over the REST states API.
HA accepts them, they appear in `/api/states`, and they render on a dashboard —
but they are not the same objects a natively-loaded integration creates. They are
states without registry identity.

This quantifies the difference instead of asserting it, by comparing the *same
integration* loaded both ways:

    native      matomo installed in /config/custom_components, configured through
                its own config flow, owned by a config entry
    framework   matomo running outside HA under the supervisor, publishing over REST

Run `./ha_compare_setup.sh` first; it arranges both halves. Then:

    ./registry_gap.py
    ./registry_gap.py --restart-test    # also measure survival across an HA restart
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOKEN_FILE = HERE / ".ha_token"
BASE = "http://127.0.0.1:8123"

# The two prefixes the same integration produces depending on how it is loaded.
NATIVE_PREFIX = "sensor.matomo_example_org_"
FRAMEWORK_PREFIX = "sensor.matomo_"

# Registry fields that carry identity and capability. Each one a framework entity
# lacks is a concrete thing a user or another integration cannot do with it.
REGISTRY_FIELDS = [
    ("unique_id", "stable identity across restarts and renames"),
    ("config_entry_id", "belongs to a configuration the user can reload or delete"),
    ("device_id", "grouped under a device in the UI"),
    ("platform", "attributed to the integration that created it"),
    ("area_id", "assignable to a room"),
    ("entity_category", "classifiable as diagnostic/config"),
    ("disabled_by", "can be disabled without deleting"),
    ("hidden_by", "can be hidden from the UI"),
    ("name", "user-renameable"),
    ("icon", "user-overridable icon"),
]


def token() -> str:
    if not TOKEN_FILE.exists():
        sys.exit("no .ha_token — run ./ha_onboard.py first")
    return TOKEN_FILE.read_text(encoding="utf-8").strip()


def rest(path: str, tok: str):
    request = urllib.request.Request(BASE + path)
    request.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(request, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def ws_dump(tok: str) -> dict:
    """Fetch the three registries that define entity identity."""
    import aiohttp

    async with aiohttp.ClientSession() as session, session.ws_connect(
        BASE.replace("http", "ws") + "/api/websocket"
    ) as ws:
        await ws.receive_str()
        await ws.send_str(json.dumps({"type": "auth", "access_token": tok}))
        await ws.receive_str()
        out = {}
        commands = [
            ("entities", "config/entity_registry/list"),
            ("devices", "config/device_registry/list"),
            ("entries", "config_entries/get"),
        ]
        for index, (key, command) in enumerate(commands, start=1):
            await ws.send_str(json.dumps({"id": index, "type": command}))
            out[key] = json.loads(await ws.receive_str())["result"]
        return out


def classify(states, registry_by_id):
    native, framework = [], []
    for state in states:
        entity_id = state["entity_id"]
        if entity_id.startswith(NATIVE_PREFIX):
            native.append(entity_id)
        elif entity_id.startswith(FRAMEWORK_PREFIX):
            framework.append(entity_id)
    return sorted(native), sorted(framework)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--restart-test", action="store_true", help="also restart HA and re-check survival")
    args = parser.parse_args()

    tok = token()
    states = rest("/api/states", tok)
    registries = asyncio.run(ws_dump(tok))
    by_entity = {entry["entity_id"]: entry for entry in registries["entities"]}

    native, framework = classify(states, by_entity)
    if not native or not framework:
        sys.exit(
            f"need both halves present: found {len(native)} native and {len(framework)} framework "
            "entities. Run ./ha_compare_setup.sh first."
        )

    print("=" * 72)
    print("THE SAME INTEGRATION, LOADED TWO WAYS")
    print("=" * 72)
    print(f"  native (config entry) : {len(native):2d} entities, e.g. {native[0]}")
    print(f"  framework (REST)      : {len(framework):2d} entities, e.g. {framework[0]}")

    sample_native = by_entity.get(native[0], {})
    sample_framework = by_entity.get(framework[0])

    print(f"\n  in entity registry — native: {native[0] in by_entity}  "
          f"framework: {framework[0] in by_entity}")

    bridged = sample_framework is not None
    mode = "sandbox_bridge integration" if bridged else "raw REST states"

    print("\n" + "=" * 72)
    print(f"REGISTRY FIELDS   (framework publishing via: {mode})")
    print("=" * 72)
    if bridged:
        print("  The framework entity has a registry row, so these fields exist for it on")
        print("  the same terms as for the native one: 'set' means something populated it,")
        print("  'available' means the row exists and a user can populate it.")
    else:
        print("  The framework entity has no registry row at all, so every field below is")
        print("  structurally unavailable to it — not merely unset. On the native side,")
        print("  'set' means the integration populated it and 'available' means the row")
        print("  exists so a user or another integration can populate it.")
    print()
    print(f"  {'field':18s} {'native':32s} {'framework':32s}")

    def render(entry, field):
        if entry is None:
            return "unavailable (no row)"
        value = entry.get(field)
        return str(value)[:30] if value is not None else "(available, unset)"

    native_set = framework_set = 0
    for field, meaning in REGISTRY_FIELDS:
        if sample_native.get(field) is not None:
            native_set += 1
        if bridged and sample_framework.get(field) is not None:
            framework_set += 1
        print(f"  {field:18s} {render(sample_native, field):32s} {render(sample_framework, field):32s}")

    total = len(REGISTRY_FIELDS)
    print(f"\n  native   : registry row — {native_set}/{total} populated, "
          f"{total - native_set} available for the user.")
    if bridged:
        print(f"  framework: registry row — {framework_set}/{total} populated, "
              f"{total - framework_set} available for the user.")
        print("\n  The gap in this table is closed. `platform` reads sandbox_bridge rather")
        print("  than matomo, which is accurate rather than a shortfall: the bridge really")
        print("  is what created the entity, and that is what makes the sandboxing visible")
        print("  to the user instead of hiding it.")
    else:
        print(f"  framework: no registry row — {total}/{total} unavailable.")

    # Devices and config entries
    matomo_entries = [e for e in registries["entries"] if e.get("domain") == "matomo"]
    bridge_entries = [e for e in registries["entries"] if e.get("domain") == "sandbox_bridge"]
    native_devices = {by_entity[e]["device_id"] for e in native if by_entity.get(e, {}).get("device_id")}
    framework_devices = {
        by_entity[e]["device_id"] for e in framework if by_entity.get(e, {}).get("device_id")
    }
    print("\n" + "=" * 72)
    print("OWNERSHIP")
    print("=" * 72)
    print(f"  {'':32s} {'native':10s} {'framework':10s}")
    print(f"  {'config entries':32s} {len(matomo_entries):<10d} {len(bridge_entries):<10d}")
    print(f"  {'devices':32s} {len(native_devices):<10d} {len(framework_devices):<10d}")
    if not bridge_entries:
        print("\n  Nothing to reload, delete, or configure for the framework, and nothing to")
        print("  group its entities under.")

    # State-level attributes do survive — worth being precise about what is NOT lost.
    native_state = next(s for s in states if s["entity_id"] == native[0])
    framework_state = next(s for s in states if s["entity_id"] == framework[0])
    print("\n" + "=" * 72)
    print("WHAT IS NOT LOST  (state-level presentation is intact)")
    print("=" * 72)
    for key in ("unit_of_measurement", "friendly_name", "device_class", "state_class", "icon"):
        n = native_state["attributes"].get(key)
        f = framework_state["attributes"].get(key)
        mark = "same kind" if (n is None) == (f is None) else "DIFFERS"
        print(f"  {key:22s} native={str(n)[:20]:22s} framework={str(f)[:20]:22s} {mark}")

    if args.restart_test:
        print("\n" + "=" * 72)
        print("SURVIVAL ACROSS A RESTART")
        print("=" * 72)
        print("  restarting Home Assistant ...")
        subprocess.run(["docker", "restart", "capstone-ha"], check=True, capture_output=True)
        for _ in range(120):
            try:
                urllib.request.urlopen(BASE + "/manifest.json", timeout=3)
                break
            except Exception:  # noqa: BLE001
                time.sleep(2)
        time.sleep(15)  # let integrations finish setting up
        after = rest("/api/states", tok)
        after_ids = {s["entity_id"] for s in after}
        native_alive = sum(1 for e in native if e in after_ids)
        framework_alive = sum(1 for e in framework if e in after_ids)
        print(f"  native     : {native_alive}/{len(native)} entities survived")
        print(f"  framework  : {framework_alive}/{len(framework)} entities survived")
        if framework_alive == 0:
            print("\n  REST-published states are in-memory only. HA restores them as 'unavailable'")
            print("  or drops them entirely; nothing re-creates them until the supervisor runs")
            print("  again. A natively-loaded integration is restarted by HA itself.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
