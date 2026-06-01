"""Provider registry.

``get_provider`` returns a provider instance by name. ``mock`` is the
default. ``list_available_providers`` returns a small DTO list intended
for the Settings UI: it includes each provider's id, label, network
requirement, current availability, and the reason it is unavailable
(when applicable).
"""

from __future__ import annotations

from typing import Any

from scripts.ai.config import AIProviderConfig
from scripts.ai.providers.anthropic import AnthropicProvider
from scripts.ai.providers.base import AIProvider, ProviderConfigurationError
from scripts.ai.providers.local import LocalProvider
from scripts.ai.providers.mock import MockProvider
from scripts.ai.providers.openai import OpenAIProvider

DEFAULT_PROVIDER_NAME = "mock"

_PROVIDER_CLASSES: dict[str, type[AIProvider]] = {
    "mock": MockProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "local": LocalProvider,
}


def get_provider(name: str | None = None) -> AIProvider:
    """Instantiate a provider by name. Defaults to the mock provider."""
    chosen = (name or DEFAULT_PROVIDER_NAME).strip().lower()
    if chosen not in _PROVIDER_CLASSES:
        raise ProviderConfigurationError(
            f"Unknown AI provider: {chosen!r}. "
            f"Known providers: {sorted(_PROVIDER_CLASSES)}."
        )
    return _PROVIDER_CLASSES[chosen]()


def list_available_providers() -> list[dict[str, Any]]:
    """Return availability metadata for each known provider."""
    return [_PROVIDER_CLASSES[name]().availability() for name in _PROVIDER_CLASSES]


def provider_from_config(config: AIProviderConfig) -> AIProvider:
    """Instantiate the provider named by an :class:`AIProviderConfig`.

    The factory always resolves to a known provider because the config
    normalizes unknown names to ``mock``.
    """
    return get_provider(config.provider_name)
