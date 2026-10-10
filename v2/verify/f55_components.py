"""F55: which of default_config's dependencies load in the unconfined arm's instance.

On the Pi, (A) down (F56), from a directory holding only a copy of sandbox_runtime.py (on the path,
confine/ would shadow the standard library's `platform`):
  ~/r2exp/ha314/bin/python verify/f55_components.py DIR > components.json
"""
import asyncio, json, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])  # framework/confine, for sandbox_runtime
from sandbox_runtime import build_hass
from homeassistant.setup import async_setup_component
from homeassistant.loader import async_get_integration

async def main():
    hass = await build_hass(Path(tempfile.mkdtemp(prefix="f55-")), with_auth=True)
    ok = {n: bool(await async_setup_component(hass, n, {})) for n in ("homeassistant", "default_config")}
    deps = (await async_get_integration(hass, "default_config")).dependencies
    loaded = set(hass.config.components)
    print(json.dumps({"setup": ok, "default_config_dependencies": sorted(deps),
                      "loaded": sorted(d for d in deps if d in loaded),
                      "not_loaded": sorted(d for d in deps if d not in loaded),
                      "network_loaded": "network" in loaded}, indent=1))
    await hass.async_stop()
asyncio.run(main())
