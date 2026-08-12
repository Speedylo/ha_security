"""Shim of homeassistant.data_entry_flow."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class FlowResultType(StrEnum):
    """Type of a flow step result."""

    FORM = "form"
    CREATE_ENTRY = "create_entry"
    ABORT = "abort"
    EXTERNAL_STEP = "external"
    EXTERNAL_STEP_DONE = "external_done"
    SHOW_PROGRESS = "progress"
    SHOW_PROGRESS_DONE = "progress_done"
    MENU = "menu"


FlowResult = dict[str, Any]


class FlowError(Exception):
    """Base flow error."""


class AbortFlow(FlowError):
    """Flow aborted."""

    def __init__(self, reason: str, description_placeholders: dict | None = None) -> None:
        super().__init__(f"Flow aborted: {reason}")
        self.reason = reason
        self.description_placeholders = description_placeholders


class UnknownFlow(FlowError):
    """Unknown flow."""


class InvalidData(FlowError):
    """Invalid data supplied to a flow."""
