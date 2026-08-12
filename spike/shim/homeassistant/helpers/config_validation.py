"""Shim of homeassistant.helpers.config_validation.

Only the validators integrations reference at import time. YAML-configuration
validators matter far less here than on real HA: the supervisor validates
configuration against the manifest before the sandbox is ever started.
"""

from __future__ import annotations

from typing import Any, Callable

import voluptuous as vol

string = str
boolean = bool
positive_int = int
port = int
url = str


def config_entry_only_config_schema(domain: str) -> Callable[[dict], dict]:
    """Schema for integrations that are UI-configured only."""

    def validator(config: dict) -> dict:
        return config

    return validator


def entity_id(value: Any) -> str:
    value = str(value).lower()
    if "." not in value:
        raise vol.Invalid(f"Entity ID {value} is an invalid entity ID")
    return value


def entity_ids(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [part.strip() for part in value.split(",")]
    return [entity_id(item) for item in value]


def ensure_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def time_period_seconds(value: Any) -> Any:
    from datetime import timedelta

    return timedelta(seconds=float(value))


def has_at_least_one_key(*keys: str) -> Callable[[dict], dict]:
    def validate(obj: dict) -> dict:
        if not any(key in obj for key in keys):
            raise vol.Invalid(f"must contain at least one of {', '.join(keys)}")
        return obj

    return validate


def deprecated(key: str, replacement_key: str | None = None) -> Callable[[dict], dict]:
    def validator(config: dict) -> dict:
        return config

    return validator


def removed(key: str, default: Any = None, raise_if_present: bool = True) -> Callable[[dict], dict]:
    def validator(config: dict) -> dict:
        return config

    return validator
