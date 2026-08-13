"""Shim of homeassistant.const.

Hand-written for the spike. In the real deliverable this file is *generated*
from HA's own source: it is pure data (enums, unit strings, config keys) and it
accounts for a large share of the long tail measured in surface_out/symbols.csv.
Generating it is what collapses the tail from ~83 symbols to a tractable number.
"""

from __future__ import annotations

from enum import StrEnum

# Version the integration sees. Must satisfy MIN_HA_VERSION checks in the wild.
__version__ = "2026.8.0"
MAJOR_VERSION = 2026
MINOR_VERSION = 8
PATCH_VERSION = "0"
REQUIRED_PYTHON_VER = (3, 12, 0)


class Platform(StrEnum):
    """Entity platforms an integration can forward setup to."""

    AIR_QUALITY = "air_quality"
    ALARM_CONTROL_PANEL = "alarm_control_panel"
    BINARY_SENSOR = "binary_sensor"
    BUTTON = "button"
    CALENDAR = "calendar"
    CAMERA = "camera"
    CLIMATE = "climate"
    COVER = "cover"
    DEVICE_TRACKER = "device_tracker"
    FAN = "fan"
    HUMIDIFIER = "humidifier"
    IMAGE = "image"
    LIGHT = "light"
    LOCK = "lock"
    MEDIA_PLAYER = "media_player"
    NOTIFY = "notify"
    NUMBER = "number"
    SCENE = "scene"
    SELECT = "select"
    SENSOR = "sensor"
    SIREN = "siren"
    SWITCH = "switch"
    TEXT = "text"
    TIME = "time"
    TODO = "todo"
    UPDATE = "update"
    VACUUM = "vacuum"
    WATER_HEATER = "water_heater"
    WEATHER = "weather"


class EntityCategory(StrEnum):
    """Classification of an entity's role."""

    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"


class UnitOfInformation(StrEnum):
    BITS = "bit"
    KILOBITS = "kbit"
    MEGABITS = "Mbit"
    GIGABITS = "Gbit"
    BYTES = "B"
    KILOBYTES = "kB"
    MEGABYTES = "MB"
    GIGABYTES = "GB"
    TERABYTES = "TB"
    PETABYTES = "PB"
    KIBIBYTES = "KiB"
    MEBIBYTES = "MiB"
    GIBIBYTES = "GiB"
    TEBIBYTES = "TiB"


class UnitOfTemperature(StrEnum):
    CELSIUS = "°C"
    FAHRENHEIT = "°F"
    KELVIN = "K"


class UnitOfTime(StrEnum):
    MICROSECONDS = "μs"
    MILLISECONDS = "ms"
    SECONDS = "s"
    MINUTES = "min"
    HOURS = "h"
    DAYS = "d"
    WEEKS = "w"
    MONTHS = "m"
    YEARS = "y"


class UnitOfPower(StrEnum):
    WATT = "W"
    KILO_WATT = "kW"
    MEGA_WATT = "MW"


class UnitOfEnergy(StrEnum):
    WATT_HOUR = "Wh"
    KILO_WATT_HOUR = "kWh"
    MEGA_WATT_HOUR = "MWh"


class UnitOfDataRate(StrEnum):
    BITS_PER_SECOND = "bit/s"
    KILOBITS_PER_SECOND = "kbit/s"
    MEGABITS_PER_SECOND = "Mbit/s"
    GIGABITS_PER_SECOND = "Gbit/s"
    BYTES_PER_SECOND = "B/s"
    KILOBYTES_PER_SECOND = "kB/s"
    MEGABYTES_PER_SECOND = "MB/s"


class UnitOfElectricPotential(StrEnum):
    MILLIVOLT = "mV"
    VOLT = "V"


class UnitOfElectricCurrent(StrEnum):
    MILLIAMPERE = "mA"
    AMPERE = "A"


class UnitOfLength(StrEnum):
    MILLIMETERS = "mm"
    CENTIMETERS = "cm"
    METERS = "m"
    KILOMETERS = "km"
    INCHES = "in"
    FEET = "ft"
    MILES = "mi"


class UnitOfDensity(StrEnum):
    GRAMS_PER_CUBIC_METER = "g/m³"
    MILLIGRAMS_PER_CUBIC_METER = "mg/m³"
    MICROGRAMS_PER_CUBIC_METER = "μg/m³"
    MICROGRAMS_PER_CUBIC_FOOT = "μg/ft³"


# Concentration units. Upstream now routes these through UnitOfDensity and marks
# the flat names deprecated, but they remain importable and air-quality
# integrations still use them, so both spellings resolve to the same string.
CONCENTRATION_GRAMS_PER_CUBIC_METER = UnitOfDensity.GRAMS_PER_CUBIC_METER.value
CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER = UnitOfDensity.MILLIGRAMS_PER_CUBIC_METER.value
CONCENTRATION_MICROGRAMS_PER_CUBIC_METER = UnitOfDensity.MICROGRAMS_PER_CUBIC_METER.value
CONCENTRATION_MICROGRAMS_PER_CUBIC_FOOT = UnitOfDensity.MICROGRAMS_PER_CUBIC_FOOT.value
CONCENTRATION_PARTS_PER_CUBIC_METER = "p/m³"
CONCENTRATION_PARTS_PER_MILLION = "ppm"
CONCENTRATION_PARTS_PER_BILLION = "ppb"


class UnitOfPressure(StrEnum):
    PA = "Pa"
    HPA = "hPa"
    KPA = "kPa"
    BAR = "bar"
    MBAR = "mbar"
    PSI = "psi"


PERCENTAGE = "%"
DEGREE = "°"
CURRENCY_EURO = "€"
CURRENCY_DOLLAR = "$"

# Configuration keys
CONF_ACCESS_TOKEN = "access_token"
CONF_API_KEY = "api_key"
CONF_API_TOKEN = "api_token"
CONF_AUTHENTICATION = "authentication"
CONF_BASE = "base"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_DEVICE = "device"
CONF_DEVICE_ID = "device_id"
CONF_DOMAIN = "domain"
CONF_EMAIL = "email"
CONF_ENTITY_ID = "entity_id"
CONF_HOST = "host"
CONF_ICON = "icon"
CONF_ID = "id"
CONF_IP_ADDRESS = "ip_address"
CONF_MAC = "mac"
CONF_MODE = "mode"
CONF_MONITORED_CONDITIONS = "monitored_conditions"
CONF_NAME = "name"
CONF_PASSWORD = "password"
CONF_PATH = "path"
CONF_PIN = "pin"
CONF_PORT = "port"
CONF_PREFIX = "prefix"
CONF_REGION = "region"
CONF_RESOURCE = "resource"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SENSORS = "sensors"
CONF_SSL = "ssl"
CONF_TIMEOUT = "timeout"
CONF_TOKEN = "token"
CONF_TYPE = "type"
CONF_UNIQUE_ID = "unique_id"
CONF_UNIT_OF_MEASUREMENT = "unit_of_measurement"
CONF_URL = "url"
CONF_USERNAME = "username"
CONF_VALUE_TEMPLATE = "value_template"
CONF_VERIFY_SSL = "verify_ssl"

# States
STATE_ON = "on"
STATE_OFF = "off"
STATE_HOME = "home"
STATE_NOT_HOME = "not_home"
STATE_UNKNOWN = "unknown"
STATE_UNAVAILABLE = "unavailable"
STATE_OPEN = "open"
STATE_OPENING = "opening"
STATE_CLOSED = "closed"
STATE_CLOSING = "closing"
STATE_LOCKED = "locked"
STATE_UNLOCKED = "unlocked"
STATE_IDLE = "idle"
STATE_PAUSED = "paused"
STATE_PLAYING = "playing"

# Attributes
ATTR_ATTRIBUTION = "attribution"
ATTR_DEVICE_CLASS = "device_class"
ATTR_ENTITY_ID = "entity_id"
ATTR_FRIENDLY_NAME = "friendly_name"
ATTR_ICON = "icon"
ATTR_NAME = "name"
ATTR_STATE = "state"
ATTR_SW_VERSION = "sw_version"
ATTR_UNIT_OF_MEASUREMENT = "unit_of_measurement"

# Events
EVENT_HOMEASSISTANT_START = "homeassistant_start"
EVENT_HOMEASSISTANT_STARTED = "homeassistant_started"
EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"
EVENT_STATE_CHANGED = "state_changed"
EVENT_CALL_SERVICE = "call_service"

# Services
SERVICE_TURN_ON = "turn_on"
SERVICE_TURN_OFF = "turn_off"
SERVICE_TOGGLE = "toggle"
SERVICE_RELOAD = "reload"
SERVICE_LOCK = "lock"
SERVICE_UNLOCK = "unlock"
