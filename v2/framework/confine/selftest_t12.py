"""T12 — the declaration re-checked per version. The clause §4.10 asserts and nothing exercised.

§7.26.5 is the reason this file exists, and it is worth quoting because it names the gap
precisely rather than generally:

    "T12's control is asserted, not demonstrated, and this is the only threat in either
     register of which that is true."

§4.10 treats T12 — a malicious update delivered through the authorised update path to an
integration already installed and trusted — with two clauses. The **first** is structural and
needs no measurement: a sandbox confines whatever code is inside it, so an update inherits the
previous version's boundary rather than escaping it. The **second** — *declaration re-checked
per version* — is the one with content, and no section spawns the same integration twice across
a manifest change. This suite is that measurement.

Nothing here is new machinery. Every part was built for this and says so:

    audit.Identity      hashes the manifest *separately from the source*, and the docstring
                        gives the reason: "precisely so that a permission change is
                        distinguishable from a code change… bounds T12's treatment"
    Identity.changes_from   returns which of the three components moved, which is the whole
                        purchase of three hashes instead of one
    describe()          takes `code_changed`, commented in `describe.py` as "the user-facing
                        half of T12"
    AuditLog.run        one record per sandbox construction, carrying the full identity, so
                        which declaration bound which run is recoverable afterwards

What each case checks:

    §4.10 / T12   a manifest edit moves `manifest` and leaves `source` alone — the authority
                  change is distinguishable from a code change, which is what makes "re-checked"
                  a statement about the grant rather than about the file
    §4.10 / T12   the request v1 permitted is DENIED under v2, with a clause pointer into v2
    §4.10 / T12   a host v2 adds is GRANTED under v2 and was denied under v1 — the bound moved
                  in **both** directions. A test that only tightened could pass against a
                  framework that had simply stopped granting anything
    §5.12.5       describe() renders the v2 surface before the sandbox runs, so what changed is
                  visible *prior* to taking effect rather than only in the log afterwards
    §5.12.5       a source change under an unchanged manifest warns that the code moved and
                  says the permissions did not — the other half of T12, and the half that must
                  not overclaim
    §5.12.2       the durable log's two run records carry different `identity.manifest` and
                  identical `identity.source`, and both chains verify
    §7.29.3       the control: a manifest edit does **not** retroactively re-bind a policy
                  already built, and re-loading is what moves the decision. See below

**The control is the case worth reading, and it is this suite's §6.4.5 moment.** The failure mode
of a test like this is that it proves nothing: write the file, ask the same already-loaded
`Manifest` object, and of course the answer changes if the object re-reads — or of course it does
not if it does not. So both halves are asserted. A live policy keeps deciding v1's way after the
file changes, which is correct and is not a weakness: a manifest edit must not silently
re-authorise a sandbox that is already running. **The re-check happens because a spawn builds a
fresh policy from a fresh load**, and that is what the harnesses do — `Manifest.load` sits inside
the per-run setup of `compat.py`, `endtoend.py` and `endtoend_egress.py`, so no manifest survives
a run. Stating it as a property of *when the policy is built* rather than of *the file* is the
honest form, and §7.30 records the limitation it implies: a long-lived mediator has no re-check
trigger of its own, because nothing in this design keeps one alive across a respawn.

**Layer.** This is the decision layer and the identity layer, not a spawned sandbox — the same
scope §7.14 states for S3's subscription half. T12's second clause is a property of what binds a
run, and a real spawn would add namespace setup and a root requirement without touching the
claim. §7.30 says so rather than leaving a reader to infer the layer from the imports.

Run:  python3 -m confine.selftest_t12
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from .audit import AuditLog, Identity, last_identity
from .describe import describe
from .manifest import Manifest, policy_for

PASS, FAIL = "  ok  ", "  FAIL"
results: list[bool] = []

DOMAIN = "updater"

#: The host v1 declares and v2 drops. A grant that disappears is the malicious-update case run
#: backwards: whatever v2 asks for, it does not inherit v1's reach.
V1_HOST = "api.vendor.example:443"
#: The host v2 adds. Checked in both directions so that a framework which had merely stopped
#: granting anything could not pass this suite.
V2_HOST = "collector.elsewhere.example:8443"


def check(claim: str, condition: bool, detail: str = "") -> None:
    results.append(condition)
    print(f"{PASS if condition else FAIL}  {claim}{f'  — {detail}' if detail else ''}")


def permissions(hosts: list[str]) -> dict:
    """A minimal well-formed `permissions` block granting egress to exactly `hosts`."""
    return {"schema_version": 1, "network": {"egress": hosts}}


def write_manifest(component: Path, hosts: list[str], version: str) -> None:
    """The manifest as an author ships it — the grant lives in `permissions`, per §5.9.4."""
    component.mkdir(parents=True, exist_ok=True)
    (component / "manifest.json").write_text(json.dumps(
        {"domain": DOMAIN, "name": "Updater", "version": version,
         "requirements": ["vendor-sdk==1.0.0"],
         "permissions": permissions(hosts)}, indent=2))


def egress(host: str) -> dict:
    """One `network.egress` request. `host` and `port` are separate fields — §7.24.3."""
    name, _, port = host.rpartition(":")
    return {"op": "network.egress", "integration": DOMAIN, "host": name, "port": int(port)}


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        component = root / "custom_components" / DOMAIN
        audit_path = root / "audit" / "decisions.jsonl"

        # ---- v1: set up, and record what the first declaration permits --------------------
        write_manifest(component, [V1_HOST], version="1.0.0")
        (component / "__init__.py").write_text("async def async_setup_entry(hass, entry):\n"
                                               "    return True\n")

        v1_identity = Identity.compute(component)
        v1_manifest = Manifest.load(component, root)
        v1_policy = policy_for({DOMAIN: v1_manifest})

        log = AuditLog(path=audit_path)
        v1_run = log.run(v1_identity, provenance=v1_manifest.provenance.value)

        granted = v1_policy(DOMAIN, egress(V1_HOST))
        log.decision(v1_run, DOMAIN, egress(V1_HOST), granted.allowed,
                     granted.clause, granted.reason)
        check("v1 permits the host it declares", granted.allowed and granted.clause is not None,
              f"clause={granted.clause}")

        v1_on_v2_host = v1_policy(DOMAIN, egress(V2_HOST))
        check("and v1 denies the host it does not", not v1_on_v2_host.allowed,
              v1_on_v2_host.reason)

        # ---- the update: the manifest changes and the source does not ---------------------
        # The malicious-update shape stated exactly: the authority moves while the code stays
        # byte-identical, which is the case a single composite hash cannot tell from any other.
        write_manifest(component, [V2_HOST], version="1.1.0")
        v2_identity = Identity.compute(component)

        moved = v2_identity.changes_from(v1_identity)
        check("a manifest edit moves `manifest` and not `source`",
              moved == ["manifest"], f"changed={moved}")
        check("and the composite moves with it, so the run is a different run",
              v2_identity.composite != v1_identity.composite)

        # ---- the control: a live policy is not re-bound by a file it already read ---------
        # §7.29.3's lesson applied before the fact. If this assertion failed, every assertion
        # below it would be measuring a stale object re-reading the disk, not a re-check.
        stale = v1_policy(DOMAIN, egress(V2_HOST))
        check("the already-built policy still decides v1's way after the file changed",
              not stale.allowed,
              "a manifest edit must not re-authorise a running sandbox")
        stale_old = v1_policy(DOMAIN, egress(V1_HOST))
        check("and still grants what v1 granted, so nothing has silently re-read the file",
              stale_old.allowed)

        # ---- v2: the respawn re-loads, and the new declaration is what binds --------------
        v2_manifest = Manifest.load(component, root)
        v2_policy = policy_for({DOMAIN: v2_manifest})
        v2_run = log.run(v2_identity, provenance=v2_manifest.provenance.value)

        revoked = v2_policy(DOMAIN, egress(V1_HOST))
        log.decision(v2_run, DOMAIN, egress(V1_HOST), revoked.allowed,
                     revoked.clause, revoked.reason)
        check("the request v1 permitted is denied under v2", not revoked.allowed, revoked.reason)
        check("and the denial carries a clause pointer into the capability v2 declares",
              revoked.clause == "/permissions/network/egress", f"clause={revoked.clause}")

        added = v2_policy(DOMAIN, egress(V2_HOST))
        log.decision(v2_run, DOMAIN, egress(V2_HOST), added.allowed, added.clause, added.reason)
        check("and the host v2 adds is granted, so the bound moved in both directions",
              added.allowed and added.clause == "/permissions/network/egress/0",
              f"clause={added.clause}")

        # ---- §5.12.5: visible before it takes effect -------------------------------------
        # The log answers "what bound that run" afterwards. F4 asks for the other direction:
        # the surface a user is shown *before* granting it.
        surface = describe(v2_manifest, name="Updater", version="1.1.0")
        check("describe() renders the v2 surface before the sandbox runs",
              V2_HOST in surface and V1_HOST not in surface)
        check("and v1's surface named v1's host, so the rendering tracks the declaration",
              V1_HOST in describe(v1_manifest, name="Updater", version="1.0.0"))

        # ---- §5.12.5, the other half: code changed, permissions did not -------------------
        (component / "__init__.py").write_text("async def async_setup_entry(hass, entry):\n"
                                               "    exfiltrate()\n"
                                               "    return True\n")
        v3_identity = Identity.compute(component)
        check("a source edit under an unchanged manifest moves `source` alone",
              v3_identity.changes_from(v2_identity) == ["source"],
              f"changed={v3_identity.changes_from(v2_identity)}")

        warned = describe(Manifest.load(component, root), name="Updater", version="1.1.1",
                          code_changed=True)
        check("and describe() warns the code changed", "code has changed" in warned)
        check("while saying the permissions did not — the half that must not overclaim",
              "What it is allowed to do has not changed." in warned)

        # ---- what `manifest` does NOT say, found by mutating this suite -------------------
        # Running this file with v2 declaring v1's host — the update as a no-op — still passed
        # "the manifest hashes differ", because the hash is over the manifest's *bytes* and the
        # version string is one of them. So `Identity.manifest` says **the manifest changed**,
        # not **the grant changed**, and a cosmetic edit is indistinguishable from a
        # re-authorisation at the identity layer. §7.30 states it; it is asserted here so the
        # limitation is in the suite rather than only in prose, and so a future change that
        # narrowed the hash to the `permissions` block would fail this check and be noticed.
        write_manifest(component, [V2_HOST], version="1.1.2")   # version only; grant unchanged
        cosmetic = Identity.compute(component)
        v2_again = Manifest.load(component, root)
        check("a version bump alone still moves `manifest` — the hash is over bytes, not grants",
              "manifest" in cosmetic.changes_from(v3_identity),
              "so `manifest` moved does not imply the authority moved")
        check("while the grant it renders is unchanged, which is the half that matters",
              describe(v2_again, name="Updater") == describe(v2_manifest, name="Updater"))

        # ---- §7.30.6: the baseline, which is what makes the warning computable ------------
        # The cases above prove the comparison works when a caller holds both identities. In an
        # installation nobody holds the earlier one, so the question "has this changed since you
        # approved it" cannot be asked at all unless the approved identity was written down.
        # These cases are the ones that fail if the lookup is removed.
        check("with no approval on record there is no baseline, and none is invented",
              last_identity(audit_path, DOMAIN) is None)

        # Approve what is on disk at the moment of approval — which is `cosmetic`, after the
        # version bump above, not the `v2_identity` computed several edits ago. Getting this
        # wrong is what the first run of this suite did, and it reported a code change that had
        # not happened: proof that a baseline taken from the wrong moment is worse than none.
        approved_now = Identity.compute(component)
        log.approval(approved_now, v2_manifest.provenance.value)
        recovered = last_identity(audit_path, DOMAIN)
        check("an approval is recoverable from the log as an Identity",
              recovered is not None and recovered.composite == approved_now.composite)
        from_runs = last_identity(audit_path, DOMAIN, kind="run")
        check("and it is the approval that is read, not the run records beside it",
              from_runs is not None and from_runs.composite == v2_identity.composite
              and recovered is not None
              and recovered.composite == approved_now.composite)

        # The hostile update: new code, the manifest left alone. What a real caller has in hand
        # is `after` and nothing else; the baseline comes from the log or not at all.
        (component / "__init__.py").write_text("async def async_setup_entry(hass, entry):\n"
                                               "    exfiltrate()\n"
                                               "    phone_home()\n"
                                               "    return True\n")
        after = Identity.compute(component)
        # None-safe deliberately: if the lookup regresses to returning nothing — which is the
        # state this whole block exists to prevent — the suite must report a failure rather than
        # raise, because a traceback is a worse signal than a named check.
        baseline = last_identity(audit_path, DOMAIN)
        moved_since_approval = after.changes_from(baseline) if baseline else []
        check("a code change after approval is computable from the log alone",
              moved_since_approval == ["source"],
              f"changed={moved_since_approval}" if baseline else "no baseline was recoverable")

        warning = describe(Manifest.load(component, root), name="Updater",
                           code_changed="source" in moved_since_approval,
                           permissions_changed="manifest" in moved_since_approval)
        check("so the banner fires without anyone being told to set the flag",
              "code has changed" in warning)

        # §7.30.6's second half: one flag could not describe three states, and the state it got
        # wrong was the reassuring one.
        both = describe(v2_manifest, name="Updater", code_changed=True,
                        permissions_changed=True)
        check("when both moved, the banner does not claim the permissions held still",
              "AND what it is allowed to do has changed" in both
              and "has not changed" not in both)
        perms_only = describe(v2_manifest, name="Updater", permissions_changed=True)
        check("and a permissions-only change says so, rather than saying nothing",
              "allowed to do has changed" in perms_only
              and "Its code has not changed" in perms_only)

        # ---- §5.12.2: both runs recoverable from the durable log --------------------------
        records = [json.loads(line) for line in audit_path.read_text().splitlines()]
        runs = [r for r in records if r["kind"] == "run"]
        check("the durable log carries one run record per declaration", len(runs) == 2,
              f"runs={len(runs)}")
        check("whose manifest hashes differ, so the version change is attributable",
              runs[0]["identity"]["manifest"] != runs[1]["identity"]["manifest"])
        check("and whose source hashes are identical, so it is not read as a code change",
              runs[0]["identity"]["source"] == runs[1]["identity"]["source"])

        decisions = [r for r in records if r["kind"] == "decision"]
        under_v2 = [r for r in decisions if r["run"] == v2_run]
        check("each decision names the run that made it, so a decision maps to a declaration",
              len(under_v2) == 2 and {r["allowed"] for r in under_v2} == {True, False},
              f"under v2: {[(r['target'], r['allowed']) for r in under_v2]}")
        check("and the revoked host appears as a denial, not as an absence",
              any(r["target"] == V1_HOST and not r["allowed"] for r in under_v2))

        breaks = log.verify()
        check("both chains verify across the version change", breaks == [], f"breaks={breaks}")

    print()
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
