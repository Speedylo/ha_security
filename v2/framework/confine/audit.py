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


@dataclass(frozen=True)
class Identity:
    """§5.12.1's three-part tuple, hashed separately and then together."""

    domain: str
    source: str
    manifest: str
    requirements: str
    composite: str

    @classmethod
    def compute(cls, component_dir: Path) -> Identity:
        """Hash what was loaded — which is not what will execute, and §5.12.1 says so.

        An integration that fetches or generates code at runtime defeats this. The limitation
        is inherited rather than introduced, and it bounds T12's treatment as well as the
        identity's meaning.
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

        # Declared requirements. §5.12.1 asks for these *with resolved versions*; resolution
        # happens when dependencies are installed into the sandbox, which is not built yet, so
        # what is hashed here is the declaration. Recorded as a gap rather than glossed.
        try:
            declared = json.loads(manifest_bytes or b"{}").get("requirements", [])
        except ValueError:
            declared = []
        requirements = hashlib.sha256(
            _canonical({"requirements": sorted(declared)})).hexdigest()

        composite = hashlib.sha256(
            _canonical({"domain": component_dir.name, "source": source,
                        "manifest": manifest, "requirements": requirements})).hexdigest()
        return cls(component_dir.name, source, manifest, requirements, composite)

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
        return {"domain": self.domain, "source": self.source, "manifest": self.manifest,
                "requirements": self.requirements, "composite": self.composite}


@dataclass
class Break:
    """Where a chain stopped being consistent, and which of the two links failed."""

    seq: int
    kind: str
    detail: str


@dataclass
class AuditLog:
    """Append-only JSON Lines, with a hash chain and a keyed MAC chain over it."""

    path: Path
    key: bytes = field(default_factory=lambda: secrets.token_bytes(32))
    _last_hash: str = GENESIS
    _last_mac: str = GENESIS
    _seq: int = 0

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # -- writing ------------------------------------------------------------------------

    def _append(self, body: dict) -> dict:
        body = {"seq": self._seq, "time": time.time(), **body,
                "prev_hash": self._last_hash, "prev_mac": self._last_mac}
        canonical = _canonical(body)
        record = dict(body)
        record["hash"] = hashlib.sha256(self._last_hash.encode() + canonical).hexdigest()
        record["mac"] = hmac.new(self.key, self._last_mac.encode() + canonical,
                                 hashlib.sha256).hexdigest()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            # A record that is only in a buffer is not a record. §5.11.3 puts the write before
            # the action so that an action which succeeds and then crashes the mediator is
            # still attributable, and that ordering is worth nothing if the write is lazy.
            os.fsync(handle.fileno())
        self._last_hash, self._last_mac = record["hash"], record["mac"]
        self._seq += 1
        return record

    def approval(self, identity: Identity, provenance: str) -> dict:
        """§5.9.6's *re-confirmed*: the user was shown this exact identity and accepted it.

        Written as its own record kind rather than inferred from the run records, because the
        two answer different questions. A run says *this code executed*; an approval says *a
        human saw what it was allowed to do*. §7.30.6 is the section that found the difference
        mattered: the warning in `describe()` is phrased "since you approved", and with only run
        records to compare against, the baseline moved every time the integration started — so
        the warning would have shown once, to nobody, and then been gone for good.
        """
        return self._append({"kind": "approval", "identity": identity.as_record(),
                             "provenance": provenance})

    def run(self, identity: Identity, provenance: str) -> str:
        """§5.12.2: one run record per sandbox construction, carrying the full identity."""
        run_id = secrets.token_hex(8)
        self._append({"kind": "run", "run": run_id, "identity": identity.as_record(),
                      "provenance": provenance})
        return run_id

    def decision(self, run_id: str, identity: str, request: dict, allowed: bool,
                 clause: str | None, reason: str) -> dict:
        """One record per decision. Consequences are not recorded — §5.12.3."""
        # An egress target is `host:port`, not `host`. §7.24.3 measured that a hostname-only
        # clause can neither grant nor withhold a port and §7.25's schema added one — but this
        # record kept extracting the host alone, so the log could not distinguish a grant of
        # 443 from a grant of 6445 on the same host. F3 requires every decision be attributable
        # to the clause that produced it, and the clause pointer does name the index; the
        # human-readable target should not be the weaker of the two. Found by §7.27.
        target = (request.get("entity") or request.get("service")
                  or request.get("host") or request.get("event"))
        if request.get("host") and request.get("port") and target == request.get("host"):
            target = f"{request['host']}:{request['port']}"
        return self._append({
            "kind": "decision", "run": run_id, "integration": identity,
            "op": request.get("op"), "target": target,
            "claimed": request.get("integration"),
            "allowed": allowed, "clause": clause, "reason": reason,
        })

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
            found = identity
    if found is None:
        return None
    try:
        return Identity(**found)
    except TypeError:
        # A record written by a different version of this module. Reported as "no baseline"
        # rather than guessed at: a wrong baseline would produce a warning about a change that
        # did not happen, which is worse than no warning.
        return None
