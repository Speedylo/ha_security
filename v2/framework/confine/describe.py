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

from .manifest import Manifest, ManifestRejected, Provenance

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


def describe(manifest: Manifest, *, name: str | None = None, version: str | None = None,
             code_changed: bool = False) -> str:
    """Render one manifest as plain text. Never raises: every state has a rendering."""
    title = name or manifest.domain
    lines = [title + (f"  {version}" if version else ""), "=" * max(len(title), 20), ""]

    if code_changed:
        # §5.12.5: the identity is machine-facing, its delta is user-facing. This is the
        # user-facing half of T12.
        lines += ["!! This integration's code has changed since you approved these",
                  "   permissions. What it is allowed to do has not changed.", ""]

    if manifest.provenance is Provenance.NONE:
        lines += [
            "This integration declares nothing.",
            "",
            "It will be run with no permissions at all. It can execute its own code, in its",
            "own folder, and nothing else: no network, no access to your devices, no access",
            "to any other integration's data, and no access to any file of yours.",
            "",
            "Nothing it asks for will be granted, because it has asked for nothing.",
        ]
        return "\n".join(lines)

    note = PROVENANCE_NOTE[manifest.provenance]
    if note:
        lines += [note, ""]

    allowed: list[str] = []
    denied: list[str] = []
    for (capability, member), granted_phrase, denied_phrase in CAPABILITIES:
        values = _values(manifest, capability, member)
        if values is None or values is False or values == []:
            denied.append(denied_phrase)
        elif values is True:
            allowed.append(granted_phrase)
        else:
            allowed.append(f"{granted_phrase}:")
            allowed += [f"    {value}" for value in values]

    lines.append("If you install this, it will be allowed to:")
    lines += [f"  - {entry}" if not entry.startswith("    ") else entry for entry in allowed] \
        or ["  - nothing at all"]
    lines += ["", "It will NOT be allowed to:"]
    lines += [f"  - {entry}" for entry in denied]

    resources = manifest.permissions.get("resources", {})
    if resources:
        limits = []
        if "memory_mb" in resources:
            limits.append(f"{resources['memory_mb']} MB of memory")
        if "max_processes" in resources:
            limits.append(f"{resources['max_processes']} processes")
        if "cpu_percent" in resources:
            limits.append(f"{resources['cpu_percent']}% of one processor")
        if limits:
            lines += ["", "It is limited to " + ", ".join(limits) + "."]
    return "\n".join(lines)


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


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Show what an integration is asking for.")
    ap.add_argument("component", type=Path, help="the integration's directory")
    ap.add_argument("--config-root", type=Path,
                    help="the Home Assistant configuration directory "
                         "(default: two levels above the integration)")
    ap.add_argument("--changed", action="store_true",
                    help="render as though the code has changed since approval (§5.12.5)")
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
    print(describe(manifest, name=metadata.get("name"), version=metadata.get("version"),
                   code_changed=args.changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
