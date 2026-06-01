from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_META_GRAPH_API_VERSION = "v20.0"


@dataclass(frozen=True)
class MetaConfig:
    clientId: str | None
    clientSecret: str | None
    redirectUri: str | None
    graphApiVersion: str
    realOAuthEnabled: bool
    realPublishingEnabled: bool
    integrationsMode: str
    clientIdConfigured: bool
    clientSecretConfigured: bool
    redirectUriConfigured: bool
    missingConfigKeys: tuple[str, ...]

    @property
    def realOAuthReady(self) -> bool:
        return (
            self.realOAuthEnabled
            and self.clientIdConfigured
            and self.clientSecretConfigured
            and self.redirectUriConfigured
        )


def load_meta_config(env: dict[str, str] | None = None) -> MetaConfig:
    values = env if env is not None else os.environ
    client_id = _blank_to_none(values.get("META_CLIENT_ID"))
    client_secret = _blank_to_none(values.get("META_CLIENT_SECRET"))
    redirect_uri = _blank_to_none(values.get("META_REDIRECT_URI"))
    graph_version = _blank_to_none(values.get("META_GRAPH_API_VERSION")) or DEFAULT_META_GRAPH_API_VERSION
    real_oauth = _bool_env(values.get("META_ENABLE_REAL_OAUTH"), default=False)
    real_publishing = _bool_env(values.get("META_ENABLE_REAL_PUBLISHING"), default=False)
    integrations_mode = (_blank_to_none(values.get("INTEGRATIONS_MODE")) or "mock").strip().lower()

    missing = []
    if not client_id:
        missing.append("META_CLIENT_ID")
    if not client_secret:
        missing.append("META_CLIENT_SECRET")
    if not redirect_uri:
        missing.append("META_REDIRECT_URI")

    return MetaConfig(
        clientId=client_id,
        clientSecret=client_secret,
        redirectUri=redirect_uri,
        graphApiVersion=graph_version,
        realOAuthEnabled=real_oauth,
        realPublishingEnabled=real_publishing,
        integrationsMode=integrations_mode,
        clientIdConfigured=bool(client_id),
        clientSecretConfigured=bool(client_secret),
        redirectUriConfigured=bool(redirect_uri),
        missingConfigKeys=tuple(missing),
    )


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _bool_env(value: str | None, *, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
