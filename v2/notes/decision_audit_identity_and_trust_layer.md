# Decision — audit identity, and the trust layer that is not being built

**Decided:** 2026-08-22 · Not part of the report. · **Affects:** Ch. 5 (log record
specification), Ch. 6 (implementation), the future-work chapter.

## The decision, plainly

**In scope now:** the audit record identifies *which code ran*, not only which integration
— an integration's identity in the log is its name plus a content hash of the source that
was loaded.

**Not in scope now:** anything shaped like an attestation — per-run clean/violation
verdicts as first-class objects, node keys, signatures, an export or wire format, gossip,
relays, trust scoring.

**Deferred, not refused:** a decentralised web-of-trust layer over those records. Revisited
in October at G3, or written up as future work. The point of the decision is that both
remain available.

## Where the idea comes from, and why it was dropped once already

`option_C_home_assistant_sandbox.md` (12 Aug, pre-spike) carried it as *Optional Phase 5 —
Decentralized trust layer*, explicitly "beyond week 12": signed attestations tied to code
hashes, gossip propagation over Nostr-style relays, locally-computed trust scores on the
PGP web-of-trust model, with trust bound to a content hash so a new release starts unproven.

It was dropped in the review recorded at `PROJECT_STATUS.md:150` — "a second capstone" that
"invites Sybil-resistance questions that cannot be won" — and replaced with a local
hash-chained audit log. `spike/supervisor.py:110-112` records the exclusion in the code.

**Evidence-rule note:** all of the above is first-pass material and therefore private
knowledge (`00_METHOD.md` §2). It informs this decision; it is not citable in a chapter.
The report reaches the same place through Ch. 4's own R4, which is where the argument has
to stand.

## The test applied

**Would this record exist if the trust layer had never been imagined?**

| Item | Verdict | Why |
|---|---|---|
| Content hash of the loaded code | **In** | Passes. Required by attribution on its own terms — see below |
| Per-run clean/violation verdict | **Out** | Fails. Derivable later from decisions already logged; building it now buys nothing |
| Signatures, node keys, export format | **Out** | Fails outright. This *is* the second capstone, under another name |

The line to hold: **log content is justified by attribution; log distribution is out of
scope.** The moment Ch. 5 specifies a format for something off-box to consume, the boundary
has been crossed.

## Why the hash stands on its own

Not a new requirement. **S7** already requires decisions be recorded "with the integration's
identity", and Ch. 5 is entitled to say what identity means. Defining it as
*name + content hash of the loaded source* is a design specification discharging S7.

Two things justify it, both already in the report:

- **T12** — a malicious update arrives through the authorised update path, treated as
  "confinement applies to whatever version runs; declaration re-checked per version". A log
  that names the integration but not the release cannot say which version misbehaved.
- **A7** — the audit record is a meta-asset whose integrity "determines whether any other
  loss is attributable". Attributable *to what* is the open half of that sentence.

Consequence: no new row in the §3.8 traceability matrix, no S10, no traceability debt.

## Why the PoC is refused for now

Recorded because a viva probes rejected alternatives, and because refusing it once is
cheaper than refusing it three times.

1. **Sybil resistance cannot be won at this scale.** "N independent nodes ran this hash
   clean" is precisely the claim an attacker manufactures cheaply. A three-node simulated
   demo does not answer the objection; it stages it. The advisor audits for a living.
2. **It cuts against the project's own framing.** §1.6 separates likelihood controls
   (community review) from impact controls (confinement) and claims the second half.
   §3.7 declines to classify intent. A behaviour-scoring trust layer is a *likelihood*
   control; adding it blurs the sentence that makes the contribution legible.
3. **The schedule has already decided this implicitly.** G3 cuts the actuator PoC first if
   October slips. A trust-layer PoC queues behind that, i.e. would be cut before starting.
4. **Ch. 7's performance axis still has no data**, and `01_PLAN.md` calls that a hole.

## What the future-work chapter gets in exchange

With hashes in the log, future work stops being "one could imagine a web of trust" — which
any reviewer could write without us — and becomes: *the artifact already emits the record
such a layer would consume; here is its schema; here is the specific unsolved problem
(Sybil resistance) that makes it a separate project.*

Also worth one paragraph there: grounding trust in **objective sandbox-observed behaviour**
rather than subjective vouching is a real departure from the PGP model, and it is the part
of the idea worth preserving. Attachment point in the report is **Ch. 4 §4.11 R4** —
"external anchoring is a different project" — which was written to leave exactly this door
open without promising anything.

## Weaknesses to concede if pressed

- **The hash records what was *loaded*, not what *executed*.** An integration that fetches
  or generates code at runtime defeats it. This is a genuine limit on T12's treatment as
  well as on any future attestation, and should be stated rather than discovered.
- **Hash granularity is unsettled** (below). Whatever is chosen, a hash that changes on
  every trivial edit and a hash that misses a meaningful change are different failure modes.
- **This decision anticipates a use.** The honest position is that the hash is justified by
  T12/A7 alone and would be added regardless — but the reason it is being added *today*,
  rather than in Ch. 6, is that it preserves an option. Both statements are true; say both.

## Open questions for Ch. 5

1. **What exactly is hashed** — the integration's source tree, its manifest, its declared
   dependencies, or the tuple? Dependencies are where supply-chain change actually lands.
2. **When** — at load time, once per run, or on every mediated decision (the last is
   redundant; the record can carry a run identifier instead).
3. **Whether the hash appears in the user-facing view of F4**, or only in the log.

## The re-decision point

October, at G3, or earlier if the artifact is ahead. The asymmetry is the reason this note
exists: deciding *with* hashes in the log costs nothing; deciding *without* them means
retrofitting the log, re-running the compatibility evaluation, and touching Ch. 5, 6 and 7.
