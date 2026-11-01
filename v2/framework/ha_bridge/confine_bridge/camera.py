"""Cameras published by confined integrations (bridge batch B4b, 2026-11-01).

(A)'s UI asks (A)'s own camera proxy for a picture, and (A) asks this entity. Here that is a
**question** to the confined integration, `camera_image`, whose answer — one picture — the mediator
checks before it reaches this entity (`notes/bridge_kinds_b4b_prediction_20261031.md`).

Snapshots only (decision 3): STREAM is never offered, so (A) never connects to an address the
integration chooses, and never feeds its bytes to a video decoder. A picture is reused for 2 s
per size asked (decision 2), and the frame interval announced is the same 2 s, so an open
"live" view asks at most once every 2 s: each question is a durable record in the mediator.
"""

from __future__ import annotations

import base64
import time
from typing import Any

from homeassistant.components.camera import Camera, CameraEntityFeature

from .entity import BridgedEntity, setup_platform

#: How long a picture is reused before the integration is asked again (decision 2).
REUSE_SECONDS = 2.0
#: Picture sizes kept at once: each card can ask its own width and height.
KEPT_SIZES = 4


class BridgedCamera(BridgedEntity, Camera):

    # `access_token` and `frontend_stream_type` are the sandbox's own instance's: (A) has its own.
    _described = frozenset({"brand", "model_name", "motion_detection", "supported_features",
                            "access_token", "frontend_stream_type"})
    _attr_frame_interval = REUSE_SECONDS

    def __init__(self, definition: dict[str, Any], data) -> None:
        Camera.__init__(self)   # (A)'s own access token, content type and stream fields
        self._pictures: dict[tuple, tuple[float, str, bytes]] = {}
        BridgedEntity.__init__(self, definition, data)

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_is_recording = state == "recording"
        self._attr_is_streaming = state == "streaming"
        self._attr_brand = _text(attributes.get("brand"))
        self._attr_model = _text(attributes.get("model_name"))
        self._attr_motion_detection_enabled = attributes.get("motion_detection") is True
        # ON_OFF only: STREAM is not offered (decision 3).
        self._attr_supported_features = CameraEntityFeature(
            int(attributes.get("supported_features") or 0) & CameraEntityFeature.ON_OFF)

    def _restorable_empty(self) -> bool:
        return False   # the state is derived from recording and streaming

    def _restore(self, state: str) -> None:
        pass

    async def async_camera_image(self, width: int | None = None,
                                 height: int | None = None) -> bytes | None:
        size = (width, height)
        now = time.monotonic()
        kept = self._pictures.get(size)
        if kept is not None and now - kept[0] < REUSE_SECONDS:
            self.content_type = kept[1]
            return kept[2]
        asked = {k: v for k, v in (("width", width), ("height", height)) if v is not None}
        answer = await self._data.command(self._integration, self._published_id,
                                          "camera_image", asked)
        content = base64.b64decode(answer["data"])
        self.content_type = answer["content_type"]
        if size not in self._pictures and len(self._pictures) >= KEPT_SIZES:
            del self._pictures[min(self._pictures, key=lambda k: self._pictures[k][0])]
        self._pictures[size] = (time.monotonic(), answer["content_type"], content)
        return content

    async def async_turn_on(self) -> None:
        await self._data.command(self._integration, self._published_id, "turn_on", {})

    async def async_turn_off(self) -> None:
        await self._data.command(self._integration, self._published_id, "turn_off", {})

    async def async_enable_motion_detection(self) -> None:
        await self._data.command(self._integration, self._published_id,
                                 "enable_motion_detection", {})

    async def async_disable_motion_detection(self) -> None:
        await self._data.command(self._integration, self._published_id,
                                 "disable_motion_detection", {})


def _text(value: Any) -> str | None:
    return value[:255] if isinstance(value, str) and value else None


async_setup_entry = setup_platform("camera", BridgedCamera)
