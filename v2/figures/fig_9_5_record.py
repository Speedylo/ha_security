#!/usr/bin/env python3
"""Figure 9.5 — The audit record: one run record, the decisions that refer to it, and two chains.

Writes fig_9_5_record.svg. Run:  python3 fig_9_5_record.py

The fields are those `AuditLog._append`, `AuditLog.run` and `AuditLog.decision` write
(`confine/audit.py`). Every record carries both links: `hash` over the previous hash and this
record's body, and `mac`, an HMAC over the previous MAC and the body, keyed with a secret held
only in the mediator's memory. Clauses are JSON pointers into the
manifest, as the log writes them. The example values are illustrative: the decision is the
retest's `adaptive_lighting` call, and the devices it targets have been in the record since F54.
"""

from pathlib import Path

from svg9 import Canvas

OUT = Path(__file__).parent / "fig_9_5_record.svg"

c = Canvas(1500, 780)

RECORDS = [
    ("RUN RECORD  ·  seq 0", "kind: run\nrun: 3f9a…\nintegration: adaptive_lighting\n"
     "identity: source, manifest and\nrequirements, each hashed,\nand one composite hash"),
    ("DECISION  ·  seq 1", "kind: decision\nrun: 3f9a…\nop: entity.subscribe\n"
     "target: light.living_room\nallowed: true\nclause: /permissions/entities/subscribe/0"),
    ("DECISION  ·  seq 2", "kind: decision\nrun: 3f9a…\nop: service.call\n"
     "target: light.turn_on\nrequested: …, entity_id: light.living_room\nallowed: true\n"
     "clause: /permissions/services/call/0"),
]
X0, W, GAP, Y, H = 40, 420, 60, 120, 330
for i, (title, body) in enumerate(RECORDS):
    x = X0 + i * (W + GAP)
    c.box(x, Y, W, H, fill="white", title=title)
    c.text(x + 20, Y + 110, body, size=12, anchor="start")
    c.box(x + 15, Y + 220, W - 30, 42, fill="light")
    c.text(x + 30, Y + 241, "prev_hash, prev_mac: the record before", size=12, anchor="start")
    c.box(x + 15, Y + 272, W - 30, 42, fill="mid")
    c.text(x + 30, Y + 293, "hash, mac: over this record and those", size=12, anchor="start")
    if i:
        # The previous record's links are carried into this one.
        px = x - GAP - 15
        c.line([(px, Y + 293), (x - GAP / 2, Y + 293), (x - GAP / 2, Y + 241), (x + 15, Y + 241)])

c.text(750, 60, "Each record names its run, its operation and target, its verdict and the "
       "clause that produced it,\nso the log answers both halves of attribution: which code "
       "acted, and which clause allowed it.", size=13, italic=True)

# --- what each link detects ----------------------------------------------------------------------
c.box(40, 500, 700, 210, fill="light", title="THE HASH CHAIN  (sha256)")
c.text(60, 615, "Anyone can verify it.\n\nDetects a record changed, deleted or reordered: every "
       "later\nhash stops matching.\n\nDoes not survive a complete rewrite of the file, "
       "because\nanyone can recompute every hash.", size=12, anchor="start")
c.box(760, 500, 700, 210, fill="light", title="THE MAC CHAIN  (HMAC-SHA256, key in the "
      "mediator's memory only)")
c.text(780, 615, "Verifiable only with the key, which is never written to disk.\n\nDetects a "
       "complete rewrite by someone who can write the file\nbut cannot read the mediator's "
       "memory.\n\nThe cost: a record from an earlier run of the mediator stays\nhash-"
       "verifiable and is no longer MAC-verifiable.", size=12, anchor="start")

c.text(750, 750, "Neither chain survives an attacker who controls the host; against one, the "
       "two give evidence and not protection.", size=12, italic=True)

c.save(OUT)
