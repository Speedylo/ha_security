"""Constants for the sandboxed-integration bridge."""

DOMAIN = "sandbox_bridge"

# Where the entity roster is persisted, so entities come back after a restart
# instead of vanishing with the supervisor's process.
STORAGE_KEY = f"{DOMAIN}.entities"
STORAGE_VERSION = 1

# Dispatched when the supervisor publishes an entity this platform has not seen.
SIGNAL_NEW_ENTITY = f"{DOMAIN}_new_entity"

SERVICE_PUBLISH = "publish"
SERVICE_REMOVE = "remove"

ATTR_INTEGRATION = "integration"
ATTR_KEY = "key"
ATTR_ENTITY_ID = "entity_id"
ATTR_STATE = "state"
ATTR_ATTRIBUTES = "attributes"
