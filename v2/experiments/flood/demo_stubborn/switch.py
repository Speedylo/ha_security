"""The *Misbehave* switch, which also blocks the event loop when turned on."""

from __future__ import annotations

import socket
import threading
import time
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

#: Not in the manifest, so every connection to it is refused by the mediator.
UNDECLARED_HOST = ("updates.example.com", 443)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([Misbehave()])


class Misbehave(SwitchEntity):
    _attr_name = "Demo Stubborn Misbehave"
    _attr_unique_id = "demo_stubborn_misbehave"
    _attr_should_poll = False

    def __init__(self) -> None:
        self._attr_is_on = False
        self._stop = threading.Event()

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self._stop.clear()
        self.async_write_ha_state()
        threading.Thread(target=self._retry, daemon=True).start()
        # The difference from `demo_flood`: a blocking call on the event loop. Nothing on this
        # loop runs again, including the runtime's reader that would see the channel close.
        time.sleep(3600)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self._stop.set()
        self.async_write_ha_state()

    def _retry(self) -> None:
        # The bug being simulated: a refused connection is retried at once, forever.
        while not self._stop.is_set():
            try:
                socket.create_connection(UNDECLARED_HOST, timeout=2).close()
            except OSError:
                pass
