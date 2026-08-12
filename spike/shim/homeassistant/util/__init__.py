"""Shim of homeassistant.util."""

from __future__ import annotations

import re
import unicodedata

_SLUG_STRIP = re.compile(r"[^a-z0-9_]+")
_SLUG_COLLAPSE = re.compile(r"_+")


def slugify(text: str | None, *, separator: str = "_") -> str:
    """Slugify a name, matching HA's entity-id-safe output closely enough."""
    if text is None:
        return ""
    normalised = unicodedata.normalize("NFKD", str(text))
    normalised = normalised.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SLUG_STRIP.sub("_", normalised)
    slug = _SLUG_COLLAPSE.sub("_", slug).strip("_")
    if separator != "_":
        slug = slug.replace("_", separator)
    return slug
