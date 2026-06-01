"""AI provider configuration loaded from app settings and environment.

The :class:`AIProviderConfig` dataclass is the single source of truth
for "which provider should the app use right now, and is real network
access allowed". It reads from environment variables and accepts an
optional ``provider_preference`` argument so callers that have already
loaded :class:`scripts.db.settings.AppSettings` can pass
``settings.aiProviderPreference`` directly.

Safety rules:
- API keys live in ``api_keys`` but are excluded from the default
  ``__repr__``. The custom ``__repr__`` further redacts them. Callers
  that need to know whether a key is present should use
  :meth:`has_api_key` or :meth:`safe_dict`, never log the value.
- The factory normalizes any unknown provider name back to the safe
  default (mock) instead of raising. This keeps the app usable even if
  the user types a typo in settings or .env.
- The factory does not open the database. If the caller already has
  loaded settings, they pass them in explicitly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from scripts.ai.schemas import SUPPORTED_PROVIDERS, AIProviderName

DEFAULT_PROVIDER_NAME: AIProviderName = "mock"

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
LOCAL_AI_BASE_URL_ENV = "LOCAL_AI_BASE_URL"
PROVIDER_PREFERENCE_ENV = "AI_PROVIDER_PREFERENCE"


def _env_truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_provider_name(candidate: Any) -> str:
    if not isinstance(candidate, str):
        return DEFAULT_PROVIDER_NAME
    cleaned = candidate.strip().lower()
    if cleaned not in SUPPORTED_PROVIDERS:
        return DEFAULT_PROVIDER_NAME
    return cleaned


@dataclass
class AIProviderConfig:
    """Resolved AI provider configuration.

    Treat ``api_keys`` as secret. Use :meth:`has_api_key` or
    :meth:`safe_dict` for any logging or UI rendering.
    """

    provider_name: str = DEFAULT_PROVIDER_NAME
    integrations_mode: str = "mock"
    enable_real_network_calls: bool = False
    api_keys: dict[str, str] = field(default_factory=dict, repr=False)
    base_urls: dict[str, str] = field(default_factory=dict)
    model_overrides: dict[str, str] = field(default_factory=dict)

    def has_api_key(self, provider: str) -> bool:
        return bool((self.api_keys.get(provider) or "").strip())

    def api_key_for(self, provider: str) -> str:
        """Return the configured API key. Caller must not log this value."""
        return (self.api_keys.get(provider) or "").strip()

    def base_url_for(self, provider: str) -> str:
        return (self.base_urls.get(provider) or "").strip()

    def safe_dict(self) -> dict[str, Any]:
        """Return a dict safe to log or expose to the UI. Excludes raw keys."""
        return {
            "provider_name": self.provider_name,
            "integrations_mode": self.integrations_mode,
            "enable_real_network_calls": self.enable_real_network_calls,
            "api_keys_present": {
                name: bool((value or "").strip()) for name, value in self.api_keys.items()
            },
            "base_urls": dict(self.base_urls),
            "model_overrides": dict(self.model_overrides),
        }

    def __repr__(self) -> str:
        return (
            "AIProviderConfig("
            f"provider_name={self.provider_name!r}, "
            f"integrations_mode={self.integrations_mode!r}, "
            f"enable_real_network_calls={self.enable_real_network_calls}, "
            f"api_keys=<redacted>, "
            f"base_urls={self.base_urls!r}, "
            f"model_overrides={self.model_overrides!r})"
        )

    @classmethod
    def from_environment(
        cls,
        *,
        provider_preference: Optional[str] = None,
        env: Optional[dict[str, str]] = None,
    ) -> "AIProviderConfig":
        """Build a config from the process environment.

        Resolution order for ``provider_name``:

        1. Explicit ``provider_preference`` argument.
        2. ``AI_PROVIDER_PREFERENCE`` environment variable.
        3. The default (``mock``).

        Unknown provider names are normalized to the default.
        """
        environment = env if env is not None else os.environ
        candidate = (
            provider_preference
            or environment.get(PROVIDER_PREFERENCE_ENV)
            or DEFAULT_PROVIDER_NAME
        )
        return cls(
            provider_name=_normalize_provider_name(candidate),
            integrations_mode=(environment.get("INTEGRATIONS_MODE") or "mock").strip().lower(),
            enable_real_network_calls=_env_truthy(environment.get("ENABLE_REAL_NETWORK_CALLS")),
            api_keys={
                "openai": environment.get(OPENAI_API_KEY_ENV, ""),
                "anthropic": environment.get(ANTHROPIC_API_KEY_ENV, ""),
            },
            base_urls={
                "local": (environment.get(LOCAL_AI_BASE_URL_ENV) or "").strip(),
            },
            model_overrides={},
        )
