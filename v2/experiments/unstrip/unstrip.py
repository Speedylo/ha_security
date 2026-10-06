#!/usr/bin/env python3
"""How much of Home Assistant can a stripped instance put back, and what does each piece cost?

§6.11.3 measured that 16 of 37 community integrations fail against the minimal instance for want
of a component they declare, and that `http` alone accounts for ten of them. §6.11.5's first G3
option is to un-strip toward `http` and pay the footprint. This measures the payment.

Deliberately run **outside** a sandbox first. §6.11.3's arm B reported `False` from
`async_setup_component` with no exception and no reason, and two questions were tangled in that:
whether the component can set up in a *minimal instance* at all, and whether it can set up in a
*sandbox*. They have different answers and different fixes, so they are separated here — this
script answers the first, and the same list is then run inside a sandbox to answer the second.

Each component is set up in dependency order, and for each one the script records whether it
succeeded, what Home Assistant logged if it did not, and what it added to resident memory.

Run:  python3 unstrip.py [--json results/out.json] [--components http,websocket_api,...]
Needs: an interpreter with `homeassistant` importable, and the components' own requirements on
`sys.path` — `--requirements` prints what to install.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import platform
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "framework"))
from confine.provenance import record_run  # noqa: E402  (F14)

# In dependency order, cheapest first. `http` leads because §6.11.3 makes it the decisive one.
DEFAULT = ["http", "websocket_api", "frontend", "lovelace", "panel_custom", "repairs",
           "python_script", "media_source", "notify", "mqtt", "stream"]


def rss_mb() -> float:
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) / 1024
    return -1.0


class Capture(logging.Handler):
    """Home Assistant reports a refused setup by logging it and returning False."""

    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.WARNING:
            try:
                self.records.append(f"{record.levelname} {record.name}: {record.getMessage()}")
            except Exception:  # noqa: BLE001
                pass


async def build_hass(config_dir: str, with_auth: bool = False):
    """§5.6.3's recipe with §6.3.2's and §6.3.3's corrections — no base component, start last.

    `with_auth` wires an authentication manager, which §5.6.3 deliberately left out ("no HTTP
    server, no recorder, no frontend and no authentication"). It is here because `http` cannot
    set up without one: its `async_setup_auth` creates a system user, and on a minimal instance
    that raises `AttributeError: 'HomeAssistant' object has no attribute 'auth'`.

    **The manager is constructed with no providers**, so its store is empty: no users, no
    credentials, no tokens belonging to anyone. That is the R2 pattern again — a real object
    whose contents are nothing — and it is what makes the tension with §5.10.3 bearable rather
    than fatal. §6.12 argues that case rather than assuming it.
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
    hass.config.latitude, hass.config.longitude, hass.config.elevation = 51.5, -0.12, 0
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
    if with_auth:
        from homeassistant import auth
        hass.auth = await auth.auth_manager_from_config(hass, [], [])
    hass.data[HassKey("bootstrap_registries_loaded")] = None
    return hass


async def run(components: list[str], config_dir: str, with_auth: bool = False) -> dict:
    capture = Capture()
    logging.getLogger().addHandler(capture)
    logging.getLogger().setLevel(logging.WARNING)

    from homeassistant.setup import async_setup_component

    baseline = rss_mb()
    hass = await build_hass(config_dir, with_auth=with_auth)
    built = rss_mb()
    result = {"host": {"machine": platform.machine(), "python": platform.python_version()},
              "baseline_mb": round(baseline, 1), "minimal_mb": round(built, 1),
              "with_auth": with_auth, "components": []}

    previous = built
    for name in components:
        mark = len(capture.records)
        try:
            ok = bool(await async_setup_component(hass, name, {}))
            error = ""
        except Exception as err:  # noqa: BLE001
            ok, error = False, f"{type(err).__name__}: {err}"[:200]
        await hass.async_block_till_done()
        now = rss_mb()
        result["components"].append({
            "component": name, "ok": ok, "error": error,
            "cost_mb": round(now - previous, 1), "total_mb": round(now, 1),
            "log": capture.records[mark:][:4],
            "in_components": name in hass.config.components,
        })
        previous = now

    result["final_mb"] = round(rss_mb(), 1)
    await hass.async_stop()
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--components", default=",".join(DEFAULT))
    ap.add_argument("--config-dir", default="/tmp/unstrip-config")
    ap.add_argument("--auth", action="store_true",
                    help="wire an authentication manager with no providers, which http needs")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--requirements", action="store_true",
                    help="print the packages these components declare, and exit")
    args = ap.parse_args()

    components = [c.strip() for c in args.components.split(",") if c.strip()]

    if args.requirements:
        import homeassistant.components as pkg
        base = Path(pkg.__file__).parent
        wanted: set[str] = set()
        pending, seen = list(components), set()
        while pending:
            name = pending.pop()
            if name in seen:
                continue
            seen.add(name)
            try:
                data = json.loads((base / name / "manifest.json").read_text())
            except (OSError, ValueError):
                continue
            wanted.update(data.get("requirements") or [])
            pending += list(data.get("dependencies") or [])
        print(" ".join(sorted(wanted)))
        return 0

    Path(args.config_dir).mkdir(parents=True, exist_ok=True)
    result = asyncio.run(run(components, args.config_dir, with_auth=args.auth))

    print(f"un-stripping — {result['host']['machine']}, Python {result['host']['python']}")
    print(f"  minimal instance: {result['minimal_mb']:.1f} MB "
          f"(bare interpreter {result['baseline_mb']:.1f} MB)"
          f"{'  + auth manager, no providers' if result['with_auth'] else ''}\n")
    print(f"  {'component':<18} {'set up':<8} {'cost':>8} {'total':>9}   why not")
    for row in result["components"]:
        why = row["error"] or (row["log"][0][:60] if row["log"] else "")
        print(f"  {row['component']:<18} {'yes' if row['ok'] else 'NO':<8} "
              f"{row['cost_mb']:>7.1f}M {row['total_mb']:>8.1f}M   {why}")
    ok = [r for r in result["components"] if r["ok"]]
    print(f"\n  {len(ok)}/{len(result['components'])} set up; "
          f"total added {result['final_mb'] - result['minimal_mb']:.1f} MB")

    if args.json:
        args.json.write_text(json.dumps(result, indent=2) + "\n")
        record_run(args.json)  # F14: how this result was produced, beside it
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
