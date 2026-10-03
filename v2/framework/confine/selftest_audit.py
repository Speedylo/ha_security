"""Identity and the audit chain, checked against what §5.12 says they do.

    §5.12.1  identity is three components hashed separately, so the log says *what* changed
    §5.12.2  identity is computed once per sandbox construction, not per decision
    §5.12.4  modifying, deleting or reordering any record breaks every link after it
    §5.12.4  the hash chain and the keyed MAC fail independently
    §5.11.3  the record is written before the action

Run:  python3 -m confine.selftest_audit
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

from .audit import GENESIS, AuditLog, Identity, _canonical, reconcile
from .channel import Channel
from .mediator import Decision, Mediator

PERMISSIONS = {"schema_version": 1, "entities": {"read": ["sensor.outdoor_temperature"]}}


def write_component(root: Path, *, code: str = "# v1\n",
                    permissions: dict | None = None,
                    requirements: list[str] | None = None) -> Path:
    component = root / "custom_components" / "demo"
    component.mkdir(parents=True, exist_ok=True)
    (component / "__init__.py").write_text(code)
    manifest = {"domain": "demo", "name": "Demo", "version": "1.0.0",
                "requirements": requirements if requirements is not None else []}
    if permissions is not None:
        manifest["permissions"] = permissions
    (component / "manifest.json").write_text(json.dumps(manifest, sort_keys=True))
    return component


def check(label: str, ok: bool, detail: str, failures: list[str]) -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {label:<56}  {detail}")
    if not ok:
        failures.append(label)


def forge_without_key(path: Path, seq: int, field: str, value: object) -> None:
    """Rewrite the log so the hash chain is consistent but the MAC chain cannot be.

    This is the adversary §5.12.4 escalates to: one who can write the file but cannot read the
    mediator's memory. They can recompute every sha256 link, because sha256 needs no secret,
    and they cannot recompute a single HMAC.
    """
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    records[seq][field] = value
    last_hash = GENESIS
    for record in records:
        record["prev_hash"] = last_hash
        body = {k: v for k, v in record.items() if k not in ("hash", "mac")}
        record["hash"] = hashlib.sha256(last_hash.encode() + _canonical(body)).hexdigest()
        last_hash = record["hash"]
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="confine-audit-"))
    failures: list[str] = []
    try:
        print("§5.12.1  identity is three components, so the log says what changed\n")
        component = write_component(root, permissions=PERMISSIONS)
        base = Identity.compute(component)

        write_component(root, code="# v2\n", permissions=PERMISSIONS)
        changed_code = Identity.compute(component)
        check("a source change moves only the source hash",
              changed_code.changes_from(base) == ["source"],
              str(changed_code.changes_from(base)), failures)

        write_component(root, permissions={**PERMISSIONS,
                                           "services": {"call": ["lock.unlock"]}})
        changed_grant = Identity.compute(component)
        check("a permission change moves the manifest hash with no code change",
              changed_grant.changes_from(base) == ["manifest"],
              str(changed_grant.changes_from(base)), failures)

        write_component(root, permissions=PERMISSIONS, requirements=["requests==2.32.0"])
        changed_deps = Identity.compute(component)
        check("a dependency change is visible",
              "requirements" in changed_deps.changes_from(base),
              str(changed_deps.changes_from(base)), failures)
        # Honest note, and it is a finding rather than a detail: Home Assistant declares
        # requirements *inside* manifest.json, so a declared-dependency change necessarily
        # moves the manifest hash too. The third component only becomes independent once
        # resolved versions are recorded — which is exactly the supply-chain case §5.12.1
        # cares about, and exactly what is not built yet.
        check("...and, as declared, it is not independent of the manifest",
              changed_deps.changes_from(base) == ["manifest", "requirements"],
              str(changed_deps.changes_from(base)), failures)

        check("the composite differs whenever any component does",
              len({base.composite, changed_code.composite, changed_grant.composite,
                   changed_deps.composite}) == 4, "four distinct composites", failures)

        print("\n§5.12.4  the chain, and the two links that fail independently\n")
        write_component(root, permissions=PERMISSIONS)
        log = AuditLog(root / "audit.jsonl")
        run_id = log.run(Identity.compute(component), "author-declared")
        for i in range(5):
            log.decision(run_id, "demo",
                         {"op": "entity.read", "entity": f"sensor.s{i}"},
                         allowed=i % 2 == 0, clause="/permissions/entities/read", reason="t")
        check("a clean chain verifies", log.verify() == [], "6 records, no breaks", failures)

        # -- modification, twice: once naively, once by an attacker who is trying
        clone = root / "modified.jsonl"
        shutil.copy(log.path, clone)
        records = [json.loads(l) for l in clone.read_text().splitlines()]
        assert records[2]["allowed"] is False, "pick a record whose value actually changes"
        records[2]["allowed"] = True          # flip a denial into a permit
        clone.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
        breaks = AuditLog(clone, key=log.key).verify()
        check("flipping a denial into a permit breaks every link after it",
              {b.seq for b in breaks} == {2, 3, 4, 5},
              f"seq {sorted({b.seq for b in breaks})}, {sorted({b.kind for b in breaks})}",
              failures)

        # The same edit, with the tampered record's own hash repaired — which is what an
        # attacker who has read §5.12.4 would try. It changes nothing, because verification
        # recomputes each link and carries the computed value forward rather than trusting the
        # one in the file. An earlier version of `verify()` chained on the stored hash, and
        # this repair reduced the damage to a single broken link; that is the bug this
        # assertion exists to keep fixed.
        records[2]["hash"] = hashlib.sha256(
            records[2]["prev_hash"].encode()
            + _canonical({k: v for k, v in records[2].items()
                          if k not in ("hash", "mac")})).hexdigest()
        clone.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
        breaks = AuditLog(clone, key=log.key).verify()
        check("repairing its own hash does not help the attacker",
              {b.seq for b in breaks} == {2, 3, 4, 5}
              and len([b for b in breaks if b.kind == "link"]) == 3,
              f"seq {sorted({b.seq for b in breaks})}, "
              f"{len([b for b in breaks if b.kind == 'link'])} link breaks", failures)

        # -- deletion
        clone = root / "deleted.jsonl"
        lines = log.path.read_text().splitlines()
        clone.write_text("\n".join(lines[:3] + lines[4:]) + "\n")
        breaks = AuditLog(clone, key=log.key).verify()
        check("deleting a record is detected",
              any(b.kind == "sequence" for b in breaks) and any(b.kind == "link" for b in breaks),
              f"{sorted({b.kind for b in breaks})}", failures)

        # -- reordering
        clone = root / "reordered.jsonl"
        lines = log.path.read_text().splitlines()
        lines[2], lines[3] = lines[3], lines[2]
        clone.write_text("\n".join(lines) + "\n")
        breaks = AuditLog(clone, key=log.key).verify()
        check("reordering two records is detected", bool(breaks),
              f"{sorted({b.kind for b in breaks})}", failures)

        # -- the escalation of §5.12.4
        clone = root / "forged.jsonl"
        shutil.copy(log.path, clone)
        forge_without_key(clone, 2, "allowed", True)
        breaks = AuditLog(clone, key=log.key).verify()
        kinds = {b.kind for b in breaks}
        check("an attacker without the key can rebuild the whole hash chain",
              "hash" not in kinds and "link" not in kinds and "sequence" not in kinds,
              "every sha256 link recomputes cleanly", failures)
        check("...and cannot rebuild one link of the MAC chain",
              kinds == {"mac"} and {b.seq for b in breaks} == {2, 3, 4, 5},
              f"MAC breaks at seq {sorted({b.seq for b in breaks})}", failures)

        print("\n§5.11.3  the record is written before the action\n")
        log2 = AuditLog(root / "ordering.jsonl")
        run2 = log2.run(Identity.compute(component), "author-declared")

        def act() -> None:
            raise RuntimeError("the mediator dies here")

        try:
            log2.decision(run2, "demo", {"op": "service.call", "service": "lock.lock"},
                          allowed=True, clause="/permissions/services/call/0", reason="declared")
            act()
        except RuntimeError:
            pass
        durable = log2.records()
        check("an action that dies after the record leaves the record", len(durable) == 2,
              f"{len(durable)} records on disk", failures)
        check("...and the record says what was permitted",
              durable[-1]["allowed"] and durable[-1]["target"] == "lock.lock",
              f"{durable[-1]['op']} {durable[-1]['target']}", failures)

        # -- T4: the record names what was decided, and the instrument that compares records --
        print("\n  T4 — what the record names, and the check that compares it with memory")
        log3 = AuditLog(path=root / "t4.jsonl")
        decoy = log3.decision("r", "demo", {"op": "service.call", "service": "lock.unlock",
                                            "entity": "sensor.harmless"}, False, None, "no")
        check("a decoy entity does not become the recorded target of a service call",
              decoy["target"] == "lock.unlock"
              and decoy["requested"].get("entity") == "sensor.harmless",
              f"target={decoy['target']!r} requested={decoy['requested']}", failures)
        portless = log3.decision("r", "demo", {"op": "network.egress", "host": "evil.invalid"},
                                 False, "/permissions/network/egress", "no")
        check("...and a refused request still records what it asked for",
              portless["requested"] == {"host": "evil.invalid"},
              str(portless["requested"]), failures)

        # A mediator with a log, driven over a real socket pair, then mutated three ways. A
        # reconciliation that reported nothing would pass every harness T4 wired, so each of its
        # findings is shown firing here before any harness relies on its silence.
        mediator = Mediator(policy=lambda identity, request: Decision(
            request.get("op") == "entity.read", "test", clause="/permissions/entities/read/0"))
        mediator.log = AuditLog(path=root / "t4-mediated.jsonl")
        try:
            mediator.register("demo", Channel(Channel.pair()[0]))
            refused = False
        except ValueError:
            refused = True
        check("a mediator with a log refuses to register a sandbox it cannot name the code of",
              refused, "ValueError raised" if refused else "register() accepted no component",
              failures)

        mine, theirs = Channel.pair()
        mediator.register("demo", Channel(mine), component=component)
        peer = Channel(theirs)
        peer.send({"id": 1, "op": "entity.read", "entity": "sensor.a"})
        mediator._handle_ready(mine.fileno())
        peer.recv()
        peer.send({"id": 2, "op": "service.call", "service": "lock.unlock"})
        mediator._handle_ready(mine.fileno())
        peer.recv()
        theirs.sendall((9).to_bytes(4, "big") + b"{not json")
        mediator._handle_ready(mine.fileno())
        records = mediator.log.records()
        check("register() writes the run record, and every decision names it",
              reconcile(mediator.audit, records) == [],
              "; ".join(reconcile(mediator.audit, records))
              or f"{len(records)} records, 0 disagreements", failures)
        check("...and a malformed frame reaches the durable record",
              any(r.get("kind") == "protocol_error" for r in records),
              str([r.get("kind") for r in records]), failures)

        decisions = [r for r in records if r.get("kind") == "decision"]
        mutations = {
            "a durable decision missing": [r for r in records if r is not decisions[0]],
            "a verdict that differs": [dict(r, allowed=not r["allowed"]) if r is decisions[1]
                                       else r for r in records],
            "a decision naming a run nobody recorded": [dict(r, run="ffff") if r is decisions[0]
                                                        else r for r in records],
        }
        for label, mutated in mutations.items():
            found = reconcile(mediator.audit, mutated)
            check(f"reconcile catches {label}", bool(found),
                  found[0] if found else "it reported nothing", failures)

        # -- the directory entries are durable too ------------------------------------------
        # A crash cannot be staged here, so the check is on what the code asks the kernel to
        # make durable: every fsync is recorded with whether its descriptor was a directory, and
        # which one. The file's own fsync covers its contents; only its directory's covers its name.
        from . import audit as audit_module
        synced: list[tuple[str, int]] = []
        real_fsync = audit_module.os.fsync

        def recording_fsync(fd: int) -> None:
            info = os.fstat(fd)
            synced.append(("dir" if stat.S_ISDIR(info.st_mode) else "file", info.st_ino))
            real_fsync(fd)

        audit_module.os.fsync = recording_fsync
        try:
            nested = root / "fresh" / "deeper" / "audit.jsonl"
            log5 = AuditLog(nested)
            at_creation = list(synced)
            log5.approval(base, "author-declared")
            first = synced[len(at_creation):]
            log5.approval(base, "author-declared")
            second = synced[len(at_creation) + len(first):]
        finally:
            audit_module.os.fsync = real_fsync
        inode = lambda d: os.stat(d).st_ino  # noqa: E731
        check("creating the log's directories fsyncs the parent of each one it made",
              at_creation == [("dir", inode(root)), ("dir", inode(root / "fresh"))],
              str(at_creation), failures)
        check("the first record fsyncs the file and then its directory",
              first == [("file", inode(nested)), ("dir", inode(nested.parent))],
              str(first), failures)
        check("...and a later record fsyncs only the file",
              second == [("file", inode(nested))], str(second), failures)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print()
    if failures:
        print(f"FAILED: {'; '.join(failures)}")
        return 1
    print("PASS — the three components move independently where they can, every form of")
    print("       tampering is detected, and the two chains fail independently.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
