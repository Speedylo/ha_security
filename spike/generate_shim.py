#!/usr/bin/env python3
"""Generate the shim's pure-data modules from Home Assistant's own source.

The project's central claim about cost is that the long tail of the HA API
surface is *constants* — units, enums, config keys, selector schemas — and that
constants are machine-generatable rather than hand-written. This script is that
claim, executed: it reads HA's source with `ast` and emits shim modules, so the
tail costs a script run instead of developer weeks.

Nothing is imported or executed from the downloaded source. It is parsed as
text, exactly like hacs_api_surface.py treats untrusted integrations.

    ./generate_shim.py                 # fetch (cached) and generate
    ./generate_shim.py --check         # report what would change, write nothing

Generated modules carry a header saying so. Hand-written behaviour is never
overwritten: the generator only emits modules listed in TARGETS, and for
`const` it preserves any name the current shim defines that HA's source does
not (there should be none, but silence about a removal would be worse).
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHIM = HERE / "shim" / "homeassistant"
CACHE = HERE / ".ha_source_cache"
# Pinned to a release tag, never `dev`. Generating against a moving branch makes
# the shim's contents depend on the day it was run — and `dev` is not always even
# parseable: at the time of writing its helpers/selector.py contains
# `except vol.Invalid, vol.MultipleInvalid:`, which is Python 2 syntax and a
# SyntaxError on any Python 3. Bump this deliberately.
HA_VERSION = "2026.8.1"
RAW = "https://raw.githubusercontent.com/home-assistant/core/" + HA_VERSION + "/homeassistant/{}.py"

HEADER = '''"""GENERATED — do not edit by hand.

Produced by spike/generate_shim.py from Home Assistant {version}'s own {source}.
Regenerate rather than patching: the point of this module is that the constant
tail of the HA API costs a script run, not developer time.
"""
'''


def fetch(module_path: str) -> str:
    """Download HA's source for one module, caching it."""
    CACHE.mkdir(exist_ok=True)
    cached = CACHE / (module_path.replace("/", "_") + ".py")
    if cached.exists() and cached.stat().st_size > 0:
        return cached.read_text(encoding="utf-8")
    url = RAW.format(module_path)
    with urllib.request.urlopen(url, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    cached.write_text(text, encoding="utf-8")
    return text


# ----------------------------------------------------------------------------
# const.py
# ----------------------------------------------------------------------------

def _literal(node: ast.AST) -> str | None:
    """Render a node if it is a self-contained literal, else None."""
    try:
        value = ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None
    # Sets and dicts of literals are fine; anything containing a name is not.
    return repr(value)


def generate_const(source: str) -> str:
    """Emit every literal constant and enum class from HA's const.py."""
    tree = ast.parse(source)
    enum_members: dict[str, dict[str, str]] = {}
    out: list[str] = []

    # Pass 1: enum classes, so that `X: Final = SomeEnum.MEMBER.value` resolves.
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        bases = {ast.unparse(b) for b in node.bases}
        if not bases & {"StrEnum", "IntEnum", "IntFlag", "Enum"}:
            continue
        members: dict[str, str] = {}
        lines = [f"class {node.name}({'StrEnum' if 'StrEnum' in bases else 'IntEnum'}):"]
        doc = ast.get_docstring(node)
        lines.append(f'    """{(doc or node.name).splitlines()[0]}"""')
        lines.append("")
        for item in node.body:
            if isinstance(item, ast.Assign) and len(item.targets) == 1:
                target = item.targets[0]
                if isinstance(target, ast.Name):
                    rendered = _literal(item.value)
                    if rendered is not None:
                        members[target.id] = rendered
                        lines.append(f"    {target.id} = {rendered}")
        if members:
            enum_members[node.name] = members
            out.append("\n".join(lines))

    # Pass 2: module-level constants.
    consts: list[str] = []
    for node in tree.body:
        target_name = value_node = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name, value_node = node.target.id, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name, value_node = node.targets[0].id, node.value
        if not target_name or value_node is None:
            continue

        if target_name.startswith("_DEPRECATED_"):
            # HA moves a constant onto an enum, then keeps the flat name alive
            # through module __getattr__ so old integrations keep working. They
            # do keep using it, so the shim must define the flat name too.
            #   _DEPRECATED_CONCENTRATION_PARTS_PER_MILLION =
            #       DeprecatedConstantEnum(UnitOfRatio.PARTS_PER_MILLION, "2027.8")
            target_name = target_name[len("_DEPRECATED_"):]
            if isinstance(value_node, ast.Call) and value_node.args:
                value_node = value_node.args[0]
        elif target_name.startswith("_"):
            continue

        rendered = _literal(value_node)
        if rendered is None and isinstance(value_node, ast.Call) and len(value_node.args) == 1:
            # Typed wrappers around a plain literal, e.g.
            #   EVENT_HOMEASSISTANT_START: EventType[...] = EventType("homeassistant_start")
            # The wrapper is a typing device; the value an integration compares
            # against is the string inside it.
            rendered = _literal(value_node.args[0])
        if rendered is None:
            # Resolve the common `SomeEnum.MEMBER.value` / `SomeEnum.MEMBER` forms.
            text = ast.unparse(value_node)
            base = text[: -len(".value")] if text.endswith(".value") else text
            if "." in base:
                enum_name, _, member = base.partition(".")
                rendered = enum_members.get(enum_name, {}).get(member)
        if rendered is not None:
            consts.append(f"{target_name} = {rendered}")

    # `Platform` is the most-imported constant in the whole catalogue (65% of
    # integrations) and since 2026.8 it does not live in const.py: it is
    # `EntityPlatforms`, re-exported from homeassistant/generated/entity_platforms.py.
    # That module is itself machine-generated upstream — independent evidence for
    # this script's premise — so it is pulled in and re-emitted here.
    platform_block = ""
    try:
        platform_source = fetch("generated/entity_platforms")
        for node in ast.parse(platform_source).body:
            if isinstance(node, ast.ClassDef) and node.name == "EntityPlatforms":
                members = [
                    f"    {item.targets[0].id} = {_literal(item.value)}"
                    for item in node.body
                    if isinstance(item, ast.Assign)
                    and isinstance(item.targets[0], ast.Name)
                    and _literal(item.value) is not None
                ]
                platform_block = (
                    "class EntityPlatforms(StrEnum):\n"
                    '    """The platforms an entity can belong to."""\n\n'
                    + "\n".join(members)
                    + "\n\n\n# Upstream re-exports it under this name; integrations import both.\n"
                    "Platform = EntityPlatforms\n"
                )
    except Exception as err:  # noqa: BLE001 - a missing extra module must not fail the run
        print(f"  const: could not generate Platform ({err}); relying on carry-over", file=sys.stderr)

    body = HEADER.format(source="const.py", version=HA_VERSION)
    body += "\nfrom enum import IntEnum, StrEnum\n\n\n"
    # Upstream builds these by f-string from MAJOR/MINOR/PATCH, so they are not
    # literals and the constant pass skips them — but integrations do import
    # `__version__` (to compare against a minimum HA version), so emit it here.
    body += (
        "# The HA release this module was generated from.\n"
        f'__version__ = "{HA_VERSION}"\n'
        f'__short_version__ = "{".".join(HA_VERSION.split(".")[:2])}"\n\n\n'
    )
    if platform_block:
        body += platform_block + "\n\n"
    body += "\n\n\n".join(out)
    body += "\n\n\n# ---- module-level constants ----\n\n"
    body += "\n".join(consts)
    return body + "\n"


# ----------------------------------------------------------------------------
# helpers/selector.py
# ----------------------------------------------------------------------------

def generate_selector(source: str) -> str:
    """Emit permissive stand-ins for every Selector class and its config dict.

    Selectors describe *config-flow form widgets*. Nothing about which widget a
    form uses can affect what an integration is permitted to do, so the shim
    only has to make the names exist and accept their arguments. The classes are
    therefore generated as accept-anything stubs rather than reimplemented.
    """
    selectors: list[str] = []
    configs: list[str] = []

    try:
        tree = ast.parse(source)
    except SyntaxError as err:
        # Upstream does not always parse. HA 2026.8.1's helpers/selector.py
        # contains `except vol.Invalid, vol.MultipleInvalid:` — Python 2 syntax,
        # a SyntaxError on any Python 3 — so an AST pass over it cannot work.
        # Only class *names* are needed to emit stubs, and those survive a
        # line-based read, so degrade to that rather than failing the run.
        print(f"  selector: upstream does not parse ({err.msg} at line {err.lineno}); "
              f"falling back to line-based class extraction", file=sys.stderr)
        for line in source.splitlines():
            match = re.match(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)", line)
            if not match:
                continue
            name, bases_text = match.group(1), match.group(2)
            if name.startswith("_"):
                continue
            if "Selector[" in bases_text or bases_text.strip() == "Selector":
                selectors.append(name)
            elif "TypedDict" in bases_text or "SelectorConfig" in bases_text:
                configs.append(name)
        return _render_selector(selectors, configs)

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name.startswith("_"):
            continue
        bases = {ast.unparse(b) for b in node.bases}
        if any(b.startswith("Selector[") or b == "Selector" for b in bases):
            selectors.append(node.name)
        elif any("TypedDict" in b or b.endswith("SelectorConfig") for b in bases):
            configs.append(node.name)

    return _render_selector(selectors, configs)


def _render_selector(selectors: list[str], configs: list[str]) -> str:
    """Emit the stub module for the given selector and config class names."""
    body = HEADER.format(source="helpers/selector.py", version=HA_VERSION)
    body += '''
from typing import Any


class Selector:
    """Accept-anything stand-in for a config-flow selector.

    Real selectors validate form input and render a widget. Neither affects what
    the integration may do at runtime, so the shim keeps the name and the
    constructor signature and discards the schema.
    """

    def __init__(self, config: Any = None, **kwargs: Any) -> None:
        self.config = config if config is not None else kwargs

    def __call__(self, data: Any) -> Any:
        return data

    def serialize(self) -> dict[str, Any]:
        return {"selector": {type(self).__name__: self.config}}


class _SelectorConfig(dict):
    """Config dicts are TypedDicts upstream: plain dicts at runtime."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


'''
    for name in sorted(selectors):
        body += f"class {name}(Selector):\n    pass\n\n\n"
    for name in sorted(configs):
        body += f"class {name}(_SelectorConfig):\n    pass\n\n\n"

    body += "def selector(config: Any) -> Selector:\n"
    body += '    """Build a selector from its serialized form."""\n'
    body += "    return Selector(config)\n"
    return body


TARGETS = {
    "const": ("const", generate_const, SHIM / "const.py"),
    "selector": ("helpers/selector", generate_selector, SHIM / "helpers" / "selector.py"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report changes, write nothing")
    parser.add_argument("--only", help="generate a single target", choices=sorted(TARGETS))
    args = parser.parse_args()

    wanted = [args.only] if args.only else sorted(TARGETS)
    for key in wanted:
        module_path, generator, destination = TARGETS[key]
        generated = generator(fetch(module_path))

        # Never silently drop a name the current shim provides. Names can vanish
        # from a source module without vanishing from the API — HA 2026.8 moved
        # `Platform` into a generated module and the lock states into their own
        # component — so lost definitions are carried over verbatim, not merely
        # reported.
        preserved = ""
        if destination.exists():
            old_source = destination.read_text(encoding="utf-8")
            lost = sorted(_exported_names(old_source) - _exported_names(generated))
            if lost:
                carried = _source_for(old_source, set(lost))
                preserved = (
                    "\n\n# ---- carried over from the previous module ----\n"
                    "# Defined by the shim but absent from the pinned HA source, usually\n"
                    "# because upstream moved them elsewhere. Copied verbatim so that\n"
                    "# regenerating cannot remove a name some integration imports.\n\n"
                    + "\n\n".join(carried)
                    + "\n"
                )
                print(f"  {key}: carried over {len(lost)} name(s) absent from the pinned source: "
                      f"{', '.join(lost[:8])}")

        if args.check:
            current = destination.read_text(encoding="utf-8") if destination.exists() else ""
            verdict = "unchanged" if current == generated + preserved else "WOULD CHANGE"
            print(f"{key:10s} -> {destination.relative_to(HERE)}  [{verdict}]  "
                  f"{len(_exported_names(generated))} names")
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(generated + preserved, encoding="utf-8")
        print(f"{key:10s} -> {destination.relative_to(HERE)}  "
              f"{len(_exported_names(generated))} names, {len(generated.splitlines())} lines")

    return 0


def _source_for(source: str, wanted: set[str]) -> list[str]:
    """Verbatim source of every top-level definition naming something in `wanted`."""
    tree = ast.parse(source)
    out: list[str] = []
    for node in tree.body:
        names: set[str] = set()
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
            names = {node.name}
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = {node.target.id}
        elif isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if names & wanted:
            segment = ast.get_source_segment(source, node)
            if segment:
                out.append(segment)
    return out


def _exported_names(source: str) -> set[str]:
    """Public top-level names a module defines."""
    def public(name: str) -> bool:
        # Dunders are part of the importable surface — integrations do
        # `from homeassistant.const import __version__` to gate on an HA
        # version — so they count, while single-underscore names do not.
        return not name.startswith("_") or (name.startswith("__") and name.endswith("__"))

    names: set[str] = set()
    for node in ast.parse(source).body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and public(node.name):
            names.add(node.name)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if public(node.target.id):
                names.add(node.target.id)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and public(target.id):
                    names.add(target.id)
    return names


if __name__ == "__main__":
    sys.exit(main())
