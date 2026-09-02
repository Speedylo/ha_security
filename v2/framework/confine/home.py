"""One home, used by both arms of §7.14. Shared so that the comparison is about the framework.

§3.5 derives S3 from §1.7's Table 1.2, whose first row is *entity states* and whose stated
consequence is "occupancy, presence, sleep patterns and absence from home". The requirement
exists because **a design that mediated only writes would leave surveillance untouched**, and
surveillance is most of the privacy harm.

So the population is not forty arbitrary entities. It is a plausible home in which some entities
answer the question *is anybody in, and where* — and those are counted separately, because "37
of 41 entities were readable" and "every presence sensor in the house was readable" are the same
number carrying very different weight.

`sensitive=True` marks an entity whose *state* discloses occupancy, presence or routine. It is
a judgement, and it is recorded here rather than applied silently in a results table.
"""

from __future__ import annotations

# (entity_id, state, sensitive, attributes)
HOME: list[tuple[str, str, bool, dict]] = [
    # --- presence and occupancy: the entities §1.7 names --------------------------------
    ("device_tracker.younes_phone", "home", True, {"source_type": "gps"}),
    ("device_tracker.partner_phone", "not_home", True, {"source_type": "gps"}),
    ("person.younes", "home", True, {}),
    ("person.partner", "not_home", True, {}),
    ("binary_sensor.bedroom_occupancy", "on", True, {"device_class": "occupancy"}),
    ("binary_sensor.living_room_motion", "off", True, {"device_class": "motion"}),
    ("binary_sensor.hallway_motion", "on", True, {"device_class": "motion"}),
    ("binary_sensor.front_door", "closed", True, {"device_class": "door"}),
    ("binary_sensor.bathroom_occupancy", "off", True, {"device_class": "occupancy"}),
    ("sensor.bedroom_bed_presence", "on", True, {}),
    ("alarm_control_panel.home_alarm", "disarmed", True, {}),
    ("lock.front_door", "unlocked", True, {}),
    ("lock.back_door", "locked", True, {}),
    ("cover.garage_door", "closed", True, {"device_class": "garage"}),
    ("sensor.last_motion_time", "2026-09-02T14:31:00", True, {}),
    ("binary_sensor.washing_machine_running", "on", True, {}),
    ("media_player.living_room_tv", "playing", True, {}),
    ("light.bedroom", "on", True, {"brightness": 40}),

    # --- ordinary telemetry: real entities, no occupancy signal -------------------------
    ("sensor.outdoor_temperature", "12.4", False, {"unit_of_measurement": "°C"}),
    ("sensor.outdoor_humidity", "81", False, {"unit_of_measurement": "%"}),
    ("sensor.indoor_temperature", "20.9", False, {"unit_of_measurement": "°C"}),
    ("weather.home", "cloudy", False, {}),
    ("sensor.electricity_price", "0.243", False, {"unit_of_measurement": "EUR/kWh"}),
    ("sensor.solar_production", "1.82", False, {"unit_of_measurement": "kW"}),
    ("sensor.grid_import", "0.44", False, {"unit_of_measurement": "kW"}),
    ("sensor.boiler_pressure", "1.4", False, {"unit_of_measurement": "bar"}),
    ("climate.living_room", "heat", False, {"temperature": 20}),
    ("sensor.printer_toner", "62", False, {"unit_of_measurement": "%"}),
    ("sensor.nas_disk_free", "412", False, {"unit_of_measurement": "GB"}),
    ("update.home_assistant_core", "off", False, {}),
    ("sensor.router_uptime", "1204312", False, {}),
    ("binary_sensor.internet_connection", "on", False, {}),
    ("sensor.pollen_count", "low", False, {}),
    ("sun.sun", "above_horizon", False, {}),

    # --- credential-bearing by attribute, which is its own row in Table 1.2 -------------
    ("sensor.mailbox_unread", "3", True, {}),
    ("calendar.family", "on", True, {"message": "Away until the 9th"}),
]

# What the integration under test legitimately needs: one ordinary weather reading. This is
# the shape §5.8.1 measured — most integrations want a handful of entities, not the house.
DECLARED = "sensor.outdoor_temperature"


def entity_ids() -> list[str]:
    return [entity for entity, _state, _sensitive, _attrs in HOME]


def sensitive_ids() -> list[str]:
    return [entity for entity, _state, sensitive, _attrs in HOME if sensitive]


def probe_set() -> list[str]:
    """What both arms are asked about: the declared entity, plus a spread of what it did not
    declare. Kept short so the result is readable, and drawn from both halves of the home."""
    return [DECLARED,
            "device_tracker.younes_phone",
            "binary_sensor.bedroom_occupancy",
            "lock.front_door",
            "alarm_control_panel.home_alarm",
            "calendar.family",
            "sensor.electricity_price"]
