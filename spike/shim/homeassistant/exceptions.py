"""Shim of homeassistant.exceptions."""

from __future__ import annotations


class HomeAssistantError(Exception):
    """Base class for HA errors."""


class ConfigEntryError(HomeAssistantError):
    """Error while setting up a config entry."""


class ConfigEntryNotReady(HomeAssistantError):
    """Config entry not ready; HA would retry setup later."""


class ConfigEntryAuthFailed(HomeAssistantError):
    """Credentials rejected; HA would start a reauth flow."""


class PlatformNotReady(HomeAssistantError):
    """Platform not ready."""


class ServiceValidationError(HomeAssistantError):
    """Invalid service call."""


class ServiceNotFound(HomeAssistantError):
    """Unknown service."""

    def __init__(self, domain: str, service: str) -> None:
        super().__init__(f"Service {domain}.{service} not found")
        self.domain = domain
        self.service = service


class InvalidStateError(HomeAssistantError):
    """Invalid state."""


class Unauthorized(HomeAssistantError):
    """Not authorised."""


class IntegrationError(HomeAssistantError):
    """Base for integration errors."""
