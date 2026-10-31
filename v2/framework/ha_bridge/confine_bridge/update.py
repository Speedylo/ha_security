"""Updates published by confined integrations (bridge batch B3, 2026-10-31).

The versions, the summary and the progress come from the integration's own instance; whether an
update is offered, and skipping one, are worked out and kept by (A) itself. Installing goes to the
integration through the mediator (decision 1). Release notes are not offered: they would be a long
text from the sandbox drawn in (A), so the feature is dropped (decision 2,
`notes/bridge_kinds_b3_prediction_20261031.md`).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature

from .entity import BridgedEntity, setup_platform

_PLAIN = {"installed_version": "_attr_installed_version",
          "latest_version": "_attr_latest_version", "release_summary": "_attr_release_summary",
          "release_url": "_attr_release_url", "title": "_attr_title",
          "update_percentage": "_attr_update_percentage"}


class BridgedUpdate(BridgedEntity, UpdateEntity):

    # `entity_picture` is the integration's own image link; (A) keeps its default.
    _described = frozenset({*_PLAIN, "auto_update", "in_progress", "skipped_version",
                            "display_precision", "entity_picture", "supported_features"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        for key, name in _PLAIN.items():
            setattr(self, name, attributes.get(key))
        self._attr_auto_update = bool(attributes.get("auto_update"))
        self._attr_in_progress = bool(attributes.get("in_progress"))
        self._attr_supported_features = (
            UpdateEntityFeature(int(attributes.get("supported_features") or 0))
            & ~UpdateEntityFeature.RELEASE_NOTES)

    def _restorable_empty(self) -> bool:
        return False

    def _restore(self, state: str) -> None:
        pass

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        data: dict[str, Any] = {"backup": backup}
        if version is not None:
            data["version"] = version
        await self._data.command(self._integration, self._published_id, "install", data)


async_setup_entry = setup_platform("update", BridgedUpdate)
