from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class IntegrationMode(StrEnum):
    DISABLED = "disabled"
    MOCK = "mock"
    REAL_OAUTH = "real_oauth"


class NetworkSafetyMode(StrEnum):
    DISABLED = "disabled"
    MOCK = "mock"
    ENABLED = "enabled"


class IntegrationStatus(StrEnum):
    DISABLED = "disabled"
    MOCK_READY = "mock_ready"
    MISSING_CONFIG = "missing_config"
    REAL_OAUTH_READY = "real_oauth_ready"
    REAL_NETWORK_DISABLED = "real_network_disabled"
    PUBLISHING_DISABLED_BY_POLICY = "publishing_disabled_by_policy"
    INVALID_CONFIG = "invalid_config"
    ERROR = "error"


TOKEN_STORAGE_MODES = {
    "keychain",
    "encrypted_file",
    "encrypted_database",
    "placeholder_not_stored",
    "insecure_dev_only",
}

KNOWN_APP_ENVIRONMENTS = {"development", "test", "production"}


@dataclass(frozen=True)
class EnvVarFlagStatus:
    name: str
    required: bool
    configured: bool
    secret: bool = False
    displayValue: str = "Not configured"

    def to_frontend_safe_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "required": self.required,
            "configured": self.configured,
            "secret": self.secret,
            "displayValue": self.displayValue,
        }


@dataclass(frozen=True)
class PlatformIntegrationFlags:
    platform: str
    label: str
    status: str
    realOAuthEnabled: bool
    realOAuthAvailable: bool
    realNetworkEnabled: bool
    realPublishingRequested: bool
    realPublishingAvailable: bool
    requiredEnvVars: tuple[str, ...]
    optionalEnvVars: tuple[str, ...]
    missingRequiredEnvVars: tuple[str, ...]
    redirectUri: str | None
    envVars: dict[str, EnvVarFlagStatus] = field(default_factory=dict)
    setupMessages: tuple[str, ...] = ()
    warningCodes: tuple[str, ...] = ()
    errorCodes: tuple[str, ...] = ()

    def to_frontend_safe_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "label": self.label,
            "status": self.status,
            "realOAuthEnabled": self.realOAuthEnabled,
            "realOAuthAvailable": self.realOAuthAvailable,
            "realNetworkEnabled": self.realNetworkEnabled,
            "realPublishingRequested": self.realPublishingRequested,
            "realPublishingAvailable": self.realPublishingAvailable,
            "requiredEnvVars": list(self.requiredEnvVars),
            "optionalEnvVars": list(self.optionalEnvVars),
            "missingRequiredEnvVars": list(self.missingRequiredEnvVars),
            "redirectUri": self.redirectUri,
            "envVars": {
                key: value.to_frontend_safe_dict()
                for key, value in self.envVars.items()
            },
            "setupMessages": list(self.setupMessages),
            "warningCodes": list(self.warningCodes),
            "errorCodes": list(self.errorCodes),
        }


@dataclass(frozen=True)
class IntegrationFeatureFlags:
    appEnvironment: str
    integrationsMode: str
    networkSafetyMode: str
    realNetworkEnabled: bool
    realOAuthEnabled: bool
    realPublishingRequested: bool
    realPublishingAvailable: bool
    allowNetworkInTests: bool
    tokenStorageMode: str
    localDataDirectory: str
    localDataDirectoryExists: bool
    platforms: dict[str, PlatformIntegrationFlags]
    warningCodes: tuple[str, ...] = ()
    errorCodes: tuple[str, ...] = ()

    def to_frontend_safe_dict(self) -> dict[str, Any]:
        return {
            "appEnvironment": self.appEnvironment,
            "integrationsMode": self.integrationsMode,
            "networkSafetyMode": self.networkSafetyMode,
            "realNetworkEnabled": self.realNetworkEnabled,
            "realOAuthEnabled": self.realOAuthEnabled,
            "realPublishingRequested": self.realPublishingRequested,
            "realPublishingAvailable": self.realPublishingAvailable,
            "allowNetworkInTests": self.allowNetworkInTests,
            "tokenStorageMode": self.tokenStorageMode,
            "localDataDirectory": self.localDataDirectory,
            "localDataDirectoryExists": self.localDataDirectoryExists,
            "platforms": {
                key: value.to_frontend_safe_dict()
                for key, value in self.platforms.items()
            },
            "warningCodes": list(self.warningCodes),
            "errorCodes": list(self.errorCodes),
        }


PLATFORM_ENV_SPECS: dict[str, dict[str, Any]] = {
    "facebook": {
        "label": "Facebook",
        "required": ("META_CLIENT_ID", "META_CLIENT_SECRET", "META_REDIRECT_URI"),
        "optional": (
            "META_GRAPH_API_VERSION",
            "META_ENABLE_REAL_OAUTH",
            "META_ENABLE_REAL_PUBLISHING",
        ),
        "redirect": "META_REDIRECT_URI",
        "real_oauth_flag": "META_ENABLE_REAL_OAUTH",
        "real_publishing_flag": "META_ENABLE_REAL_PUBLISHING",
    },
    "instagram": {
        "label": "Instagram",
        "required": ("META_CLIENT_ID", "META_CLIENT_SECRET", "META_REDIRECT_URI"),
        "optional": (
            "META_GRAPH_API_VERSION",
            "META_ENABLE_REAL_OAUTH",
            "META_ENABLE_REAL_PUBLISHING",
        ),
        "redirect": "META_REDIRECT_URI",
        "real_oauth_flag": "META_ENABLE_REAL_OAUTH",
        "real_publishing_flag": "META_ENABLE_REAL_PUBLISHING",
    },
    "threads": {
        "label": "Threads",
        "required": ("META_CLIENT_ID", "META_CLIENT_SECRET", "META_REDIRECT_URI"),
        "optional": (
            "META_GRAPH_API_VERSION",
            "META_ENABLE_REAL_OAUTH",
            "META_ENABLE_REAL_PUBLISHING",
        ),
        "redirect": "META_REDIRECT_URI",
        "real_oauth_flag": "META_ENABLE_REAL_OAUTH",
        "real_publishing_flag": "META_ENABLE_REAL_PUBLISHING",
    },
    "youtube": {
        "label": "YouTube Shorts",
        "required": ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"),
        "optional": ("GOOGLE_ENABLE_REAL_OAUTH", "GOOGLE_ENABLE_REAL_PUBLISHING"),
        "redirect": "GOOGLE_REDIRECT_URI",
        "real_oauth_flag": "GOOGLE_ENABLE_REAL_OAUTH",
        "real_publishing_flag": "GOOGLE_ENABLE_REAL_PUBLISHING",
    },
    "tiktok": {
        "label": "TikTok",
        "required": ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REDIRECT_URI"),
        "optional": ("TIKTOK_ENABLE_REAL_OAUTH", "TIKTOK_ENABLE_REAL_PUBLISHING"),
        "redirect": "TIKTOK_REDIRECT_URI",
        "real_oauth_flag": "TIKTOK_ENABLE_REAL_OAUTH",
        "real_publishing_flag": "TIKTOK_ENABLE_REAL_PUBLISHING",
    },
    "linkedin": {
        "label": "LinkedIn",
        "required": (
            "LINKEDIN_CLIENT_ID",
            "LINKEDIN_CLIENT_SECRET",
            "LINKEDIN_REDIRECT_URI",
        ),
        "optional": ("LINKEDIN_ENABLE_REAL_OAUTH", "LINKEDIN_ENABLE_REAL_PUBLISHING"),
        "redirect": "LINKEDIN_REDIRECT_URI",
        "real_oauth_flag": "LINKEDIN_ENABLE_REAL_OAUTH",
        "real_publishing_flag": "LINKEDIN_ENABLE_REAL_PUBLISHING",
    },
    "x": {
        "label": "X",
        "required": ("X_CLIENT_ID", "X_CLIENT_SECRET", "X_REDIRECT_URI"),
        "optional": ("X_ENABLE_REAL_OAUTH", "X_ENABLE_REAL_PUBLISHING"),
        "redirect": "X_REDIRECT_URI",
        "real_oauth_flag": "X_ENABLE_REAL_OAUTH",
        "real_publishing_flag": "X_ENABLE_REAL_PUBLISHING",
    },
}


def validate_integration_feature_flags(
    env: dict[str, str] | None = None,
) -> IntegrationFeatureFlags:
    values = env if env is not None else dict(os.environ)
    app_env = _env_value(values, "APP_ENV") or "development"
    local_data_dir = _env_value(values, "LOCAL_DATA_DIR") or "./data"
    raw_mode = (_env_value(values, "INTEGRATIONS_MODE") or IntegrationMode.MOCK.value).lower()
    token_storage_mode = (
        _env_value(values, "TOKEN_STORAGE_MODE") or "placeholder_not_stored"
    ).lower()

    warnings: list[str] = []
    errors: list[str] = []
    if app_env not in KNOWN_APP_ENVIRONMENTS:
        errors.append("unknown_app_environment")
    if raw_mode not in {mode.value for mode in IntegrationMode}:
        errors.append("invalid_integrations_mode")
    if token_storage_mode not in TOKEN_STORAGE_MODES:
        errors.append("invalid_token_storage_mode")

    bools = {
        "ENABLE_REAL_NETWORK_CALLS": _parse_bool_flag(
            values, "ENABLE_REAL_NETWORK_CALLS", default=False, errors=errors
        ),
        "ENABLE_REAL_OAUTH": _parse_bool_flag(
            values, "ENABLE_REAL_OAUTH", default=False, errors=errors
        ),
        "ENABLE_REAL_PUBLISHING": _parse_bool_flag(
            values, "ENABLE_REAL_PUBLISHING", default=False, errors=errors
        ),
        "ALLOW_NETWORK_IN_TESTS": _parse_bool_flag(
            values, "ALLOW_NETWORK_IN_TESTS", default=False, errors=errors
        ),
    }
    if bools["ENABLE_REAL_PUBLISHING"]:
        warnings.append("real_publishing_disabled_by_policy")

    local_data_exists = Path(local_data_dir).expanduser().exists()
    if not local_data_exists:
        warnings.append("missing_local_data_directory")

    network_safety = resolve_network_safety_mode(
        env=values,
        connector_allows_network=bools["ENABLE_REAL_NETWORK_CALLS"],
        errors=errors,
    )
    mode = raw_mode if raw_mode in {item.value for item in IntegrationMode} else IntegrationMode.MOCK.value
    platforms = {
        platform: _platform_flags(
            platform,
            values,
            integrations_mode=mode,
            real_network_enabled=bools["ENABLE_REAL_NETWORK_CALLS"],
            global_real_oauth=bools["ENABLE_REAL_OAUTH"],
            errors=errors,
        )
        for platform in PLATFORM_ENV_SPECS
    }

    return IntegrationFeatureFlags(
        appEnvironment=app_env,
        integrationsMode=mode,
        networkSafetyMode=network_safety.value,
        realNetworkEnabled=bools["ENABLE_REAL_NETWORK_CALLS"],
        realOAuthEnabled=bools["ENABLE_REAL_OAUTH"],
        realPublishingRequested=bools["ENABLE_REAL_PUBLISHING"],
        realPublishingAvailable=False,
        allowNetworkInTests=bools["ALLOW_NETWORK_IN_TESTS"],
        tokenStorageMode=token_storage_mode,
        localDataDirectory=local_data_dir,
        localDataDirectoryExists=local_data_exists,
        platforms=platforms,
        warningCodes=tuple(_dedupe(warnings)),
        errorCodes=tuple(_dedupe(errors)),
    )


def resolve_network_safety_mode(
    *,
    env: dict[str, str] | None = None,
    connector_allows_network: bool = False,
    errors: list[str] | None = None,
) -> NetworkSafetyMode:
    values = env if env is not None else dict(os.environ)
    app_env = _env_value(values, "APP_ENV") or "development"
    allow_in_tests = _parse_bool_flag(
        values, "ALLOW_NETWORK_IN_TESTS", default=False, errors=errors
    )
    real_network = _parse_bool_flag(
        values, "ENABLE_REAL_NETWORK_CALLS", default=False, errors=errors
    )

    if app_env == "test" and not allow_in_tests:
        return NetworkSafetyMode.DISABLED
    if not connector_allows_network or not real_network:
        return NetworkSafetyMode.MOCK if app_env == "development" else NetworkSafetyMode.DISABLED
    return NetworkSafetyMode.ENABLED


def mask_config_value(name: str, value: str | None) -> str:
    clean_value = (value or "").strip()
    if not clean_value:
        return "Not configured"
    upper_name = name.upper()
    if _is_secret_name(upper_name):
        return "Configured, hidden"
    if "REDIRECT_URI" in upper_name:
        return clean_value
    if len(clean_value) <= 4:
        return "Configured"
    return f"{clean_value[:2]}...{clean_value[-2:]}"


def _platform_flags(
    platform: str,
    env: dict[str, str],
    *,
    integrations_mode: str,
    real_network_enabled: bool,
    global_real_oauth: bool,
    errors: list[str],
) -> PlatformIntegrationFlags:
    spec = PLATFORM_ENV_SPECS[platform]
    required = tuple(spec["required"])
    optional = tuple(spec["optional"])
    env_vars = {
        key: EnvVarFlagStatus(
            name=key,
            required=key in required,
            configured=bool(_env_value(env, key)),
            secret=_is_secret_name(key),
            displayValue=mask_config_value(key, env.get(key)),
        )
        for key in required + optional
    }
    missing_required = tuple(key for key in required if not env_vars[key].configured)
    platform_real_oauth = _parse_bool_flag(
        env, spec["real_oauth_flag"], default=False, errors=errors
    )
    platform_real_publishing = _parse_bool_flag(
        env, spec["real_publishing_flag"], default=False, errors=errors
    )

    warnings: list[str] = []
    platform_errors: list[str] = []
    if platform_real_publishing:
        warnings.append("real_publishing_disabled_by_policy")

    if integrations_mode == IntegrationMode.DISABLED.value:
        status = IntegrationStatus.DISABLED.value
        messages = ("Integrations are disabled. Mock connection tests are not active.",)
    elif integrations_mode == IntegrationMode.MOCK.value:
        status = IntegrationStatus.MOCK_READY.value
        messages = (
            "Mock mode is ready. Real provider APIs will not be called.",
            "You can add API keys later without enabling publishing.",
        )
    elif missing_required and global_real_oauth and platform_real_oauth:
        status = IntegrationStatus.MISSING_CONFIG.value
        messages = (
            "Real OAuth was requested, but required local environment variables are missing.",
            "Add the missing values to .env later; never commit secrets.",
        )
    elif global_real_oauth and platform_real_oauth and not real_network_enabled:
        status = IntegrationStatus.REAL_NETWORK_DISABLED.value
        messages = (
            "Real OAuth flags are set, but real network calls are still disabled.",
            "This is safe for setup review and will not call provider APIs.",
        )
    elif global_real_oauth and platform_real_oauth:
        status = IntegrationStatus.REAL_OAUTH_READY.value
        messages = (
            "Real OAuth configuration appears ready for guarded server-side testing.",
            "Publishing still remains disabled by policy.",
        )
    elif integrations_mode == IntegrationMode.REAL_OAUTH.value:
        status = IntegrationStatus.DISABLED.value
        messages = (
            "Real OAuth mode is selected, but this platform's real OAuth flag is not enabled.",
        )
    else:
        status = IntegrationStatus.INVALID_CONFIG.value
        platform_errors.append("invalid_integrations_mode")
        messages = ("Integration mode is invalid.",)

    return PlatformIntegrationFlags(
        platform=platform,
        label=str(spec["label"]),
        status=status,
        realOAuthEnabled=global_real_oauth and platform_real_oauth,
        realOAuthAvailable=status == IntegrationStatus.REAL_OAUTH_READY.value,
        realNetworkEnabled=real_network_enabled,
        realPublishingRequested=platform_real_publishing,
        realPublishingAvailable=False,
        requiredEnvVars=required,
        optionalEnvVars=optional,
        missingRequiredEnvVars=missing_required,
        redirectUri=_env_value(env, str(spec["redirect"])),
        envVars=env_vars,
        setupMessages=messages,
        warningCodes=tuple(_dedupe(warnings)),
        errorCodes=tuple(_dedupe(platform_errors)),
    )


def _parse_bool_flag(
    env: dict[str, str],
    key: str,
    *,
    default: bool,
    errors: list[str] | None,
) -> bool:
    value = env.get(key)
    if value is None or not str(value).strip():
        return default
    clean_value = str(value).strip().lower()
    if clean_value in {"1", "true", "yes", "on"}:
        return True
    if clean_value in {"0", "false", "no", "off"}:
        return False
    if errors is not None:
        errors.append(f"invalid_boolean_{key}")
    return default


def _env_value(env: dict[str, str], key: str) -> str | None:
    value = env.get(key)
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _is_secret_name(name: str) -> bool:
    upper_name = name.upper()
    if "CLIENT_SECRET" in upper_name or "SECRET" in upper_name:
        return True
    if "TOKEN" in upper_name:
        return True
    return "KEY" in upper_name and "CLIENT_KEY" not in upper_name


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
