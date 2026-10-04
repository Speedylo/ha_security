"""Constants for the confined-integration bridge."""

DOMAIN = "confine_bridge"

#: The roster of everything published, persisted so entities come back after a restart without
#: waiting for their sandbox to run again.
STORAGE_KEY = f"{DOMAIN}.entities"
STORAGE_VERSION = 1

#: Dispatched when a definition arrives for an entity this platform has not built yet.
SIGNAL_NEW_ENTITY = f"{DOMAIN}_new_entity_{{}}"

#: The entity domains the bridge can stand in for. Others are refused, not approximated.
SUPPORTED = ("sensor", "binary_sensor")
