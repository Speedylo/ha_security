"""Images published by confined integrations (bridge batch B4b, 2026-11-01).

The state is the time the image last changed, as the integration published it. The picture is a
**question**, `image`, whose answer the mediator checks before it reaches this entity
(`notes/bridge_kinds_b4b_prediction_20261031.md`). (A) never downloads a link the integration
gives: this entity has no `image_url`, and the published `entity_picture` and `access_token` are
the sandbox's own instance's, not passed on. The picture is kept until the published time changes.
"""

from __future__ import annotations

import base64
import collections
import time
from datetime import datetime
from typing import Any

from homeassistant.components.image import ImageEntity

from .entity import BridgedEntity, setup_platform

#: Asked again no sooner than this, even if the published time keeps changing (decision 2).
REUSE_SECONDS = 2.0


class BridgedImage(BridgedEntity, ImageEntity):

    _described = frozenset({"access_token"})
    _attr_image_url = None   # never a link (A) would download

    def __init__(self, definition: dict[str, Any], data) -> None:
        # Not `ImageEntity.__init__`, which needs `hass` only for the HTTP client `image_url` uses.
        self.access_tokens: collections.deque = collections.deque(maxlen=2)
        self.async_update_token()
        self._picture: tuple[datetime | None, float, bytes] | None = None
        BridgedEntity.__init__(self, definition, data)

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        try:
            self._attr_image_last_updated = datetime.fromisoformat(str(state))
        except ValueError:
            self._attr_image_last_updated = None

    def _restorable_empty(self) -> bool:
        return self._attr_image_last_updated is None

    def _restore(self, state: str) -> None:
        self._take_state(state, {})

    async def async_image(self) -> bytes | None:
        published = self._attr_image_last_updated
        kept = self._picture
        if kept is not None and (kept[0] == published
                                 or time.monotonic() - kept[1] < REUSE_SECONDS):
            return kept[2]
        answer = await self._data.command(self._integration, self._published_id, "image", {})
        content = base64.b64decode(answer["data"])
        self._attr_content_type = answer["content_type"]
        self._picture = (published, time.monotonic(), content)
        return content


async_setup_entry = setup_platform("image", BridgedImage)
