"""A RestoreSensor whose value is a generation counter.

The counter makes the test a crisp pass or fail rather than a judgement:

    run 1  nothing to restore   -> publishes 1
    run 2  restored 1           -> publishes 2

So a second run that publishes 1 means restoration silently did not happen, which is
exactly the failure mode worth catching. The harness reads `restored_from` to distinguish
"restored nothing because there was nothing" from "restored nothing because it is broken".
"""

from __future__ import annotations

from homeassistant.components.sensor import RestoreSensor, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the restore probe sensor."""
    async_add_entities([GenerationSensor()])


class GenerationSensor(RestoreSensor):
    """Publishes 1 on a fresh config directory, and n+1 whenever it restored n."""

    _attr_has_entity_name = True
    _attr_name = "Generation"
    _attr_unique_id = "probe_restore_generation"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self) -> None:
        self._attr_native_value = 1
        self._restored_from: int | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the previous generation, if the machinery is running."""
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        if last is not None and last.native_value is not None:
            self._restored_from = int(last.native_value)
            self._attr_native_value = self._restored_from + 1

    @property
    def extra_state_attributes(self) -> dict[str, int | None]:
        """Expose what was restored, so the harness need not infer it."""
        return {"restored_from": self._restored_from}
