"""Rendering a declaration for the person deciding whether to install the integration.

F4: "the declared authority shall be presentable to the user before installation", derived from
§1.8 — the user "cannot see what an integration intends to access before installing it".
§5.14.4's traceability check found this half of T13's control specified but placed nowhere, and
recorded it as owed by Chapter 6. This is it.

**What this deliberately does not do, and why.** §3.7 excludes user *comprehension* as a
human-factors question with its own literature, and F4 is explicit that it "concerns
availability of the information, not user comprehension". So this renders; it does not persuade.
Three things were considered and left out, each because it would claim more than the project can
support:

  - **Risk labels** — marking `lock.unlock` as dangerous and `sensor.read` as harmless. An
    unvalidated risk ranking presented as authoritative is a claim about how users decide, which
    is exactly what §3.7 declines to make.
  - **The content hash** — §5.12.5 settled this: no for the digest, yes for the change. A hex
    string means nothing to the reader F4 exists to serve, and showing one would be security
    theatre in the literal sense. A *change* in it is a sentence a non-programmer can act on.
  - **Consent flow** — buttons, prompts, a wizard. §3.7 puts it out of scope, and a surface is
    what is owed rather than an interaction.

**The negative list is the part that matters.** §5.10.7 observes that in its worked example nine
of the ten capabilities are denied by their absence — the manifest never mentions them. A
rendering that shows only grants shows the small half of what enforcement does, so what an
integration *cannot* do is printed at the same weight as what it can.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .audit import DEFAULT_LOG, AuditLog, Identity, grant_digest, last_identity, last_record
from .manifest import Manifest, ManifestRejected, NotApproved, Provenance

# One row per declarable capability of §5.10.3. `granted` is completed with the declared
# values; `denied` stands alone, because absence has no values to list.
CAPABILITIES: list[tuple[tuple[str, str], str, str]] = [
    (("services", "call"), "ask other integrations to do specific things",
     "control anything — it cannot ask any other integration to do anything"),
    (("entities", "write"), "change the state of",
     "change the state of any of your devices"),
    (("entities", "read"), "read the state of",
     "read the state of any of your devices"),
    (("entities", "subscribe"), "be told when these change",
     "be told when anything in your home changes"),
    (("network", "egress"), "contact these addresses on the internet",
     "contact anything on the internet"),
    # §7.24's three additions, and the ordering is the design (`decision_network_capability.md`
    # §6). The four network sentences are deliberately of different loudness — watching is
    # quieter than searching, and searching is the one that touches every machine in the house.
    # A non-expert can rank them without knowing what a port is, which is what F4 asks for and
    # what a single `network` permission could not deliver.
    (("network", "local"), "contact the device you set up, and nothing else on your network",
     "contact anything on your home network"),
    (("network", "discover"), "look for its own devices on your home network",
     "look for devices on your home network"),
    (("files", "read"), "read these files",
     "read any file outside its own folder"),
    (("files", "write"), "write to these files",
     "change any file outside its own folder"),
    (("events", "fire"), "announce these events",
     "announce anything to the rest of Home Assistant"),
    (("events", "subscribe"), "listen for these events",
     "listen to what other parts of Home Assistant are doing"),
    (("config_entries", "read_all"), "see every integration's settings and saved passwords",
     "see any other integration's settings or saved passwords"),
    (("http", "register"), "add these web addresses to Home Assistant",
     "add anything to Home Assistant's web interface"),
]

PROVENANCE_NOTE = {
    Provenance.AUTHOR:
        "These permissions were declared by whoever wrote this integration.",
    Provenance.DERIVED:
        "These permissions were worked out for you, not declared by the author.\n"
        "Check them before continuing.",
    Provenance.NONE: "",
}


def _values(manifest: Manifest, capability: str, member: str) -> list[str] | bool | None:
    return manifest.permissions.get(capability, {}).get(member)


def _banner(code_changed: bool, permissions_changed: bool) -> list[str]:
    """The changed-since-approval warning, as lines; empty when nothing changed."""
    lines: list[str] = []
    # §5.12.5: the identity is machine-facing, its delta is user-facing. This is the
    # user-facing half of T12, and the three cases are kept apart because the original single
    # message asserted "what it is allowed to do has not changed" — which is a statement about
    # the manifest, made by a flag that only ever meant the source had moved. With both
    # components able to move independently (§7.30.3), one message could not be true of all
    # three states, and the one that was wrong would be wrong in the reassuring direction.
    if code_changed and permissions_changed:
        lines += ["!! This integration's code has changed since you approved these",
                  "   permissions, AND what it is allowed to do has changed. Read the",
                  "   list below before accepting it.", ""]
    elif code_changed:
        lines += ["!! This integration's code has changed since you approved these",
                  "   permissions. What it is allowed to do has not changed.", ""]
    elif permissions_changed:
        lines += ["!! What this integration is allowed to do has changed since you",
                  "   approved it. Its code has not changed. Read the list below.", ""]
    return lines


NOTHING_DECLARED = [
    "This integration declares nothing.",
    "",
    "It will be run with no permissions at all. It can execute its own code, in its",
    "own folder, and nothing else: no network, no access to your devices, no access",
    "to any other integration's data, and no access to any file of yours.",
    "",
    "Nothing it asks for will be granted, because it has asked for nothing.",
]
ALLOWED_HEADING = "If you install this, it will be allowed to:"
DENIED_HEADING = "It will NOT be allowed to:"


def _grants(manifest: Manifest) -> tuple[list[tuple[str, list[str]]], list[str]]:
    """What it may do, each phrase with its values, and what it may not, in `CAPABILITIES` order."""
    allowed: list[tuple[str, list[str]]] = []
    denied: list[str] = []
    for (capability, member), granted_phrase, denied_phrase in CAPABILITIES:
        values = _values(manifest, capability, member)
        if values is None or values is False or values == []:
            denied.append(denied_phrase)
        elif values is True:
            allowed.append((granted_phrase, []))
        else:
            allowed.append((f"{granted_phrase}:", [str(value) for value in values]))
    return allowed, denied


def _limits(manifest: Manifest) -> str | None:
    """The resource sentence, or None when nothing is declared."""
    # The figures that will be applied, not the ones asked for: a declaration above the
    # framework's default gets the default (§7.22.3, verification 4.7 finding F32).
    declared = manifest.permissions.get("resources", {})
    resources = {member: getattr(manifest.resources, member) for member in declared}
    limits = []
    if "memory_mb" in resources:
        limits.append(f"{resources['memory_mb']} MB of memory")
    if "max_processes" in resources:
        limits.append(f"{resources['max_processes']} processes")
    if "cpu_percent" in resources:
        limits.append(f"{resources['cpu_percent']}% of one processor")
    if "disk_mb" in resources:
        limits.append(f"{resources['disk_mb']} MB of temporary disk space")
    return "It is limited to " + ", ".join(limits) + "." if limits else None


def describe(manifest: Manifest, *, name: str | None = None, version: str | None = None,
             code_changed: bool = False, permissions_changed: bool = False) -> str:
    """Render one manifest as plain text. Never raises: every state has a rendering."""
    title = name or manifest.domain
    lines = [title + (f"  {version}" if version else ""), "=" * max(len(title), 20), ""]
    lines += _banner(code_changed, permissions_changed)

    if manifest.provenance is Provenance.NONE:
        return "\n".join(lines + NOTHING_DECLARED)

    note = PROVENANCE_NOTE[manifest.provenance]
    if note:
        lines += [note, ""]

    allowed, denied = _grants(manifest)
    lines.append(ALLOWED_HEADING)
    for phrase, values in allowed:
        lines.append(f"  - {phrase}")
        lines += [f"    {value}" for value in values]
    if not allowed:
        lines.append("  - nothing at all")
    lines += ["", DENIED_HEADING]
    lines += [f"  - {entry}" for entry in denied]

    limits = _limits(manifest)
    if limits:
        lines += ["", limits]
    return "\n".join(lines)


def _md(text: str) -> str:
    """A value from the manifest, safe to place in Markdown: one line, no markup of its own.

    Entity ids, hosts and paths are the author's strings. Escaped, a value cannot start a new
    line, a heading or a link on the screen an administrator reads before allowing (F57c §1).
    """
    flat = " ".join(text.split())
    return "".join(f"\\{c}" if c in "\\`*_{}[]()<>#+-.!|~" else c for c in flat)


def describe_markdown(manifest: Manifest, *, code_changed: bool = False,
                      permissions_changed: bool = False) -> str:
    """`describe`, for the Repairs screen (F57c): the same sentences, as Markdown.

    No title, because the screen has its own; the banner joined into one paragraph, because the
    terminal's line breaks mean nothing in a window; every value from the manifest escaped.
    """
    parts: list[str] = []
    banner = " ".join(line.strip(" !") for line in _banner(code_changed, permissions_changed)
                      if line.strip())
    if banner:
        parts.append(f"**{banner}**")
    if manifest.provenance is Provenance.NONE:
        paragraphs = "\n".join(NOTHING_DECLARED).split("\n\n")
        return "\n\n".join(parts + [" ".join(p.split()) for p in paragraphs])
    note = PROVENANCE_NOTE[manifest.provenance]
    if note:
        parts.append(" ".join(note.split()))
    allowed, denied = _grants(manifest)
    items = []
    for phrase, values in allowed:
        items.append(f"- {phrase}" + "".join(f"\n  - {_md(value)}" for value in values))
    parts.append(ALLOWED_HEADING + "\n\n" + ("\n".join(items) or "- nothing at all"))
    parts.append(DENIED_HEADING + "\n\n" + "\n".join(f"- {entry}" for entry in denied))
    limits = _limits(manifest)
    if limits:
        parts.append(limits)
    return "\n\n".join(parts)


def changes_since_approval(component: Path, manifest: Manifest,
                           approvals: Path) -> tuple[bool, bool, bool]:
    """(approved before, code changed, permissions changed), against the last approval.

    The permissions count as changed when the identity's manifest or requirements moved, as
    `main` says, **or when the grant digest differs**: a derived grant lives in a file the
    identity does not hash, so only the digest sees it widen (F57).
    """
    record = last_record(approvals, component.name)
    if record is None:
        return False, False, False
    try:
        moved = Identity.compute(component).changes_from(Identity(**record["identity"]))
    except TypeError:
        return True, True, True
    grant = grant_digest(manifest.provenance.value, manifest.permissions)
    return (True, "source" in moved,
            "manifest" in moved or "requirements" in moved or record.get("grant") != grant)


def describe_refusal(error: ManifestRejected, domain: str) -> str:
    """A declaration that could not be read is still something the user must be shown.

    Rendering nothing here would reproduce §1.8's complaint exactly: the user is left unable to
    see what the integration intends, and this time the framework knows and did not say.
    """
    return "\n".join([
        domain,
        "=" * max(len(domain), 20),
        "",
        "This integration's declaration could not be read, so it will be given no",
        "permissions at all. It can execute its own code and nothing else.",
        "",
        "What was wrong with it:",
        f"  {error}",
    ])


def record_approval(component: Path, path: Path, manifest: Manifest,
                    by: str | None = None) -> Identity:
    """Record that a person was shown this integration's grant and accepted it (§5.9.6, F57).

    Behind `--approve`. Harnesses call it too, because in an experiment the experimenter is the
    user who approves, and since F57 the mediator registers nothing that no one approved. The
    record carries the identity and, separately, the grant (`grant_digest`), because the
    identity does not cover a derived manifest's file.
    """
    current = Identity.compute(component)
    AuditLog(path=path).approval(current, manifest.provenance.value,
                                 grant_digest(manifest.provenance.value, manifest.permissions),
                                 by=by)
    return current


def approve_shown(component: Path, path: Path, manifest: Manifest, shown_identity: str,
                  shown_grant: str, by: str) -> Identity:
    """Record an approval of what a screen showed, only if it is still what is on disk (F57c).

    The Repairs screen is rendered from one identity and one grant and carries both; Allow
    sends them back. Between the two, the integration may have been updated or its derived grant
    rewritten, and an approval of the new state by someone who read the old one is not an
    approval. So both are recomputed here, and a difference records nothing and raises.
    """
    current = Identity.compute(component)
    if current.composite != shown_identity:
        raise NotApproved(f"{component.name}: its code changed after its permissions were shown; "
                          "nothing was approved")
    if grant_digest(manifest.provenance.value, manifest.permissions) != shown_grant:
        raise NotApproved(f"{component.name}: its permissions changed after they were shown; "
                          "nothing was approved")
    return record_approval(component, path, manifest, by=by)


def approve_as_experimenter(component: Path, config_root: Path | None = None) -> None:
    """`record_approval` for a harness: the experimenter is the user, and approves what is on disk.

    Called just before a harness registers a component, so the approval matches exactly the
    code and grant the mediator is about to load (F57). Written where `describe` and the
    mediator's policy both look by default, `<config-root>/` + `DEFAULT_LOG`.
    """
    root = config_root or component.parent.parent
    record_approval(component, root / DEFAULT_LOG, Manifest.load(component, root))


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Show what an integration is asking for.")
    ap.add_argument("component", type=Path, help="the integration's directory")
    ap.add_argument("--config-root", type=Path,
                    help="the Home Assistant configuration directory "
                         "(default: two levels above the integration)")
    ap.add_argument("--audit", type=Path,
                    help=f"the mediator's log, for the identity last approved "
                         f"(default: <config-root>/{DEFAULT_LOG})")
    ap.add_argument("--approve", action="store_true",
                    help="record that this exact identity was shown and accepted (§5.9.6)")
    ap.add_argument("--changed", action="store_true",
                    help="force the changed-since-approval banner, whatever the log says. "
                         "A rendering override for inspecting the output, not a measurement")
    args = ap.parse_args()

    component = args.component.resolve()
    config_root = (args.config_root or component.parent.parent).resolve()
    try:
        manifest = Manifest.load(component, config_root)
    except ManifestRejected as err:
        print(describe_refusal(err, component.name))
        return 1

    import json
    metadata = {}
    own = component / "manifest.json"
    if own.is_file():
        try:
            metadata = json.loads(own.read_text())
        except ValueError:
            metadata = {}
    # The identity of what is on disk now, against the identity the user last accepted.
    #
    # **This lookup is the fix §7.30.6 records.** `code_changed` was a parameter nobody
    # computed: it was set by two self-tests and by `--changed`, a flag a human toggles, so the
    # user-facing half of T12 could not fire in a real installation however correct the
    # rendering was. Both halves of the comparison have to exist, and only one of them can be
    # computed from the directory — the other has to have been written down.
    audit_path = args.audit or (config_root / DEFAULT_LOG)
    current = Identity.compute(component)
    approved = last_identity(audit_path, component.name)
    moved = current.changes_from(approved) if approved is not None else []

    print(describe(manifest, name=metadata.get("name"), version=metadata.get("version"),
                   code_changed=args.changed or "source" in moved,
                   permissions_changed="manifest" in moved or "requirements" in moved))

    if approved is None and not args.approve:
        # Said out loud rather than rendered as "nothing has changed". A first install and an
        # update whose baseline was never recorded look identical to this code, and reporting
        # the second as the first is the §6.4.5 shape: an absence that reads like a clean result.
        print()
        print("(No approval is on record for this integration, so nothing above is a "
              "comparison.\n Run again with --approve once you have read it.)")

    if args.approve:
        record_approval(component, audit_path, manifest)
        print()
        print(f"Recorded. {component.name} is approved at {current.composite[:12]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
