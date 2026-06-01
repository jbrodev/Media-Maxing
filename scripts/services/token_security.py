from __future__ import annotations

import copy
import os
import re
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from scripts.db.init_db import initialize_database, resolve_database_path
from scripts.db.social_connections import (
    SUPPORTED_SOCIAL_PLATFORMS,
    list_safe_social_accounts,
)


class TokenSecurityError(ValueError):
    pass


class TokenStorageMode(StrEnum):
    KEYCHAIN = "keychain"
    ENCRYPTED_FILE = "encrypted_file"
    ENCRYPTED_DATABASE = "encrypted_database"
    PLACEHOLDER_NOT_STORED = "placeholder_not_stored"
    INSECURE_DEV_ONLY = "insecure_dev_only"


class TokenAccessPolicy(StrEnum):
    SERVER_CONNECTOR_ONLY = "server_connector_only"
    FRONTEND_SAFE_DTO = "frontend_safe_dto"


@dataclass(frozen=True)
class TokenStorageResult:
    success: bool
    storageMode: str
    encryptionStatus: str
    tokenVersion: int | None = None
    accessTokenExpiresAt: str | None = None
    refreshTokenExpiresAt: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def error_codes(self) -> list[str]:
        return [_message_code(error) for error in self.errors]

    @property
    def warning_codes(self) -> list[str]:
        return [_message_code(warning) for warning in self.warnings]


@dataclass(frozen=True)
class TokenRedactionResult:
    value: Any
    redacted: bool
    redactedFields: list[str] = field(default_factory=list)


SafeSocialAccountDTO = dict[str, Any]
SafeTokenMetadataDTO = dict[str, Any]


TOKEN_FIELD_NAMES = {
    "access_token",
    "accesstoken",
    "accessToken",
    "refresh_token",
    "refreshtoken",
    "refreshToken",
    "client_secret",
    "clientSecret",
    "authorization_code",
    "authorizationCode",
    "code",
    "id_token",
    "idToken",
    "bearer",
    "Authorization",
    "authorization",
}

LONG_RANDOM_PATTERN = re.compile(r"^[A-Za-z0-9_\-./+=]{24,}$")
BEARER_PATTERN = re.compile(r"(?i)^Bearer\s+[A-Za-z0-9._\-+/=]{12,}$")


class TokenSecurityService:
    """Server-side token handling boundary for future social connectors.

    The current safe default is placeholder mode. It records token metadata but
    refuses to persist raw tokens unless secure storage exists or explicit
    development-only insecure mode is enabled.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        storage_mode: TokenStorageMode | str | None = None,
    ):
        self.database_path = initialize_database(resolve_database_path(database_path))
        self.storage_mode = _storage_mode_from_value(
            storage_mode or os.environ.get("TOKEN_STORAGE_MODE") or TokenStorageMode.PLACEHOLDER_NOT_STORED
        )

    def store_token_set(
        self,
        *,
        social_account_id: str,
        platform: str,
        token_set: dict[str, Any],
        token_type: str = "oauth_access",
    ) -> TokenStorageResult:
        _validate_platform(platform)
        redacted = redact_token_data(token_set)
        access_expires = _first_string(
            token_set,
            "access_token_expires_at",
            "accessTokenExpiresAt",
            "expires_at",
            "expiresAt",
        )
        refresh_expires = _first_string(
            token_set,
            "refresh_token_expires_at",
            "refreshTokenExpiresAt",
        )
        scopes = token_set.get("scope") or token_set.get("scopes") or ""
        scope = " ".join(scopes) if isinstance(scopes, list) else str(scopes or "")

        if self.storage_mode == TokenStorageMode.PLACEHOLDER_NOT_STORED:
            return TokenStorageResult(
                success=False,
                storageMode=self.storage_mode.value,
                encryptionStatus="placeholder_not_stored",
                accessTokenExpiresAt=access_expires,
                refreshTokenExpiresAt=refresh_expires,
                warnings=[
                    "tokens_redacted: Raw token values were redacted and not stored."
                ]
                if redacted.redacted
                else [],
                errors=[
                    "secure_storage_unavailable: Raw tokens are refused in placeholder_not_stored mode."
                ],
            )

        if self.storage_mode in {
            TokenStorageMode.KEYCHAIN,
            TokenStorageMode.ENCRYPTED_FILE,
            TokenStorageMode.ENCRYPTED_DATABASE,
        }:
            return TokenStorageResult(
                success=False,
                storageMode=self.storage_mode.value,
                encryptionStatus=_encryption_status_for_mode(self.storage_mode),
                accessTokenExpiresAt=access_expires,
                refreshTokenExpiresAt=refresh_expires,
                errors=[
                    "secure_storage_not_implemented: Secure token storage is not available in the current stack."
                ],
            )

        if self.storage_mode == TokenStorageMode.INSECURE_DEV_ONLY:
            if not _insecure_dev_mode_allowed():
                return TokenStorageResult(
                    success=False,
                    storageMode=self.storage_mode.value,
                    encryptionStatus="insecure_dev_only",
                    accessTokenExpiresAt=access_expires,
                    refreshTokenExpiresAt=refresh_expires,
                    errors=[
                        "insecure_dev_mode_blocked: APP_ENV must be development and ALLOW_INSECURE_TOKEN_STORAGE=true."
                    ],
                )
            token_version = self._store_insecure_dev_token(
                social_account_id=social_account_id,
                platform=platform,
                token_type=token_type,
                access_token=_first_string(token_set, "access_token", "accessToken"),
                refresh_token=_first_string(token_set, "refresh_token", "refreshToken"),
                access_expires=access_expires,
                refresh_expires=refresh_expires,
                scope=scope,
            )
            return TokenStorageResult(
                success=True,
                storageMode=self.storage_mode.value,
                encryptionStatus="insecure_dev_only",
                tokenVersion=token_version,
                accessTokenExpiresAt=access_expires,
                refreshTokenExpiresAt=refresh_expires,
                warnings=[
                    "insecure_dev_only: Raw tokens were stored only because explicit development mode allowed it."
                ],
            )

        raise TokenSecurityError(f"Unsupported token storage mode: {self.storage_mode}")

    def retrieve_token_metadata(
        self,
        *,
        social_account_id: str,
        access_policy: TokenAccessPolicy | str = TokenAccessPolicy.SERVER_CONNECTOR_ONLY,
    ) -> SafeTokenMetadataDTO:
        policy = (
            access_policy
            if isinstance(access_policy, TokenAccessPolicy)
            else TokenAccessPolicy(str(access_policy))
        )
        if policy != TokenAccessPolicy.SERVER_CONNECTOR_ONLY:
            return {
                "success": False,
                "status": "forbidden",
                "message": "Token retrieval is server-side connector code only.",
            }

        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT
                  platform,
                  token_type,
                  access_token_expires_at,
                  refresh_token_expires_at,
                  scope,
                  token_version,
                  encryption_status,
                  last_refresh_at,
                  revoked_at,
                  created_at,
                  updated_at
                FROM platform_tokens
                WHERE social_account_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (social_account_id,),
            ).fetchone()

        if row is None:
            return {
                "success": False,
                "status": "missing",
                "message": "No token metadata exists for this social account.",
            }

        return {
            "success": True,
            "status": "metadata_only",
            "platform": row["platform"],
            "tokenType": row["token_type"],
            "accessTokenExpiresAt": row["access_token_expires_at"],
            "refreshTokenExpiresAt": row["refresh_token_expires_at"],
            "scope": row["scope"],
            "tokenVersion": row["token_version"],
            "encryptionStatus": row["encryption_status"],
            "lastRefreshAt": row["last_refresh_at"],
            "revokedAt": row["revoked_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def list_safe_social_account_dtos(self) -> list[SafeSocialAccountDTO]:
        safe_accounts = list_safe_social_accounts(self.database_path)
        return [_safe_social_account_dto(account) for account in safe_accounts]

    def _store_insecure_dev_token(
        self,
        *,
        social_account_id: str,
        platform: str,
        token_type: str,
        access_token: str | None,
        refresh_token: str | None,
        access_expires: str | None,
        refresh_expires: str | None,
        scope: str,
    ) -> int:
        token_id = f"token-dev-{platform}-{uuid.uuid4().hex[:12]}"
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO platform_tokens (
                  id, social_account_id, platform, token_type,
                  encrypted_access_token, encrypted_refresh_token,
                  access_token_expires_at, refresh_token_expires_at,
                  scope, token_version, encryption_status,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    token_id,
                    social_account_id,
                    platform,
                    token_type,
                    access_token,
                    refresh_token,
                    access_expires,
                    refresh_expires,
                    scope,
                    1,
                    "insecure_dev_only",
                ),
            )
            connection.commit()
        return 1


def redact_token_data(value: Any) -> TokenRedactionResult:
    redacted_fields: list[str] = []
    redacted_value = _redact_value(copy.deepcopy(value), redacted_fields, field_path="")
    return TokenRedactionResult(
        value=redacted_value,
        redacted=bool(redacted_fields),
        redactedFields=redacted_fields,
    )


def is_token_expired(
    expires_at: str | None,
    *,
    now: str | datetime | None = None,
    skew_seconds: int = 0,
) -> bool:
    if not expires_at:
        return False
    parsed_expires = _parse_iso_datetime(expires_at)
    parsed_now = _parse_iso_datetime(now) if now else datetime.now(timezone.utc)
    if skew_seconds:
        from datetime import timedelta

        parsed_now = parsed_now.replace(microsecond=0) + timedelta(seconds=skew_seconds)
    return parsed_expires <= parsed_now


def requires_reauth(
    *,
    access_token_expires_at: str | None,
    refresh_token_expires_at: str | None,
    connection_status: str,
    requires_reauth_flag: bool,
    now: str | datetime | None = None,
) -> bool:
    if requires_reauth_flag:
        return True
    if connection_status in {"expired", "revoked", "disconnected", "error", "requires_reauth"}:
        return True
    if is_token_expired(access_token_expires_at, now=now):
        return True
    if is_token_expired(refresh_token_expires_at, now=now):
        return True
    return False


def _safe_social_account_dto(account: dict[str, Any]) -> SafeSocialAccountDTO:
    return {
        "id": account["id"],
        "platform": account["platform"],
        "displayName": account["displayName"],
        "username": account.get("username"),
        "accountType": account["accountType"],
        "connectionStatus": account["connectionStatus"],
        "capabilities": account.get("capabilities") or {},
        "grantedScopes": account.get("grantedScopes") or [],
        "missingScopes": account.get("missingScopes") or [],
        "requiresReauth": requires_reauth(
            access_token_expires_at=None,
            refresh_token_expires_at=None,
            connection_status=account["connectionStatus"],
            requires_reauth_flag=bool(account.get("requiresReauth")),
        ),
        "lastConnectedAt": account.get("lastConnectedAt"),
        "lastValidatedAt": account.get("lastValidatedAt"),
        "tokenStorageStatus": account.get("tokenStorageStatus", "missing"),
        "healthStatus": account.get("healthStatus", "not_checked"),
        "healthWarnings": (account.get("healthMetadata") or {}).get("warnings", []),
        "healthErrors": (account.get("healthMetadata") or {}).get("errors", []),
        "missingPermissions": (account.get("healthMetadata") or {}).get("missingPermissions", []),
    }


def _redact_value(value: Any, redacted_fields: list[str], *, field_path: str) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            child_path = f"{field_path}.{key}" if field_path else str(key)
            if _is_sensitive_field(str(key), child):
                result[key] = "[REDACTED]"
                redacted_fields.append(child_path)
            else:
                result[key] = _redact_value(child, redacted_fields, field_path=child_path)
        return result
    if isinstance(value, list):
        return [
            _redact_value(child, redacted_fields, field_path=f"{field_path}[{index}]")
            for index, child in enumerate(value)
        ]
    if isinstance(value, str) and BEARER_PATTERN.match(value):
        redacted_fields.append(field_path or "<value>")
        return "[REDACTED]"
    return value


def _is_sensitive_field(key: str, value: Any) -> bool:
    normalized_key = key.replace("-", "_")
    if key in TOKEN_FIELD_NAMES or normalized_key in TOKEN_FIELD_NAMES:
        return True
    lowered = normalized_key.lower()
    if any(
        marker in lowered
        for marker in ("access_token", "refresh_token", "client_secret", "authorization")
    ):
        return True
    if isinstance(value, str) and lowered in {"code", "token"} and LONG_RANDOM_PATTERN.match(value):
        return True
    return False


def _storage_mode_from_value(value: TokenStorageMode | str) -> TokenStorageMode:
    try:
        return value if isinstance(value, TokenStorageMode) else TokenStorageMode(str(value))
    except ValueError as error:
        raise TokenSecurityError(
            "TOKEN_STORAGE_MODE must be one of: "
            + ", ".join(mode.value for mode in TokenStorageMode)
        ) from error


def _encryption_status_for_mode(mode: TokenStorageMode) -> str:
    if mode == TokenStorageMode.KEYCHAIN:
        return "keychain"
    if mode in {TokenStorageMode.ENCRYPTED_FILE, TokenStorageMode.ENCRYPTED_DATABASE}:
        return "encrypted"
    return mode.value


def _insecure_dev_mode_allowed() -> bool:
    return (
        os.environ.get("APP_ENV") == "development"
        and os.environ.get("ALLOW_INSECURE_TOKEN_STORAGE", "").lower() == "true"
    )


def _first_string(source: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _validate_platform(platform: str) -> None:
    if platform not in SUPPORTED_SOCIAL_PLATFORMS:
        raise TokenSecurityError(
            f"Unsupported platform {platform!r}. Supported platforms: "
            + ", ".join(SUPPORTED_SOCIAL_PLATFORMS)
        )


def _parse_iso_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _message_code(message: str) -> str:
    return message.split(":", 1)[0]
