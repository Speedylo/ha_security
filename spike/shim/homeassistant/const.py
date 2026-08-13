"""GENERATED — do not edit by hand.

Produced by spike/generate_shim.py from Home Assistant 2026.8.1's own const.py.
Regenerate rather than patching: the point of this module is that the constant
tail of the HA API costs a script run, not developer time.
"""

from enum import IntEnum, StrEnum


# The HA release this module was generated from.
__version__ = "2026.8.1"
__short_version__ = "2026.8"


class EntityPlatforms(StrEnum):
    """The platforms an entity can belong to."""

    AI_TASK = 'ai_task'
    AIR_QUALITY = 'air_quality'
    ALARM_CONTROL_PANEL = 'alarm_control_panel'
    ASSIST_SATELLITE = 'assist_satellite'
    BINARY_SENSOR = 'binary_sensor'
    BUTTON = 'button'
    CALENDAR = 'calendar'
    CAMERA = 'camera'
    CLIMATE = 'climate'
    CONVERSATION = 'conversation'
    COVER = 'cover'
    DATE = 'date'
    DATETIME = 'datetime'
    DEVICE_TRACKER = 'device_tracker'
    EVENT = 'event'
    FAN = 'fan'
    GEO_LOCATION = 'geo_location'
    HUMIDIFIER = 'humidifier'
    IMAGE = 'image'
    IMAGE_PROCESSING = 'image_processing'
    INFRARED = 'infrared'
    LAWN_MOWER = 'lawn_mower'
    LIGHT = 'light'
    LOCK = 'lock'
    MEDIA_PLAYER = 'media_player'
    NOTIFY = 'notify'
    NUMBER = 'number'
    RADIO_FREQUENCY = 'radio_frequency'
    REMOTE = 'remote'
    SCENE = 'scene'
    SELECT = 'select'
    SENSOR = 'sensor'
    SIREN = 'siren'
    STT = 'stt'
    SWITCH = 'switch'
    TEXT = 'text'
    TIME = 'time'
    TODO = 'todo'
    TTS = 'tts'
    UPDATE = 'update'
    VACUUM = 'vacuum'
    VALVE = 'valve'
    WAKE_WORD = 'wake_word'
    WATER_HEATER = 'water_heater'
    WEATHER = 'weather'


# Upstream re-exports it under this name; integrations import both.
Platform = EntityPlatforms


class EntityCapabilityAttribute(StrEnum):
    """Capability attributes shared by all entities."""

    GROUP_ENTITIES = 'group_entities'


class EntityStateAttribute(StrEnum):
    """State attributes shared by all entities."""

    ASSUMED_STATE = 'assumed_state'
    ATTRIBUTION = 'attribution'
    DEVICE_CLASS = 'device_class'
    ENTITY_PICTURE = 'entity_picture'
    FRIENDLY_NAME = 'friendly_name'
    ICON = 'icon'
    LATITUDE = 'latitude'
    LONGITUDE = 'longitude'
    RESTORED = 'restored'
    SUPPORTED_FEATURES = 'supported_features'
    UNIT_OF_MEASUREMENT = 'unit_of_measurement'


class UnitOfApparentPower(StrEnum):
    """Apparent power units."""

    MILLIVOLT_AMPERE = 'mVA'
    VOLT_AMPERE = 'VA'
    KILO_VOLT_AMPERE = 'kVA'


class UnitOfPower(StrEnum):
    """Power units."""

    MILLIWATT = 'mW'
    WATT = 'W'
    KILO_WATT = 'kW'
    MEGA_WATT = 'MW'
    GIGA_WATT = 'GW'
    TERA_WATT = 'TW'
    BTU_PER_HOUR = 'BTU/h'


class UnitOfReactivePower(StrEnum):
    """Reactive power units."""

    MILLIVOLT_AMPERE_REACTIVE = 'mvar'
    VOLT_AMPERE_REACTIVE = 'var'
    KILO_VOLT_AMPERE_REACTIVE = 'kvar'


class UnitOfEnergy(StrEnum):
    """Energy units."""

    JOULE = 'J'
    KILO_JOULE = 'kJ'
    MEGA_JOULE = 'MJ'
    GIGA_JOULE = 'GJ'
    MILLIWATT_HOUR = 'mWh'
    WATT_HOUR = 'Wh'
    KILO_WATT_HOUR = 'kWh'
    MEGA_WATT_HOUR = 'MWh'
    GIGA_WATT_HOUR = 'GWh'
    TERA_WATT_HOUR = 'TWh'
    CALORIE = 'cal'
    KILO_CALORIE = 'kcal'
    MEGA_CALORIE = 'Mcal'
    GIGA_CALORIE = 'Gcal'


class UnitOfReactiveEnergy(StrEnum):
    """Reactive energy units."""

    VOLT_AMPERE_REACTIVE_HOUR = 'varh'
    KILO_VOLT_AMPERE_REACTIVE_HOUR = 'kvarh'


class UnitOfEnergyDistance(StrEnum):
    """Energy Distance units."""

    KILO_WATT_HOUR_PER_100_KM = 'kWh/100km'
    WATT_HOUR_PER_KM = 'Wh/km'
    MILES_PER_KILO_WATT_HOUR = 'mi/kWh'
    KM_PER_KILO_WATT_HOUR = 'km/kWh'


class UnitOfElectricCurrent(StrEnum):
    """Electric current units."""

    MICROAMPERE = 'μA'
    MILLIAMPERE = 'mA'
    AMPERE = 'A'


class UnitOfElectricPotential(StrEnum):
    """Electric potential units."""

    MICROVOLT = 'μV'
    MILLIVOLT = 'mV'
    VOLT = 'V'
    KILOVOLT = 'kV'
    MEGAVOLT = 'MV'


class UnitOfTemperature(StrEnum):
    """Temperature units."""

    CELSIUS = '°C'
    FAHRENHEIT = '°F'
    KELVIN = 'K'


class UnitOfTime(StrEnum):
    """Time units."""

    MICROSECONDS = 'μs'
    MILLISECONDS = 'ms'
    SECONDS = 's'
    MINUTES = 'min'
    HOURS = 'h'
    DAYS = 'd'
    WEEKS = 'w'
    MONTHS = 'm'
    YEARS = 'y'


class UnitOfLength(StrEnum):
    """Length units."""

    MILLIMETERS = 'mm'
    CENTIMETERS = 'cm'
    METERS = 'm'
    KILOMETERS = 'km'
    INCHES = 'in'
    FEET = 'ft'
    YARDS = 'yd'
    MILES = 'mi'
    NAUTICAL_MILES = 'nmi'


class UnitOfFrequency(StrEnum):
    """Frequency units."""

    MILLIHERTZ = 'mHz'
    HERTZ = 'Hz'
    KILOHERTZ = 'kHz'
    MEGAHERTZ = 'MHz'
    GIGAHERTZ = 'GHz'


class UnitOfPressure(StrEnum):
    """Pressure units."""

    MILLIPASCAL = 'mPa'
    PA = 'Pa'
    HPA = 'hPa'
    KPA = 'kPa'
    BAR = 'bar'
    CBAR = 'cbar'
    MBAR = 'mbar'
    MMHG = 'mmHg'
    INHG = 'inHg'
    INH2O = 'inH₂O'
    PSI = 'psi'


class UnitOfSoundPressure(StrEnum):
    """Sound pressure units."""

    DECIBEL = 'dB'
    WEIGHTED_DECIBEL_A = 'dBA'


class UnitOfVolume(StrEnum):
    """Volume units."""

    CUBIC_FEET = 'ft³'
    CENTUM_CUBIC_FEET = 'CCF'
    MILLE_CUBIC_FEET = 'MCF'
    CUBIC_METERS = 'm³'
    LITERS = 'L'
    MILLILITERS = 'mL'
    GALLONS = 'gal'
    FLUID_OUNCES = 'fl. oz.'


class UnitOfVolumeFlowRate(StrEnum):
    """Volume flow rate units."""

    CUBIC_METERS_PER_HOUR = 'm³/h'
    CUBIC_METERS_PER_MINUTE = 'm³/min'
    CUBIC_METERS_PER_SECOND = 'm³/s'
    CUBIC_FEET_PER_MINUTE = 'ft³/min'
    LITERS_PER_HOUR = 'L/h'
    LITERS_PER_MINUTE = 'L/min'
    LITERS_PER_SECOND = 'L/s'
    GALLONS_PER_HOUR = 'gal/h'
    GALLONS_PER_MINUTE = 'gal/min'
    GALLONS_PER_DAY = 'gal/d'
    MILLILITERS_PER_SECOND = 'mL/s'


class UnitOfArea(StrEnum):
    """Area units."""

    SQUARE_METERS = 'm²'
    SQUARE_CENTIMETERS = 'cm²'
    SQUARE_KILOMETERS = 'km²'
    SQUARE_MILLIMETERS = 'mm²'
    SQUARE_INCHES = 'in²'
    SQUARE_FEET = 'ft²'
    SQUARE_YARDS = 'yd²'
    SQUARE_MILES = 'mi²'
    ACRES = 'ac'
    HECTARES = 'ha'


class UnitOfMass(StrEnum):
    """Mass units."""

    GRAMS = 'g'
    KILOGRAMS = 'kg'
    MILLIGRAMS = 'mg'
    MICROGRAMS = 'μg'
    OUNCES = 'oz'
    POUNDS = 'lb'
    STONES = 'st'


class UnitOfConductivity(StrEnum):
    """Conductivity units."""

    SIEMENS_PER_CM = 'S/cm'
    MICROSIEMENS_PER_CM = 'μS/cm'
    MILLISIEMENS_PER_CM = 'mS/cm'


class UnitOfIrradiance(StrEnum):
    """Irradiance units."""

    WATTS_PER_SQUARE_METER = 'W/m²'
    BTUS_PER_HOUR_SQUARE_FOOT = 'BTU/(h⋅ft²)'


class UnitOfVolumetricFlux(StrEnum):
    """Volumetric flux, commonly used for precipitation intensity."""

    INCHES_PER_DAY = 'in/d'
    INCHES_PER_HOUR = 'in/h'
    MILLIMETERS_PER_DAY = 'mm/d'
    MILLIMETERS_PER_HOUR = 'mm/h'


class UnitOfPrecipitationDepth(StrEnum):
    """Precipitation depth."""

    INCHES = 'in'
    MILLIMETERS = 'mm'
    CENTIMETERS = 'cm'


class UnitOfDensity(StrEnum):
    """Density units."""

    GRAMS_PER_CUBIC_METER = 'g/m³'
    MILLIGRAMS_PER_CUBIC_METER = 'mg/m³'
    MICROGRAMS_PER_CUBIC_METER = 'μg/m³'
    MICROGRAMS_PER_CUBIC_FOOT = 'μg/ft³'


class UnitOfRatio(StrEnum):
    """Ratio units."""

    PARTS_PER_MILLION = 'ppm'
    PARTS_PER_BILLION = 'ppb'
    PERCENTAGE = '%'


class UnitOfBloodGlucoseConcentration(StrEnum):
    """Blood glucose concentration units."""

    MILLIGRAMS_PER_DECILITER = 'mg/dL'
    MILLIMOLE_PER_LITER = 'mmol/L'


class UnitOfRadiationConcentration(StrEnum):
    """Radiation concentration units."""

    BECQUEREL_PER_CUBIC_METER = 'Bq/m³'
    PICOCURIES_PER_LITER = 'pCi/L'


class UnitOfSpeed(StrEnum):
    """Speed units."""

    BEAUFORT = 'Beaufort'
    FEET_PER_SECOND = 'ft/s'
    INCHES_PER_SECOND = 'in/s'
    METERS_PER_MINUTE = 'm/min'
    METERS_PER_SECOND = 'm/s'
    KILOMETERS_PER_HOUR = 'km/h'
    KNOTS = 'kn'
    MILES_PER_HOUR = 'mph'
    MILLIMETERS_PER_SECOND = 'mm/s'


class UnitOfInformation(StrEnum):
    """Information units."""

    BITS = 'bit'
    KILOBITS = 'kbit'
    MEGABITS = 'Mbit'
    GIGABITS = 'Gbit'
    BYTES = 'B'
    KILOBYTES = 'kB'
    MEGABYTES = 'MB'
    GIGABYTES = 'GB'
    TERABYTES = 'TB'
    PETABYTES = 'PB'
    EXABYTES = 'EB'
    ZETTABYTES = 'ZB'
    YOTTABYTES = 'YB'
    KIBIBYTES = 'KiB'
    MEBIBYTES = 'MiB'
    GIBIBYTES = 'GiB'
    TEBIBYTES = 'TiB'
    PEBIBYTES = 'PiB'
    EXBIBYTES = 'EiB'
    ZEBIBYTES = 'ZiB'
    YOBIBYTES = 'YiB'


class UnitOfDataRate(StrEnum):
    """Data rate units."""

    BITS_PER_SECOND = 'bit/s'
    KILOBITS_PER_SECOND = 'kbit/s'
    MEGABITS_PER_SECOND = 'Mbit/s'
    GIGABITS_PER_SECOND = 'Gbit/s'
    BYTES_PER_SECOND = 'B/s'
    KILOBYTES_PER_SECOND = 'kB/s'
    MEGABYTES_PER_SECOND = 'MB/s'
    GIGABYTES_PER_SECOND = 'GB/s'
    KIBIBYTES_PER_SECOND = 'KiB/s'
    MEBIBYTES_PER_SECOND = 'MiB/s'
    GIBIBYTES_PER_SECOND = 'GiB/s'


class EntityCategory(StrEnum):
    """Category of an entity."""

    CONFIG = 'config'
    DIAGNOSTIC = 'diagnostic'


# ---- module-level constants ----

APPLICATION_NAME = 'HomeAssistant'
MAJOR_VERSION = 2026
MINOR_VERSION = 8
PATCH_VERSION = '1'
REQUIRED_PYTHON_VER = (3, 14, 2)
PLATFORM_FORMAT = '{platform}.{domain}'
MATCH_ALL = '*'
ENTITY_MATCH_NONE = 'none'
ENTITY_MATCH_ALL = 'all'
ENTITY_MATCH_ANY = 'any'
DEVICE_DEFAULT_NAME = 'Unnamed Device'
DEFAULT_RADIUS = 100
MAX_LENGTH_EVENT_EVENT_TYPE = 64
MAX_LENGTH_EVENT_ORIGIN = 32
MAX_LENGTH_EVENT_CONTEXT_ID = 36
MAX_LENGTH_STATE_DOMAIN = 64
MAX_LENGTH_STATE_ENTITY_ID = 255
MAX_LENGTH_STATE_STATE = 255
SUN_EVENT_SUNSET = 'sunset'
SUN_EVENT_SUNRISE = 'sunrise'
CONF_ABOVE = 'above'
CONF_ACCESS_TOKEN = 'access_token'
CONF_ACTION = 'action'
CONF_ACTIONS = 'actions'
CONF_ADDRESS = 'address'
CONF_AFTER = 'after'
CONF_ALIAS = 'alias'
CONF_LLM_HASS_API = 'llm_hass_api'
CONF_ALLOWLIST_EXTERNAL_URLS = 'allowlist_external_urls'
CONF_API_KEY = 'api_key'
CONF_API_TOKEN = 'api_token'
CONF_API_VERSION = 'api_version'
CONF_ARMING_TIME = 'arming_time'
CONF_AT = 'at'
CONF_ATTRIBUTE = 'attribute'
CONF_AUTH_MFA_MODULES = 'auth_mfa_modules'
CONF_AUTH_PROVIDERS = 'auth_providers'
CONF_AUTHENTICATION = 'authentication'
CONF_BASE = 'base'
CONF_BEFORE = 'before'
CONF_BELOW = 'below'
CONF_BINARY_SENSORS = 'binary_sensors'
CONF_BRIGHTNESS = 'brightness'
CONF_BROADCAST_ADDRESS = 'broadcast_address'
CONF_BROADCAST_PORT = 'broadcast_port'
CONF_CHOOSE = 'choose'
CONF_CLIENT_ID = 'client_id'
CONF_CLIENT_SECRET = 'client_secret'
CONF_CODE = 'code'
CONF_COLOR_TEMP = 'color_temp'
CONF_COMMAND = 'command'
CONF_COMMAND_CLOSE = 'command_close'
CONF_COMMAND_OFF = 'command_off'
CONF_COMMAND_ON = 'command_on'
CONF_COMMAND_OPEN = 'command_open'
CONF_COMMAND_STATE = 'command_state'
CONF_COMMAND_STOP = 'command_stop'
CONF_CONDITION = 'condition'
CONF_CONDITIONS = 'conditions'
CONF_CONTINUE_ON_ERROR = 'continue_on_error'
CONF_CONTINUE_ON_TIMEOUT = 'continue_on_timeout'
CONF_COUNT = 'count'
CONF_COUNTRY = 'country'
CONF_COUNTRY_CODE = 'country_code'
CONF_COVERS = 'covers'
CONF_CURRENCY = 'currency'
CONF_CUSTOMIZE = 'customize'
CONF_CUSTOMIZE_DOMAIN = 'customize_domain'
CONF_CUSTOMIZE_GLOB = 'customize_glob'
CONF_DEFAULT = 'default'
CONF_DELAY = 'delay'
CONF_DELAY_TIME = 'delay_time'
CONF_DESCRIPTION = 'description'
CONF_DEVICE = 'device'
CONF_DEVICES = 'devices'
CONF_DEVICE_CLASS = 'device_class'
CONF_DEVICE_ID = 'device_id'
CONF_DISARM_AFTER_TRIGGER = 'disarm_after_trigger'
CONF_DISCOVERY = 'discovery'
CONF_DISKS = 'disks'
CONF_DISPLAY_CURRENCY = 'display_currency'
CONF_DISPLAY_OPTIONS = 'display_options'
CONF_DOMAIN = 'domain'
CONF_DOMAINS = 'domains'
CONF_EFFECT = 'effect'
CONF_ELEVATION = 'elevation'
CONF_ELSE = 'else'
CONF_EMAIL = 'email'
CONF_ENABLED = 'enabled'
CONF_ENTITIES = 'entities'
CONF_ENTITY_CATEGORY = 'entity_category'
CONF_ENTITY_ID = 'entity_id'
CONF_ENTITY_NAMESPACE = 'entity_namespace'
CONF_ENTITY_PICTURE_TEMPLATE = 'entity_picture_template'
CONF_ERROR = 'error'
CONF_EVENT = 'event'
CONF_EVENT_DATA = 'event_data'
CONF_EVENT_DATA_TEMPLATE = 'event_data_template'
CONF_EXCLUDE = 'exclude'
CONF_EXTERNAL_URL = 'external_url'
CONF_FILENAME = 'filename'
CONF_FILE_PATH = 'file_path'
CONF_FOR = 'for'
CONF_FOR_EACH = 'for_each'
CONF_FORCE_UPDATE = 'force_update'
CONF_FRIENDLY_NAME = 'friendly_name'
CONF_FRIENDLY_NAME_TEMPLATE = 'friendly_name_template'
CONF_HEADERS = 'headers'
CONF_HOST = 'host'
CONF_HOSTS = 'hosts'
CONF_HS = 'hs'
CONF_ICON = 'icon'
CONF_ICON_TEMPLATE = 'icon_template'
CONF_ID = 'id'
CONF_IF = 'if'
CONF_INCLUDE = 'include'
CONF_INTERNAL_URL = 'internal_url'
CONF_IP_ADDRESS = 'ip_address'
CONF_LANGUAGE = 'language'
CONF_LATITUDE = 'latitude'
CONF_LEGACY_TEMPLATES = 'legacy_templates'
CONF_LIGHTS = 'lights'
CONF_LOCATION = 'location'
CONF_LONGITUDE = 'longitude'
CONF_MAC = 'mac'
CONF_MATCH = 'match'
CONF_MAXIMUM = 'maximum'
CONF_MEDIA_DIRS = 'media_dirs'
CONF_METHOD = 'method'
CONF_MINIMUM = 'minimum'
CONF_MODE = 'mode'
CONF_MODEL = 'model'
CONF_MODEL_ID = 'model_id'
CONF_MONITORED_CONDITIONS = 'monitored_conditions'
CONF_MONITORED_VARIABLES = 'monitored_variables'
CONF_NAME = 'name'
CONF_NOTE = 'note'
CONF_OFFSET = 'offset'
CONF_OPTIMISTIC = 'optimistic'
CONF_OPTIONS = 'options'
CONF_PACKAGES = 'packages'
CONF_PARALLEL = 'parallel'
CONF_PARAMS = 'params'
CONF_PASSWORD = 'password'
CONF_PATH = 'path'
CONF_PAYLOAD = 'payload'
CONF_PAYLOAD_OFF = 'payload_off'
CONF_PAYLOAD_ON = 'payload_on'
CONF_PENDING_TIME = 'pending_time'
CONF_PIN = 'pin'
CONF_PLATFORM = 'platform'
CONF_PORT = 'port'
CONF_PREFIX = 'prefix'
CONF_PROFILE_NAME = 'profile_name'
CONF_PROMPT = 'prompt'
CONF_PROTOCOL = 'protocol'
CONF_PROXY_SSL = 'proxy_ssl'
CONF_QUOTE = 'quote'
CONF_RADIUS = 'radius'
CONF_RECIPIENT = 'recipient'
CONF_REGION = 'region'
CONF_REPEAT = 'repeat'
CONF_RESOURCE = 'resource'
CONF_RESOURCE_TEMPLATE = 'resource_template'
CONF_RESOURCES = 'resources'
CONF_RESPONSE_VARIABLE = 'response_variable'
CONF_RGB = 'rgb'
CONF_ROOM = 'room'
CONF_SCAN_INTERVAL = 'scan_interval'
CONF_SCENE = 'scene'
CONF_SELECTOR = 'selector'
CONF_SENDER = 'sender'
CONF_SENSORS = 'sensors'
CONF_SENSOR_TYPE = 'sensor_type'
CONF_SEQUENCE = 'sequence'
CONF_SERVICE = 'service'
CONF_SERVICE_DATA = 'data'
CONF_SERVICE_DATA_TEMPLATE = 'data_template'
CONF_SERVICE_TEMPLATE = 'service_template'
CONF_SET_CONVERSATION_RESPONSE = 'set_conversation_response'
CONF_SHOW_ON_MAP = 'show_on_map'
CONF_SLAVE = 'slave'
CONF_SOURCE = 'source'
CONF_SSL = 'ssl'
CONF_STATE = 'state'
CONF_STATE_TEMPLATE = 'state_template'
CONF_STOP = 'stop'
CONF_STRUCTURE = 'structure'
CONF_SWITCHES = 'switches'
CONF_TARGET = 'target'
CONF_TEMPERATURE_UNIT = 'temperature_unit'
CONF_THEN = 'then'
CONF_TIMEOUT = 'timeout'
CONF_TIME_ZONE = 'time_zone'
CONF_TOKEN = 'token'
CONF_TRIGGER = 'trigger'
CONF_TRIGGERS = 'triggers'
CONF_TRIGGER_TIME = 'trigger_time'
CONF_TTL = 'ttl'
CONF_TYPE = 'type'
CONF_UNIQUE_ID = 'unique_id'
CONF_UNIT_OF_MEASUREMENT = 'unit_of_measurement'
CONF_UNIT_SYSTEM = 'unit_system'
CONF_UNTIL = 'until'
CONF_URL = 'url'
CONF_USERNAME = 'username'
CONF_UUID = 'uuid'
CONF_VALUE_TEMPLATE = 'value_template'
CONF_VARIABLES = 'variables'
CONF_VERIFY_SSL = 'verify_ssl'
CONF_WAIT_FOR_TRIGGER = 'wait_for_trigger'
CONF_WAIT_TEMPLATE = 'wait_template'
CONF_WEBHOOK_ID = 'webhook_id'
CONF_WEEKDAY = 'weekday'
CONF_WHILE = 'while'
CONF_WHITELIST = 'whitelist'
CONF_ALLOWLIST_EXTERNAL_DIRS = 'allowlist_external_dirs'
LEGACY_CONF_WHITELIST_EXTERNAL_DIRS = 'whitelist_external_dirs'
CONF_DEBUG = 'debug'
CONF_XY = 'xy'
CONF_ZONE = 'zone'
EVENT_CALL_SERVICE = 'call_service'
EVENT_COMPONENT_LOADED = 'component_loaded'
EVENT_CORE_CONFIG_UPDATE = 'core_config_updated'
EVENT_HOMEASSISTANT_CLOSE = 'homeassistant_close'
EVENT_HOMEASSISTANT_START = 'homeassistant_start'
EVENT_HOMEASSISTANT_STARTED = 'homeassistant_started'
EVENT_HOMEASSISTANT_STOP = 'homeassistant_stop'
EVENT_HOMEASSISTANT_FINAL_WRITE = 'homeassistant_final_write'
EVENT_LABS_UPDATED = 'labs_updated'
EVENT_LOGBOOK_ENTRY = 'logbook_entry'
EVENT_LOGGING_CHANGED = 'logging_changed'
EVENT_SERVICE_REGISTERED = 'service_registered'
EVENT_SERVICE_REMOVED = 'service_removed'
EVENT_STATE_CHANGED = 'state_changed'
EVENT_STATE_REPORTED = 'state_reported'
EVENT_THEMES_UPDATED = 'themes_updated'
EVENT_PANELS_UPDATED = 'panels_updated'
EVENT_LOVELACE_UPDATED = 'lovelace_updated'
EVENT_RECORDER_5MIN_STATISTICS_GENERATED = 'recorder_5min_statistics_generated'
EVENT_RECORDER_HOURLY_STATISTICS_GENERATED = 'recorder_hourly_statistics_generated'
EVENT_SHOPPING_LIST_UPDATED = 'shopping_list_updated'
STATE_ON = 'on'
STATE_OFF = 'off'
STATE_HOME = 'home'
STATE_NOT_HOME = 'not_home'
STATE_UNKNOWN = 'unknown'
STATE_OPEN = 'open'
STATE_OPENING = 'opening'
STATE_CLOSED = 'closed'
STATE_CLOSING = 'closing'
STATE_BUFFERING = 'buffering'
STATE_PLAYING = 'playing'
STATE_PAUSED = 'paused'
STATE_IDLE = 'idle'
STATE_STANDBY = 'standby'
STATE_UNAVAILABLE = 'unavailable'
STATE_OK = 'ok'
STATE_PROBLEM = 'problem'
ATTR_ATTRIBUTION = 'attribution'
ATTR_CREDENTIALS = 'credentials'
ATTR_NOW = 'now'
ATTR_DATE = 'date'
ATTR_TIME = 'time'
ATTR_SECONDS = 'seconds'
ATTR_DOMAIN = 'domain'
ATTR_SERVICE = 'service'
ATTR_SERVICE_DATA = 'service_data'
ATTR_ID = 'id'
ATTR_NAME = 'name'
ATTR_ENTITY_ID = 'entity_id'
ATTR_GROUP_ENTITIES = 'group_entities'
ATTR_CONFIG_ENTRY_ID = 'config_entry_id'
ATTR_AREA_ID = 'area_id'
ATTR_DEVICE_ID = 'device_id'
ATTR_FLOOR_ID = 'floor_id'
ATTR_LABEL_ID = 'label_id'
ATTR_FRIENDLY_NAME = 'friendly_name'
ATTR_ENTITY_PICTURE = 'entity_picture'
ATTR_IDENTIFIERS = 'identifiers'
ATTR_ICON = 'icon'
ATTR_UNIT_OF_MEASUREMENT = 'unit_of_measurement'
CONF_UNIT_SYSTEM_METRIC = 'metric'
CONF_UNIT_SYSTEM_IMPERIAL = 'imperial'
ATTR_VOLTAGE = 'voltage'
ATTR_LOCATION = 'location'
ATTR_MODE = 'mode'
ATTR_CONFIGURATION_URL = 'configuration_url'
ATTR_CONNECTIONS = 'connections'
ATTR_DEFAULT_NAME = 'default_name'
ATTR_MANUFACTURER = 'manufacturer'
ATTR_MODEL = 'model'
ATTR_MODEL_ID = 'model_id'
ATTR_SERIAL_NUMBER = 'serial_number'
ATTR_SUGGESTED_AREA = 'suggested_area'
ATTR_SW_VERSION = 'sw_version'
ATTR_HW_VERSION = 'hw_version'
ATTR_VIA_DEVICE = 'via_device'
ATTR_BATTERY_CHARGING = 'battery_charging'
ATTR_BATTERY_LEVEL = 'battery_level'
ATTR_WAKEUP = 'wake_up_interval'
ATTR_CODE = 'code'
ATTR_CODE_FORMAT = 'code_format'
ATTR_COMMAND = 'command'
ATTR_ARMED = 'device_armed'
ATTR_LOCKED = 'locked'
ATTR_TRIPPED = 'device_tripped'
ATTR_LAST_TRIP_TIME = 'last_tripped_time'
ATTR_HIDDEN = 'hidden'
ATTR_LATITUDE = 'latitude'
ATTR_LONGITUDE = 'longitude'
ATTR_ELEVATION = 'elevation'
ATTR_GPS_ACCURACY = 'gps_accuracy'
ATTR_ASSUMED_STATE = 'assumed_state'
ATTR_STATE = 'state'
ATTR_EDITABLE = 'editable'
ATTR_OPTION = 'option'
ATTR_RESTORED = 'restored'
ATTR_SUPPORTED_FEATURES = 'supported_features'
ATTR_DEVICE_CLASS = 'device_class'
ATTR_TEMPERATURE = 'temperature'
ATTR_PERSONS = 'persons'
DEGREE = '°'
CURRENCY_EURO = '€'
CURRENCY_DOLLAR = '$'
CURRENCY_CENT = '¢'
LIGHT_LUX = 'lx'
UV_INDEX = 'UV index'
REVOLUTIONS_PER_MINUTE = 'rpm'
CONCENTRATION_GRAMS_PER_CUBIC_METER = 'g/m³'
CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER = 'mg/m³'
CONCENTRATION_MICROGRAMS_PER_CUBIC_METER = 'μg/m³'
CONCENTRATION_MICROGRAMS_PER_CUBIC_FOOT = 'μg/ft³'
CONCENTRATION_PARTS_PER_CUBIC_METER = 'p/m³'
CONCENTRATION_PARTS_PER_MILLION = 'ppm'
CONCENTRATION_PARTS_PER_BILLION = 'ppb'
PERCENTAGE = '%'
SIGNAL_STRENGTH_DECIBELS = 'dB'
SIGNAL_STRENGTH_DECIBELS_MILLIWATT = 'dBm'
COMPRESSED_STATE_STATE = 's'
COMPRESSED_STATE_ATTRIBUTES = 'a'
COMPRESSED_STATE_CONTEXT = 'c'
COMPRESSED_STATE_LAST_CHANGED = 'lc'
COMPRESSED_STATE_LAST_UPDATED = 'lu'
SERVICE_TURN_ON = 'turn_on'
SERVICE_TURN_OFF = 'turn_off'
SERVICE_TOGGLE = 'toggle'
SERVICE_RELOAD = 'reload'
SERVICE_VOLUME_UP = 'volume_up'
SERVICE_VOLUME_DOWN = 'volume_down'
SERVICE_VOLUME_MUTE = 'volume_mute'
SERVICE_VOLUME_SET = 'volume_set'
SERVICE_MEDIA_PLAY_PAUSE = 'media_play_pause'
SERVICE_MEDIA_PLAY = 'media_play'
SERVICE_MEDIA_PAUSE = 'media_pause'
SERVICE_MEDIA_STOP = 'media_stop'
SERVICE_MEDIA_NEXT_TRACK = 'media_next_track'
SERVICE_MEDIA_PREVIOUS_TRACK = 'media_previous_track'
SERVICE_MEDIA_SEEK = 'media_seek'
SERVICE_REPEAT_SET = 'repeat_set'
SERVICE_SHUFFLE_SET = 'shuffle_set'
SERVICE_ALARM_DISARM = 'alarm_disarm'
SERVICE_ALARM_ARM_HOME = 'alarm_arm_home'
SERVICE_ALARM_ARM_AWAY = 'alarm_arm_away'
SERVICE_ALARM_ARM_NIGHT = 'alarm_arm_night'
SERVICE_ALARM_ARM_VACATION = 'alarm_arm_vacation'
SERVICE_ALARM_ARM_CUSTOM_BYPASS = 'alarm_arm_custom_bypass'
SERVICE_ALARM_TRIGGER = 'alarm_trigger'
SERVICE_LOCK = 'lock'
SERVICE_UNLOCK = 'unlock'
SERVICE_OPEN = 'open'
SERVICE_CLOSE = 'close'
SERVICE_CLOSE_COVER = 'close_cover'
SERVICE_CLOSE_COVER_TILT = 'close_cover_tilt'
SERVICE_OPEN_COVER = 'open_cover'
SERVICE_OPEN_COVER_TILT = 'open_cover_tilt'
SERVICE_SAVE_PERSISTENT_STATES = 'save_persistent_states'
SERVICE_SET_COVER_POSITION = 'set_cover_position'
SERVICE_SET_COVER_TILT_POSITION = 'set_cover_tilt_position'
SERVICE_STOP_COVER = 'stop_cover'
SERVICE_STOP_COVER_TILT = 'stop_cover_tilt'
SERVICE_TOGGLE_COVER_TILT = 'toggle_cover_tilt'
SERVICE_CLOSE_VALVE = 'close_valve'
SERVICE_OPEN_VALVE = 'open_valve'
SERVICE_SET_VALVE_POSITION = 'set_valve_position'
SERVICE_STOP_VALVE = 'stop_valve'
SERVICE_SELECT_OPTION = 'select_option'
SERVER_PORT = 8123
URL_ROOT = '/'
URL_API = '/api/'
URL_API_STREAM = '/api/stream'
URL_API_CORE_STATE = '/api/core/state'
URL_API_CONFIG = '/api/config'
URL_API_STATES = '/api/states'
URL_API_STATES_ENTITY = '/api/states/{}'
URL_API_EVENTS = '/api/events'
URL_API_EVENTS_EVENT = '/api/events/{}'
URL_API_SERVICES = '/api/services'
URL_API_SERVICES_SERVICE = '/api/services/{}/{}'
URL_API_COMPONENTS = '/api/components'
URL_API_ERROR_LOG = '/api/error_log'
URL_API_LOG_OUT = '/api/log_out'
URL_API_TEMPLATE = '/api/template'
HTTP_BASIC_AUTHENTICATION = 'basic'
HTTP_BEARER_AUTHENTICATION = 'bearer_token'
HTTP_DIGEST_AUTHENTICATION = 'digest'
HTTP_HEADER_X_REQUESTED_WITH = 'X-Requested-With'
CONTENT_TYPE_JSON = 'application/json'
CONTENT_TYPE_MULTIPART = 'multipart/x-mixed-replace; boundary={}'
CONTENT_TYPE_TEXT_PLAIN = 'text/plain'
RESTART_EXIT_CODE = 100
UNIT_NOT_RECOGNIZED_TEMPLATE = '{} is not a recognized {} unit.'
LENGTH = 'length'
AREA = 'area'
MASS = 'mass'
PRESSURE = 'pressure'
VOLUME = 'volume'
TEMPERATURE = 'temperature'
SPEED = 'speed'
WIND_SPEED = 'wind_speed'
ILLUMINANCE = 'illuminance'
ACCUMULATED_PRECIPITATION = 'accumulated_precipitation'
WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
PRECISION_WHOLE = 1
PRECISION_HALVES = 0.5
PRECISION_TENTHS = 0.1
CAST_APP_ID_HOMEASSISTANT_MEDIA = 'B45F4572'
CAST_APP_ID_HOMEASSISTANT_LOVELACE = 'A078F6B0'
HASSIO_USER_NAME = 'Supervisor'
SIGNAL_BOOTSTRAP_INTEGRATIONS = 'bootstrap_integrations'
KEY_DATA_LOGGING = 'logging'
KEY_DATA_LOGGING_DISABLED_REASON = 'logging_disabled_reason'
FORMAT_DATE = '%Y-%m-%d'
FORMAT_TIME = '%H:%M:%S'
MAX_EXPECTED_ENTITY_IDS = 16384


# ---- carried over from the previous module ----
# Defined by the shim but absent from the pinned HA source, usually
# because upstream moved them elsewhere. Copied verbatim so that
# regenerating cannot remove a name some integration imports.

STATE_LOCKED = "locked"

STATE_UNLOCKED = "unlocked"
