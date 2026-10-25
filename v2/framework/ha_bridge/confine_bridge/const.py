"""Constants for the confined-integration bridge."""

DOMAIN = "confine_bridge"

#: The roster of everything published, persisted so entities come back after a restart without
#: waiting for their sandbox to run again.
STORAGE_KEY = f"{DOMAIN}.entities"
STORAGE_VERSION = 1

#: Dispatched when a definition arrives for an entity this platform has not built yet.
SIGNAL_NEW_ENTITY = f"{DOMAIN}_new_entity_{{}}"

#: The entity domains the bridge can stand in for. Others are refused, not approximated.
SUPPORTED = ("sensor", "binary_sensor", "switch", "button", "text", "select", "number")

#: How long a user's command waits for the confined integration to answer (W1 step 2b).
COMMAND_TIMEOUT = 10

#: Commands waiting for an answer, at most. Past this a command is refused, not queued.
MAX_PENDING_COMMANDS = 32

#: The Repairs issue raised when the mediator cuts an integration off (the refusal flood).
ISSUE_CUT_OFF = "cut_off_{}"

#: The Repairs issue raised when the supervisor does not start an integration (F57c). Its
#: translation key is the reason: `not_approved`, or `too_much_data` (F59).
ISSUE_NOT_STARTED = "not_started_{}"
NOT_STARTED_REASONS = ("not_approved", "too_much_data")
