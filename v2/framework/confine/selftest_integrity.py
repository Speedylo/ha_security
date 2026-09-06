"""The C1 count, checked against trees whose answer is known in advance.

§7.28 downgraded C1 from *counted* to *argued* because the count §7.4.1 described did not
exist. A count that is wrong would be worse than the argument it replaces, so every case here
is a tree modified in a specific way with a specific expected verdict:

    §7.5 / C1     an untouched tree reports zero changed source files and zero diff lines
    §7.5 / C1     a one-line edit is caught, and counted in the **lines** the criterion asks for
    §7.5 / C1     a deleted source file and an added source file are both caught
    §5.12.1       a manifest edit is caught and attributed to `manifest`, not to `source` —
                  which is the property `Identity`'s three parts exist to give
    §5.12.1       a `requirements` edit moves two components, because the manifest contains it
    §7.28         a `__pycache__` tree is **not** a source change and is still reported, so a
                  run that wrote bytecode cannot be reported as one that touched nothing

The fifth is the one worth reading. The baseline arm imports each integration from a tree it
can write to, so bytecode caches are the expected outcome of a clean run — and if this module
counted them as modifications, C1 would fail everywhere for a reason that has nothing to do
with the integration's source.

Run:  python3 -m confine.selftest_integrity
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from .integrity import TreeState, compare, summarise

PASS, FAIL = "  ok  ", "  FAIL"
results: list[bool] = []


def check(claim: str, condition: bool, detail: str = "") -> None:
    results.append(condition)
    print(f"{PASS if condition else FAIL}  {claim}{f'  — {detail}' if detail else ''}")


def build_component(root: Path, domain: str = "probe") -> Path:
    """A component with the shape `Identity` expects: a manifest and some source beside it."""
    component = root / "custom_components" / domain
    component.mkdir(parents=True)
    (component / "manifest.json").write_text(json.dumps(
        {"domain": domain, "name": domain, "version": "1.0.0",
         "requirements": ["example-package==1.0.0"]}, indent=2))
    (component / "__init__.py").write_text("alpha\nbravo\ncharlie\n")
    (component / "sensor.py").write_text("SENSOR = 1\n")
    return component


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # §7.5 / C1 — the case that must hold 37 times out of 37 for C1 to be counted.
        component = build_component(root, "untouched")
        before = TreeState.capture(component)
        after = TreeState.capture(component)
        clean = compare(before, after)
        check("an untouched tree reports no source change",
              not clean.source_changed and clean.diff_lines == 0)

        # §7.5 / C1 — one line, and the criterion is stated in lines. `retain` is what makes
        # the count possible at all when the tree is edited in place, which is the baseline arm.
        component = build_component(root, "edited")
        before = TreeState.capture(component, retain=True)
        (component / "__init__.py").write_text("alpha\nBRAVO\ncharlie\n")
        edited = compare(before, TreeState.capture(component))
        check("a one-line edit is caught", edited.source_changed
              and edited.modified == ["__init__.py"], f"modified={edited.modified}")
        check("and is counted in lines, not hashes", edited.diff_lines == 2,
              f"diff_lines={edited.diff_lines} (one removed, one added)")
        check("and is attributed to source", edited.components_changed == ["source"],
              f"components={edited.components_changed}")

        # §7.28 — the confined arm compares a copy against a still-present original, so the
        # count works there without retaining anything.
        component = build_component(root, "copied")
        copy = root / "copy_of_copied"
        shutil.copytree(component, copy)
        (copy / "__init__.py").write_text("alpha\nbravo\ncharlie\ndelta\n")
        two_trees = compare(TreeState.capture(component), TreeState.capture(copy))
        check("two distinct trees are counted without retention",
              two_trees.source_changed and two_trees.diff_lines == 1
              and not two_trees.lines_unknown, f"diff_lines={two_trees.diff_lines}")

        # §6.4.5 — the defect this module nearly shipped. Without retained bytes and with one
        # directory, the pre-run content is gone; reporting zero lines would be an absence
        # masquerading as a clean result. It must say it does not know.
        component = build_component(root, "unknowable")
        before = TreeState.capture(component)
        (component / "__init__.py").write_text("alpha\nBRAVO\ncharlie\n")
        blind = compare(before, TreeState.capture(component))
        check("an uncountable change is reported unknown, not zero",
              blind.source_changed and blind.lines_unknown == ["__init__.py"]
              and blind.diff_lines == 0,
              f"unknown={blind.lines_unknown}")

        # §7.5 / C1 — a tree can be modified by losing a file as well as by changing one.
        component = build_component(root, "deleted")
        before = TreeState.capture(component)
        (component / "sensor.py").unlink()
        gone = compare(before, TreeState.capture(component))
        check("a deleted source file is caught",
              gone.source_changed and gone.removed == ["sensor.py"])

        component = build_component(root, "added")
        before = TreeState.capture(component)
        (component / "extra.py").write_text("INJECTED = True\n")
        grew = compare(before, TreeState.capture(component))
        check("an added source file is caught",
              grew.source_changed and grew.added == ["extra.py"])

        # §5.12.1 — the three-part tuple earns its keep here: a permission change is not a
        # code change, and a count that conflated them would report the wrong event.
        component = build_component(root, "manifest_edit")
        before = TreeState.capture(component)
        manifest = json.loads((component / "manifest.json").read_text())
        manifest["name"] = "renamed"
        (component / "manifest.json").write_text(json.dumps(manifest, indent=2))
        renamed = compare(before, TreeState.capture(component))
        check("a manifest edit is attributed to manifest, not source",
              renamed.components_changed == ["manifest"],
              f"components={renamed.components_changed}")

        component = build_component(root, "requirements_edit")
        before = TreeState.capture(component)
        manifest = json.loads((component / "manifest.json").read_text())
        manifest["requirements"] = ["example-package==2.0.0"]
        (component / "manifest.json").write_text(json.dumps(manifest, indent=2))
        bumped = compare(before, TreeState.capture(component))
        check("a requirements edit moves manifest and requirements together",
              bumped.components_changed == ["manifest", "requirements"],
              f"components={bumped.components_changed}")

        # §7.28 — the case that decides whether the baseline arm can pass at all.
        component = build_component(root, "bytecode")
        before = TreeState.capture(component)
        cache = component / "__pycache__"
        cache.mkdir()
        (cache / "__init__.cpython-314.pyc").write_bytes(b"\x00\x0f\x0d\x0a" * 8)
        (cache / "sensor.cpython-314.pyc").write_bytes(b"\x00\x0f\x0d\x0a" * 8)
        cached = compare(before, TreeState.capture(component))
        check("bytecode is not a source change", not cached.source_changed)
        check("and is still reported rather than silently dropped",
              len(cached.cache_added) == 2, f"cache_added={len(cached.cache_added)}")

        # Both at once: the shape a genuine violation would have in the baseline arm.
        component = build_component(root, "both")
        before = TreeState.capture(component)
        (component / "__pycache__").mkdir()
        (component / "__pycache__" / "x.pyc").write_bytes(b"\x00")
        (component / "sensor.py").write_text("SENSOR = 2\n")
        both = compare(before, TreeState.capture(component))
        check("a real change is still caught through the bytecode noise",
              both.source_changed and both.modified == ["sensor.py"]
              and len(both.cache_added) == 1)

        # The run-level count §7.5's C1 row asks for.
        rolled = summarise([
            {"domain": "clean_a", "integrity": clean.as_dict()},
            {"domain": "clean_b", "integrity": cached.as_dict()},
            {"domain": "dirty", "integrity": both.as_dict()},
            {"domain": "not_checked"},
        ])
        check("the run-level summary counts only what it checked",
              rolled["integrations_checked"] == 3 and rolled["source_changed"] == 1
              and rolled["domains_with_changes"] == ["dirty"], json.dumps(rolled))
        check("and counts the trees that gained bytecode separately",
              rolled["trees_gaining_bytecode"] == 2,
              f"trees_gaining_bytecode={rolled['trees_gaining_bytecode']}")

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
