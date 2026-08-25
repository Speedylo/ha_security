"""F4's verification: render the declaration for each of the states an integration can be in.

§3.7 bounds what this can claim — availability of the information, not comprehension of it — so
what is checked here is that every state has a rendering, that the rendering names what is
*denied* as well as what is granted, and that it never shows what §5.12.5 said not to show.

Run:  python3 -m confine.selftest_describe
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from .describe import describe, describe_refusal
from .manifest import Manifest, ManifestRejected

WORKED_EXAMPLE = {
    "schema_version": 1,
    "network": {"egress": ["api.example-weather.invalid"]},
    "entities": {"read": ["sensor.outdoor_temperature"]},
    "resources": {"memory_mb": 192, "max_processes": 8},
}


def write(root: Path, domain: str, name: str, permissions: dict | None,
          broken: bool = False) -> Path:
    component = root / "custom_components" / domain
    component.mkdir(parents=True, exist_ok=True)
    if broken:
        (component / "manifest.json").write_text("{ not json")
        return component
    manifest = {"domain": domain, "name": name, "version": "1.4.2"}
    if permissions is not None:
        manifest["permissions"] = permissions
    (component / "manifest.json").write_text(json.dumps(manifest))
    return component


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="confine-describe-"))
    failures: list[str] = []
    try:
        # ---- 1. the §5.10.7 worked example ------------------------------------------
        component = write(root, "example_weather", "Example Weather", WORKED_EXAMPLE)
        manifest = Manifest.load(component, root)
        rendered = describe(manifest, name="Example Weather", version="1.4.2")
        print(rendered)
        print("\n" + "-" * 72 + "\n")

        checks = [
            ("names the one host it may contact",
             "api.example-weather.invalid" in rendered),
            ("names the one entity it may read",
             "sensor.outdoor_temperature" in rendered),
            ("says it cannot control anything", "control anything" in rendered),
            ("says it cannot see other integrations' passwords",
             "saved passwords" in rendered),
            ("says who declared it", "declared by whoever wrote" in rendered),
            ("shows the resource limits", "192 MB of memory" in rendered),
            # §5.12.5: no for the digest. A hex string helps nobody F4 exists to serve.
            ("shows no content hash", "sha256" not in rendered.lower()),
            # §5.10.7's point: the denials are most of what enforcement does.
            ("lists more denials than grants",
             rendered.count("\n  - ") >= 8),
        ]

        # ---- 2. an integration that declares nothing --------------------------------
        component = write(root, "demo_silent", "Silent Demo", None)
        silent = describe(Manifest.load(component, root), name="Silent Demo")
        print(silent)
        print("\n" + "-" * 72 + "\n")
        checks.append(("an undeclared integration renders as no permissions at all",
                       "no permissions at all" in silent))

        # ---- 3. a declaration that could not be read --------------------------------
        component = write(root, "demo_broken", "Broken Demo", None, broken=True)
        try:
            Manifest.load(component, root)
            refusal = ""
        except ManifestRejected as err:
            refusal = describe_refusal(err, "Broken Demo")
        print(refusal)
        print("\n" + "-" * 72 + "\n")
        checks.append(("an unreadable declaration says so, and says why",
                       "could not be read" in refusal and "not valid JSON" in refusal))

        # ---- 4. the code has changed since approval (§5.12.5) -----------------------
        component = write(root, "example_weather", "Example Weather", WORKED_EXAMPLE)
        changed = describe(Manifest.load(component, root), name="Example Weather",
                           code_changed=True)
        checks.append(("a changed integration says the code changed",
                       "code has changed" in changed))
        checks.append(("...and says the permissions did not",
                       "has not changed" in changed))

        # ---- 5. a derived manifest is marked as derived ------------------------------
        derived_dir = root / "custom_components"
        (derived_dir / "demo_derived.permissions.json").write_text(json.dumps(WORKED_EXAMPLE))
        component = write(root, "demo_derived", "Derived Demo", None)
        derived = describe(Manifest.load(component, root), name="Derived Demo")
        checks.append(("a derived manifest says it was not the author's",
                       "not declared by the author" in derived))
        checks.append(("...and asks the user to check it", "Check them" in derived))

        print("F4 — the declaration is presentable before installation\n")
        for label, ok in checks:
            print(f"  {'ok  ' if ok else 'FAIL'}  {label}")
            if not ok:
                failures.append(label)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print()
    if failures:
        print(f"FAILED: {'; '.join(failures)}")
        return 1
    print("PASS — every state an integration can be in has a rendering, the denials are")
    print("       shown at the same weight as the grants, and no digest is presented.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
