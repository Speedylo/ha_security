"""F57: a sandbox starts only under permissions a person has approved, whoever wrote them.

§5.9.4 says a derived manifest "requires explicit user confirmation", and §5.9.6 says a new version
"does not inherit the previous version's grants". Until F57 (2026-10-10) neither was enforced at
the point that matters, registration: `describe --approve` wrote an approval and nothing read it
except the "changed since you approved" banner. Younes decided to gate **both** provenances, because
the author of an author-declared manifest is the party the threat model constrains.

The rule this suite holds the framework to (`notes/f57_approval_gate_prediction.md` §1): a sandbox
with an author-declared or derived manifest registers only if the most recent approval for its
domain matches its current identity **and** the grant actually loaded. An integration with no
manifest is not gated, because it receives nothing to approve.

Approvals are given the way a user gives them, by running `describe --approve`, so the suite needs
nothing that did not exist before the fix. No sandbox is started: what is tested is the mediator's
registration, which is where a manifest is bound to a channel.

Run:  python3 -m confine.selftest_approval
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .audit import DEFAULT_LOG, Identity, grant_digest, last_record
from .channel import Channel
from .manifest import Manifest, ManifestRejected
from .mediator import Mediator
from .platform import ActingPolicy, Platform

PASS, FAIL = "  ok  ", "  FAIL"
results: list[bool] = []
FRAMEWORK = Path(__file__).resolve().parent.parent

DOMAIN = "demo_approval"
READ = {"schema_version": 1, "entities": {"read": ["sensor.outside"]}}
WIDER = {**READ, "services": {"call": ["lock.unlock"]}}


def check(claim: str, condition: bool, detail: str = "") -> None:
    results.append(condition)
    print(f"{PASS if condition else FAIL}  {claim}{f'  — {detail}' if detail else ''}")


def component(root: Path, domain: str, permissions: dict | None = None) -> Path:
    """An integration directory; `permissions`, if given, goes into its own manifest.json."""
    directory = root / "custom_components" / domain
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {"domain": domain, "name": domain, "version": "1.0.0", "requirements": []}
    if permissions is not None:
        manifest["permissions"] = permissions
    (directory / "manifest.json").write_text(json.dumps(manifest))
    (directory / "__init__.py").write_text("async def async_setup(hass, config):\n    return True\n")
    return directory


def derive(directory: Path, permissions: dict | None) -> None:
    """Write, or with None remove, the derived manifest beside the integration (§5.9.4 rank 2)."""
    path = directory.parent / f"{directory.name}.permissions.json"
    if permissions is None:
        path.unlink(missing_ok=True)
    else:
        path.write_text(json.dumps(permissions))


def approve(directory: Path) -> None:
    """What a user does: read the rendering, then accept it."""
    subprocess.run([sys.executable, "-m", "confine.describe", str(directory), "--approve"],
                   cwd=FRAMEWORK, check=True, capture_output=True)


def register(mediator: Mediator, directory: Path) -> str | None:
    """None if registered, or why it was refused. The channel is closed again either way."""
    ours, theirs = Channel.pair()
    try:
        mediator.register(directory.name, Channel(ours), component=directory)
    except ManifestRejected as err:
        ours.close()
        theirs.close()
        return str(err)
    mediator.unregister(ours.fileno())
    theirs.close()
    return None


def refused(reason: str | None, *words: str) -> bool:
    """Refused for want of an approval, and, if `words` are given, saying why in those words."""
    return (reason is not None and "approv" in reason.lower()
            and all(w in reason.lower() for w in words))


def shown_steps(root: Path, mediator: Mediator, demo: Path) -> None:
    """Checks 11–14 (`notes/f57c_not_started_issue_prediction.md` §3).

    The screen carries the identity and the grant digest it was rendered from, and Allow sends
    them back. `approve_shown` records an approval only if both still describe what is on disk,
    so a screen read before the code or the permissions moved approves nothing.
    """
    try:
        from .describe import approve_shown
    except ImportError as err:
        check("11–13. `approve_shown` exists", False, str(err))
        return
    approvals = root / DEFAULT_LOG
    by = "an administrator, from the Repairs panel"

    def shown() -> tuple[str, str]:
        manifest = Manifest.load(demo, root)
        return (Identity.compute(demo).composite,
                grant_digest(manifest.provenance.value, manifest.permissions))

    def allow(identity: str, grant: str) -> str | None:
        """None if recorded, or why not."""
        try:
            approve_shown(demo, approvals, Manifest.load(demo, root), identity, grant, by)
        except ManifestRejected as err:
            return str(err)
        return None

    def approvals_on_record() -> int:
        return sum(1 for line in approvals.read_text().splitlines() if '"approval"' in line)

    # Check 8 left an author-declared update that widened itself, refused.
    reason = allow(*shown())
    record = last_record(approvals, DOMAIN) or {}
    registered = register(mediator, demo)
    check("11. Allow with the screen's identity and grant records an approval, with who gave it, "
          "and it then registers", reason is None and record.get("by") == by and registered is None,
          str(reason or registered or record.get("by")))

    component(root, DOMAIN)                 # back to a derived grant, approved as shown
    derive(demo, READ)
    allow(*shown())
    screen = shown()
    derive(demo, WIDER)                     # widened after the screen was read
    before = approvals_on_record()
    reason = allow(*screen)
    check("12. a screen read before the permissions were widened approves nothing",
          reason is not None and approvals_on_record() == before
          and refused(register(mediator, demo), "permission"), str(reason))

    derive(demo, READ)
    allow(*shown())
    screen = shown()
    (demo / "__init__.py").write_text("async def async_setup(hass, config):\n"
                                      "    return True  # 1.0.2\n")
    before = approvals_on_record()
    reason = allow(*screen)
    check("13. a screen read before the code changed approves nothing",
          reason is not None and approvals_on_record() == before
          and refused(register(mediator, demo), "source"), str(reason))

    decision = mediator.policy(DOMAIN, {"op": "approve", "integration": DOMAIN})
    check("14. a sandbox cannot approve itself: `approve` is no operation, denied (S6)",
          not decision.allowed, decision.reason)


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="selftest-approval-"))
    try:
        mediator = Mediator(policy=ActingPolicy({}, Platform()))
        demo = component(root, DOMAIN)

        print("A derived manifest, written beside the integration:")
        derive(demo, READ)
        reason = register(mediator, demo)
        check("1. with no approval on record, it is refused", refused(reason), str(reason))
        approve(demo)
        reason = register(mediator, demo)
        check("2. after `describe --approve`, it registers", reason is None, str(reason))
        derive(demo, WIDER)
        reason = register(mediator, demo)
        check("3. widened to lock.unlock, it is refused, and the reason names the permissions",
              refused(reason, "permission"), str(reason))
        approve(demo)
        reason = register(mediator, demo)
        check("4. approved again, it registers", reason is None, str(reason))
        (demo / "__init__.py").write_text("async def async_setup(hass, config):\n"
                                          "    return True  # 1.0.1\n")
        reason = register(mediator, demo)
        check("5. its code changed, it is refused, and the reason names the source",
              refused(reason, "source"), str(reason))

        print("\nThe same grant, declared by the author in manifest.json:")
        derive(demo, None)
        component(root, DOMAIN, READ)
        reason = register(mediator, demo)
        check("6. with no approval of this exact declaration, it is refused",
              refused(reason), str(reason))
        approve(demo)
        reason = register(mediator, demo)
        check("7. after `describe --approve`, it registers", reason is None, str(reason))
        component(root, DOMAIN, WIDER)
        reason = register(mediator, demo)
        check("8. an update that widens its own permissions block is refused",
              refused(reason), str(reason))

        print("\nWhat an approval is not:")
        other = component(root, "demo_other")
        derive(other, READ)
        reason = register(mediator, other)
        check("9. another integration's approval does not admit this one",
              refused(reason), str(reason))
        bare = component(root, "demo_bare")
        reason = register(mediator, bare)
        decision = mediator.policy("demo_bare", {"op": "entity.read", "entity": "sensor.outside"})
        check("10. with no manifest at all it registers ungated, and is granted nothing (S6)",
              reason is None and not decision.allowed, str(reason or decision.reason))

        print("\nAllowed from the Repairs panel (F57c): an approval of exactly what was shown:")
        shown_steps(root, mediator, demo)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if results and all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
