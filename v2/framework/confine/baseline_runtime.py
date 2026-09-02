"""The unconfined arm. Runs an integration against a **full** Home Assistant, no sandbox.

§7.4.1 calls this the measurement that decomposes the compatibility figure. Chapter 6 reports
84% of the corpus importing clean under confinement, and that number is a joint property of the
corpus and the design until something separates:

    failures(confined) = failures(baseline) + failures(design)

Only the second term is this project's result. This file produces the first.

**The methodological requirement is that nothing else varies.** §7.9 fixes it: same corpus, same
release, same host, same interpreter, same measurement — and confinement as the only difference.
Two consequences shape this file:

  - **The measurement is not reimplemented.** `inspect()` is imported from `sandbox_runtime`
    and called with the same arguments. A copy that drifted by one platform name or one
    truncation length would silently make the comparison meaningless.
  - **The instance construction is shared too.** `build_hass()` is the same helper, with
    §6.3.3's `async_start()` correction already in it, so the baseline cannot accidentally
    carry a defect the confined arms do not, or vice versa.

**What "full" means here is computed, not asserted, and it is the same definition already in
use.** §6.13.4's core package set is the `default_config` dependency closure; this arm sets up
`default_config` itself. Using one definition of "a stock installation" for both the package set
and the baseline is what keeps §7.4.1's subtraction meaningful. The base `homeassistant`
component — dropped from the sandbox in §6.3.2 — is set up here, because a real installation has
it and a baseline that is *stingier* than reality would understate what confinement costs.

**Bias, stated in the direction it runs.** Every doubtful choice here is resolved in favour of
the baseline: the base component is present, `default_config` is set up, the platform's core
packages are on the path, and the integration's own declared requirements are installed exactly
as the confined arms install them. A generous baseline makes `failures(design)` *larger*, so the
design is charged for anything this arm can fix. That is the direction an evaluation of one's
own artifact should err in.
"""

from __future__ import annotations

import asyncio
import json
import resource
import sys
import traceback
from pathlib import Path

from sandbox_runtime import build_hass, inspect


async def run(spec: dict) -> dict:
    config_dir = spec["config_dir"]
    component_dir = spec["component_dir"]
    domain = spec["domain"]

    # The platform loads a custom integration from `<config_dir>/custom_components/<domain>`.
    # Symlinked rather than copied, for the same reason as the sandbox: the code that gets
    # imported is the corpus's own copy, so C1's zero-line claim stays checkable afterwards.
    custom = Path(config_dir) / "custom_components"
    custom.mkdir(parents=True, exist_ok=True)
    link = custom / domain
    if not link.exists():
        link.symlink_to(component_dir)

    result: dict = {"domain": domain}
    hass = await build_hass(config_dir, with_auth=True)

    from homeassistant.setup import async_setup_component

    # `homeassistant` first, then `default_config`. Reported rather than assumed: if the
    # baseline instance is not actually full, every number derived from it is wrong, and the
    # failure must be visible in the result rather than inferred from a low score.
    result["components_setup"] = {}
    for name in spec.get("setup_components", ["homeassistant", "default_config"]):
        try:
            result["components_setup"][name] = bool(
                await async_setup_component(hass, name, {}))
        except Exception as err:  # noqa: BLE001
            result["components_setup"][name] = f"{type(err).__name__}: {err}"[:160]

    await hass.async_start()
    await hass.async_block_till_done()

    # The same function the confined arms use, on the same levels: not_found -> import_failed
    # -> imports_clean -> platform_import_failed -> platforms_clean.
    result.update(await inspect(hass, domain, component_dir=component_dir))
    result["components_available"] = len(hass.config.components)

    try:
        await hass.async_stop()
    except Exception:  # noqa: BLE001 — teardown noise is not a compatibility result
        pass
    return result


def main() -> int:
    spec = json.loads(Path(sys.argv[1]).read_text())
    try:
        result = asyncio.run(run(spec))
    except Exception:  # noqa: BLE001 — the traceback is the compatibility result
        print(json.dumps({"fatal": traceback.format_exc()[-1500:]}))
        return 1
    # Peak RSS of this process. **Not comparable to the confined arms' figures**, which are the
    # cgroup's `memory.peak` and include page cache; §6.11.3 already records that caution and it
    # applies here in the other direction. Reported because omitting it would be worse.
    result["peak_rss_mb"] = round(
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
