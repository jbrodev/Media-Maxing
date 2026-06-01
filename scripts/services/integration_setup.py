from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.connectors.registry import get_connector
from scripts.connectors.registry import SUPPORTED_SOCIAL_PLATFORMS
from scripts.services.integration_flags import (
    PlatformIntegrationFlags,
    mask_config_value,
    validate_integration_feature_flags,
)


KNOWN_APP_ENVIRONMENTS = {"development", "test", "production"}
KNOWN_INTEGRATIONS_MODES = {"mock", "disabled", "real_oauth"}
KNOWN_TOKEN_STORAGE_MODES = {
    "keychain",
    "encrypted_file",
    "encrypted_database",
    "placeholder_not_stored",
    "insecure_dev_only",
}
MOCK_CONNECT_PLATFORMS = {"facebook", "instagram", "youtube", "tiktok", "linkedin", "x"}


@dataclass(frozen=True)
class EnvVarStatus:
    name: str
    required: bool
    configured: bool
    secret: bool = False
    displayValue: str = "Not configured"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "required": self.required,
            "configured": self.configured,
            "secret": self.secret,
            "displayValue": self.displayValue,
        }


@dataclass(frozen=True)
class PlatformSetupStatus:
    platform: str
    label: str
    status: str
    requiredEnvVars: tuple[str, ...]
    optionalEnvVars: tuple[str, ...]
    missingRequiredEnvVars: tuple[str, ...]
    redirectUri: str | None
    requiredAccountType: str
    requiredScopes: tuple[str, ...]
    appReviewLikelyNeeded: bool
    connectorFeatureStatus: str
    mockConnectAvailable: bool
    realOAuthAvailable: bool
    realPublishingAvailable: bool
    envVars: dict[str, EnvVarStatus] = field(default_factory=dict)
    checklist: tuple[str, ...] = ()
    docsLinks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "label": self.label,
            "status": self.status,
            "requiredEnvVars": list(self.requiredEnvVars),
            "optionalEnvVars": list(self.optionalEnvVars),
            "missingRequiredEnvVars": list(self.missingRequiredEnvVars),
            "redirectUri": self.redirectUri,
            "requiredAccountType": self.requiredAccountType,
            "requiredScopes": list(self.requiredScopes),
            "appReviewLikelyNeeded": self.appReviewLikelyNeeded,
            "connectorFeatureStatus": self.connectorFeatureStatus,
            "mockConnectAvailable": self.mockConnectAvailable,
            "realOAuthAvailable": self.realOAuthAvailable,
            "realPublishingAvailable": self.realPublishingAvailable,
            "envVars": {key: value.to_dict() for key, value in self.envVars.items()},
            "checklist": list(self.checklist),
            "docsLinks": list(self.docsLinks),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class IntegrationSetupStatus:
    appEnvironment: str
    integrationsMode: str
    tokenStorageMode: str
    localDataDirectory: str
    localDataDirectoryExists: bool
    realOAuthEnabled: bool
    realPublishingEnabled: bool
    realPublishingAvailable: bool
    platforms: dict[str, PlatformSetupStatus]
    warningCodes: tuple[str, ...] = ()
    errorCodes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "appEnvironment": self.appEnvironment,
            "integrationsMode": self.integrationsMode,
            "tokenStorageMode": self.tokenStorageMode,
            "localDataDirectory": self.localDataDirectory,
            "localDataDirectoryExists": self.localDataDirectoryExists,
            "realOAuthEnabled": self.realOAuthEnabled,
            "realPublishingEnabled": self.realPublishingEnabled,
            "realPublishingAvailable": self.realPublishingAvailable,
            "platforms": {
                key: value.to_dict() for key, value in self.platforms.items()
            },
            "warningCodes": list(self.warningCodes),
            "errorCodes": list(self.errorCodes),
        }


def validate_social_integration_setup(
    env: dict[str, str] | None = None,
) -> IntegrationSetupStatus:
    values = env if env is not None else dict(os.environ)
    feature_flags = validate_integration_feature_flags(values)

    warnings: list[str] = []
    errors: list[str] = []
    warnings.extend(feature_flags.warningCodes)
    errors.extend(feature_flags.errorCodes)

    platforms = {
        platform: _platform_setup_status(
            platform,
            values,
            flag_status=feature_flags.platforms[platform],
        )
        for platform in SUPPORTED_SOCIAL_PLATFORMS
    }

    return IntegrationSetupStatus(
        appEnvironment=feature_flags.appEnvironment,
        integrationsMode=feature_flags.integrationsMode,
        tokenStorageMode=feature_flags.tokenStorageMode,
        localDataDirectory=feature_flags.localDataDirectory,
        localDataDirectoryExists=feature_flags.localDataDirectoryExists,
        realOAuthEnabled=feature_flags.realOAuthEnabled,
        realPublishingEnabled=feature_flags.realPublishingRequested,
        realPublishingAvailable=False,
        platforms=platforms,
        warningCodes=tuple(_dedupe(warnings)),
        errorCodes=tuple(_dedupe(errors)),
    )


def _platform_setup_status(
    platform: str,
    env: dict[str, str],
    *,
    flag_status: PlatformIntegrationFlags,
) -> PlatformSetupStatus:
    spec = _platform_env_spec(platform)
    connector = get_connector(platform)
    required_vars = spec["required"]
    optional_vars = spec["optional"]
    all_vars = required_vars + optional_vars
    env_vars = {
        key: EnvVarStatus(
            name=key,
            required=key in required_vars,
            configured=bool(_env_value(env, key)),
            secret=_is_secret_name(key),
            displayValue=mask_config_value(key, env.get(key)),
        )
        for key in all_vars
    }
    missing_required = tuple(
        key for key in required_vars if not env_vars[key].configured
    )
    redirect_uri = _env_value(env, spec["redirect"])
    required_scopes = tuple(scope.id for scope in connector.getRequiredScopes())
    return PlatformSetupStatus(
        platform=platform,
        label=connector.label,
        status=flag_status.status,
        requiredEnvVars=tuple(required_vars),
        optionalEnvVars=tuple(optional_vars),
        missingRequiredEnvVars=missing_required,
        redirectUri=redirect_uri,
        requiredAccountType=spec["account_type"],
        requiredScopes=required_scopes,
        appReviewLikelyNeeded=connector.getCapabilities().requiresAppReview,
        connectorFeatureStatus=connector.featureStatus.value,
        mockConnectAvailable=platform in MOCK_CONNECT_PLATFORMS,
        realOAuthAvailable=flag_status.realOAuthAvailable,
        realPublishingAvailable=False,
        envVars=env_vars,
        checklist=tuple(_checklist_for_platform(platform, missing_required)),
        docsLinks=tuple(_docs_links_for_platform(platform)),
        warnings=tuple(flag_status.warningCodes),
    )


def _platform_env_spec(platform: str) -> dict[str, Any]:
    if platform in {"facebook", "instagram", "threads"}:
        return {
            "required": ["META_CLIENT_ID", "META_CLIENT_SECRET", "META_REDIRECT_URI"],
            "optional": [
                "META_GRAPH_API_VERSION",
                "META_ENABLE_REAL_OAUTH",
                "META_ENABLE_REAL_PUBLISHING",
            ],
            "redirect": "META_REDIRECT_URI",
            "real_oauth_flag": "META_ENABLE_REAL_OAUTH",
            "real_publishing_flag": "META_ENABLE_REAL_PUBLISHING",
            "account_type": "Facebook Page, Instagram Business/Creator, or Threads profile",
        }
    if platform == "youtube":
        return {
            "required": [
                "GOOGLE_CLIENT_ID",
                "GOOGLE_CLIENT_SECRET",
                "GOOGLE_REDIRECT_URI",
            ],
            "optional": [
                "GOOGLE_ENABLE_REAL_OAUTH",
                "GOOGLE_ENABLE_REAL_PUBLISHING",
            ],
            "redirect": "GOOGLE_REDIRECT_URI",
            "real_oauth_flag": "GOOGLE_ENABLE_REAL_OAUTH",
            "real_publishing_flag": "GOOGLE_ENABLE_REAL_PUBLISHING",
            "account_type": "YouTube channel",
        }
    if platform == "tiktok":
        return {
            "required": [
                "TIKTOK_CLIENT_KEY",
                "TIKTOK_CLIENT_SECRET",
                "TIKTOK_REDIRECT_URI",
            ],
            "optional": [
                "TIKTOK_ENABLE_REAL_OAUTH",
                "TIKTOK_ENABLE_REAL_PUBLISHING",
            ],
            "redirect": "TIKTOK_REDIRECT_URI",
            "real_oauth_flag": "TIKTOK_ENABLE_REAL_OAUTH",
            "real_publishing_flag": "TIKTOK_ENABLE_REAL_PUBLISHING",
            "account_type": "TikTok business or creator account",
        }
    if platform == "linkedin":
        return {
            "required": [
                "LINKEDIN_CLIENT_ID",
                "LINKEDIN_CLIENT_SECRET",
                "LINKEDIN_REDIRECT_URI",
            ],
            "optional": [
                "LINKEDIN_ENABLE_REAL_OAUTH",
                "LINKEDIN_ENABLE_REAL_PUBLISHING",
            ],
            "redirect": "LINKEDIN_REDIRECT_URI",
            "real_oauth_flag": "LINKEDIN_ENABLE_REAL_OAUTH",
            "real_publishing_flag": "LINKEDIN_ENABLE_REAL_PUBLISHING",
            "account_type": "LinkedIn organization or member account",
        }
    return {
        "required": ["X_CLIENT_ID", "X_CLIENT_SECRET", "X_REDIRECT_URI"],
        "optional": ["X_ENABLE_REAL_OAUTH", "X_ENABLE_REAL_PUBLISHING"],
        "redirect": "X_REDIRECT_URI",
        "real_oauth_flag": "X_ENABLE_REAL_OAUTH",
        "real_publishing_flag": "X_ENABLE_REAL_PUBLISHING",
        "account_type": "X account",
    }


def _checklist_for_platform(platform: str, missing_required: tuple[str, ...]) -> list[str]:
    checklist = [
        "Stay in mock mode while setting up local testing.",
        "Create or configure the provider developer app later.",
        "Add required environment variables locally; never commit .env.",
        "Confirm redirect URI exactly matches the developer app setting.",
        "Use Connected Accounts to run mock connection testing.",
        "Use manual export until real publishing is explicitly implemented.",
    ]
    if missing_required:
        checklist.insert(1, "Add missing required environment variables: " + ", ".join(missing_required))
    if platform in {"facebook", "instagram", "threads", "tiktok", "linkedin"}:
        checklist.append("Plan for app review or provider approval before real use.")
    if platform == "youtube":
        checklist.append("Enable the YouTube Data API later and verify Google app verification requirements.")
    if platform == "tiktok":
        checklist.append("Plan for TikTok content posting review before any real video posting work.")
    if platform == "linkedin":
        checklist.append("Plan for LinkedIn Product access and organization/page access before real posting work.")
    if platform == "x":
        checklist.append("Review X API access, pricing, limits, and product tier before real OAuth or posting work.")
    return checklist


def _docs_links_for_platform(platform: str) -> list[str]:
    labels = {
        "facebook": "Official Meta developer docs link placeholder",
        "instagram": "Official Instagram developer docs link placeholder",
        "threads": "Official Threads developer docs link placeholder",
        "youtube": "Official Google/YouTube developer docs link placeholder",
        "tiktok": "Official TikTok developer docs link placeholder",
        "linkedin": "Official LinkedIn developer docs link placeholder",
        "x": "Official X developer docs link placeholder",
    }
    return [
        labels[platform],
        "Verify official docs before enabling real OAuth or publishing.",
    ]


def _env_value(env: dict[str, str], key: str) -> str | None:
    value = env.get(key)
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _bool_env(value: str | None, *, default: bool) -> bool:
    if value is None or not str(value).strip():
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _is_secret_name(name: str) -> bool:
    return "SECRET" in name.upper() or "TOKEN" in name.upper() or "KEY" in name.upper() and "CLIENT_KEY" not in name.upper()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
