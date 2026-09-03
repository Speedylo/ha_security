"""Reading a manifest, refusing a bad one, and deciding one request against it.

§5.9.4 fixes where a manifest comes from and §5.10 fixes what it can say. Both are
security-relevant rather than presentational, so this module is written to two rules that are
worth stating before the code:

**Reject at parse time, not at use time.** §5.10.5 says a declared path that encloses the
configuration root or `.storage/` "is rejected when the manifest is parsed, not when it is
first used". The same discipline is applied to every other constraint: a wildcard in
`services.call`, an unknown capability, a pattern without a domain. A manifest that reaches the
mediator has already been found well-formed, so the decision path has no error cases in it that
could be got wrong per request.

**Unknown keys are a rejection, not something to ignore.** Ignoring an unrecognised capability
means a manifest written against a later schema is silently under-enforced, and silent
under-enforcement is the failure this whole design exists to remove. It is also what Home
Assistant's own `hassfest` does — its voluptuous schemas default to `PREVENT_EXTRA` (§5.10.1).

The decision path returns a **clause pointer** with every answer, permitted or denied, which is
§5.10.8's requirement that every enforcement decision be attributable to a clause. A decision
that cannot name one is a bug, and it is a bug this module cannot produce: the pointer is
constructed by whichever branch decided, not looked up afterwards.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from .cgroup import ResourceLimits
from .mediator import Decision
from .sandbox import GrantRefused, reject_forbidden

SCHEMA_VERSION = 1


class Provenance(Enum):
    """§5.9.4's precedence. The file's *location* is the signal; nothing self-reports."""

    AUTHOR = "author-declared"      # the `permissions` key of the integration's manifest.json
    DERIVED = "derived"             # permissions.json, supplied by the installation
    NONE = "none"                   # neither: S6 applies


class ManifestRejected(ValueError):
    """The manifest is not well-formed. The integration gets nothing, and the user gets why."""


# Capability -> the request operations it governs. A request whose operation is not here has
# no capability to match and is denied by absence, which is S6.
OPERATIONS = {
    "entity.read": ("entities", "read"),
    "entity.subscribe": ("entities", "subscribe"),
    "entity.write": ("entities", "write"),
    "service.call": ("services", "call"),
    "event.subscribe": ("events", "subscribe"),
    "event.fire": ("events", "fire"),
    "config_entries.list": ("config_entries", "read_all"),
    "network.egress": ("network", "egress"),
}

KNOWN_CAPABILITIES = {"entities", "services", "events", "network", "files",
                      "config_entries", "http", "resources"}
KNOWN_MEMBERS = {
    "entities": {"read", "subscribe", "write"},
    "services": {"call"},
    "events": {"subscribe", "fire"},
    "files": {"read", "write"},
    # `local` and `discover` are §7.24's additions; `allow_private` is superseded by `local`,
    # which says which ports rather than granting the private address space as a boolean, and is
    # kept accepted so that a manifest written against the older schema still parses.
    "network": {"egress", "allow_private", "local", "discover"},
    "config_entries": {"read_all"},
    "http": {"register"},
    "resources": {"memory_mb", "cpu_percent", "max_processes", "disk_mb"},
}

# §5.10.6's clause, with the bounds each member is validated against at parse time. The upper
# bounds are not security limits — a manifest asking for more than the device has is refused by
# the device — they are there so that a typo declares a refusal rather than a limit so large it
# is indistinguishable from none. `cpu_percent` is a percentage of one processor, so a value
# above 100 is legitimate on a multi-core host and the ceiling is the host's core count × 100.
RESOURCE_BOUNDS = {
    "memory_mb": (16, 8192),
    "cpu_percent": (1, 1600),
    "max_processes": (1, 4096),
    "disk_mb": (1, 4096),
}


def _require_list(value: object, where: str) -> list:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ManifestRejected(f"{where} must be a list of strings")
    return value


def _validate_entity_patterns(patterns: list[str], where: str) -> None:
    """§5.10.4: patterns are allowed for entities, but a domain is always required."""
    for pattern in patterns:
        domain, _, object_id = pattern.partition(".")
        if not domain or not object_id:
            raise ManifestRejected(
                f"{where}: '{pattern}' must be domain.object_id; a domain is always required "
                f"so that '*' alone is never a grant (§5.10.4)")
        if "*" in domain:
            raise ManifestRejected(
                f"{where}: '{pattern}' wildcards the domain, which grants across domains")


def _validate_services(services: list[str]) -> None:
    """§5.10.4, the rule S5 exists to produce: no wildcard, ever, in `services.call`."""
    for entry in services:
        if "*" in entry:
            raise ManifestRejected(
                f"/permissions/services/call: '{entry}' contains a wildcard. Every entry names "
                f"one domain.service, because a lock.* grant hands over the unlock with the "
                f"lock (§5.10.4)")
        domain, _, service = entry.partition(".")
        if not domain or not service:
            raise ManifestRejected(
                f"/permissions/services/call: '{entry}' must be domain.service")


def _validate_resources(resources: object) -> None:
    """§5.10.6, at parse time — because the alternative is what §7.21.1 found.

    Every member of this clause is a positive integer within a stated range. Validating the
    *keys* and not the *values* is how `"memory_mb": "lots"` reached the point of being written
    into a kernel file, and a limit that fails to apply at sandbox-construction time is a limit
    the user was already told was in force (§6.7.1).
    """
    if not isinstance(resources, dict):
        raise ManifestRejected("/permissions/resources must be an object")
    for member, value in resources.items():
        low, high = RESOURCE_BOUNDS[member]      # membership already checked by _validated
        if isinstance(value, bool) or not isinstance(value, int):
            raise ManifestRejected(
                f"/permissions/resources/{member}: {value!r} is not an integer")
        if not low <= value <= high:
            raise ManifestRejected(
                f"/permissions/resources/{member}: {value} is outside {low}–{high}")


def _validate_network(entries: list[str], where: str) -> None:
    """§7.24.3 and `notes/decision_network_capability.md` §3.1 — a host without a port is not a
    grant of "the web", it is a grant of every port on that machine.

    §5.10.3 wrote this clause as a list of hostnames, and twelve running integrations showed
    that wrong: they reached 443 but also 8123, 6445, 20086 and 5000. A clause with no port
    field can express none of those **in either direction** — it can neither grant 6445 nor
    withhold it — so an integration granted a host was silently granted all 65,535 ports on it.
    That is exactly the over-breadth §5.10.4 refuses in `services.call`, one section later and
    unnoticed.

    Wildcards are refused for the same reason they are refused there: an author knows their own
    API hosts because they are written into the source, so exactness is knowable and therefore
    required. A suffix pattern would grant every subdomain, including ones that do not exist
    yet and whose control the author cannot vouch for.
    """
    for entry in entries:
        if "*" in entry:
            raise ManifestRejected(
                f"{where}: '{entry}' contains a wildcard. Every entry names one host and one "
                f"port, because an author knows the hosts their own code contacts (§5.10.4's "
                f"rule, applied to the network in §7.24.3)")
        host, separator, port = entry.rpartition(":")
        if not separator or not host:
            raise ManifestRejected(
                f"{where}: '{entry}' must be host:port. A host alone grants every one of the "
                f"65,535 ports on that machine, which is wider than any manifest intends")
        if not port.isdigit() or not 1 <= int(port) <= 65535:
            raise ManifestRejected(
                f"{where}: '{entry}' has no usable port; expected 1-65535")
        if host.startswith("[") and host.endswith("]"):
            continue                       # a bracketed IPv6 literal, whose colons are its own
        if ":" in host:
            raise ManifestRejected(
                f"{where}: '{entry}' has more than one colon; bracket an IPv6 literal as "
                f"[::1]:8123 so that host and port are unambiguous")


def _validate_ports(ports: object, where: str) -> None:
    """`local` and `discover` declare ports and never addresses.

    The split is the design's spine: a protocol port is a constant in the integration's source
    and the author knows it, while a device's address is a DHCP lease that does not exist when
    the manifest is written. Asking an author for the address would be asking for something
    nobody has (`decision_network_capability.md` §2).
    """
    if not isinstance(ports, list) or not all(isinstance(p, int) for p in ports):
        raise ManifestRejected(f"{where} must be a list of port numbers")
    for port in ports:
        if not 1 <= port <= 65535:
            raise ManifestRejected(f"{where}: {port} is not a port number")


def _validate_events(events: list[str], where: str) -> None:
    for entry in events:
        if "*" in entry:
            raise ManifestRejected(
                f"{where}: '{entry}' contains a wildcard. The bus carries every state change "
                f"in the home, so event types are named explicitly (§5.10.3)")


@dataclass(frozen=True)
class Manifest:
    """A validated manifest, and the decision procedure that goes with it."""

    domain: str
    provenance: Provenance
    permissions: dict
    source: Path | None = None

    # -- loading -----------------------------------------------------------------------

    @classmethod
    def load(cls, component_dir: Path, config_root: Path,
             derived_dir: Path | None = None) -> Manifest:
        """Find a manifest by §5.9.4's precedence, or return the one that grants nothing.

        The file's location is the provenance signal (§5.10.1). No field asserts who wrote a
        declaration, which is the correct way to represent a fact an adversary would otherwise
        be asked to self-report.
        """
        domain = component_dir.name

        own = component_dir / "manifest.json"
        if own.is_file():
            try:
                data = json.loads(own.read_text())
            except ValueError as err:
                raise ManifestRejected(f"{own}: not valid JSON: {err}") from err
            if isinstance(data, dict) and "permissions" in data:
                return cls._validated(domain, Provenance.AUTHOR, data["permissions"],
                                      own, config_root)

        derived = (derived_dir or component_dir.parent) / f"{domain}.permissions.json"
        if derived.is_file():
            try:
                data = json.loads(derived.read_text())
            except ValueError as err:
                raise ManifestRejected(f"{derived}: not valid JSON: {err}") from err
            return cls._validated(domain, Provenance.DERIVED, data, derived, config_root)

        # §5.9.4 precedence 3. Not an error: an unconfined integration is the status quo, and
        # the framework's answer to it is to grant nothing rather than to refuse to run.
        return cls(domain, Provenance.NONE, {}, None)

    @classmethod
    def _validated(cls, domain: str, provenance: Provenance, permissions: object,
                   source: Path, config_root: Path) -> Manifest:
        if not isinstance(permissions, dict):
            raise ManifestRejected(f"{source}: permissions must be an object")
        version = permissions.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ManifestRejected(
                f"{source}: schema_version is {version!r}, expected {SCHEMA_VERSION}")

        unknown = set(permissions) - KNOWN_CAPABILITIES - {"schema_version"}
        if unknown:
            raise ManifestRejected(
                f"{source}: unknown capabilities {sorted(unknown)}. An unrecognised capability "
                f"is rejected rather than ignored, because ignoring it under-enforces silently")

        for capability, clauses in permissions.items():
            if capability == "schema_version":
                continue
            if not isinstance(clauses, dict):
                raise ManifestRejected(f"{source}: /permissions/{capability} must be an object")
            unknown_members = set(clauses) - KNOWN_MEMBERS.get(capability, set())
            if unknown_members:
                raise ManifestRejected(
                    f"{source}: unknown members {sorted(unknown_members)} in "
                    f"/permissions/{capability}")

        entities = permissions.get("entities", {})
        for member in ("read", "subscribe", "write"):
            if member in entities:
                patterns = _require_list(entities[member], f"/permissions/entities/{member}")
                _validate_entity_patterns(patterns, f"/permissions/entities/{member}")

        services = permissions.get("services", {})
        if "call" in services:
            _validate_services(_require_list(services["call"], "/permissions/services/call"))

        events = permissions.get("events", {})
        for member in ("subscribe", "fire"):
            if member in events:
                _validate_events(_require_list(events[member], f"/permissions/events/{member}"),
                                 f"/permissions/events/{member}")

        network = permissions.get("network", {})
        if "egress" in network:
            _validate_network(_require_list(network["egress"], "/permissions/network/egress"),
                              "/permissions/network/egress")
        for member in ("tcp", "udp"):
            if member in network.get("local", {}):
                _validate_ports(network["local"][member],
                                f"/permissions/network/local/{member}")
        for member in ("listen", "scan"):
            if member in network.get("discover", {}):
                _validate_ports(network["discover"][member],
                                f"/permissions/network/discover/{member}")

        if "resources" in permissions:
            _validate_resources(permissions["resources"])

        # §5.10.5, at parse time: a path that reaches the configuration root, its storage or
        # its secrets is rejected here rather than refused later.
        for entry in _require_list(permissions.get("files", {}).get("read", []),
                                   "/permissions/files/read") + \
                _require_list(permissions.get("files", {}).get("write", []),
                              "/permissions/files/write"):
            try:
                reject_forbidden(Path(entry), config_root)
            except GrantRefused as err:
                raise ManifestRejected(f"{source}: {err}") from err

        return cls(domain, provenance, permissions, source)

    @property
    def resources(self) -> ResourceLimits:
        """S9's bound for this integration, from its own clause where it declared one.

        **A manifest that declares nothing gets the defaults, not no limit.** S6 makes an
        absent capability a denial everywhere else in this module, and the same reading here
        would mean an integration that declares no `resources` clause runs unbounded — which
        inverts default-deny for the one requirement whose threat, T16, is an integration
        consuming everything. So absence means the framework's own bound rather than the
        integration's, and §7.22 records that as the one place where absence is not denial.
        """
        return replace(ResourceLimits(), **self.permissions.get("resources", {}))

    # -- deciding ----------------------------------------------------------------------

    def decide(self, request: dict) -> Decision:
        """§5.11.3 step 3. Match the request against the clauses; absent a match, deny."""
        operation = request.get("op")
        if not isinstance(operation, str) or operation not in OPERATIONS:
            return Decision(False, f"unknown operation {operation!r}", clause="/permissions")

        capability, member = OPERATIONS[operation]
        pointer = f"/permissions/{capability}/{member}"

        if self.provenance is Provenance.NONE:
            return Decision(False, "no manifest is bound to this integration (S6)",
                            clause=pointer)

        clauses = self.permissions.get(capability, {}).get(member)
        if clauses is None:
            # Denied by absence — §5.10.8's second row. The pointer names the capability that
            # held no matching clause, which is what makes "denied because nothing said yes"
            # attributable rather than merely true.
            return Decision(False, f"nothing is declared at {pointer}", clause=pointer)

        target = self._target_of(operation, request)
        if target is None:
            return Decision(False, f"{operation} names no target", clause=pointer)

        if capability == "config_entries":
            allowed = clauses is True
            return Decision(allowed,
                            "declared" if allowed else f"{pointer} is not enabled",
                            clause=pointer)

        for index, clause in enumerate(clauses):
            if self._matches(capability, clause, target):
                return Decision(True, "declared", clause=f"{pointer}/{index}")

        return Decision(False, f"{target!r} matches no clause at {pointer}", clause=pointer)

    @staticmethod
    def _target_of(operation: str, request: dict) -> str | None:
        if operation.startswith("entity."):
            return request.get("entity")
        if operation == "service.call":
            service = request.get("service")
            if service is None and "domain" in request:
                service = f"{request['domain']}.{request.get('service_name')}"
            return service
        if operation.startswith("event."):
            return request.get("event")
        if operation == "network.egress":
            # The target is host **and** port, because the clause grants a service on a machine
            # rather than the machine (§7.24.3). A request naming no port cannot be matched
            # against a clause that names one, and is denied by returning something no clause
            # can equal rather than by defaulting to 443 — a default here would silently widen
            # every grant to the port the framework guessed.
            host, port = request.get("host"), request.get("port")
            if host is None or port is None:
                return None
            return f"{host}:{port}"
        return ""  # config_entries.list takes no target

    @staticmethod
    def _matches(capability: str, clause: str, target: str) -> bool:
        if capability == "services":
            # No wildcards here at all — validation guarantees the clause has none, so this
            # is exact string equality and S5 is a property of the comparison itself.
            return clause == target
        if capability == "entities":
            clause_domain, _, clause_object = clause.partition(".")
            target_domain, _, target_object = target.partition(".")
            if clause_domain != target_domain:
                return False
            return clause_object == "*" or clause_object == target_object
        if capability == "network":
            return clause == target
        return clause == target


def policy_for(manifests: dict[str, Manifest]) -> Callable[[str, dict], Decision]:
    """Bind manifests to identities, for `Mediator(policy=...)`.

    The dictionary is keyed by the identity the *socket* established (§5.11.2), never by
    anything a request said about itself. An integration with no entry here is denied
    everything, which is S6 and is also what happens to one that lies about being another.
    """
    def policy(identity: str, request: dict) -> Decision:
        manifest = manifests.get(identity)
        if manifest is None:
            return Decision(False, f"no manifest is bound to {identity} (S6)",
                            clause="/permissions")
        return manifest.decide(request)

    return policy
