"""Provider interface and shared scaffolding for real provider stubs."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Optional

from scripts.ai.schemas import (
    AIStructuredGenerationRequest,
    AIStructuredGenerationResponse,
    AITextGenerationRequest,
    AITextGenerationResponse,
    ContentGenerationInput,
    ContentGenerationOptions,
    GeneratedContentBundle,
)


class AIProviderError(RuntimeError):
    """Base class for all AI provider errors.

    Catch this in calling code when you want to handle every AI failure
    in one place (for example, to fall back to the mock provider or to
    show a friendly UI message).
    """


class ProviderDisabledError(AIProviderError):
    """A provider cannot run because safety gates or configuration are missing."""


class ProviderConfigurationError(AIProviderError):
    """A provider is configured incorrectly (for example, unknown name)."""


def _env_truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


class AIProvider(ABC):
    """Abstract base for all AI providers.

    Every provider must implement three operations:

    * ``generate_text`` — a free-form text response.
    * ``generate_structured`` — a JSON-like dict response.
    * ``generate_bundle`` — the content-generation bundle used by the
      content generation service. A later batch may refactor this to
      build on top of ``generate_structured`` internally.

    Providers must never read API keys directly from logs, never expose
    raw vendor responses to the UI, and never call the network in mock
    mode.
    """

    name: str = ""
    label: str = ""
    requires_network: bool = False

    @abstractmethod
    def generate_text(self, request: AITextGenerationRequest) -> AITextGenerationResponse:
        """Return a free-form text response."""

    @abstractmethod
    def generate_structured(
        self,
        request: AIStructuredGenerationRequest,
    ) -> AIStructuredGenerationResponse:
        """Return a structured (dict) response under a named schema."""

    @abstractmethod
    def generate_bundle(
        self,
        input: ContentGenerationInput,
        options: ContentGenerationOptions,
    ) -> GeneratedContentBundle:
        """Return a complete content-generation bundle."""

    def availability(self) -> dict[str, Any]:
        """Return a small DTO describing whether the provider is usable right now."""
        return {
            "id": self.name,
            "label": self.label,
            "requiresNetwork": self.requires_network,
            "available": True,
            "reason": None,
        }


class RealProviderStub(AIProvider):
    """Shared scaffold for real provider adapters.

    The constructor reads safety gates from the environment but does not
    raise. Every ``generate_*`` method raises ``ProviderDisabledError``
    in Batch 3, either because the gates are off or because the real
    adapter is intentionally not implemented yet. Constructors never
    raise so that the Settings UI can list every provider with a
    reason for unavailability.
    """

    requires_network = True
    api_key_env: str = ""
    api_key_required: bool = True
    not_implemented_message: str = (
        "real adapter is scaffolded but not yet implemented. "
        "Batch 3 keeps real provider calls off by policy."
    )

    def __init__(self) -> None:
        self._integrations_mode = (os.environ.get("INTEGRATIONS_MODE") or "mock").strip().lower()
        self._real_network_enabled = _env_truthy(os.environ.get("ENABLE_REAL_NETWORK_CALLS"))
        self._api_key = (os.environ.get(self.api_key_env) or "").strip() if self.api_key_env else ""

    def _disabled_reason(self) -> Optional[str]:
        if self._integrations_mode == "mock":
            return (
                "INTEGRATIONS_MODE=mock keeps real providers disabled. "
                "Set INTEGRATIONS_MODE to a non-mock value to opt in."
            )
        if not self._real_network_enabled:
            return (
                "ENABLE_REAL_NETWORK_CALLS=false keeps real providers disabled. "
                "Set ENABLE_REAL_NETWORK_CALLS=true to opt in."
            )
        if self.api_key_required and not self._api_key:
            return (
                f"{self.api_key_env or 'API key'} is empty. "
                "Add a key in your local .env before enabling this provider."
            )
        return None

    def _raise_disabled(self) -> None:
        reason = self._disabled_reason()
        label = self.label or self.name or "provider"
        if reason:
            raise ProviderDisabledError(f"{label} is disabled: {reason}")
        raise ProviderDisabledError(f"{label}: {self.not_implemented_message}")

    def availability(self) -> dict[str, Any]:
        reason = self._disabled_reason() or self.not_implemented_message
        return {
            "id": self.name,
            "label": self.label,
            "requiresNetwork": True,
            "available": False,
            "reason": reason,
        }

    def generate_text(self, request: AITextGenerationRequest) -> AITextGenerationResponse:
        self._raise_disabled()

    def generate_structured(
        self,
        request: AIStructuredGenerationRequest,
    ) -> AIStructuredGenerationResponse:
        self._raise_disabled()

    def generate_bundle(
        self,
        input: ContentGenerationInput,
        options: ContentGenerationOptions,
    ) -> GeneratedContentBundle:
        self._raise_disabled()
