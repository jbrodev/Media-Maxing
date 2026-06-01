from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.db.init_db import initialize_database, resolve_database_path


SOCIAL_ACCOUNT_TYPES = (
    "personal",
    "business",
    "creator",
    "page",
    "channel",
    "organization",
    "unknown",
)

SOCIAL_CONNECTION_STATUSES = (
    "not_connected",
    "connecting",
    "connected",
    "limited",
    "expired",
    "revoked",
    "disconnected",
    "error",
    "requires_reauth",
)

PLATFORM_TOKEN_TYPES = (
    "oauth_access",
    "oauth_refresh",
    "long_lived_access",
    "page_access",
    "app_token_placeholder",
    "unknown",
)

TOKEN_ENCRYPTION_STATUSES = (
    "encrypted",
    "keychain",
    "placeholder_not_stored",
    "insecure_dev_only",
    "missing",
)

OAUTH_STATE_STATUSES = (
    "created",
    "consumed",
    "expired",
    "failed",
)

CONNECTOR_AUDIT_ACTIONS = (
    "oauth_start",
    "oauth_callback",
    "token_exchange",
    "token_refresh",
    "connection_validate",
    "disconnect",
    "reauth_required",
    "error",
)

SUPPORTED_SOCIAL_PLATFORMS = (
    "facebook",
    "instagram",
    "threads",
    "youtube",
    "tiktok",
    "linkedin",
    "x",
)

SAFE_ACCOUNT_FORBIDDEN_KEYS = {
    "encrypted_access_token",
    "encrypted_refresh_token",
    "access_token",
    "refresh_token",
    "authorization_code",
    "state",
    "state_hash",
    "client_secret",
}


class SocialConnectionError(ValueError):
    pass


def create_mock_social_account(
    database_path: str | Path | None = None,
    *,
    platform: str,
    display_name: str,
    username: str | None = None,
    platform_account_id: str | None = None,
    brand_profile_id: str | None = None,
    profile_url: str | None = None,
    profile_image_url: str | None = None,
    account_type: str = "unknown",
    connection_status: str = "connected",
    capabilities: dict[str, Any] | None = None,
    granted_scopes: list[str] | None = None,
    missing_scopes: list[str] | None = None,
    requires_reauth: bool = False,
    account_id: str | None = None,
    now: str | None = None,
) -> str:
    _validate_platform(platform)
    _validate_choice(account_type, SOCIAL_ACCOUNT_TYPES, "account_type")
    _validate_choice(connection_status, SOCIAL_CONNECTION_STATUSES, "connection_status")

    db_path = initialize_database(resolve_database_path(database_path))
    timestamp = now or _utc_now()
    account_id = account_id or f"acct-{platform}-{uuid.uuid4().hex[:12]}"
    platform_account_id = platform_account_id or f"mock-{platform}-{account_id}"

    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO social_accounts (
              id, brand_profile_id, platform, platform_account_id, display_name,
              username, profile_url, profile_image_url, account_type,
              connection_status, capabilities_json, granted_scopes_json,
              missing_scopes_json, requires_reauth, last_connected_at,
              last_validated_at, disconnected_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              brand_profile_id = excluded.brand_profile_id,
              platform_account_id = excluded.platform_account_id,
              display_name = excluded.display_name,
              username = excluded.username,
              profile_url = excluded.profile_url,
              profile_image_url = excluded.profile_image_url,
              account_type = excluded.account_type,
              connection_status = excluded.connection_status,
              capabilities_json = excluded.capabilities_json,
              granted_scopes_json = excluded.granted_scopes_json,
              missing_scopes_json = excluded.missing_scopes_json,
              requires_reauth = excluded.requires_reauth,
              last_connected_at = excluded.last_connected_at,
              last_validated_at = excluded.last_validated_at,
              disconnected_at = excluded.disconnected_at,
              updated_at = excluded.updated_at
            """,
            (
                account_id,
                brand_profile_id,
                platform,
                platform_account_id,
                display_name,
                username,
                profile_url,
                profile_image_url,
                account_type,
                connection_status,
                _json(capabilities or {}),
                _json(granted_scopes or []),
                _json(missing_scopes or []),
                1 if requires_reauth else 0,
                timestamp if connection_status == "connected" else None,
                timestamp if connection_status in {"connected", "limited"} else None,
                timestamp if connection_status == "disconnected" else None,
                timestamp,
                timestamp,
            ),
        )
        connection.commit()

    return account_id


def create_placeholder_platform_token(
    database_path: str | Path | None = None,
    *,
    social_account_id: str,
    platform: str,
    token_type: str = "app_token_placeholder",
    scope: str = "",
    token_id: str | None = None,
    now: str | None = None,
) -> str:
    _validate_platform(platform)
    _validate_choice(token_type, PLATFORM_TOKEN_TYPES, "token_type")

    db_path = initialize_database(resolve_database_path(database_path))
    timestamp = now or _utc_now()
    token_id = token_id or f"token-{platform}-{uuid.uuid4().hex[:12]}"

    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO platform_tokens (
              id, social_account_id, platform, token_type,
              encrypted_access_token, encrypted_refresh_token,
              access_token_expires_at, refresh_token_expires_at, scope,
              token_version, encryption_status, last_refresh_at, revoked_at,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, ?, ?, ?, NULL, NULL, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              social_account_id = excluded.social_account_id,
              platform = excluded.platform,
              token_type = excluded.token_type,
              encrypted_access_token = NULL,
              encrypted_refresh_token = NULL,
              scope = excluded.scope,
              encryption_status = excluded.encryption_status,
              updated_at = excluded.updated_at
            """,
            (
                token_id,
                social_account_id,
                platform,
                token_type,
                scope,
                1,
                "placeholder_not_stored",
                timestamp,
                timestamp,
            ),
        )
        connection.commit()

    return token_id


def create_oauth_state_record(
    database_path: str | Path | None = None,
    *,
    platform: str,
    state_hash: str,
    redirect_uri: str,
    requested_scopes: list[str] | None = None,
    expires_at: str,
    code_verifier_hash: str | None = None,
    state_id: str | None = None,
    now: str | None = None,
) -> str:
    _validate_platform(platform)
    if not state_hash or not state_hash.strip():
        raise SocialConnectionError("state_hash is required; raw OAuth state must not be stored.")

    db_path = initialize_database(resolve_database_path(database_path))
    timestamp = now or _utc_now()
    state_id = state_id or f"oauth-state-{platform}-{uuid.uuid4().hex[:12]}"

    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO oauth_states (
              id, platform, state_hash, redirect_uri, code_verifier_hash,
              requested_scopes_json, status, created_at, expires_at,
              consumed_at, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
            ON CONFLICT(id) DO UPDATE SET
              platform = excluded.platform,
              state_hash = excluded.state_hash,
              redirect_uri = excluded.redirect_uri,
              code_verifier_hash = excluded.code_verifier_hash,
              requested_scopes_json = excluded.requested_scopes_json,
              status = excluded.status,
              expires_at = excluded.expires_at,
              consumed_at = NULL,
              error_message = NULL
            """,
            (
                state_id,
                platform,
                state_hash,
                redirect_uri,
                code_verifier_hash,
                _json(requested_scopes or []),
                "created",
                timestamp,
                expires_at,
            ),
        )
        connection.commit()

    return state_id


def create_connector_audit_log(
    database_path: str | Path | None = None,
    *,
    platform: str,
    action: str,
    status: str,
    message: str,
    social_account_id: str | None = None,
    safe_metadata: dict[str, Any] | None = None,
    audit_id: str | None = None,
    now: str | None = None,
) -> str:
    _validate_platform(platform)
    _validate_choice(action, CONNECTOR_AUDIT_ACTIONS, "action")
    _reject_secret_metadata(safe_metadata or {})

    db_path = initialize_database(resolve_database_path(database_path))
    timestamp = now or _utc_now()
    audit_id = audit_id or f"audit-{platform}-{uuid.uuid4().hex[:12]}"

    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO connector_audit_logs (
              id, platform, social_account_id, action, status, message,
              safe_metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                platform,
                social_account_id,
                action,
                status,
                message,
                _json(safe_metadata or {}),
                timestamp,
            ),
        )
        connection.commit()

    return audit_id


def list_safe_social_accounts(
    database_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    db_path = initialize_database(resolve_database_path(database_path))
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
              sa.id,
              sa.brand_profile_id,
              sa.platform,
              sa.platform_account_id,
              sa.display_name,
              sa.username,
              sa.profile_url,
              sa.profile_image_url,
              sa.account_type,
              sa.connection_status,
              sa.capabilities_json,
              sa.granted_scopes_json,
              sa.missing_scopes_json,
              sa.requires_reauth,
              sa.last_connected_at,
              sa.last_validated_at,
              sa.disconnected_at,
              sa.created_at,
              sa.updated_at,
              COALESCE(MAX(pt.encryption_status), 'missing') AS token_storage_status,
              (
                SELECT chc.health_status
                FROM connector_health_checks chc
                WHERE chc.social_account_id = sa.id
                ORDER BY chc.checked_at DESC, chc.created_at DESC
                LIMIT 1
              ) AS health_status,
              (
                SELECT chc.safe_metadata_json
                FROM connector_health_checks chc
                WHERE chc.social_account_id = sa.id
                ORDER BY chc.checked_at DESC, chc.created_at DESC
                LIMIT 1
              ) AS health_metadata_json
            FROM social_accounts sa
            LEFT JOIN platform_tokens pt
              ON pt.social_account_id = sa.id
             AND pt.revoked_at IS NULL
            GROUP BY sa.id
            ORDER BY sa.platform, sa.display_name
            """
        ).fetchall()

    return [_safe_account_dict(row) for row in rows]


def _safe_account_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "brandProfileId": row["brand_profile_id"],
        "platform": row["platform"],
        "platformAccountId": row["platform_account_id"],
        "displayName": row["display_name"],
        "username": row["username"],
        "profileUrl": row["profile_url"],
        "profileImageUrl": row["profile_image_url"],
        "accountType": row["account_type"],
        "connectionStatus": row["connection_status"],
        "capabilities": _decode_json(row["capabilities_json"], {}),
        "grantedScopes": _decode_json(row["granted_scopes_json"], []),
        "missingScopes": _decode_json(row["missing_scopes_json"], []),
        "requiresReauth": bool(row["requires_reauth"]),
        "lastConnectedAt": row["last_connected_at"],
        "lastValidatedAt": row["last_validated_at"],
        "disconnectedAt": row["disconnected_at"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "tokenStorageStatus": row["token_storage_status"],
        "healthStatus": row["health_status"] or "not_checked",
        "healthMetadata": _decode_json(row["health_metadata_json"], {}),
    }


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _decode_json(raw_value: str | None, fallback: Any) -> Any:
    if not raw_value:
        return fallback
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return fallback
    return decoded if isinstance(decoded, type(fallback)) else fallback


def _validate_platform(platform: str) -> None:
    _validate_choice(platform, SUPPORTED_SOCIAL_PLATFORMS, "platform")


def _validate_choice(value: str, allowed_values: tuple[str, ...], field_name: str) -> None:
    if value not in allowed_values:
        raise SocialConnectionError(
            f"Invalid {field_name} {value!r}. Allowed values: {', '.join(allowed_values)}"
        )


def _reject_secret_metadata(metadata: dict[str, Any]) -> None:
    lower_keys = {key.lower() for key in metadata}
    forbidden = {
        "access_token",
        "refreshtoken",
        "refresh_token",
        "authorization",
        "authorization_code",
        "client_secret",
        "bearer",
        "state",
        "state_hash",
    }
    if lower_keys & forbidden:
        raise SocialConnectionError("safe_metadata must not include tokens, secrets, or OAuth state.")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
