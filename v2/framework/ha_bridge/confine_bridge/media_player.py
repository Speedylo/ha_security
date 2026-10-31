"""Media players published by confined integrations (bridge batch B4a, 2026-10-31).

The state, the volume, what is playing and the source lists come from the integration's own
instance. Every command goes to the integration through the mediator under the service's own
field names, because its instance runs the service again. `toggle`, `volume_up`, `volume_down`
and `media_play_pause` go on as themselves, so the integration's own method runs if it has one
(decision 1). Not offered: artwork (the published picture is a link to the sandbox's own image
proxy), browsing, searching and grouping (decisions 3–5,
`notes/bridge_kinds_b4a_prediction_20261031.md`).

Media (A) owns — its library, text-to-speech — is resolved here into a signed link to (A) before it
is sent, because the integration would otherwise try to resolve it in the sandbox, which has none
of it. An id naming a source (A) does not have goes on unchanged, for the integration's own
instance (decision 2, option (c)).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components import media_source
from homeassistant.components.media_player import (MediaPlayerEntity, MediaPlayerEntityFeature,
                                                   MediaPlayerState, RepeatMode,
                                                   async_process_play_media_url)

from .entity import BridgedEntity, setup_platform

_PLAIN = ("volume_level", "is_volume_muted", "media_content_id", "media_content_type",
          "media_duration", "media_position", "media_title", "media_artist", "media_album_name",
          "media_album_artist", "media_track", "media_series_title", "media_season",
          "media_episode", "media_channel", "media_playlist", "app_id", "app_name", "source",
          "source_list", "sound_mode", "sound_mode_list", "shuffle", "volume_step")
_NOT_OFFERED = (MediaPlayerEntityFeature.BROWSE_MEDIA | MediaPlayerEntityFeature.SEARCH_MEDIA
                | MediaPlayerEntityFeature.GROUPING)


def _state(value: Any) -> MediaPlayerState | None:
    try:
        return MediaPlayerState(value)
    except ValueError:
        return None


class BridgedMediaPlayer(BridgedEntity, MediaPlayerEntity):

    _described = frozenset({*_PLAIN, "media_position_updated_at", "repeat", "group_members",
                            "entity_picture", "entity_picture_local", "supported_features"})

    def _take_state(self, state: Any, attributes: dict[str, Any]) -> None:
        self._attr_state = _state(state)
        for key in _PLAIN:
            setattr(self, f"_attr_{key}", attributes.get(key))
        try:
            self._attr_media_position_updated_at = datetime.fromisoformat(
                str(attributes["media_position_updated_at"]))
        except (KeyError, ValueError):
            self._attr_media_position_updated_at = None
        try:
            self._attr_repeat = RepeatMode(attributes["repeat"]) if attributes.get("repeat") \
                else None
        except ValueError:
            self._attr_repeat = None
        self._attr_supported_features = (
            MediaPlayerEntityFeature(int(attributes.get("supported_features") or 0))
            & ~_NOT_OFFERED)

    def _restorable_empty(self) -> bool:
        return self._attr_state is None

    def _restore(self, state: str) -> None:
        self._attr_state = _state(state)

    async def _send(self, service: str, data: dict[str, Any] | None = None) -> None:
        await self._data.command(self._integration, self._published_id, service, data or {})

    async def async_turn_on(self) -> None:
        await self._send("turn_on")

    async def async_turn_off(self) -> None:
        await self._send("turn_off")

    async def async_toggle(self) -> None:
        await self._send("toggle")

    async def async_media_play(self) -> None:
        await self._send("media_play")

    async def async_media_pause(self) -> None:
        await self._send("media_pause")

    async def async_media_play_pause(self) -> None:
        await self._send("media_play_pause")

    async def async_media_stop(self) -> None:
        await self._send("media_stop")

    async def async_media_next_track(self) -> None:
        await self._send("media_next_track")

    async def async_media_previous_track(self) -> None:
        await self._send("media_previous_track")

    async def async_clear_playlist(self) -> None:
        await self._send("clear_playlist")

    async def async_volume_up(self) -> None:
        await self._send("volume_up")

    async def async_volume_down(self) -> None:
        await self._send("volume_down")

    async def async_set_volume_level(self, volume: float) -> None:
        await self._send("volume_set", {"volume_level": volume})

    async def async_mute_volume(self, mute: bool) -> None:
        await self._send("volume_mute", {"is_volume_muted": mute})

    async def async_media_seek(self, position: float) -> None:
        await self._send("media_seek", {"seek_position": position})

    async def async_select_source(self, source: str) -> None:
        await self._send("select_source", {"source": source})

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        await self._send("select_sound_mode", {"sound_mode": sound_mode})

    async def async_set_shuffle(self, shuffle: bool) -> None:
        await self._send("shuffle_set", {"shuffle": shuffle})

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        await self._send("repeat_set", {"repeat": RepeatMode(repeat).value})

    async def async_play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        if media_source.is_media_source_id(media_id):
            try:
                media = await media_source.async_resolve_media(self.hass, media_id,
                                                               self.entity_id)
            except media_source.MediaSourceError:
                pass  # not a source (A) has: the integration's own instance resolves it, or not
            else:
                media_id = async_process_play_media_url(self.hass, media.url)
        data: dict[str, Any] = {"media_content_type": str(media_type),
                                "media_content_id": media_id}
        if kwargs.get("enqueue") is not None:
            data["enqueue"] = str(getattr(kwargs["enqueue"], "value", kwargs["enqueue"]))
        if kwargs.get("announce") is not None:
            data["announce"] = bool(kwargs["announce"])
        if kwargs.get("extra") is not None:
            data["extra"] = kwargs["extra"]
        await self._send("play_media", data)


async_setup_entry = setup_platform("media_player", BridgedMediaPlayer)
