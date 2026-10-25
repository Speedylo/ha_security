"""Identity, and the record that makes a decision attributable.

§5.12 fixes both. Identity is **the domain name plus a content hash of what was loaded**, and
the hash is of a tuple of three components hashed separately *and* together:

    source        the code that ran
    manifest      the manifest including its `permissions` block — the manifest *is* the grant,
                  so a manifest swapped without a source change is an authority change
    requirements  the declared dependencies, which is where supply-chain change actually lands

**Keeping the three separate is the point.** A single composite says *something changed*; three
components say *what* changed, and a source change, a permission change and a dependency change
are different events warranting different responses. The composite is what a manifest binds to
(§5.9.6); the components are what make the log diagnostic rather than merely tamper-evident.

The log is a chain, and it carries **two** independent links per record:

    hash   sha256 over the previous record's hash and this record's body. Anyone can verify it
           and anyone who can rewrite the whole file can forge it.
    mac    HMAC over the previous record's mac and this record's body, keyed with a secret held
           only in the mediator's memory. An attacker who can write the file but cannot read
           that memory can no longer produce a consistent chain.

§5.12.4 describes exactly this escalation. Carrying both is what makes the two fail
independently: a partial rewrite breaks the hash chain, and a *complete* rewrite by someone
without the key still breaks the MAC chain. Neither survives a full host compromise, which
§4.2 places out of scope and §5.12.4 says plainly.

**The key does not outlive the mediator**, which is the cost of holding it only in memory:
records written by an earlier run remain hash-verifiable and are no longer MAC-verifiable. That
is a real limitation and it is stated here rather than discovered later.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path

GENESIS = "0" * 64

#: Where the log lives relative to the Home Assistant configuration directory. Named here so
#: that the mediator which writes it and the `describe` surface which reads it back cannot
#: disagree about the path — §7.30.6 exists because a reader of this log did not exist at all.
DEFAULT_LOG = Path("confine/audit/decisions.jsonl")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(payload: dict) -> bytes:
    """One byte string per record, so that verification cannot disagree with writing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def grant_digest(provenance: str, permissions: dict) -> str:
    """What an approval of a grant is an approval *of* (F57).

    The identity alone does not cover it: a derived manifest lives beside the integration, in
    `<domain>.permissions.json`, which `Identity.compute` does not hash, so widening a derived
    grant changes no identity. This digest covers the grant that was actually loaded, whichever
    file it came from, and the provenance it was shown to the user under.
    """
    return hashlib.sha256(_canonical({"provenance": provenance,
                                      "permissions": permissions})).hexdigest()


@dataclass(frozen=True)
class Identity:
    """§5.12.1's three-part tuple, hashed separately and then together."""

    domain: str
    source: str
    manifest: str
    requirements: str
    composite: str
    #: The distributions installed for this run, as sorted `name==version`, or None when no
    #: install directory was given (an approval, made before anything is installed). An empty
    #: list means an install directory was given and held nothing.
    resolved: list[str] | None = None

    @classmethod
    def compute(cls, component_dir: Path, installed: Path | None = None) -> Identity:
        """Hash what was loaded — which is not what will execute, and §5.12.1 says so.

        An integration that fetches or generates code at runtime defeats this. The limitation
        is inherited rather than introduced, and it bounds T12's treatment as well as the
        identity's meaning.

        `installed` is the directory the integration's requirements were installed into for
        this run. With it, the third component hashes the resolved versions as well as the
        declaration (§5.12.1). Without it, the hash is exactly what it was before that was
        added, so approvals recorded earlier stay comparable.
        """
        manifest_path = component_dir / "manifest.json"
        manifest_bytes = manifest_path.read_bytes() if manifest_path.is_file() else b""

        # Source: every file except the manifest, which is hashed separately precisely so that
        # a permission change is distinguishable from a code change.
        entries = sorted(
            p for p in component_dir.rglob("*")
            if p.is_file() and p != manifest_path and "__pycache__" not in p.parts)
        source_digest = hashlib.sha256()
        for path in entries:
            source_digest.update(str(path.relative_to(component_dir)).encode())
            source_digest.update(b"\0")
            source_digest.update(sha256_file(path).encode())
        source = source_digest.hexdigest()

        manifest = hashlib.sha256(manifest_bytes).hexdigest()

        # Declared requirements, and with an install directory, what they resolved to. Until
        # verification finding F08 (2026-10-06) only the declaration was hashed, under a comment
        # saying installation was not built. It was: the harnesses install each integration's
        # requirements before its sandbox registers. So a dependency that moved between two
        # runs (F13) left the identity unchanged, which is the case §5.12.1 has this part for.
        try:
            declared = json.loads(manifest_bytes or b"{}").get("requirements", [])
        except ValueError:
            declared = []
        resolved = None if installed is None else resolved_versions(installed)
        payload: dict = {"requirements": sorted(declared)}
        if resolved is not None:
            payload["resolved"] = resolved
        requirements = hashlib.sha256(_canonical(payload)).hexdigest()

        composite = hashlib.sha256(
            _canonical({"domain": component_dir.name, "source": source,
                        "manifest": manifest, "requirements": requirements})).hexdigest()
        return cls(component_dir.name, source, manifest, requirements, composite, resolved)

    def changes_from(self, other: Identity) -> list[str]:
        """Which of the three components moved. This is what three hashes buy."""
        changed = []
        if self.source != other.source:
            changed.append("source")
        if self.manifest != other.manifest:
            changed.append("manifest")
        if self.requirements != other.requirements:
            changed.append("requirements")
        return changed

    def as_record(self) -> dict:
        record = {"domain": self.domain, "source": self.source, "manifest": self.manifest,
                  "requirements": self.requirements, "composite": self.composite}
        if self.resolved is not None:
            record["resolved"] = list(self.resolved)
        return record


def resolved_versions(installed: Path) -> list[str]:
    """Every distribution in an install directory, as sorted `name==version`.

    Read from each `*.dist-info`'s own metadata, the way the interpreter in the sandbox will
    find them, rather than from the declaration that asked for them.
    """
    found = set()
    for dist in importlib.metadata.distributions(path=[str(installed)]):
        name = dist.metadata["Name"]
        if name:
            found.add(f"{name}=={dist.version}")
    return sorted(found)


@dataclass
class Break:
    """Where a chain stopped being consistent, and which of the two links failed."""

    seq: int
    kind: str
    detail: str


#: The fields Home Assistant reads a service call's targets from (`helpers/target.py`,
#: `TargetSelection`, at 2026.8.3). Each may be a string or a list.
SERVICE_TARGETS = ("entity_id", "device_id", "area_id", "floor_id", "label_id")


def target_of(operation: str | None, request: dict) -> str | None:
    """What a request is *about*, read from the field its operation is decided on.

    Lives here rather than in `manifest` so that the policy and the durable record share one
    definition. They did not, and T4 found what that cost: `decision()` took `entity` before
    `service` for every operation, so a `service.call` for `lock.unlock` that also carried
    `"entity": "sensor.harmless"` was decided on the service and **recorded against the sensor** —
    the field chosen by the party being audited. The manifest is the authority on what an
    operation targets; the log now records what the manifest decided on.
    """
    operation = operation or ""
    if operation.startswith("entity."):
        return request.get("entity")
    if operation == "service.call":
        service = request.get("service")
        if service is None and "domain" in request:
            service = f"{request['domain']}.{request.get('service_name')}"
        return service
    if operation.startswith("event."):
        return request.get("event")
    if operation in ("network.udp.send", "network.udp.recv", "network.tcp.local",
                     "discover.scan", "discover.listen"):
        # The port, and only the port. The address is not part of the grant — it is pinned
        # separately, and only to something the mediator observed answering (§4 of the
        # design note). A clause that named an address would be asking the author for a
        # DHCP lease.
        port = request.get("port")
        return str(port) if isinstance(port, int) else None
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


def _fsync_directory(directory: Path) -> None:
    """Make a directory's entries durable: open it read-only and fsync the descriptor."""
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@dataclass
class AuditLog:
    """Append-only JSON Lines, with a hash chain and a keyed MAC chain over it."""

    path: Path
    key: bytes = field(default_factory=lambda: secrets.token_bytes(32))
    _last_hash: str = GENESIS
    _last_mac: str = GENESIS
    _seq: int = 0
    #: Whether the file's name is known durable: it existed when this log was opened, or its
    #: directory has been fsynced since. Set only after that fsync succeeds (F35 R9).
    _named: bool = False

    def __post_init__(self) -> None:
        # Every directory this creates is a new entry in its parent, and an entry is durable only
        # once the parent is fsynced. Without that, a crash can keep the records the file's own
        # fsync promised and lose the name that reaches them.
        missing = [d for d in (self.path.parent, *self.path.parent.parents) if not d.exists()]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for directory in reversed(missing):
            _fsync_directory(directory.parent)
        self._named = self.path.exists()

    # -- writing ------------------------------------------------------------------------

    def _append(self, body: dict) -> dict:
        body = {"seq": self._seq, "time": time.time(), **body,
                "prev_hash": self._last_hash, "prev_mac": self._last_mac}
        canonical = _canonical(body)
        record = dict(body)
        record["hash"] = hashlib.sha256(self._last_hash.encode() + canonical).hexdigest()
        record["mac"] = hmac.new(self.key, self._last_mac.encode() + canonical,
                                 hashlib.sha256).hexdigest()
        # Unbuffered and binary, so that nothing of a failed record can wait in a buffer and be
        # written when the file is closed, after the truncation below has undone it.
        with self.path.open("ab", buffering=0) as handle:
            # Where the file ends before this record, so a failed append can be undone. A full
            # disk (verification 4.5, finding F28) left half a record behind, and every record
            # written after space was freed sat beyond it where `verify` could never reach.
            size = handle.seek(0, os.SEEK_END)
            try:
                line = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
                while line:
                    line = line[handle.write(line):]
                # A record that is only in a buffer is not a record. §5.11.3 puts the write
                # before the action so that an action which succeeds and then crashes the
                # mediator is still attributable, and that ordering is worth nothing if the
                # write is lazy.
                os.fsync(handle.fileno())
            except BaseException:
                # The record did not happen. Leave the file as the last complete record left it,
                # then fail as before: the chain is not advanced, and the caller does not act.
                os.ftruncate(handle.fileno(), size)
                os.fsync(handle.fileno())
                raise
        if not self._named:
            # The file's fsync makes its contents durable, not its name. Until the directory is
            # fsynced too, a crash can leave the first record written to a file nothing points
            # at (fsync(2), NOTES). Once per log, since appends do not change the directory, and
            # not decided by whether the file exists: a first record that failed leaves an empty
            # file behind, and the next record must still sync its name (verification 4.7, R9).
            _fsync_directory(self.path.parent)
            self._named = True
        self._last_hash, self._last_mac = record["hash"], record["mac"]
        self._seq += 1
        return record

    def approval(self, identity: Identity, provenance: str, grant: str | None = None,
                 by: str | None = None) -> dict:
        """§5.9.6's *re-confirmed*: the user was shown this exact identity and accepted it.

        Written as its own record kind rather than inferred from the run records, because the
        two answer different questions. A run says *this code executed*; an approval says *a
        human saw what it was allowed to do*. §7.30.6 is the section that found the difference
        mattered: the warning in `describe()` is phrased "since you approved", and with only run
        records to compare against, the baseline moved every time the integration started — so
        the warning would have shown once, to nobody, and then been gone for good.
        """
        record = {"kind": "approval", "identity": identity.as_record(), "provenance": provenance}
        # Since F57 the mediator refuses to register a sandbox whose grant has no approval, and
        # this digest is what it compares (`grant_digest`). An approval without one, as every
        # approval written before F57 is, admits nothing.
        if grant is not None:
            record["grant"] = grant
        # F57c: who approved, when it was not the operator at the terminal. The Repairs panel
        # does not tell a flow which administrator opened it, so this names the role.
        if by is not None:
            record["by"] = by
        return self._append(record)

    def run(self, identity: Identity, provenance: str, integration: str | None = None) -> str:
        """§5.12.2: one run record per sandbox construction, carrying the full identity.

        `integration` is the name the mediator bound the socket to, which is what every
        decision record carries. It defaults to the identity's domain and differs only where a
        supervisor names two sandboxes of one component apart; T4 records it rather than
        leaving a reader to infer which run a decision belonged to from a directory name.
        """
        run_id = secrets.token_hex(8)
        self._append({"kind": "run", "run": run_id, "identity": identity.as_record(),
                      "integration": integration or identity.domain,
                      "provenance": provenance})
        return run_id

    def decision(self, run_id: str, identity: str, request: dict, allowed: bool,
                 clause: str | None, reason: str) -> dict:
        """One record per decision. Consequences are not recorded — §5.12.3."""
        # F3, at the durable end too: `Decision` already refuses to exist without a clause, and
        # this refuses to write a record without one, before anything reaches the file.
        if not clause:
            raise ValueError(f"a decision record must name its clause: {reason!r}")
        # An egress target is `host:port`, not `host`. §7.24.3 measured that a hostname-only
        # clause can neither grant nor withhold a port and §7.25's schema added one — but this
        # record kept extracting the host alone, so the log could not distinguish a grant of
        # 443 from a grant of 6445 on the same host. F3 requires every decision be attributable
        # to the clause that produced it, and the clause pointer does name the index; the
        # human-readable target should not be the weaker of the two. Found by §7.27.
        #
        # And the target is the one the decision was made on — `target_of`, shared with the
        # manifest — never a field picked by precedence from whatever the sandbox sent (T4).
        target = target_of(request.get("op"), request)
        # What the sandbox *asked about*, kept apart from what was decided on. Without it, a
        # refused egress request that named no port records target `None` and the log no longer
        # says which host was attempted — a denial should still say what it denied. These are
        # the sandbox's own claims, labelled as such, exactly as `claimed` is for identity.
        # `address` since W2 (a): a `network.tcp.local` decision is made on the port, and the
        # address it pins must be in the record too, or the log could not say which device.
        requested = {k: request[k] for k in ("entity", "service", "domain", "service_name",
                                             "host", "address", "port", "event") if k in request}
        # A service call's devices are in its data, not at the top level, so until F54 no record
        # said which device a granted service was used on. The decision is still made on the
        # service, and `target` stays that; these are the sandbox's claims, beside the others.
        data = request.get("data")
        if request.get("op") == "service.call" and isinstance(data, dict):
            requested.update({k: data[k] for k in SERVICE_TARGETS if k in data})
        # A user's command, with what it set (bridge step 2). The mediator has already replaced
        # the data of a command it refused for its shape by each value's type and length.
        if request.get("op") == "entity.command" and isinstance(data, dict):
            requested["data"] = data
        return self._append({
            "kind": "decision", "run": run_id, "integration": identity,
            "op": request.get("op"), "target": target, "requested": requested,
            "claimed": request.get("integration"),
            "allowed": allowed, "clause": clause, "reason": reason,
        })

    def protocol_error(self, run_id: str, identity: str, detail: str) -> dict:
        """A sandbox sent a frame the mediator could not parse, and lost its channel for it.

        Recorded durably from T4 on. Before, it went to the in-memory list alone — and a
        malformed frame is precisely what a hostile sandbox produces, so the one event S7 most
        needs attributable was the one event the durable record never saw.
        """
        return self._append({"kind": "protocol_error", "run": run_id, "integration": identity,
                             "detail": detail})

    def cutoff(self, run_id: str, identity: str, refusals: int, window: float) -> dict:
        """A sandbox refused too often, and was stopped (`notes/flood_cutoff_prediction.md`).

        One record in place of the unbounded number its refusals would otherwise have cost:
        the refusals up to the limit are each recorded as decisions, and this says why the
        channel then closed and who closed it.
        """
        return self._append({"kind": "cutoff", "run": run_id, "integration": identity,
                             "detail": f"{refusals} refusals within {window:g} s"})

    def reinstate(self, identity: str, by: str) -> dict:
        """A cut-off integration was allowed to run again, and on whose say-so.

        No run: the integration is not running when this is written. The next run record,
        written when it registers again, is the one its decisions will name.
        """
        return self._append({"kind": "reinstate", "run": "", "integration": identity,
                             "detail": f"reinstated by {by}"})

    # -- verifying ----------------------------------------------------------------------

    def verify(self, key: bytes | None = None) -> list[Break]:
        """Walk the chain and report every inconsistency, not only the first.

        Reporting only the first would make a deletion and a rewrite look alike; §5.12.4's
        claim is that "modifying, deleting or reordering any record breaks every link after
        it", and a verifier that stops at one cannot show that.
        """
        key = self.key if key is None else key
        breaks: list[Break] = []
        last_hash, last_mac, expected_seq = GENESIS, GENESIS, 0
        if not self.path.exists():
            return breaks

        for line_number, line in enumerate(self.path.read_text().splitlines()):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError as err:
                breaks.append(Break(line_number, "unreadable", str(err)))
                return breaks

            body = {k: v for k, v in record.items() if k not in ("hash", "mac")}
            canonical = _canonical(body)
            seq = record.get("seq", line_number)

            if seq != expected_seq:
                breaks.append(Break(seq, "sequence",
                                    f"record {seq} where {expected_seq} was expected"))
            if record.get("prev_hash") != last_hash:
                breaks.append(Break(seq, "link", "prev_hash does not name the record before it"))

            computed_hash = hashlib.sha256(last_hash.encode() + canonical).hexdigest()
            if computed_hash != record.get("hash"):
                breaks.append(Break(seq, "hash", "the record's contents do not match its hash"))
            computed_mac = hmac.new(key, last_mac.encode() + canonical, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(computed_mac, record.get("mac", "")):
                breaks.append(Break(seq, "mac", "the keyed MAC does not verify"))

            # Carry forward what was *computed*, never what the file claims. Chaining on the
            # stored value would let an attacker who edits one record and repairs that record's
            # own hash break exactly one downstream link instead of all of them — which is how
            # §5.12.4's "breaks every link after it" stops being true. The stored hash is a
            # convenience for a reader; it is not an input to verification.
            last_hash, last_mac = computed_hash, computed_mac
            expected_seq = seq + 1
        return breaks

    def records(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]


#: Records that are not decisions, but are kept in the mediator's memory beside them and must
#: match one for one: a malformed frame (T4), and a cut-off and a reinstatement (the flood).
EVENTS = ("protocol_error", "cutoff", "reinstate")


def reconcile(memory: list[dict], records: list[dict]) -> list[str]:
    """Every way the durable record disagrees with the mediator's in-memory one, in order.

    T4's instrument. The in-memory list is what every harness reported from; the durable log is
    what S7 is claimed of. If they disagree, one of them is wrong, and until T4 only the first
    was ever read. Compared entry by entry rather than by count, because §7.31.12 is the record
    of what a matching total can hide.
    """
    problems: list[str] = []
    runs = {r.get("run"): r for r in records if r.get("kind") == "run"}
    durable = [r for r in records if r.get("kind") in ("decision", *EVENTS)]
    if len(memory) != len(durable):
        problems.append(f"{len(memory)} in memory against {len(durable)} durable")
    for index, (mem, rec) in enumerate(zip(memory, durable)):
        if mem.get("event") in EVENTS:
            if rec.get("kind") != mem["event"] or rec.get("integration") != mem.get("identity"):
                problems.append(f"#{index}: a {mem['event']} in memory is {rec.get('kind')} "
                                f"durably")
            continue
        for field_mem, field_rec in (("identity", "integration"), ("op", "op"),
                                     ("allowed", "allowed"), ("clause", "clause")):
            if mem.get(field_mem) != rec.get(field_rec):
                problems.append(f"#{index} {mem.get('op')}: {field_mem} "
                                f"{mem.get(field_mem)!r} in memory, {rec.get(field_rec)!r} durably")
        run = runs.get(rec.get("run"))
        if run is None:
            problems.append(f"#{index} {rec.get('op')}: names run {rec.get('run')!r}, "
                            f"which no run record carries")
        elif run.get("integration", (run.get("identity") or {}).get("domain")) \
                != rec.get("integration"):
            problems.append(f"#{index} {rec.get('op')}: decided for {rec.get('integration')!r}, "
                            f"but its run record is for {run.get('integration')!r}")
    return problems


def attach(mediator, prefix: str) -> Path:
    """Give `mediator` a durable log in a fresh directory, and return the directory.

    The directory is created **outside** whatever tree a harness removes, which is §7.27.6's
    first defect: a log inside the sandbox's root was deleted before it was read, and the run
    reported no decisions at all.
    """
    import tempfile

    directory = Path(tempfile.mkdtemp(prefix=prefix))
    mediator.log = AuditLog(path=directory / "decisions.jsonl")
    return directory


def summarise(mediator, directory: Path, keep_records: bool = False) -> dict:
    """Verify the chains, reconcile against `mediator.audit`, then remove the directory.

    What every T4-wired harness reports beside its own result, so that a run whose durable
    record disagrees with what the harness counted says so in the same JSON.
    """
    import shutil

    try:
        log = mediator.log
        records = log.records() if log is not None else []
        breaks = [str(b) for b in log.verify()] if log is not None else ["no log attached"]
        problems = reconcile(mediator.audit, records)
        summary = {"records": len(records),
                "runs": sum(1 for r in records if r.get("kind") == "run"),
                "decisions": sum(1 for r in records if r.get("kind") == "decision"),
                "breaks": breaks, "reconcile": problems,
                "ok": not breaks and not problems}
        if keep_records:
            summary["log"] = records
        return summary
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def report_durable(durable: dict | None) -> int:
    """Print T4's verdict on one confined run's durable record; 0 if it holds, 1 if not."""
    if not durable:
        print("  FAIL  the durable record (T4): no summary — the log was not engaged")
        return 1
    problems = list(durable.get("breaks") or []) + list(durable.get("reconcile") or [])
    print(f"  {'ok  ' if durable.get('ok') else 'FAIL'}  the durable record (T4): "
          f"{durable.get('runs')} run, {durable.get('decisions')} decisions, chains verify and "
          f"match the in-memory record" if durable.get("ok") else
          f"  FAIL  the durable record (T4): " + "; ".join(problems[:4]))
    return 0 if durable.get("ok") else 1


def last_record(path: Path, domain: str, kind: str = "approval") -> dict | None:
    """The most recent `kind` record whose identity is `domain`'s, or None if there is none.

    Read without the key, so it verifies nothing; `last_identity` says why that is the bound.
    """
    if not path.exists():
        return None
    found = None
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get("kind") != kind:
            continue
        identity = record.get("identity")
        if isinstance(identity, dict) and identity.get("domain") == domain:
            found = record
    return found


def last_identity(path: Path, domain: str, kind: str = "approval") -> Identity | None:
    """The identity of the most recent `kind` record for `domain`, or None if there is none.

    **This is the half of T12 that §7.30 demonstrated and §7.30.6 found nothing was calling.**
    Deciding whether an integration's code has changed *since the user approved it* needs two
    identities, and only one of them — the current one — can be computed from the directory on
    disk. The other has to be remembered, and the log is already the thing that remembers it.

    Reads without the key, and therefore verifies nothing. The MAC chain cannot be checked
    across runs at all, because §5.12.4's key is held only in the mediator's memory and does not
    outlive it, so a baseline read back from an earlier run is hash-verifiable and no more. That
    is R4's bound, not a new one: a reader who can rewrite the whole file can rewrite this
    baseline too, and nothing in this log defends against whoever owns the machine. Callers that
    want the weaker guarantee stated plainly get it here rather than by assuming otherwise.
    """
    record = last_record(path, domain, kind)
    if record is None:
        return None
    try:
        return Identity(**record["identity"])
    except TypeError:
        # A record written by a different version of this module. Reported as "no baseline"
        # rather than guessed at: a wrong baseline would produce a warning about a change that
        # did not happen, which is worse than no warning.
        return None
