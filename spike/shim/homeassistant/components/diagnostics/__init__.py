"""Shim of homeassistant.components.diagnostics.

Only ``async_redact_data`` matters to integrations: it is what they call before
handing a payload to HA's diagnostics download, to strip credentials and
coordinates. Seven of the thirty polling sensors in the sample import it, and it
is pure data manipulation with no HA state involved, so the real implementation
and this one are the same function.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, TypeVar

REDACTED = "**REDACTED**"

_T = TypeVar("_T")


def async_redact_data(data: _T, to_redact: Iterable[Any]) -> _T:
    """Return a copy of ``data`` with every key in ``to_redact`` masked.

    Recurses through mappings and sequences. Empty values are left alone, as HA
    does, so that a redacted payload still shows which fields were simply absent
    rather than hidden.
    """
    if not isinstance(data, (Mapping, list, tuple)):
        return data

    if isinstance(data, (list, tuple)):
        return type(data)(async_redact_data(item, to_redact) for item in data)  # type: ignore[return-value]

    redacted = {**data}

    for key, value in redacted.items():
        if value is None or (isinstance(value, (str, list, tuple, dict)) and not value):
            continue
        if key in to_redact:
            redacted[key] = REDACTED
        elif isinstance(value, Mapping):
            redacted[key] = async_redact_data(value, to_redact)
        elif isinstance(value, (list, tuple)):
            redacted[key] = [async_redact_data(item, to_redact) for item in value]

    return redacted  # type: ignore[return-value]
