"""Shared parts of §7.15's garbage-collector pairing, so both arms attack the same thing.

§2.4.1 is the single published result that eliminates every in-process design: Corno and
Mannella demonstrate an integration walking `gc.get_objects()` to reach *another* integration's
live object and read its private state. It is the reason S1 exists, and §7.15 is where it stops
being a citation and becomes a measurement here.

The attack is one function (`GC_SWEEP`), run identically in both arms. What differs is where the
credential lives:

    unconfined   a victim integration holds it, in the same process, exactly as today
    confined     the mediator holds it (S2), in a different process from the sandbox (S1)

The canary is long and unique so a substring match cannot succeed by accident.
"""

from __future__ import annotations

import json
from pathlib import Path

CANARY_CREDENTIAL = "CANARY-GCACCESS-7f3a1e9c4b28d60f-DO-NOT-DISCLOSE"

# A real victim integration. Small, but set up through Home Assistant's own config-entry path,
# so what the adversary reaches is genuinely another integration's live object rather than
# something the test placed on the heap by hand. It holds its credential the way an ordinary
# integration does: in a client object, stashed in `hass.data` and in `entry.runtime_data`.
VICTIM = {
    "manifest.json": json.dumps({
        "domain": "victim_cloud", "name": "Victim Cloud", "version": "1.0.0",
        "config_flow": True, "iot_class": "cloud_polling", "requirements": [],
        "codeowners": [], "documentation": "https://example.invalid/victim"}),
    "__init__.py": '''
"""An ordinary cloud integration that holds an API token in a live client object."""
DOMAIN = "victim_cloud"


class CloudClient:
    """What a real integration stores in hass.data: a client holding its credential."""

    def __init__(self, token):
        self._token = token
        self.session_headers = {"Authorization": f"Bearer {token}"}


async def async_setup_entry(hass, entry):
    from . import CloudClient as _C  # noqa: F401
    client = CloudClient(entry.data["token"])
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client
    entry.runtime_data = client
    return True


async def async_unload_entry(hass, entry):
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True
''',
    "config_flow.py": '''
from homeassistant.config_entries import ConfigFlow


class VictimFlow(ConfigFlow, domain="victim_cloud"):
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input=None):
        return self.async_create_entry(title="victim", data=user_input or {})
''',
}

# The published attack, verbatim in intent: walk every live object, and report any that carries
# the credential. Strings, bytes, dict values and object __dict__ are the reaches C&M describe.
GC_SWEEP = r'''
import gc

def gc_find(needle):
    hits = []
    for obj in gc.get_objects():
        try:
            if isinstance(obj, str) and needle in obj:
                hits.append(("str", obj[:80]))
            elif isinstance(obj, bytes) and needle.encode() in obj:
                hits.append(("bytes", obj[:80].decode(errors="replace")))
            elif isinstance(obj, dict):
                for v in obj.values():
                    if isinstance(v, str) and needle in v:
                        hits.append(("dict-value", v[:80]))
                    elif isinstance(v, dict):
                        for vv in v.values():
                            if isinstance(vv, str) and needle in vv:
                                hits.append(("nested-dict", vv[:80]))
            else:
                d = getattr(obj, "__dict__", None)
                if isinstance(d, dict):
                    for v in d.values():
                        if isinstance(v, str) and needle in v:
                            hits.append((type(obj).__name__ + ".attr", v[:80]))
        except BaseException:
            continue
    return hits
'''


def write_victim(root: Path) -> Path:
    component = root / "custom_components" / "victim_cloud"
    component.mkdir(parents=True)
    for name, body in VICTIM.items():
        (component / name).write_text(body.lstrip() if body.startswith("\n") else body)
    return component
