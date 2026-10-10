# F57, no approval before a sandbox starts: predictions for the fix

**Written 2026-10-10, before the test is written and before any run.** F57
(`notes/verification_plan_20261005.md`): nothing requires an approval before a sandbox starts.
`describe --approve` records one, and `last_identity` reads it back, but only for the "changed since
you approved" banner. So a derived manifest is enforced without the confirmation §5.9.4 requires, an
author-declared one is used with no human look at all, and an update that widens its own
`permissions` block is granted the wider authority at its next start. **Younes decided on 2026-10-10
to gate both provenances**, and to fix it once his review of §9 was complete, which it now is. Commit
this note before the test runs; do not edit it after a run (`verify/prereg.py`). Results go to
`experiments/verify/results/f57/`.

## 1. The rule

A sandbox whose manifest is author-declared or derived is registered only if the most recent
approval on record for its domain matches **both** of these:

1. **The integration's current identity**, the composite hash of its source, its `manifest.json`
   and its declared requirements (`Identity.compute`, as `describe` computes it).
2. **The grant actually loaded**, a new digest over the provenance and the validated `permissions`
   dictionary (`grant_digest`). The identity alone is not enough: a derived manifest lives beside
   the integration, in `<domain>.permissions.json`, which `Identity.compute` does not hash, so
   widening a derived file changes no identity. The grant digest covers both provenances the same
   way.

An integration with no manifest at all (provenance *none*) is not gated: it receives nothing
mediated, so there is nothing to approve, and S6 already holds. Provenance still changes only what
the user is shown, never what the mediator does, as §5.9.4 requires: both provenances pass through
one check.

## 2. The change

- **`audit.py`.** `grant_digest(provenance, permissions)`; `AuditLog.approval` takes the digest
  and writes it into the approval record as `grant`; `last_approval(path, domain)` returns the most
  recent approval record, and `last_identity` is rebuilt on the same reader, unchanged in behaviour.
- **`manifest.py`.** `NotApproved`, a subclass of `ManifestRejected`, so that every caller that
  already stops on an unreadable manifest stops on an unapproved one; and
  `require_approval(manifest, component, approvals)`, which raises it with a reason a person can act
  on: no approval on record; the code, manifest or requirements changed since approval (naming which,
  through `Identity.changes_from`); or the permissions differ from the ones approved.
- **`platform.py`.** `ActingPolicy.bind`, which the mediator calls at every registration, calls
  `require_approval` after loading the manifest. The approvals file is the one `describe` writes,
  `<config-root>/confine/audit/decisions.jsonl` (`DEFAULT_LOG`), unless the policy is given another
  (`approvals=`).
- **`describe.py`.** `record_approval(component, path, manifest)`, the function behind `--approve`,
  now records the grant digest. The command line is unchanged.
- **`supervise.py`.** `--approvals PATH`, defaulting to `DEFAULT_LOG` under the original component's
  configuration root, because the supervisor runs a copy in a temporary directory whose own root
  holds no approvals. A refused registration is reported (`not started: …`) and the supervisor keeps
  running, as it already does for a cut-off integration, instead of crashing.
- **Harnesses.** Every suite and experiment that registers a component under the acting policy with
  a manifest records an approval first, through `record_approval`. In an experiment, the
  experimenter is the user who approves, and the code now says so at each site.

`policy_for`, the decision-only policy that several unit suites use, binds no manifest from disk and
is unchanged; the gate is on the path that the supervisor and every harness acting on (A) take.

**What this does not do.** The refusal is printed by the supervisor, not yet raised as a Repairs
issue in Home Assistant, so a household would not see why an updated integration stopped. Approvals
are read without verification, as `last_identity` already states, so someone who can write the
configuration directory can forge one; that is R4's bound, the machine's owner. Each `--approve`
opens its own log writer, so successive approvals in one file do not form one hash chain; the gate
does not depend on the chain.

## 3. The test, written first

A new suite, `selftest_approval`, built from a temporary configuration root, the real `Mediator`,
the real `ActingPolicy` and the stand-in `Platform`, with no sandbox. It approves the way a user
does, by running `python3 -m confine.describe <component> --approve`, so before the fix it uses only
what already exists. A registration counts as refused if it raises `ManifestRejected` whose message
mentions approval.

1. A derived manifest granting `sensor.outside` read, with no approval: **refused**.
2. After `describe --approve`: **registered**.
3. The derived file widened with `services.call: ["lock.unlock"]`: **refused**, naming permissions.
4. Approved again: **registered**.
5. The integration's code changed (`__init__.py` edited): **refused**, naming the source.
6. The derived file removed and the same grant written into `manifest.json` (author-declared), with
   no new approval: **refused**.
7. Approved: **registered**.
8. An update that widens its own `permissions` block in `manifest.json`: **refused**.
9. Another integration's approval does not admit this one: **refused**.
10. An integration with no manifest at all: **registered**, and an `entity.read` is denied (S6).

## 4. Predictions

**A1, the test before the fix** (the test commit, laptop and Pi): checks 1, 3, 5, 6, 8 and 9 fail,
because nothing refuses; checks 2, 4, 7 and 10 pass. Exit 1.

**A2, after the fix** (laptop and Pi): 10/10, exit 0.

**A3, every suite twice** at the tag, on the Pi with (A) up: all pass, now 28 with
`selftest_approval`. `selftest_t12` keeps its checks: its second version is approved before it
registers, because what it tests is that a new version does not inherit the old grant.

**A4, `nordpool` end to end** at the tag: 16/16, its harness approving first.

**A5, mutants** at the tag, every mutant whose file this change touches (`manifest.py`,
`platform.py`, `audit.py`, `supervise.py`), plus two new ones: **M39**, `require_approval` returns at
once, killed by `selftest_approval`; **M40**, the grant digest is not compared, killed by
`selftest_approval` (check 3). Every mutant killed before stays killed, and M25 stays equivalent.

**A6, F58's suites requirement.** A3 runs at a tag that contains F58's fix, so it also discharges
F58's R6.

## 5. After the runs

Ledger lines for both tags, Appendix F rows F57 and F58, §9.3's sentence on confirmation reworded to
the built behaviour, and F57/F58 closed in the findings table if A1–A5 hold.
